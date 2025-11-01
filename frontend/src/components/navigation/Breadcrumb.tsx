import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, UIMatch } from 'react-router-dom';
import { createLogger } from '@/utils/logger';
import './Breadcrumb.css';

const logger = createLogger('Breadcrumb');

interface BreadcrumbProps {
    className?: string;
    maxItems?: number;
    matches: UIMatch[];
    mode?: 'path' | 'history'; // 'path' = reflect current URL, 'history' = accumulate navigation
}

/**
 * Breadcrumb Component
 * 
 * Renders breadcrumbs based on React Router's useMatches() hook.
 * Each route can define a `handle.breadcrumb` function that returns a React node.
 * 
 * Modes:
 * - path (default): Breadcrumbs reflect current URL hierarchy, update automatically on route change
 * - history: Breadcrumbs accumulate as you navigate, persist when going back, truncate when clicking middle
 * 
 * Features:
 * - Automatic breadcrumb generation from route hierarchy
 * - Collapse long paths (shows first + last N items)
 * - Keyboard shortcuts (Alt + Arrow keys)
 * - Context menus for advanced navigation
 */
const Breadcrumb: React.FC<BreadcrumbProps> = ({
    className = '',
    maxItems = 4,
    matches,
    mode = 'path'
}) => {
    const navigate = useNavigate();
    const [showFullPath, setShowFullPath] = useState(false);
    const [contextMenuOpen, setContextMenuOpen] = useState<number | null>(null);
    const contextMenuRef = useRef<HTMLDivElement>(null);

    // History mode: maintain breadcrumb stack
    const [breadcrumbHistory, setBreadcrumbHistory] = useState<UIMatch[]>([]);
    const previousPathRef = useRef<string>('');

    // Filter matches that have breadcrumb handles
    const currentBreadcrumbs = matches.filter(
        (match) => match.handle && (match.handle as any).breadcrumb
    );

    // History mode: Update breadcrumb history based on navigation
    useEffect(() => {
        if (mode !== 'history') return;

        const currentPath = matches[matches.length - 1]?.pathname || '/';
        const previousPath = previousPathRef.current;

        // First render or significant change - initialize history
        if (breadcrumbHistory.length === 0) {
            setBreadcrumbHistory(currentBreadcrumbs);
            previousPathRef.current = currentPath;
            return;
        }

        // Check if current path is an extension of a path in history
        const matchIndex = breadcrumbHistory.findIndex(
            (historyMatch) => historyMatch.pathname === currentPath
        );

        if (matchIndex >= 0) {
            // Clicked on an existing breadcrumb - truncate history
            setBreadcrumbHistory(breadcrumbHistory.slice(0, matchIndex + 1));
        } else if (currentPath.startsWith(previousPath) && currentPath !== previousPath) {
            // Navigating deeper (forward) - append new breadcrumbs
            const newCrumbs = currentBreadcrumbs.filter(
                (crumb) => !breadcrumbHistory.some(
                    (existing) => existing.pathname === crumb.pathname
                )
            );
            setBreadcrumbHistory([...breadcrumbHistory, ...newCrumbs]);
        } else if (previousPath.startsWith(currentPath) && currentPath !== previousPath) {
            // Navigating backward (e.g., browser back button) - find matching point
            const matchingIndex = breadcrumbHistory.findIndex(
                (historyMatch) => historyMatch.pathname === currentPath
            );
            if (matchingIndex >= 0) {
                setBreadcrumbHistory(breadcrumbHistory.slice(0, matchingIndex + 1));
            }
        } else {
            // Navigating to unrelated path - reset to current breadcrumbs
            setBreadcrumbHistory(currentBreadcrumbs);
        }

        previousPathRef.current = currentPath;
    }, [matches, mode, currentBreadcrumbs.length]); // eslint-disable-line react-hooks/exhaustive-deps

    // Choose which breadcrumbs to display based on mode
    const breadcrumbMatches = mode === 'history' ? breadcrumbHistory : currentBreadcrumbs;


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
                navigate(-1);
            }

            // Alt + Home = Go to root (Home)
            if (event.altKey && event.key === 'Home') {
                event.preventDefault();
                navigate('/home');
            }

            // Alt + Number = Jump to specific level
            if (event.altKey && /^[1-9]$/.test(event.key)) {
                event.preventDefault();
                const level = parseInt(event.key) - 1;
                if (level < breadcrumbMatches.length) {
                    const match = breadcrumbMatches[level];
                    navigate(match.pathname);
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [breadcrumbMatches, navigate]);

    // Determine which items to show
    const visibleItems = showFullPath || breadcrumbMatches.length <= maxItems
        ? breadcrumbMatches
        : [
            breadcrumbMatches[0], // Always show root
            ...breadcrumbMatches.slice(-maxItems + 1) // Show last few items
        ];

    const hasHiddenItems = !showFullPath && breadcrumbMatches.length > maxItems;

    const handleItemClick = (match: UIMatch, index: number, event: React.MouseEvent) => {
        event.preventDefault();

        // Middle click or Ctrl+click = open in new tab (future feature)
        if (event.button === 1 || event.ctrlKey) {
            // TODO: Implement new tab navigation
            logger.debug('Open in new tab', { pathname: match.pathname });
            return;
        }

        // Right click = show context menu
        if (event.button === 2) {
            setContextMenuOpen(index);
            return;
        }

        // In history mode, truncate history when clicking a breadcrumb
        if (mode === 'history') {
            const actualIndex = hasHiddenItems && index > 0
                ? breadcrumbMatches.length - (visibleItems.length - index)
                : index;
            setBreadcrumbHistory(breadcrumbMatches.slice(0, actualIndex + 1));
        }

        // Regular click = navigate
        navigate(match.pathname);
    };

    const handleContextMenu = (event: React.MouseEvent, index: number) => {
        event.preventDefault();
        setContextMenuOpen(index);
    };

    const copyPath = (upToIndex: number) => {
        const path = breadcrumbMatches.slice(0, upToIndex + 1)
            .map(match => {
                // Extract text from breadcrumb React node
                const breadcrumb = (match.handle as any).breadcrumb(match);
                // For Link components, get the children text
                if (breadcrumb?.props?.children) {
                    return breadcrumb.props.children;
                }
                return match.pathname.split('/').pop() || '';
            })
            .join(' > ');
        navigator.clipboard.writeText(path);
        setContextMenuOpen(null);
    };

    const copyUrl = (match: UIMatch) => {
        const url = window.location.origin + match.pathname;
        navigator.clipboard.writeText(url);
        setContextMenuOpen(null);
    };

    if (breadcrumbMatches.length <= 1) {
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
                        title={`${breadcrumbMatches.length - maxItems + 1} hidden items`}
                    >
                        {showFullPath ? '←' : '...'}
                    </button>
                )}

                {/* Breadcrumb items */}
                <ol className="breadcrumb-list">
                    {visibleItems.map((match, index) => {
                        const isLast = index === visibleItems.length - 1;
                        const actualIndex = hasHiddenItems && index > 0
                            ? breadcrumbMatches.length - (visibleItems.length - index)
                            : index;

                        const actualMatch = breadcrumbMatches[actualIndex];
                        const breadcrumbContent = (actualMatch.handle as any).breadcrumb(actualMatch);

                        return (
                            <li
                                key={`${actualMatch.id}-${actualIndex}`}
                                className={`breadcrumb-item ${isLast ? 'current' : ''}`}
                            >
                                {!isLast ? (
                                    <>
                                        <button
                                            className="breadcrumb-link"
                                            onClick={(e) => handleItemClick(actualMatch, actualIndex, e)}
                                            onContextMenu={(e) => handleContextMenu(e, actualIndex)}
                                            onMouseDown={(e) => {
                                                if (e.button === 1) { // Middle click
                                                    handleItemClick(actualMatch, actualIndex, e);
                                                }
                                            }}
                                            title={`Navigate to ${actualMatch.pathname}`}
                                            aria-label={`Navigate to breadcrumb ${actualIndex + 1}`}
                                        >
                                            {breadcrumbContent}
                                        </button>
                                        <span className="breadcrumb-separator" aria-hidden="true">
                                            /
                                        </span>
                                    </>
                                ) : (
                                    <span
                                        className="breadcrumb-current"
                                        aria-current="page"
                                        title={`Current: ${actualMatch.pathname}`}
                                    >
                                        {breadcrumbContent}
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
                                            onClick={() => {
                                                navigate(actualMatch.pathname);
                                                setContextMenuOpen(null);
                                            }}
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
                                            onClick={() => copyUrl(actualMatch)}
                                            role="menuitem"
                                        >
                                            Copy URL
                                        </button>
                                        {actualIndex > 0 && (
                                            <button
                                                onClick={() => {
                                                    navigate(breadcrumbMatches[actualIndex - 1].pathname);
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
                    {breadcrumbMatches.length > 1 && (
                        <button
                            className="breadcrumb-back"
                            onClick={() => navigate(-1)}
                            title="Go back one level (Alt + ←)"
                            aria-label="Go back one level"
                        >
                            ←
                        </button>
                    )}

                    {breadcrumbMatches.length > 2 && (
                        <button
                            className="breadcrumb-home"
                            onClick={() => navigate('/home')}
                            title="Go to root (Alt + Home)"
                            aria-label="Go to home"
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
