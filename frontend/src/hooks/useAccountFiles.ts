import { useState, useEffect, useCallback } from 'react';
import {
    ServiceFile, // Assuming this will be exported from FileService
    listAssociatedFiles,
    listUnlinkedFiles,
    linkFileToAccount,
    unlinkFileFromAccount
} from '../../services/FileService'; // Correct path to services

// Placeholder types - these will need to align with actual backend API response
// and potentially a FileService.ts
interface ServiceTransactionFile {
  // Assuming fields from docs/new_ui_accounts_view.md
  fileId: string;
  fileName: string;
  uploadDate: string; // Or Date/number
  status?: string; // e.g., "Processed", "Pending"
  transactionCount?: number;
  // Fields for unlinked files might be simpler
}

export interface UIAssociatedFile {
  id: string;
  name: string;
  uploadDate: string;
  status: string;
  transactionCount: number;
}

export interface UIUnlinkedFile {
  id: string;
  name: string;
  uploadDate: string;
}

// Placeholder mapping functions - adjust based on actual ServiceFile structure
const mapServiceFileToUIAssociatedFile = (serviceFile: ServiceFile): UIAssociatedFile => ({
  id: serviceFile.fileId,
  name: serviceFile.fileName,
  uploadDate: serviceFile.uploadDate, // TODO: Format if necessary
  status: serviceFile.status || 'N/A',
  transactionCount: serviceFile.transactionCount || 0,
});

const mapServiceFileToUIUnlinkedFile = (serviceFile: ServiceFile): UIUnlinkedFile => ({
  id: serviceFile.fileId,
  name: serviceFile.fileName,
  uploadDate: serviceFile.uploadDate, // TODO: Format if necessary
});

const useAccountFiles = (accountId: string | null) => {
  const [associatedFiles, setAssociatedFiles] = useState<UIAssociatedFile[]>([]);
  const [unlinkedFiles, setUnlinkedFiles] = useState<UIUnlinkedFile[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = useCallback(async () => {
    if (!accountId) {
      // If no accountId, we might still want to fetch unlinked files
      // Or, if this hook is strictly for an account context, clear associated files
      setAssociatedFiles([]); 
      // Decide if unlinked files should be fetched when no accountId is active
      // For now, let's fetch unlinked files regardless of a selected accountId, as they are user-specific.
    } else {
        // Clear associated files before fetching for a new accountId if it changes
        setAssociatedFiles([]);
    }
    // Always fetch unlinked files as they are user-specific, not account-specific
    setUnlinkedFiles([]); 

    setLoading(true);
    setError(null);
    try {
      const promises = [];
      if (accountId) {
        promises.push(listAssociatedFiles(accountId));
      } else {
        promises.push(Promise.resolve([])); // Empty promise if no accountId for associated files
      }
      promises.push(listUnlinkedFiles());

      const [associatedResult, unlinkedResult] = await Promise.all(promises);

      if (accountId && associatedResult) {
        setAssociatedFiles((associatedResult as ServiceFile[]).map(mapServiceFileToUIAssociatedFile));
      }
      if (unlinkedResult) {
        setUnlinkedFiles((unlinkedResult as ServiceFile[]).map(mapServiceFileToUIUnlinkedFile));
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred while fetching files');
      console.error("Error fetching files:", err);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]); // fetchFiles dependency is correct due to useCallback wrapping it

  const linkFile = useCallback(async (fileId: string, targetAccountId: string) => {
    if (!targetAccountId) {
        setError('No account selected to link the file to.');
        return;
    }
    setLoading(true);
    try {
      await linkFileToAccount(fileId, targetAccountId);
      await fetchFiles(); // Refresh data after linking
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error linking file');
      console.error("Error linking file:", err);
    } finally {
      setLoading(false);
    }
  }, [fetchFiles]); // fetchFiles is a dependency of linkFile

  const unlinkFile = useCallback(async (fileId: string) => {
    setLoading(true);
    try {
      await unlinkFileFromAccount(fileId);
      await fetchFiles(); // Refresh data after unlinking
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error unlinking file');
      console.error("Error unlinking file:", err);
    } finally {
      setLoading(false);
    }
  }, [fetchFiles]); // fetchFiles is a dependency of unlinkFile

  return { associatedFiles, unlinkedFiles, loading, error, linkFile, unlinkFile, refetchFiles: fetchFiles };
};

export default useAccountFiles; 