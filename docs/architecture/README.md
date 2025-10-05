# Architecture Documentation

System-wide architectural designs and technical foundations for Housef3.

## Documents

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


