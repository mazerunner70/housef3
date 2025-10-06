# Housef3 Documentation

This directory contains all technical documentation for the Housef3 project, organized by purpose and scope.

## 📁 Directory Structure

### [`architecture/`](./architecture/)
System-wide architectural designs and technical foundations:
- **event-driven-architecture-design.md** - Pub-sub event system design using EventBridge
- **analytics-implementation-design.md** - Comprehensive analytics system architecture
- **storage_design.md** - DynamoDB schema design and transaction deduplication
- **component-organization-strategy.md** - React component organization patterns

### [`features/`](./features/)
Feature-specific design documents organized by domain:

#### [`features/transfers/`](./features/transfers/)
Transfer detection and management:
- **transfer-detection-design.md** - Technical design for transfer detection system
- **transfer-user-guide.md** - User guide for transfer functionality

#### [`features/fzip/`](./features/fzip/)
Financial ZIP backup/restore system:
- **fzip-backup-restore-guide.md** - Comprehensive design and implementation guide
- **fzip-restore-flow.md** - Detailed restore flow and state management
- **fzip-restore-implementation-plan.md** - Implementation roadmap and phases

#### [`features/imports/`](./features/imports/)
Transaction file import functionality:
- **ofx-import-design.md** - OFX file format support design
- **qif_file_processing_design.md** - QIF file processing implementation
- **transaction_file_handling.md** - Transaction file lifecycle and management

### [`ui/`](./ui/)
UI/UX design specifications:
- **ui_design.md** - High-level UI design principles and structure
- **ui_theme.md** - CSS scheme and component styling guide
- **ui-design-transaction-import-page.md** - Transaction import page designs
- **new_ui_accounts_view.md** - Accounts management interface design
- **new_ui_transactions_view.md** - Transactions section with tabbed interface
- **contextual-sidebar-design.md** - Contextual sidebar navigation pattern
- **breadcrumb-navigation-design.md** - Breadcrumb navigation system
- **url-depth-management.md** - URL depth strategy and management

### [`api/`](./api/)
API documentation and specifications:
- **api_documentation.md** - Comprehensive API endpoint documentation

## 🚀 Quick Start Guides

**New to the project?** Start here:
1. [`ui/ui_design.md`](./ui/ui_design.md) - Understand the UI principles
2. [`architecture/storage_design.md`](./architecture/storage_design.md) - Learn the data model
3. [`api/api_documentation.md`](./api/api_documentation.md) - Explore available APIs

**Working on a specific feature?**
- Transfers: [`features/transfers/transfer-detection-design.md`](./features/transfers/transfer-detection-design.md)
- Backup/Restore: [`features/fzip/fzip-backup-restore-guide.md`](./features/fzip/fzip-backup-restore-guide.md)
- Imports: [`features/imports/transaction_file_handling.md`](./features/imports/transaction_file_handling.md)

**Building UI components?**
- Start with [`architecture/component-organization-strategy.md`](./architecture/component-organization-strategy.md)
- Reference [`ui/ui_theme.md`](./ui/ui_theme.md) for styling
- Check [`ui/contextual-sidebar-design.md`](./ui/contextual-sidebar-design.md) for navigation patterns

## 📝 Documentation Standards

When adding new documentation:
1. Place in the appropriate subfolder based on scope (architecture/features/ui/api)
2. For feature docs, create a new subfolder under `features/` if it's a distinct domain
3. Use descriptive filenames with hyphens (e.g., `feature-name-design.md`)
4. Update this README with links to new documents
5. Include design rationale, technical specifications, and implementation details

## 🔗 Related Documentation

- Root level design docs: See `/design.md` and `/implementation.md` in project root
- Backend conventions: See `/backend/README.md`
- Frontend conventions: See `/frontend/README.md`
- Infrastructure: See `/infrastructure/terraform/README.md`


