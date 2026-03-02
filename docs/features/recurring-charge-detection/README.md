# Recurring Charge Detection - Documentation

ML-based automatic detection of recurring charges (subscriptions, bills, salaries) in transaction history.

---

## Core Documents

### [`overview.md`](./overview.md)
**Non-technical overview for stakeholders**
- 200-word explanation of how the ML works
- Comprehensive glossary of terms
- Quick reference guide

**Audience:** Product managers, stakeholders, non-technical users

### [`design.md`](./design.md)
**Feature technical design summary**
- How the ML detection works (simplified)
- Data models and API endpoints
- Performance characteristics and limitations
- Real-world examples

**Audience:** Engineers, architects, technical leads

### [`implementation-guide.md`](./implementation-guide.md)
**Code patterns and implementation details**
- Enum handling patterns
- DynamoDB serialization/deserialization
- Circular encoding for temporal features
- Confidence score calculation
- Common pitfalls and solutions

**Audience:** Engineers implementing or maintaining the feature

---

## Architecture & Decisions

### [ADR-0004: Unsupervised ML Approach](../../architecture/adr/adr-0004-unsupervised-ml-recurring-charge-detection.md)
**Architecture Decision Record**
- Why DBSCAN clustering was chosen
- Alternatives considered (rule-based, supervised ML, K-means, time series)
- Trade-offs and consequences
- Performance expectations

**Audience:** Architects, technical leads, engineers

### [ML Architecture Design](../../architecture/recurring-charge-ml-design.md)
**System architecture documentation**
- Complete ML pipeline architecture
- Feature engineering details (67-dimensional vectors)
- DBSCAN algorithm parameters and rationale
- Pattern analysis algorithms
- Performance characteristics and scalability
- Integration points with other systems

**Audience:** Architects, ML engineers, senior engineers

---

## Implementation & Delivery

### [Implementation Log](../../impl-log/recurring-charge-detection.md)
**Phase-by-phase delivery tracking**
- Phase 1-4 completion summaries
- Phase 5 (Testing & Launch) progress
- Detailed metrics and timelines
- Key learnings and challenges overcome
- Migration notes

**Audience:** Project managers, team leads, engineers

### [Subfolder Migration](../../impl-log/recurring-charge-subfolder-migration.md)
**Code organization migration (Nov 22, 2025)**
- Service file restructuring
- Import path changes
- Migration impact

**Audience:** Engineers maintaining the codebase

---

## UX & Design

### [Criteria Builder UX](../../ui/recurring-charges-criteria-builder-ux.md)
**Phase 1 Review UX design**
- Criteria builder interface design
- Field-by-field mapping
- Real-time validation approach
- Progressive disclosure strategy

**Audience:** Product designers, frontend engineers

### [Review Workflow](../../ui/recurring-charges-review-workflow.md)
**Pattern review workflow design**
- User review process
- Approval/rejection flows
- Confidence visualization
- Category linking UX

**Audience:** Product designers, frontend engineers

---

## Reference Materials

### [`recurring-charge-detection-quick-reference.md`](./recurring-charge-detection-quick-reference.md)
**Quick reference guide**
- File structure overview
- Service architecture map
- Key functions and their purposes
- Data flow diagrams

**Audience:** Engineers working with the codebase

### [`refactoring-suggestions-recurring-charge-detection.md`](./refactoring-suggestions-recurring-charge-detection.md)
**Future improvements**
- Refactoring opportunities
- Code quality improvements
- Performance optimizations
- Feature enhancements

**Audience:** Engineers planning improvements

---

## Quick Start

**Want to understand the feature?** Start with [`overview.md`](./overview.md)

**Need technical architecture?** Read [ML Architecture Design](../../architecture/recurring-charge-ml-design.md)

**Why this approach?** See [ADR-0004](../../architecture/adr/adr-0004-unsupervised-ml-recurring-charge-detection.md)

**Implementing the code?** Use [`implementation-guide.md`](./implementation-guide.md) for patterns

**Tracking progress?** Check [Implementation Log](../../impl-log/recurring-charge-detection.md)

**Designing UX?** Review [Criteria Builder UX](../../ui/recurring-charges-criteria-builder-ux.md) and [Review Workflow](../../ui/recurring-charges-review-workflow.md)

---

## Feature Status

**Current Phase:** Phases 1-4 Complete, Phase 5 In Progress

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Infrastructure | ✅ Complete | 100% |
| Phase 2: ML Services | ✅ Complete | 100% |
| Phase 3: API Layer | ✅ Complete | 100% |
| Phase 4: Frontend | ✅ Complete | 100% |
| Phase 5: Testing & Launch | 🔄 In Progress | 60% |

See [Implementation Log](../../impl-log/recurring-charge-detection.md) for detailed phase information and timeline.

---

## Document Organization

This feature follows the [documentation conventions](../../architecture/../.cursor/rules/documentation-conventions.mdc):

- **Feature docs** (`docs/features/recurring-charge-detection/`) - Feature overview, design summary, implementation guide, reference materials
- **Architecture docs** (`docs/architecture/`) - System architecture, ML design details
- **ADRs** (`docs/architecture/adr/`) - Key architectural decisions with rationale
- **Implementation logs** (`docs/impl-log/`) - Phase tracking, delivery timeline, migrations
- **UI docs** (`docs/ui/`) - UX designs, workflows, interface specifications

---

**Last Updated:** November 30, 2025
