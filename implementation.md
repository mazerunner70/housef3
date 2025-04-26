# Timeline Plot for Account File Overlap Visualization

## Overview
To help users understand overlaps (shared transactions) between multiple account files, we will use a timeline plot on the account summary screen. This visualization is intuitive for sequential, dated files and makes overlaps and gaps visually obvious.

## Key Requirements
1. **Timeline Coverage Visualization**
   - Clearly show the date ranges covered by imported transaction files
   - Highlight gaps between files where no transactions are recorded
   - Indicate overlapping periods where multiple files contain transactions
   - Display the density of transactions within each file's date range

2. **Gap Analysis and Export Suggestions**
   - Automatically identify gaps in the timeline where no transaction data exists
   - For each gap, suggest optimal date ranges for exporting transactions from the source
   - Consider typical statement periods (e.g., monthly, quarterly) when suggesting ranges
   - Prioritize suggestions that would connect existing transaction periods

### Example Gap Suggestion
If files cover Jan 1-15 and Feb 1-28, the system should suggest:
- Export transactions from Jan 16-31 to complete January coverage
- Consider combining with February export if the source allows 45-day ranges

## Data Needed from Backend
The backend should provide, for a given account:
- A list of all files (file IDs and names)
- For each file:
  - Start date (earliest transaction)
  - End date (latest transaction)
  - (Optional) Number of transactions
  - (Optional) List of transaction dates for more granular visualization

### Example API Response
```json
[
  {
    "id": "fileA",
    "name": "Jan.csv",
    "startDate": "2024-01-01",
    "endDate": "2024-01-31",
    "transactionCount": 100
  },
  {
    "id": "fileB",
    "name": "Feb.csv",
    "startDate": "2024-01-25",
    "endDate": "2024-02-28",
    "transactionCount": 120
  }
  // etc.
]
```
- Overlaps are visually apparent where date ranges intersect.

## Backend Implementation Notes
- For each file, compute the minimum and maximum transaction date.
- Optionally, include the number of transactions and a list of all transaction dates for more detailed visualization.
- Return the above structure via a new endpoint, e.g., `GET /accounts/{accountId}/file-timeline`.

## Frontend Implementation Notes
- **Recommended Library:** Use [`react-chrono`](https://www.npmjs.com/package/react-chrono), a flexible, data-driven timeline library for React. It offers vertical and horizontal timeline modes, customizable styles, and interactive features.
- **Installation:**
  ```bash
  npm install react-chrono
  ```
- **Usage:**
  Prepare your data as an array of items, including both existing files and gap suggestions:
  ```js
  const items = [
    {
      title: "Jan.csv",
      cardTitle: "January Transactions (First Half)",
      cardSubtitle: "100 transactions",
      cardDetailedText: "Date range: 2024-01-01 to 2024-01-15\nComplete coverage for early January",
      timelineContent: "Jan.csv",
      // Custom styling for existing files
      cardBackground: "#e3f2fd",
      contentStyle: { background: "#bbdefb" }
    },
    {
      title: "Missing Coverage",
      cardTitle: "Suggested Export",
      cardSubtitle: "Gap Detected",
      cardDetailedText: "Recommended: Export transactions from Jan 16-31 to complete January coverage",
      timelineContent: "📥 Export Needed",
      // Custom styling for gap suggestions
      cardBackground: "#fff3e0",
      contentStyle: { background: "#ffe0b2" }
    },
    {
      title: "Feb.csv",
      cardTitle: "February Transactions",
      cardSubtitle: "120 transactions",
      cardDetailedText: "Date range: 2024-02-01 to 2024-02-28\nComplete coverage for February",
      timelineContent: "Feb.csv",
      cardBackground: "#e3f2fd",
      contentStyle: { background: "#bbdefb" }
    }
    // ...
  ];
  ```
  Render the enhanced timeline with coverage indicators:
  ```jsx
  import { Chrono } from "react-chrono";
  // ...
  <Chrono 
    items={items}
    mode="HORIZONTAL"
    cardHeight={200}
    slideShow
    enableOutline
    theme={{
      primary: "#1976d2",
      secondary: "#90caf9",
      cardBgColor: "#e3f2fd",
      titleColor: "#1976d2",
      titleColorActive: "#1565c0"
    }}
  />
  ```
- Display the plot on the account summary screen, with clear visual distinction between:
  - Existing transaction files (solid colors)
  - Suggested export ranges (striped or highlighted differently)
  - Overlapping periods (darker shading)
- Allow clicking on a file to view its transactions or on a gap to initiate an export
- Use consistent color coding:
  - Blue shades for existing files
  - Orange/yellow for gaps and suggestions
  - Darker shades for overlapping periods
- Customize the appearance using react-chrono's theming options to match your application's design

## Benefits
- Modern and visually appealing timeline visualization
- Multiple display modes (horizontal, vertical, vertical-alternating)
- Built-in support for interactive features like slideshow and outline
- Highly customizable with themes and styling options
- Responsive design that works well on all screen sizes

## Account Page Integration
- **Component Placement:** The timeline will be positioned prominently below the account summary header and above the transaction list/table
  ```
  +----------------------------------+
  |        Account Summary           |
  |   (balance, account #, etc.)     |
  +----------------------------------+
  |                                  |
  |      Timeline Visualization      |
  |   (file coverage & suggestions)  |
  |                                  |
  +----------------------------------+
  |    Transaction List/Table        |
  |                                  |
  +----------------------------------+
  ```

- **Layout Considerations:**
  - Timeline should span full width of the content area for maximum visibility
  - Default height of 200-250px, expandable when interacting with cards
  - Collapsible when screen space is needed for transaction table
  - Responsive behavior:
    - Horizontal mode on desktop/tablet (width >= 768px)
    - Switches to vertical mode on mobile for better readability
    - Cards stack vertically on narrow screens

- **User Interaction Flow:**
  1. User lands on account page
  2. Timeline immediately shows coverage status of imported files
  3. Gaps are highlighted with suggested export ranges
  4. Clicking a file card filters transaction table to that date range
  5. Clicking a gap card opens the export dialog with pre-filled dates
