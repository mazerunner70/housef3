import { useState, useEffect, useCallback } from 'react';
import { UITransaction } from '../components/accounts/TransactionList'; // Import placeholder type

// Placeholder for actual ServiceTransaction type from backend/service
interface ServiceTransaction {
  transactionId: string;
  transactionDate: string; // Or number (timestamp)
  description: string;
  // ... other fields from backend ...
  amount: number; // Or string if backend sends as string
  type: string; // e.g. "DEBIT" or "CREDIT"
  category?: string;
  status?: string;
}

// Example mapping function - adjust based on actual ServiceTransaction structure
const mapServiceTransactionToUITransaction = (st: ServiceTransaction): UITransaction => ({
  id: st.transactionId,
  date: new Date(st.transactionDate).toLocaleDateString(), // Basic date formatting
  description: st.description,
  category: st.category,
  amount: st.amount.toFixed(2), // Basic amount formatting, assumes number
  type: st.type === 'DEBIT' ? 'Debit' : 'Credit', // Example mapping
  status: st.status,
});

const useAccountTransactions = (accountId: string | null) => {
  const [transactions, setTransactions] = useState<UITransaction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    if (!accountId) return; // Don't fetch if no accountId

    setLoading(true);
    setError(null);
    try {
      // TODO: Replace with actual API call to GET /api/transactions?accountId={accountId}
      // Potentially via a TransactionService.ts
      // const response = await fetch(`/api/transactions?accountId=${accountId}`);
      // if (!response.ok) throw new Error('Failed to fetch transactions');
      // const data: ServiceTransaction[] = await response.json();
      // setTransactions(data.map(mapServiceTransactionToUITransaction));
      console.log(`Simulating fetch for transactions for account ${accountId}`);
      await new Promise(resolve => setTimeout(resolve, 700)); // Simulate network delay
      
      // Placeholder data
      const placeholderData: UITransaction[] = [
        { id: 'tx1', date: '2024-03-01', description: 'Coffee Shop', category: 'Food & Drink', amount: '5.50', type: 'Debit', status: 'Cleared' },
        { id: 'tx2', date: '2024-03-02', description: 'Salary Deposit', category: 'Income', amount: '2500.00', type: 'Credit', status: 'Cleared' },
        { id: 'tx3', date: '2024-03-03', description: 'Online Subscription', category: 'Bills', amount: '15.00', type: 'Debit', status: 'Pending' },
      ];
      setTransactions(placeholderData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred while fetching transactions');
      console.error("Error fetching transactions:", err);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  return { transactions, loading, error, refetchTransactions: fetchTransactions };
};

export default useAccountTransactions; 