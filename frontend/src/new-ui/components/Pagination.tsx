import React from 'react';
import './Pagination.css';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  itemsPerPage?: number; // Optional, for future use or display
  totalItems?: number; // Optional, for future use or display
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
}) => {
  if (totalPages <= 1) {
    return null; // Don't render pagination if there's only one page or less
  }

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

  // Basic page numbers - can be made more sophisticated with ellipses for many pages
  const pageNumbers = [];
  for (let i = 1; i <= totalPages; i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="pagination-container">
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
        disabled={currentPage === totalPages}
        className="pagination-button next-button"
      >
        Next
      </button>
    </div>
  );
};

export default Pagination; 