"""
Enhanced S3 File Handler for the import/export system.
Provides streaming, compression, retry logic, and large file handling capabilities.
"""
import gzip
import hashlib
import io
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Iterator, Union, BinaryIO, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from utils.s3_dao import get_s3_client, get_object_content, put_object

logger = logging.getLogger(__name__)


@dataclass
class FileStreamingOptions:
    """Configuration options for file streaming operations"""
    chunk_size: int = 8192  # 8KB chunks
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_compression: bool = True
    compression_level: int = 6
    enable_checksum: bool = True
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB max in memory


@dataclass
class FileProcessingResult:
    """Result of file processing operation"""
    success: bool
    file_id: str
    original_size: int
    compressed_size: Optional[int] = None
    checksum: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    retries_used: int = 0


class S3FileStreamer:
    """Enhanced S3 file handler with streaming and compression capabilities"""
    
    def __init__(self, bucket_name: str, options: Optional[FileStreamingOptions] = None):
        self.bucket_name = bucket_name
        self.options = options or FileStreamingOptions()
        self.s3_client = get_s3_client()
        self._processed_files = {}
        
    def stream_file_to_local(self, s3_key: str, local_path: str) -> FileProcessingResult:
        """
        Stream a file from S3 to local storage with retry logic
        
        Args:
            s3_key: S3 object key
            local_path: Local file path to write to
            
        Returns:
            FileProcessingResult with operation details
        """
        start_time = time.time()
        file_id = os.path.basename(s3_key)
        
        for attempt in range(self.options.max_retries + 1):
            try:
                logger.debug(f"Streaming file {s3_key} to {local_path}, attempt {attempt + 1}")
                
                # Get object metadata first
                try:
                    head_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                    original_size = head_response['ContentLength']
                except ClientError as e:
                    # Type assertion since ClientError always has Error key in practice
                    error_response = e.response.get('Error', {})
                    if error_response.get('Code') == 'NoSuchKey':
                        return FileProcessingResult(
                            success=False,
                            file_id=file_id,
                            original_size=0,
                            error=f"File not found: {s3_key}",
                            processing_time=time.time() - start_time,
                            retries_used=attempt
                        )
                    raise
                
                # Stream the file
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                
                checksum = None
                if self.options.enable_checksum:
                    checksum = hashlib.sha256()
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'wb') as local_file:
                    # Stream in chunks
                    for chunk in self._read_chunks(response['Body']):
                        local_file.write(chunk)
                        if checksum:
                            checksum.update(chunk)
                
                return FileProcessingResult(
                    success=True,
                    file_id=file_id,
                    original_size=original_size,
                    checksum=checksum.hexdigest() if checksum else None,
                    processing_time=time.time() - start_time,
                    retries_used=attempt
                )
                
            except (ClientError, BotoCoreError, IOError) as e:
                logger.warning(f"Attempt {attempt + 1} failed for {s3_key}: {str(e)}")
                
                if attempt < self.options.max_retries:
                    time.sleep(self.options.retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    return FileProcessingResult(
                        success=False,
                        file_id=file_id,
                        original_size=0,
                        error=f"Failed after {attempt + 1} attempts: {str(e)}",
                        processing_time=time.time() - start_time,
                        retries_used=attempt
                    )
        
        return FileProcessingResult(
            success=False,
            file_id=file_id,
            original_size=0,
            error="Unexpected error in streaming",
            processing_time=time.time() - start_time,
            retries_used=self.options.max_retries
        )
    
    def stream_file_to_memory(self, s3_key: str) -> Tuple[Optional[bytes], FileProcessingResult]:
        """
        Stream a file from S3 to memory with size limits
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Tuple of (file_content, processing_result)
        """
        start_time = time.time()
        file_id = os.path.basename(s3_key)
        
        try:
            # Check file size first
            head_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            original_size = head_response['ContentLength']
            
            if original_size > self.options.max_memory_usage:
                return None, FileProcessingResult(
                    success=False,
                    file_id=file_id,
                    original_size=original_size,
                    error=f"File too large for memory streaming: {original_size} bytes",
                    processing_time=time.time() - start_time
                )
            
            # Stream to memory
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            
            content = b''
            checksum = hashlib.sha256() if self.options.enable_checksum else None
            
            for chunk in self._read_chunks(response['Body']):
                content += chunk
                if checksum:
                    checksum.update(chunk)
            
            return content, FileProcessingResult(
                success=True,
                file_id=file_id,
                original_size=original_size,
                checksum=checksum.hexdigest() if checksum else None,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return None, FileProcessingResult(
                success=False,
                file_id=file_id,
                original_size=0,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def compress_and_upload(self, local_path: str, s3_key: str, 
                          content_type: str = 'application/octet-stream') -> FileProcessingResult:
        """
        Compress a local file and upload to S3
        
        Args:
            local_path: Local file path
            s3_key: S3 destination key
            content_type: Content type for S3 object
            
        Returns:
            FileProcessingResult with operation details
        """
        start_time = time.time()
        file_id = os.path.basename(local_path)
        
        try:
            original_size = os.path.getsize(local_path)
            
            if self.options.enable_compression:
                # Compress to temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    with open(local_path, 'rb') as input_file:
                        with gzip.open(temp_path, 'wb', compresslevel=self.options.compression_level) as gz_file:
                            while True:
                                chunk = input_file.read(self.options.chunk_size)
                                if not chunk:
                                    break
                                gz_file.write(chunk)
                    
                    compressed_size = os.path.getsize(temp_path)
                    upload_path = temp_path
                    content_encoding = 'gzip'
                    
                finally:
                    # Clean up temp file after upload
                    def cleanup():
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass
                
            else:
                upload_path = local_path
                compressed_size = original_size
                content_encoding = None
            
            # Upload to S3
            extra_args = {'ContentType': content_type}
            if content_encoding:
                extra_args['ContentEncoding'] = content_encoding
            
            with open(upload_path, 'rb') as upload_file:
                self.s3_client.upload_fileobj(
                    upload_file,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs=extra_args
                )
            
            # Cleanup if we used compression
            if self.options.enable_compression:
                cleanup()
            
            return FileProcessingResult(
                success=True,
                file_id=file_id,
                original_size=original_size,
                compressed_size=compressed_size,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return FileProcessingResult(
                success=False,
                file_id=file_id,
                original_size=0,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def batch_download_files(self, file_list: List[Dict[str, str]], 
                           destination_dir: str, max_workers: int = 4) -> List[FileProcessingResult]:
        """
        Download multiple files in parallel
        
        Args:
            file_list: List of dicts with 's3_key' and 'local_filename'
            destination_dir: Local destination directory
            max_workers: Maximum number of concurrent downloads
            
        Returns:
            List of FileProcessingResult objects
        """
        logger.info(f"Starting batch download of {len(file_list)} files to {destination_dir}")
        
        results = []
        os.makedirs(destination_dir, exist_ok=True)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_file = {}
            for file_info in file_list:
                s3_key = file_info['s3_key']
                local_filename = file_info['local_filename']
                local_path = os.path.join(destination_dir, local_filename)
                
                future = executor.submit(self.stream_file_to_local, s3_key, local_path)
                future_to_file[future] = file_info
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.success:
                        logger.debug(f"Successfully downloaded {file_info['s3_key']}")
                    else:
                        logger.error(f"Failed to download {file_info['s3_key']}: {result.error}")
                        
                except Exception as e:
                    logger.error(f"Unexpected error downloading {file_info['s3_key']}: {str(e)}")
                    results.append(FileProcessingResult(
                        success=False,
                        file_id=file_info['s3_key'],
                        original_size=0,
                        error=str(e)
                    ))
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Batch download complete: {success_count}/{len(results)} files successful")
        
        return results
    
    def create_file_archive(self, file_list: List[Dict[str, str]], 
                          archive_path: str) -> FileProcessingResult:
        """
        Create a compressed archive of multiple files
        
        Args:
            file_list: List of dicts with 's3_key' and 'archive_name'
            archive_path: Local path for the created archive
            
        Returns:
            FileProcessingResult with archive creation details
        """
        start_time = time.time()
        
        try:
            import zipfile
            
            total_original_size = 0
            files_processed = 0
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=self.options.compression_level) as zipf:
                
                for file_info in file_list:
                    s3_key = file_info['s3_key']
                    archive_name = file_info['archive_name']
                    
                    try:
                        # Stream file content to memory if small enough
                        content, result = self.stream_file_to_memory(s3_key)
                        
                        if result.success and content:
                            zipf.writestr(archive_name, content)
                            total_original_size += result.original_size
                            files_processed += 1
                            
                        else:
                            logger.warning(f"Skipping file {s3_key}: {result.error}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {s3_key} for archive: {str(e)}")
                        continue
            
            compressed_size = os.path.getsize(archive_path)
            
            return FileProcessingResult(
                success=True,
                file_id=f"archive_{files_processed}_files",
                original_size=total_original_size,
                compressed_size=compressed_size,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return FileProcessingResult(
                success=False,
                file_id="archive_creation",
                original_size=0,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _read_chunks(self, stream: BinaryIO) -> Iterator[bytes]:
        """Read stream in chunks"""
        while True:
            chunk = stream.read(self.options.chunk_size)
            if not chunk:
                break
            yield chunk
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed files"""
        return {
            'files_processed': len(self._processed_files),
            'total_bytes_processed': sum(f.get('size', 0) for f in self._processed_files.values()),
            'average_processing_time': sum(f.get('time', 0) for f in self._processed_files.values()) / 
                                     max(len(self._processed_files), 1),
            'success_rate': sum(1 for f in self._processed_files.values() if f.get('success', False)) / 
                           max(len(self._processed_files), 1) * 100
        }


class ExportPackageBuilder:
    """Enhanced package builder with streaming and compression capabilities"""
    
    def __init__(self, bucket_name: str, streaming_options: Optional[FileStreamingOptions] = None):
        self.bucket_name = bucket_name
        self.file_streamer = S3FileStreamer(bucket_name, streaming_options)
        self.compression_enabled = streaming_options.enable_compression if streaming_options else True
        
    def build_package_with_streaming(self, export_data: Dict[str, Any], 
                                   transaction_files: List[Dict[str, Any]],
                                   package_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Build export package with streaming file handling
        
        Args:
            export_data: Collected export data
            transaction_files: List of transaction file metadata
            package_dir: Directory to build package in
            
        Returns:
            Tuple of (package_path, processing_summary)
        """
        try:
            logger.info(f"Building export package with streaming in {package_dir}")
            
            # Create package structure
            data_dir = os.path.join(package_dir, "data")
            files_dir = os.path.join(package_dir, "files")
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(files_dir, exist_ok=True)
            
            processing_summary = {
                'data_files_created': 0,
                'transaction_files_processed': 0,
                'transaction_files_failed': 0,
                'total_original_size': 0,
                'total_compressed_size': 0,
                'compression_ratio': 0.0,
                'processing_time': 0.0
            }
            
            start_time = time.time()
            
            # Write data files with optional compression
            data_files = {
                'accounts.json': export_data.get('accounts', []),
                'transactions.json': export_data.get('transactions', []),
                'categories.json': export_data.get('categories', []),
                'file_maps.json': export_data.get('file_maps', []),
                'transaction_files.json': export_data.get('transaction_files', [])
            }
            
            if export_data.get('analytics'):
                data_files['analytics.json'] = export_data['analytics']
            
            for filename, data in data_files.items():
                self._write_data_file(os.path.join(data_dir, filename), data)
                processing_summary['data_files_created'] += 1
            
            # Process transaction files with streaming
            if transaction_files:
                file_results = self._process_transaction_files_streaming(transaction_files, files_dir)
                
                for result in file_results:
                    if result.success:
                        processing_summary['transaction_files_processed'] += 1
                        processing_summary['total_original_size'] += result.original_size
                        if result.compressed_size:
                            processing_summary['total_compressed_size'] += result.compressed_size
                    else:
                        processing_summary['transaction_files_failed'] += 1
            
            # Calculate compression ratio
            if processing_summary['total_original_size'] > 0:
                processing_summary['compression_ratio'] = (
                    (processing_summary['total_original_size'] - processing_summary['total_compressed_size']) /
                    processing_summary['total_original_size']
                ) * 100
            
            processing_summary['processing_time'] = time.time() - start_time
            
            logger.info(f"Package building complete: {processing_summary}")
            
            return package_dir, processing_summary
            
        except Exception as e:
            logger.error(f"Failed to build package with streaming: {str(e)}")
            raise
    
    def _write_data_file(self, file_path: str, data: Any):
        """Write data file with optional compression"""
        import json
        
        if self.compression_enabled:
            with gzip.open(file_path + '.gz', 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
    
    def _process_transaction_files_streaming(self, transaction_files: List[Dict[str, Any]], 
                                           files_dir: str) -> List[FileProcessingResult]:
        """Process transaction files using streaming"""
        # Prepare file list for batch processing
        file_list = []
        for file_info in transaction_files:
            if not file_info.get('s3Key'):
                continue
                
            file_id = str(file_info['fileId'])  # Convert UUID to string for path operations
            filename = file_info.get('fileName', f'file_{file_id}')
            
            # Create subdirectory for each file
            file_subdir = os.path.join(files_dir, file_id)
            os.makedirs(file_subdir, exist_ok=True)
            
            file_list.append({
                's3_key': file_info['s3Key'],
                'local_filename': os.path.join(file_id, filename)
            })
        
        # Process files in batches
        if file_list:
            return self.file_streamer.batch_download_files(file_list, files_dir, max_workers=4)
        else:
            return []


@contextmanager
def temporary_export_workspace(base_dir: Optional[str] = None):
    """Context manager for temporary export workspace"""
    if base_dir:
        workspace = tempfile.mkdtemp(dir=base_dir)
    else:
        workspace = tempfile.mkdtemp()
    
    try:
        yield workspace
    finally:
        import shutil
        try:
            shutil.rmtree(workspace)
        except OSError as e:
            logger.warning(f"Failed to cleanup temporary workspace {workspace}: {str(e)}") 