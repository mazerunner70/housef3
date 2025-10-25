/**
 * Configuration for FZIP Backup & Restore sidebar content
 */

import { SidebarContentConfig } from '@/components/navigation/sidebar-content/types';
import { createNavItem } from '@/components/navigation/sidebar-content/SidebarConfigFactory';
import { mainNavigationSection } from '@/components/navigation/sidebar-content/configs/sharedNavigation';

export const fzipConfig: SidebarContentConfig = {
    sections: [
        mainNavigationSection,
        {
            type: 'context',
            title: 'FZIP Operations',
            items: [
                createNavItem(
                    'fzip-info',
                    'About FZIP',
                    '/fzip',
                    'ℹ️'
                )
            ],
            collapsible: true,
            collapsed: false
        }
    ]
};



