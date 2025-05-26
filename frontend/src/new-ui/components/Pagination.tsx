import React, { useState } from 'react';
import './Pagination.css';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  itemsPerPage: number;
  onPageSizeChange: (newPageSize: number) => void;
  totalItems?: number;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  itemsPerPage,
  onPageSizeChange,
}) => {
  const [pageSizeInput, setPageSizeInput] = useState<string>(itemsPerPage.toString());

  React.useEffect(() => {
    setPageSizeInput(itemsPerPage.toString());
  }, [itemsPerPage]);

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageSizeInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageSizeInput(e.target.value);
  };

  const handlePageSizeSubmit = () => {
    const newSize = parseInt(pageSizeInput, 10);
    if (!isNaN(newSize) && newSize > 0) {
      onPageSizeChange(newSize);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handlePageSizeSubmit();
    }
  };

  const pageNumbers = [];
  for (let i = 1; i <= totalPages; i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="pagination-container">
      {totalPages > 1 && (
        <>
          <button 
            onClick={handlePrevious} 
            disabled={currentPage === 1}
            className="pagination-button prev-button"
          >
            Previous
          </button>
          {pageNumbers.map(number => (
            <button 
              key={number} 
              onClick={() => onPageChange(number)} 
              className={`pagination-button page-number ${currentPage === number ? 'active' : ''}`}
            >
              {number}
            </button>
          ))}
          <button 
            onClick={handleNext} 
            disabled={currentPage === totalPages || totalPages === 0}
            className="pagination-button next-button"
          >
            Next
          </button>
        </>
      )}
      <div className="page-size-changer">
        <label htmlFor="pageSizeInput" className="page-size-label">Items per page: </label>
        <input 
          type="number" 
          id="pageSizeInput" 
          value={pageSizeInput} 
          onChange={handlePageSizeInputChange} 
          onBlur={handlePageSizeSubmit}
          onKeyDown={handleKeyDown}
          min="1"
          className="page-size-input"
        />
      </div>
    </div>
  );
};

export default Pagination; 