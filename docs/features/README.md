# Feature Documentation

Feature-specific design documents organized by domain.

## Feature Domains

### [📤 Transfers](./transfers/)
Transfer detection and management system for identifying matching transactions between accounts.

**Key Documents:**
- `transfer-detection-design.md` - Technical architecture and algorithms (compact review flow, end-of-cycle updates)
- `compact-review-ui-design.md` - Compact Transfers Dashboard UX and keyboard-first flow
- `backend-call-pattern-analysis.md` - Optimized backend call pattern and progress semantics
- `implementation-plan.md` - Review cycle correctness plan and milestones
- `transfer-user-guide.md` - User-facing documentation

**Use Cases:** Detecting paired transactions, managing transfer relationships, category management for transfers

---

### [📦 FZIP](./fzip/)
Financial ZIP (FZIP) backup and restore system for complete financial profile management.

**Key Documents:**
- `fzip-backup-restore-guide.md` - Comprehensive guide and data format
- `fzip-restore-flow.md` - Detailed restore workflow and state management
- `fzip-restore-implementation-plan.md` - Implementation phases and roadmap

**Use Cases:** Backing up financial data, restoring from backup, data migration, profile management

---

### [📁 Imports](./imports/)
Transaction file import and processing functionality supporting multiple formats.

**Key Documents:**
- `transaction_file_handling.md` - File lifecycle and management principles
- `qif_file_processing_design.md` - QIF format support
- `ofx-import-design.md` - OFX format support
- `associatefile.md` - File-account association process and deduplication

**Use Cases:** Importing transaction files, supporting new file formats, file processing pipelines

---

### [🏷️ Categories](./category-management-design.md)
Comprehensive category management system with rules engine and intelligent categorization.

**Key Document:**
- `category-management-design.md` - Complete design for category management, rule engine, hierarchical categories, and suggestion workflow

**Use Cases:** Creating transaction categories, defining matching rules, automatic categorization, category hierarchy management

## Adding New Features

When documenting a new feature:

1. **Create a subdirectory** under `features/` with a clear domain name
2. **Include these document types:**
   - Design document (`*-design.md`) - Technical architecture
   - User guide (`*-user-guide.md`) - User-facing documentation (if applicable)
   - Implementation plan (`*-implementation-plan.md`) - Phased rollout (if complex)
3. **Update this README** with a summary and key use cases
4. **Link related documents** across architecture, UI, and API docs

