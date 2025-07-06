import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// Making date fields potentially undefined to align with component outputs
export interface FilterValues {
  startDate?: string;
  endDate?: string;
  accountIds: string[];
  categoryIds: string[];
  transactionType: 'all' | 'income' | 'expense' | 'transfer';
  searchTerm: string;
}

const initialFilters: FilterValues = {
  startDate: undefined,
  endDate: undefined,
  accountIds: [],
  categoryIds: [],
  transactionType: 'all',
  searchTerm: '',
};

const DEFAULT_TRANSACTIONS_PAGE_SIZE = 25;

interface TransactionsUIStore {
  filters: FilterValues;
  currentPage: number;
  pageSize: number;
  setFilters: (newFilters: Partial<FilterValues>) => void;
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  resetPaginationAndFilters: () => void;
  applyNewFilters: (newFilters: FilterValues) => void;
}

export const useTransactionsUIStore = create<TransactionsUIStore>()(
  persist(
    (set) => ({
      filters: initialFilters,
      currentPage: 1,
      pageSize: DEFAULT_TRANSACTIONS_PAGE_SIZE,

      setFilters: (newFilters) =>
        set((state) => ({ filters: { ...state.filters, ...newFilters } })),
      
      setCurrentPage: (page) => set({ currentPage: page }),
      
      setPageSize: (size) => 
        set({ pageSize: size, currentPage: 1 }),

      resetPaginationAndFilters: () => 
        set({ 
          filters: initialFilters, 
          currentPage: 1, 
          pageSize: DEFAULT_TRANSACTIONS_PAGE_SIZE 
        }),

      applyNewFilters: (newFiltersSet) => 
        set({ filters: newFiltersSet, currentPage: 1 }),
    }),
    {
      name: 'transactions-ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        filters: state.filters,
        currentPage: state.currentPage,
        pageSize: state.pageSize 
      }),
    }
  )
); 