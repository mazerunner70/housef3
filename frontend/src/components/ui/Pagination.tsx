import React from 'react';
import './Pagination.css';

interface LoadMoreProps {
    hasMore: boolean;
    isLoading: boolean;
    onLoadMore: () => void;
    itemsLoaded: number;
    pageSize: number;
    onPageSizeChange: (newPageSize: number) => void;
}

const LoadMore: React.FC<LoadMoreProps> = ({
    hasMore,
    isLoading,
    onLoadMore,
    itemsLoaded,
    pageSize,
    onPageSizeChange
}) => {
    const [pageSizeInput, setPageSizeInput] = React.useState<string>(pageSize.toString());

    React.useEffect(() => {
        setPageSizeInput(pageSize.toString());
    }, [pageSize]);

    const handlePageSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setPageSizeInput(e.target.value);
    };

    const handlePageSizeSubmit = () => {
        const newSize = parseInt(pageSizeInput, 10);
        if (!isNaN(newSize) && newSize > 0 && newSize <= 1000) {
            onPageSizeChange(newSize);
        }
    };

    return (
        <div className="load-more-container">
            <div className="results-info">
                Showing {itemsLoaded.toLocaleString()} transactions
            </div>

            {hasMore && (
                <button
                    onClick={onLoadMore}
                    disabled={isLoading}
                    className="load-more-button"
                >
                    {isLoading ? 'Loading...' : 'Load More'}
                </button>
            )}

            <div className="page-size-changer">
                <label>Batch size:</label>
                <input
                    type="number"
                    value={pageSizeInput}
                    onChange={handlePageSizeChange}
                    onBlur={handlePageSizeSubmit}
                    onKeyDown={(e) => e.key === 'Enter' && handlePageSizeSubmit()}
                    min="1"
                    max="1000"
                    className="page-size-input"
                />
            </div>
        </div>
    );
};

export default LoadMore;

