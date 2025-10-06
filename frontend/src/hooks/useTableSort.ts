import { useState, useMemo } from 'react';
import {
    SortConfig,
    SortDirection,
    SortFieldsConfig,
    createGenericSortFunction
} from '@/utils/sortUtils';

interface UseTableSortProps<T> {
    data: T[];
    defaultSortKey?: keyof T | null;
    defaultSortDirection?: SortDirection;
    fieldsConfig?: SortFieldsConfig<T>;
    lookupMaps?: { [K in keyof T]?: Map<string, string> };
}

interface UseTableSortReturn<T> {
    sortedData: T[];
    sortConfig: SortConfig<T>;
    handleSort: (key: keyof T) => void;
    getSortIndicator: (key: keyof T) => string;
}

export function useTableSort<T>({
    data,
    defaultSortKey = null,
    defaultSortDirection = 'ascending',
    fieldsConfig,
    lookupMaps
}: UseTableSortProps<T>): UseTableSortReturn<T> {
    const [sortConfig, setSortConfig] = useState<SortConfig<T>>({
        key: defaultSortKey,
        direction: defaultSortDirection
    });

    // Create the generic sort function with the provided configuration
    const getSortableValue = useMemo(() => {
        return createGenericSortFunction(fieldsConfig, lookupMaps);
    }, [fieldsConfig, lookupMaps]);

    const handleSort = (key: keyof T) => {
        let direction: SortDirection = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });
    };

    const sortedData = useMemo(() => {
        const sortableItems = [...data];

        if (sortConfig.key) {
            sortableItems.sort((a, b) => {
                const sortableA = getSortableValue(a, sortConfig.key!);
                const sortableB = getSortableValue(b, sortConfig.key!);
                const result = sortableA.compareTo(sortableB);

                // Apply sort direction
                return sortConfig.direction === 'ascending' ? result : -result;
            });
        }

        return sortableItems;
    }, [data, sortConfig, getSortableValue]);

    const getSortIndicator = (key: keyof T): string => {
        if (sortConfig.key === key) {
            return sortConfig.direction === 'ascending' ? ' ↑' : ' ↓';
        }
        return '';
    };

    return {
        sortedData,
        sortConfig,
        handleSort,
        getSortIndicator
    };
}


