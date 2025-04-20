# Storage Design Decisions

## Transaction Deduplication Strategy

### Current Implementation
The current implementation uses DynamoDB queries to check for duplicate transactions. For each new transaction, it:
1. Queries the transactions table using the `AccountIdIndex`
2. Filters results by date, description, and amount
3. Marks transactions as duplicates if matches are found

### Analysis of Approaches

#### In-Memory Approach
**Pros:**
1. Single database query to fetch all transactions
2. Faster comparison operations in memory
3. Better for small accounts with few transactions

**Cons:**
1. Memory usage could be high for large accounts (e.g., 10,000 transactions = 10-20MB)
2. Need to handle pagination for large result sets
3. Could hit Lambda memory limits (128MB-10GB)
4. More expensive in terms of DynamoDB read capacity

#### Current DynamoDB Query Approach
**Pros:**
1. Memory efficient - only loads potential matches
2. Scales well with large datasets
3. Uses indexes effectively
4. No pagination needed

**Cons:**
1. More database queries (one per transaction)
2. More expensive in terms of DynamoDB read operations
3. Slightly slower due to network latency

### Decision Rationale
The current DynamoDB query approach was chosen because:
1. It's more memory efficient, which is important for Lambda functions
2. It scales better with large accounts
3. The cost of DynamoDB queries is likely less than the cost of increased Lambda memory usage
4. The current implementation already handles the query efficiently using the `AccountIdIndex`

### Potential Optimizations
1. **Date Range Filtering**
   - Add a date range filter to the query to reduce the number of potential matches
   - This would be particularly effective for accounts with many transactions over long periods

2. **Batch Processing**
   - Batch the duplicate checks (e.g., check 25 transactions at a time)
   - This would reduce the number of database queries while maintaining memory efficiency

3. **Caching Layer**
   - Add a cache layer for frequently accessed accounts
   - This would improve performance for accounts that are frequently updated

### Transaction Model Details
Each transaction contains:
- Required fields: transaction_id, file_id, user_id, date, description, amount, running_total
- Optional fields: transaction_type, category, payee, memo, check_number, reference
- Estimated size: 1-2KB per transaction

### Batch Processing Limits
- DynamoDB has a batch limit of 25 items
- This is used in the `delete_transactions_for_file` function
- Could be leveraged for batch duplicate checking

### Future Considerations
1. **Scaling**
   - Monitor DynamoDB read capacity as the number of transactions grows
   - Consider implementing batch processing if query costs become significant

2. **Performance**
   - Track processing times for different account sizes
   - Consider implementing caching if certain accounts show high latency

3. **Cost Optimization**
   - Monitor DynamoDB costs
   - Consider implementing batch processing if query costs become significant
   - Evaluate the trade-off between Lambda memory usage and DynamoDB query costs 