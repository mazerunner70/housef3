import { Decimal } from 'decimal.js';

// Comparable interface for type-safe sorting
export interface Comparable<T> {
    compareTo(other: T): number;
}

// Sortable value wrappers that implement compareTo
export class SortableString implements Comparable<SortableString> {
    constructor(private value: string) { }
    compareTo(other: SortableString): number {
        return this.value.localeCompare(other.value);
    }
}

export class SortableNumber implements Comparable<SortableNumber> {
    constructor(private value: number) { }
    compareTo(other: SortableNumber): number {
        return this.value - other.value;
    }
}

export class SortableDecimal implements Comparable<SortableDecimal> {
    constructor(private value: Decimal) { }
    compareTo(other: SortableDecimal): number {
        return this.value.comparedTo(other.value);
    }
}

export class SortableDate implements Comparable<SortableDate> {
    constructor(private value: number | Date) { }
    compareTo(other: SortableDate): number {
        const thisTime = typeof this.value === 'number' ? this.value : this.value.getTime();
        const otherTime = typeof other.value === 'number' ? other.value : other.value.getTime();
        return thisTime - otherTime;
    }
}

export class SortableBoolean implements Comparable<SortableBoolean> {
    constructor(private value: boolean) { }
    compareTo(other: SortableBoolean): number {
        return Number(this.value) - Number(other.value);
    }
}

export class SortableLookup implements Comparable<SortableLookup> {
    constructor(private id: string | undefined, private lookupMap: Map<string, string>) { }
    compareTo(other: SortableLookup): number {
        const thisName = this.lookupMap.get(this.id || '') || 'N/A';
        const otherName = other.lookupMap.get(other.id || '') || 'N/A';
        return thisName.localeCompare(otherName);
    }
}

export type SortDirection = 'ascending' | 'descending';

export interface SortConfig<T> {
    key: keyof T | null;
    direction: SortDirection;
}

// Field type detection and sorting algorithm selection
export type FieldType = 'string' | 'number' | 'decimal' | 'date' | 'boolean' | 'lookup';

export interface FieldConfig {
    type: FieldType;
    lookupMap?: Map<string, string>; // For lookup fields like accountId -> accountName
}

export type SortFieldsConfig<T> = {
    [K in keyof T]?: FieldConfig;
};

// Auto-detect field type based on value
export function detectFieldType(value: any): FieldType {
    if (value === null || value === undefined) return 'string';

    if (value instanceof Decimal) return 'decimal';
    if (typeof value === 'number') {
        // Check if it looks like a timestamp (reasonable date range)
        if (value > 946684800000 && value < 4102444800000) { // 2000-2100 range
            return 'date';
        }
        return 'number';
    }
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'string') return 'string';
    if (value instanceof Date) return 'date';

    return 'string'; // Default fallback
}

// Create sortable value based on field type
export function createSortableValue(
    value: any,
    fieldType: FieldType,
    lookupMap?: Map<string, string>
): Comparable<any> {
    switch (fieldType) {
        case 'string':
            return new SortableString(String(value || ''));
        case 'number':
            return new SortableNumber(Number(value || 0));
        case 'decimal':
            return new SortableDecimal(value instanceof Decimal ? value : new Decimal(value?.toString() || '0'));
        case 'date':
            return new SortableDate(value);
        case 'boolean':
            return new SortableBoolean(Boolean(value));
        case 'lookup':
            if (!lookupMap) {
                console.warn('Lookup field requires lookupMap');
                return new SortableString(String(value || ''));
            }
            return new SortableLookup(value, lookupMap);
        default:
            return new SortableString(String(value || ''));
    }
}

// Generic sort function that automatically detects field types
export function createGenericSortFunction<T>(
    fieldsConfig?: SortFieldsConfig<T>,
    lookupMaps?: { [K in keyof T]?: Map<string, string> }
) {
    return function getSortableValue(item: T, key: keyof T): Comparable<any> {
        const value = item[key];

        // Use explicit field config if provided
        if (fieldsConfig && fieldsConfig[key]) {
            const config = fieldsConfig[key]!;
            const lookupMap = config.lookupMap || (lookupMaps && lookupMaps[key]);
            return createSortableValue(value, config.type, lookupMap);
        }

        // Auto-detect field type
        const detectedType = detectFieldType(value);
        const lookupMap = lookupMaps && lookupMaps[key];
        return createSortableValue(value, detectedType, lookupMap);
    };
}
