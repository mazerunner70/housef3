import React from 'react';
import ImportTransactionsView from './ImportTransactionsView'; // Import the detailed view

const StatementsImportsTab: React.FC = () => {
  return (
    // The parent div can remain if you want consistent padding/styling for all tab contents
    // or ImportTransactionsView can manage its own top-level styling.
    // For now, let ImportTransactionsView handle its own container styling.
    <ImportTransactionsView />
  );
};
export default StatementsImportsTab; 