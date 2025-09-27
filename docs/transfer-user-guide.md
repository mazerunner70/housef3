# Transfer Detection and Management - User Guide

## What Are Transfers?

When you move money between your own accounts (like from checking to savings), this creates two separate transactions:
- **Outgoing**: -$500 from your checking account
- **Incoming**: +$500 to your savings account

Without proper handling, these would incorrectly show as:
- $500 expense (reducing your net worth)
- $500 income (increasing your net worth)

The transfer detection system automatically finds these pairs and marks them as transfers, ensuring accurate financial reporting.

## Getting Started

### Accessing Transfer Management

1. Navigate to the **Transactions** section
2. Click on the **Transfers** tab
3. You'll see two main sections:
   - **Existing Transfer Pairs**: Already identified transfers
   - **Detect New Transfers**: Find new potential transfers

## Understanding the Interface

### Progress Tracking

The system shows your transfer checking progress:

```
Account Data Range: Jan 1, 2024 - Dec 31, 2024
Checked So Far: Jun 1, 2024 - Jun 30, 2024 [25%] ████████░░░░░░░░░░░░░░░░░░░░░░░░
Suggested Next Range: May 1, 2024 - May 31, 2024
```

- **Account Data Range**: The full span of your transaction data
- **Checked So Far**: Date ranges you've already scanned for transfers
- **Progress Bar**: Visual representation of completion percentage
- **Suggested Next Range**: Recommended date range for your next scan

### Why Progressive Checking?

Transfer detection is computationally intensive, so the system processes your data in manageable chunks:
- **Efficiency**: Faster processing of smaller date ranges
- **Accuracy**: Better matching within focused time periods
- **Progress**: Clear visibility into what's been checked
- **Flexibility**: You control when and what to process

## Detecting New Transfers

### Step 1: Choose Date Range

You have several options for selecting a date range:

#### Quick Range Options
- **7 days**: Good for recent activity
- **14 days**: Balanced approach
- **30 days**: Monthly review
- **90 days**: Quarterly analysis

#### Custom Date Range
- Use the date picker to select specific start and end dates
- Useful for targeting specific time periods

#### Smart Recommendations
- The system suggests optimal next ranges based on your progress
- Click "Use This Range" to apply the recommendation
- Ensures systematic coverage of all your data

### Step 2: Scan for Transfers

1. Select your desired date range
2. Click **"Scan for Transfers"**
3. The system will analyze all transactions in that period
4. Results appear in the "Potential Transfer Matches" section

### Step 3: Review Detected Transfers

The system shows potential matches in a table format:

| ☐ | Source Account | Date | Source Amount | Target Account | Date | Target Amount | Days Apart |
|---|----------------|------|---------------|----------------|------|---------------|------------|
| ☐ | Checking | 1/15 | -$500.00 | Savings | 1/15 | +$500.00 | 0 |
| ☐ | Credit Card | 1/20 | -$1,200.00 | Checking | 1/22 | +$1,200.00 | 2 |

**Review each potential match:**
- ✅ **Good Match**: Same amounts, reasonable date difference, makes sense
- ❌ **False Positive**: Different purposes, coincidental amounts

### Step 4: Mark as Transfers

#### Individual Selection
- Check the boxes next to transfers you want to mark
- Use "Select All" / "Deselect All" for bulk selection

#### Bulk Marking
1. Select the transfers you want to mark
2. Click **"Mark X as Transfers"**
3. The system will:
   - Create/assign a "Transfers" category
   - Categorize both transactions as transfers
   - Remove them from income/expense calculations

## Managing Existing Transfers

### Viewing Transfer Pairs

The "Existing Transfer Pairs" section shows all previously identified transfers:
- **Source/Target accounts**
- **Transaction dates**
- **Amounts**
- **Days between transactions**

### Filtering by Date Range

Use the date range picker at the top to filter existing transfers:
- View transfers from specific time periods
- Analyze transfer patterns over time
- Generate reports for specific date ranges

## Understanding Detection Criteria

The system looks for transaction pairs that meet ALL these criteria:

### ✅ Different Accounts
- Transactions must be from different accounts
- Same-account transactions are ignored

### ✅ Opposite Amounts
- One transaction is negative (outgoing)
- One transaction is positive (incoming)
- Amounts match within $0.01 tolerance

### ✅ Close in Time
- Transactions occur within 7 days of each other
- Closer dates are more likely to be transfers

### ✅ Not Already Categorized
- Only uncategorized transactions are considered
- Previously marked transfers are excluded

## Best Practices

### Systematic Approach

1. **Start Recent**: Begin with the most recent 30 days
2. **Work Backwards**: Use suggested ranges to work through historical data
3. **Regular Maintenance**: Check for new transfers monthly
4. **Complete Coverage**: Aim to check your entire transaction history

### Date Range Selection

#### For New Users
- Start with **30 days** to get familiar with the system
- Use **suggested ranges** for systematic coverage

