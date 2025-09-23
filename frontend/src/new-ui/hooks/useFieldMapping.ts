import { useState, useEffect, useCallback } from 'react';
import {
    listFieldMaps,
    getFieldMap,
    createFieldMap,
    deleteFieldMap,
    type FieldMap
} from '@/services/FileMapService';

/**
 * Enhanced hook for managing field mapping configuration
 * 
 * Features:
 * - Account-specific field mapping management
 * - CRUD operations for field mappings
 * - Validation and error handling
 * - Integration with existing FileMapService
 * 
 * Field Mapping Workflow:
 * 1. Load existing mappings for account
 * 2. Allow creation/editing of mappings
 * 3. Validate mapping configuration
 * 4. Save/update mappings
 * 5. Associate mappings with files
 */

interface UseFieldMappingReturn {
    // Current mapping state
    mapping: FieldMap | null;
    availableMappings: FieldMap[];
    isLoading: boolean;
    error: string | null;

    // Mapping operations
    createMapping: (mappingData: Partial<FieldMap>) => Promise<FieldMap | null>;
    editMapping: (mapping: FieldMap) => void;
    deleteMapping: (mappingId: string) => Promise<void>;
    viewMapping: (mapping: FieldMap) => void;
    loadMapping: (mappingId: string) => Promise<FieldMap | null>;

    // Utility functions
    clearError: () => void;
    refetch: () => Promise<void>;
}

interface Account {
    accountId: string;
    defaultFileMapId?: string;
}

const useFieldMapping = (accountId: string, account?: Account): UseFieldMappingReturn => {
    const [mapping, setMapping] = useState<FieldMap | null>(null);
    const [availableMappings, setAvailableMappings] = useState<FieldMap[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    const fetchMappings = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);

            // If account has a defaultFileMapId, fetch that specific mapping
            if (account?.defaultFileMapId) {
                try {
                    const defaultMapping = await getFieldMap(account.defaultFileMapId);
                    setMapping(defaultMapping);
                    setAvailableMappings([defaultMapping]);
                    return;
                } catch (defaultMappingError: any) {
                    console.warn('Failed to load default field mapping, falling back to list:', defaultMappingError);
                    // Fall through to list all mappings
                }
            }

            // Fallback: fetch all mappings and filter for this account
            const response = await listFieldMaps();
            const mappings = response.fieldMaps;

            // Filter mappings for this account or global mappings
            const accountMappings = mappings.filter(mapping =>
                !mapping.accountId || mapping.accountId === accountId
            );

            setAvailableMappings(accountMappings);

            // If there's a default mapping for this account, load it
            const defaultMapping = accountMappings.find(mapping =>
                mapping.accountId === accountId
            );

            if (defaultMapping) {
                setMapping(defaultMapping);
            }

        } catch (fetchError: any) {
            console.error('Error fetching field mappings:', fetchError);
            setError(fetchError.message || 'Failed to load field mappings');
        } finally {
            setIsLoading(false);
        }
    }, [accountId, account?.defaultFileMapId]);

    // Initial fetch
    useEffect(() => {
        fetchMappings();
    }, [fetchMappings]);

    const createMapping = useCallback(async (mappingData: Partial<FieldMap>): Promise<FieldMap | null> => {
        try {
            setError(null);

            const newMapping = await createFieldMap({
                ...mappingData,
                accountId: mappingData.accountId || accountId, // Associate with current account
                name: mappingData.name || 'New Mapping',
                mappings: mappingData.mappings || []
            });

            // Refresh the list to include the new mapping
            await fetchMappings();

            // Set as current mapping
            setMapping(newMapping);

            return newMapping;

        } catch (createError: any) {
            console.error('Error creating field mapping:', createError);
            setError(createError.message || 'Failed to create field mapping');
            return null;
        }
    }, [accountId, fetchMappings]);

    const editMapping = useCallback((mappingToEdit: FieldMap) => {
        // For now, just set as current mapping
        // In a full implementation, this might open a modal or navigate to edit page
        setMapping(mappingToEdit);

        // TODO: Implement mapping edit modal or navigation
        console.log('Edit mapping:', mappingToEdit);
    }, []);

    const deleteMapping = useCallback(async (mappingId: string) => {
        try {
            setError(null);

            // Confirm deletion
            const confirmed = window.confirm('Are you sure you want to delete this field mapping? This action cannot be undone.');
            if (!confirmed) {
                return;
            }

            await deleteFieldMap(mappingId);

            // If the deleted mapping was the current one, clear it
            if (mapping && mapping.fileMapId === mappingId) {
                setMapping(null);
            }

            // Refresh the list
            await fetchMappings();

        } catch (deleteError: any) {
            console.error('Error deleting field mapping:', deleteError);
            setError(deleteError.message || 'Failed to delete field mapping');
        }
    }, [mapping, fetchMappings]);

    const viewMapping = useCallback((mappingToView: FieldMap) => {
        // For now, just log the mapping details
        // In a full implementation, this might open a read-only modal
        console.log('View mapping:', mappingToView);

        // TODO: Implement mapping view modal
        alert(`Mapping: ${mappingToView.name}\nFields: ${mappingToView.mappings.length} mapped`);
    }, []);

    const loadMapping = useCallback(async (mappingId: string): Promise<FieldMap | null> => {
        try {
            setError(null);

            const loadedMapping = await getFieldMap(mappingId);
            setMapping(loadedMapping);

            return loadedMapping;

        } catch (loadError: any) {
            console.error('Error loading field mapping:', loadError);
            setError(loadError.message || 'Failed to load field mapping');
            return null;
        }
    }, []);

    const refetch = useCallback(async () => {
        await fetchMappings();
    }, [fetchMappings]);

    return {
        // Current mapping state
        mapping,
        availableMappings,
        isLoading,
        error,

        // Mapping operations
        createMapping,
        editMapping,
        deleteMapping,
        viewMapping,
        loadMapping,

        // Utility functions
        clearError,
        refetch
    };
};

export default useFieldMapping;
