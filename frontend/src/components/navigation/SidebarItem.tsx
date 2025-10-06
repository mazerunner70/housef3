import React from 'react';
import './SidebarItem.css';

export interface SidebarItemData {
    id: string;
    label: string;
    icon?: string;
    active: boolean;
    onClick: () => void;
    children?: SidebarItemData[];
    level?: number;
}

interface SidebarItemProps {
    item: SidebarItemData;
    collapsed?: boolean;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ item, collapsed = false }) => {
    const handleClick = () => {
        item.onClick();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            item.onClick();
        }
    };

    return (
        <div className="sidebar-item-container">
            <div
                className={`sidebar-item ${item.active ? 'active' : ''} ${collapsed ? 'collapsed' : ''}`}
                onClick={handleClick}
                onKeyDown={handleKeyDown}
                tabIndex={0}
                role="button"
                aria-label={item.label}
                style={{ paddingLeft: `${(item.level || 0) * 16 + 12}px` }}
            >
                {item.icon && (
                    <span className="sidebar-item-icon" aria-hidden="true">
                        {item.icon}
                    </span>
                )}
                {!collapsed && (
                    <span className="sidebar-item-label">{item.label}</span>
                )}
            </div>

            {!collapsed && item.children && item.children.length > 0 && (
                <div className="sidebar-item-children">
                    {item.children.map(child => (
                        <SidebarItem
                            key={child.id}
                            item={{ ...child, level: (item.level || 0) + 1 }}
                            collapsed={collapsed}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default SidebarItem;