#### For Regular Maintenance
- **7-14 days** for weekly/bi-weekly reviews
- **30 days** for monthly reviews

#### For Historical Analysis
- **90 days** for quarterly reviews
- **Custom ranges** for specific time periods

### Quality Control

#### Review Before Marking
- **Verify amounts match exactly**
- **Check dates are reasonable** (same day or within a few days)
- **Confirm accounts make sense** (your checking to your savings)

#### Common False Positives
- **Coincidental amounts**: Same amount, different purposes
- **Recurring payments**: Regular bills that happen to match
- **Split transactions**: Parts of larger transactions

## Troubleshooting

### No Transfers Found

If the system finds no transfers in your selected range:

1. **Expand Date Range**: Try a longer period (30-90 days)
2. **Check Different Periods**: Transfers might be clustered in specific timeframes
3. **Verify Account Setup**: Ensure all your accounts are properly configured
4. **Review Criteria**: Your transfers might not meet the matching criteria

### Too Many False Positives

If you see many incorrect matches:

1. **Use Shorter Date Ranges**: Smaller ranges often have better accuracy
2. **Review Carefully**: Don't bulk-select without reviewing each match
3. **Check Account Names**: Ensure account names are clear and distinct

### Missing Expected Transfers

If you know about transfers that aren't detected:

1. **Check Amount Differences**: Amounts must match within $0.01
2. **Verify Date Range**: Transfers must be within 7 days of each other
3. **Confirm Account Differences**: Must be between different accounts
4. **Check Existing Categories**: Already categorized transactions are excluded

### Performance Issues

If detection is slow:

1. **Use Smaller Date Ranges**: 7-30 days typically perform better
2. **Check During Off-Peak Hours**: System may be less loaded
3. **Clear Browser Cache**: Refresh the page if needed

## Advanced Features

### Progress Tracking Benefits

The system tracks your progress to:
- **Avoid Duplicate Work**: Don't re-scan the same periods
- **Show Completion**: Visual progress toward full coverage
- **Smart Suggestions**: Recommend optimal next ranges
- **Maintain History**: Remember what you've already checked

### Overlap Strategy

The system uses a 3-day overlap between date ranges to ensure:
- **No Missed Transfers**: Transfers spanning range boundaries are caught
- **Complete Coverage**: Every transaction is considered
- **Optimal Accuracy**: Better matching with sufficient context

### Bulk Operations

Efficient bulk operations allow you to:
- **Select Multiple Transfers**: Use checkboxes for bulk selection
- **Mark Many at Once**: Process multiple transfers simultaneously
- **Save Time**: Avoid individual marking for obvious transfers

## Impact on Financial Reports

### Before Transfer Detection
```
Income:  $3,000 (salary) + $500 (false transfer income) = $3,500
Expenses: $2,000 (bills) + $500 (false transfer expense) = $2,500
Net: $1,000
```

### After Transfer Detection
```
Income:  $3,000 (salary)
Expenses: $2,000 (bills)
Transfers: $500 (checking → savings)
Net: $1,000 (accurate)
```

### Benefits
- **Accurate Net Worth**: Transfers don't affect your total wealth
- **Clear Cash Flow**: See actual income and expenses
- **Better Budgeting**: Budget based on real spending, not transfers
- **Proper Categorization**: Transfers appear in their own category

## Tips for Success

### Getting Started
1. **Start Small**: Begin with 7-14 days to learn the system
2. **Use Suggestions**: Follow the recommended date ranges
3. **Review Carefully**: Don't rush the review process
4. **Ask Questions**: Contact support if you're unsure about matches

### Ongoing Maintenance
1. **Regular Reviews**: Check for new transfers monthly
2. **Systematic Approach**: Use the progress tracking to stay organized
3. **Quality Over Speed**: Better to be accurate than fast
4. **Learn Patterns**: Notice your typical transfer patterns over time

### Maximizing Accuracy
1. **Understand Your Habits**: Know your typical transfer patterns
2. **Check Account Names**: Ensure accounts are clearly labeled
3. **Review Edge Cases**: Pay attention to unusual amounts or timing
4. **Use Custom Ranges**: Target specific periods when needed

## Getting Help

### Common Questions

**Q: How often should I check for transfers?**
A: Monthly is usually sufficient, but weekly works well for active users.

**Q: What if I accidentally mark something as a transfer?**
A: You can manually change the category back in the transaction details.

**Q: Why doesn't the system find all my transfers automatically?**
A: The system is conservative to avoid false positives. Manual review ensures accuracy.

**Q: Can I undo bulk transfer marking?**
A: Yes, you can change categories manually in the transaction management section.

### Support Resources

- **Documentation**: Refer to this guide and the technical documentation
- **Help System**: Use the in-app help for specific questions
- **Support Team**: Contact support for complex issues or bugs

Remember: The transfer detection system is designed to help you maintain accurate financial records. Take your time to review matches carefully, and don't hesitate to ask for help if you're unsure about any aspect of the process.
