import { ApiClient } from '@/utils/apiClient';

export interface FieldMap {
  fileMapId: string;
  name: string;
  description?: string;
  accountId?: string;
  mappings: Array<{
    sourceField: string;
    targetField: string;
  }>;
  reverseAmounts?: boolean;  // Flag to reverse transaction amounts (multiply by -1)
  createdAt: string;
  updatedAt: string;
}

export interface FieldMapListResponse {
  fieldMaps: FieldMap[];
}

// API endpoint path - ApiClient will handle the full URL construction
const API_ENDPOINT = '/file-maps';

// Get list of field maps
export const listFieldMaps = async (): Promise<FieldMapListResponse> => {
  try {
    console.log('Fetching field maps from:', API_ENDPOINT);
    const data = await ApiClient.getJson<any>(API_ENDPOINT);
    console.log('Raw field maps response:', data);
    return {
      fieldMaps: data.fileMaps || [] // Ensure we always return an array
    };
  } catch (error) {
    console.error('Error listing field maps:', error);
    throw error;
  }
};

// Get a single field map
export const getFieldMap = async (fileMapId: string): Promise<FieldMap> => {
  try {
    const data: FieldMap = await ApiClient.getJson(`${API_ENDPOINT}/${fileMapId}`);
    return data;
  } catch (error) {
    console.error('Error getting field map:', error);
    throw error;
  }
};

// Create a new field map
export const createFieldMap = async (fieldMap: Omit<FieldMap, 'fileMapId' | 'createdAt' | 'updatedAt'>): Promise<FieldMap> => {
  try {
    const data: FieldMap = await ApiClient.postJson(API_ENDPOINT, fieldMap);
    return data;
  } catch (error) {
    console.error('Error creating field map:', error);
    throw error;
  }
};

// Update a field map
export const updateFieldMap = async (fileMapId: string, updates: Partial<FieldMap>): Promise<FieldMap> => {
  try {
    const data: FieldMap = await ApiClient.putJson(`${API_ENDPOINT}/${fileMapId}`, updates);
    return data;
  } catch (error) {
    console.error('Error updating field map:', error);
    throw error;
  }
};

// Delete a field map
export const deleteFieldMap = async (fileMapId: string): Promise<void> => {
  try {
    await ApiClient.delete(`${API_ENDPOINT}/${fileMapId}`);
  } catch (error) {
    console.error('Error deleting field map:', error);
    throw error;
  }
};

export default {
  listFieldMaps,
  getFieldMap,
  createFieldMap,
  updateFieldMap,
  deleteFieldMap
}; 