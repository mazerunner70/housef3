import React, { useState, useRef, useEffect } from 'react';
import { useNavigationStore, BreadcrumbItem } from '@/stores/navigationStore';
import './Breadcrumb.css';

interface BreadcrumbProps {
    className?: string;
    maxItems?: number;
    showDropdown?: boolean;
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({
    className = '',
    maxItems = 4,
    showDropdown = true
}) => {
    const { breadcrumb, goBack } = useNavigationStore();
    const [showFullPath, setShowFullPath] = useState(false);
    const [contextMenuOpen, setContextMenuOpen] = useState<number | null>(null);
    const contextMenuRef = useRef<HTMLDivElement>(null);

    // Close context menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
                setContextMenuOpen(null);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Handle keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            // Alt + Left Arrow = Go back one level
            if (event.altKey && event.key === 'ArrowLeft') {
                event.preventDefault();
                goBack();
            }

            // Alt + Home = Go to root (Accounts)
            if (event.altKey && event.key === 'Home') {
                event.preventDefault();
                if (breadcrumb.length > 0) {
                    breadcrumb[0].action();
                }
            }

            // Alt + Number = Jump to specific level
            if (event.altKey && /^[1-9]$/.test(event.key)) {
                event.preventDefault();
                const level = parseInt(event.key) - 1;
                if (level < breadcrumb.length) {
                    breadcrumb[level].action();
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [breadcrumb, goBack]);

    // Determine which items to show
    const visibleItems = showFullPath || breadcrumb.length <= maxItems
        ? breadcrumb
        : [
            breadcrumb[0], // Always show root
            ...breadcrumb.slice(-maxItems + 1) // Show last few items
        ];

    const hasHiddenItems = !showFullPath && breadcrumb.length > maxItems;

    const handleItemClick = (item: BreadcrumbItem, index: number, event: React.MouseEvent) => {
        event.preventDefault();

        // Middle click or Ctrl+click = open in new tab (future feature)
        if (event.button === 1 || event.ctrlKey) {
            // TODO: Implement new tab navigation
            console.log('Open in new tab:', item.label);
            return;
        }

        // Right click = show context menu
        if (event.button === 2) {
            setContextMenuOpen(index);
            return;
        }

        // Regular click = navigate
        item.action();
    };

    const handleContextMenu = (event: React.MouseEvent, index: number) => {
        event.preventDefault();
        setContextMenuOpen(index);
    };

    const copyPath = (upToIndex: number) => {
        const path = breadcrumb.slice(0, upToIndex + 1).map(item => item.label).join(' > ');
        navigator.clipboard.writeText(path);
        setContextMenuOpen(null);
    };

    const copyUrl = (upToIndex: number) => {
        // This would copy the URL up to this breadcrumb level
        // Implementation depends on the routing system
        const url = window.location.origin + window.location.pathname;
        navigator.clipboard.writeText(url);
        setContextMenuOpen(null);
    };

    if (breadcrumb.length <= 1) {
        return null; // Don't show breadcrumb for single item
    }

    return (
        <nav
            className={`breadcrumb ${className}`}
            aria-label="Breadcrumb navigation"
            role="navigation"
        >
            <div className="breadcrumb-container">
                {/* Expand/collapse button for long paths */}
                {hasHiddenItems && (
                    <button
                        className="breadcrumb-expand"
                        onClick={() => setShowFullPath(!showFullPath)}
                        aria-label={showFullPath ? 'Collapse breadcrumb' : 'Expand breadcrumb'}
                        title={`${breadcrumb.length - maxItems + 1} hidden items`}
                    >
                        {showFullPath ? '←' : '...'}
                    </button>
                )}

                {/* Breadcrumb items */}
                <ol className="breadcrumb-list">
                    {visibleItems.map((item, index) => {
                        const isLast = index === visibleItems.length - 1;
                        const actualIndex = hasHiddenItems && index > 0
                            ? breadcrumb.length - (visibleItems.length - index)
                            : index;

                        return (
                            <li
                                key={`${item.level}-${item.label}`}
                                className={`breadcrumb-item ${isLast ? 'current' : ''}`}
                            >
                                {!isLast ? (
                                    <>
                                        <button
                                            className="breadcrumb-link"
                                            onClick={(e) => handleItemClick(item, actualIndex, e)}
                                            onContextMenu={(e) => handleContextMenu(e, actualIndex)}
                                            onMouseDown={(e) => {
                                                if (e.button === 1) { // Middle click
                                                    handleItemClick(item, actualIndex, e);
                                                }
                                            }}
                                            title={`Navigate to ${item.label} (Level ${item.level + 1})`}
                                            aria-label={`Navigate to ${item.label}`}
                                        >
                                            {item.label}
                                        </button>
                                        <span className="breadcrumb-separator" aria-hidden="true">
                                            /
                                        </span>
                                    </>
                                ) : (
                                    <span
                                        className="breadcrumb-current"
                                        aria-current="page"
                                        title={`Current: ${item.label}`}
                                    >
                                        {item.label}
                                    </span>
                                )}

                                {/* Context menu */}
                                {contextMenuOpen === actualIndex && (
                                    <div
                                        ref={contextMenuRef}
                                        className="breadcrumb-context-menu"
                                        role="menu"
                                    >
                                        <button
                                            onClick={() => item.action()}
                                            role="menuitem"
                                        >
                                            Navigate Here
                                        </button>
                                        <button
                                            onClick={() => copyPath(actualIndex)}
                                            role="menuitem"
                                        >
                                            Copy Path
                                        </button>
                                        <button
                                            onClick={() => copyUrl(actualIndex)}
                                            role="menuitem"
                                        >
                                            Copy URL
                                        </button>
                                        {actualIndex > 0 && (
                                            <button
                                                onClick={() => {
                                                    breadcrumb[actualIndex - 1].action();
                                                    setContextMenuOpen(null);
                                                }}
                                                role="menuitem"
                                            >
                                                Go Back One Level
                                            </button>
                                        )}
                                    </div>
                                )}
                            </li>
                        );
                    })}
                </ol>

                {/* Quick navigation buttons */}
                <div className="breadcrumb-actions">
                    {breadcrumb.length > 1 && (
                        <button
                            className="breadcrumb-back"
                            onClick={goBack}
                            title="Go back one level (Alt + ←)"
                            aria-label="Go back one level"
                        >
                            ←
                        </button>
                    )}

                    {breadcrumb.length > 2 && (
                        <button
                            className="breadcrumb-home"
                            onClick={() => breadcrumb[0].action()}
                            title="Go to root (Alt + Home)"
                            aria-label="Go to accounts root"
                        >
                            🏠
                        </button>
                    )}
                </div>
            </div>

            {/* Keyboard shortcuts help (hidden, for screen readers) */}
            <div className="sr-only" aria-live="polite">
                Keyboard shortcuts: Alt + ← (back), Alt + Home (root), Alt + 1-9 (jump to level)
            </div>
        </nav>
    );
};

export default Breadcrumb;
