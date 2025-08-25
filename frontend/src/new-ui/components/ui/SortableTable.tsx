import React from 'react';
import { useTableSort } from '@/new-ui/hooks/useTableSort';
import { SortFieldsConfig } from '@/utils/sortUtils';

interface SortableTableProps<T> {
    data: T[];
    columns: Array<{
        key: keyof T;
        label: string;
        render?: (value: any, item: T) => React.ReactNode;
    }>;
    fieldsConfig?: SortFieldsConfig<T>;
    lookupMaps?: { [K in keyof T]?: Map<string, string> };
    defaultSortKey?: keyof T;
    defaultSortDirection?: 'ascending' | 'descending';
}

/**
 * Sortable table component that automatically detects field types
 * and applies appropriate sorting algorithms based on data type.
 * 
 * Features:
 * - Automatic type detection (string, number, decimal, date, boolean, lookup)
 * - Click column headers to sort
 * - Visual sort indicators (↑/↓)
 * - Support for lookup fields (e.g., ID -> display name)
 * - Customizable field type configuration
 * 
 * Example usage:
 * ```tsx
 * interface User {
 *   id: string;
 *   name: string;
 *   age: number;
 *   createdAt: number; // timestamp
 *   isActive: boolean;
 * }
 * 
 * <SortableTable
 *   data={users}
 *   columns={[
 *     { key: 'name', label: 'Name' },
 *     { key: 'age', label: 'Age' },
 *     { key: 'createdAt', label: 'Created' },
 *     { key: 'isActive', label: 'Active' }
 *   ]}
 *   defaultSortKey="name"
 * />
 * ```
 */
export function SortableTable<T extends Record<string, any>>({
    data,
    columns,
    fieldsConfig,
    lookupMaps,
    defaultSortKey,
    defaultSortDirection = 'ascending'
}: SortableTableProps<T>) {
    const { sortedData, handleSort, getSortIndicator } = useTableSort({
        data,
        defaultSortKey,
        defaultSortDirection,
        fieldsConfig,
        lookupMaps
    });

    return (
        <table className="sortable-table">
            <thead>
                <tr>
                    {columns.map((column) => (
                        <th
                            key={String(column.key)}
                            onClick={() => handleSort(column.key)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSort(column.key)}
                            tabIndex={0}
                            role="button"
                            aria-label={`Sort by ${column.label}`}
                            style={{ cursor: 'pointer' }}
                        >
                            {column.label}{getSortIndicator(column.key)}
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {sortedData.map((item, index) => (
                    <tr key={index}>
                        {columns.map((column) => (
                            <td key={String(column.key)}>
                                {column.render
                                    ? column.render(item[column.key], item)
                                    : String(item[column.key] || '')
                                }
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

export default SortableTable;
