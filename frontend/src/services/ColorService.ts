import { ApiClient } from '@/utils/apiClient';

// API endpoint path - ApiClient will handle the full URL construction
const API_ENDPOINT = '/colors';

export interface Color {
  id?: string;
  name: string;
  hex: string;
  rgb?: string;
  hsl?: string;
  category?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ColorListResponse {
  colors: Color[];
  metadata: {
    totalColors: number;
  };
  user: {
    id: string;
    email: string;
  };
}

// List colors with pagination
export const listColors = async (): Promise<ColorListResponse> => {
  return ApiClient.getJson<ColorListResponse>(API_ENDPOINT);
}; 