import React from 'react';
import SidebarItem, { SidebarItemData } from '@/components/navigation/SidebarItem';
import './SidebarSection.css';

export interface SidebarSectionData {
    type: 'navigation' | 'context' | 'actions';
    title?: string;
    items: SidebarItemData[];
    collapsible?: boolean;
    collapsed?: boolean;
}

interface SidebarSectionProps {
    section: SidebarSectionData;
    sidebarCollapsed?: boolean;
}

const SidebarSection: React.FC<SidebarSectionProps> = ({
    section,
    sidebarCollapsed = false
}) => {
    if (section.items.length === 0) {
        return null;
    }

    return (
        <div className={`sidebar-section sidebar-section-${section.type}`}>
            {section.title && !sidebarCollapsed && (
                <div className="sidebar-section-title">
                    <h3>{section.title}</h3>
                </div>
            )}

            <div className="sidebar-section-items">
                {section.items.map(item => (
                    <SidebarItem
                        key={item.id}
                        item={item}
                        collapsed={sidebarCollapsed}
                    />
                ))}
            </div>
        </div>
    );
};

export default SidebarSection;
