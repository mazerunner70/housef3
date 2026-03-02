# Architecture Documentation

System-wide architectural designs and technical foundations for Housef3.

## Architecture Decision Records (ADRs)

See [adr/README.md](./adr/README.md) for architectural decisions that affect system functionality.

Current ADRs:
- [ADR-0001: Decorator-Based Database Architecture](./adr/adr-0001-decorator-based-db-architecture.md) - Decorator pattern for database utilities
- [ADR-0002: React Router Data API Migration](./adr/adr-0002-react-router-data-api.md) - Migration to React Router Data API
- [ADR-0003: Four-Layer Component Organization Pattern](./adr/adr-0003-component-organization-pattern.md) - React component organization strategy
- [ADR-0004: Unsupervised ML for Recurring Charge Detection](./adr/adr-0004-unsupervised-ml-recurring-charge-detection.md) - DBSCAN clustering approach for pattern detection

---

## Design Documents

### [event-driven-architecture-design.md](./event-driven-architecture-design.md)
**Purpose:** Design for pub-sub event-driven architecture using AWS EventBridge

**Key Topics:**
- Event schema design (file, transaction, account, category events)
- Consumer architecture (analytics, categorization, notification, audit)
- Migration strategy from direct triggers
- Implementation phases and roadmap

**When to read:** Understanding the event system, implementing new consumers, or migrating services to event-driven patterns

---

### [analytics-implementation-design.md](./analytics-implementation-design.md)
**Purpose:** Comprehensive analytics system architecture

**Key Topics:**
- Data layer architecture and precalculations
- DynamoDB storage design for analytics
- Lambda triggers and caching strategies
- Frontend chart integration
- Performance optimization

**When to read:** Working on analytics features, dashboard development, or performance optimization

---

### [storage_design.md](./storage_design.md)
**Purpose:** Database schema design and data management strategies

**Key Topics:**
- DynamoDB table designs (Transactions, Files, Accounts, Field Maps, Categories)
- Transaction deduplication strategy
- Global Secondary Indexes (GSIs)
- Batch processing patterns

**When to read:** Implementing new data models, optimizing queries, or understanding the data layer

---

### [recurring-charge-ml-design.md](./recurring-charge-ml-design.md)
**Purpose:** ML architecture for recurring charge detection

**Key Topics:**
- Feature engineering (67-dimensional vectors)
- DBSCAN clustering algorithm
- Pattern analysis and confidence scoring
- Performance characteristics and scalability
- Integration with category system

**When to read:** Working on ML features, understanding the detection algorithm, or optimizing performance

---

### [component-organization-strategy.md](./component-organization-strategy.md)
**Purpose:** React component organization patterns

**Key Topics:**
- Component categorization (ui, business, composite, domain)
- Directory structure and naming conventions
- Migration strategy for existing components
- Best practices (SRP, props interfaces, CSS organization)

**When to read:** Creating new components, refactoring the frontend, or establishing coding standards

## Architecture Principles

1. **Event-Driven:** Loosely coupled services communicating via events
2. **Data-First:** DynamoDB as the single source of truth with strategic indexing
3. **Component-Based:** Modular React components organized by purpose
4. **Performance-Focused:** Precalculations, caching, and optimization by design


