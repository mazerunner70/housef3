# Recurring Charge Detection - Documentation

ML-based automatic detection of recurring charges (subscriptions, bills, salaries) in transaction history.

---

## Documents

### overview.md
**Non-technical overview for stakeholders**

- 200-word explanation of how the ML works
- Comprehensive glossary of terms
- Quick reference guide
- External resources and links

**Audience:** Product managers, stakeholders, non-technical users

---

### design.md
**Complete technical design**

- Feature engineering (67-dimensional vectors)
- DBSCAN clustering algorithm
- Pattern detection and confidence scoring
- Data models and API endpoints
- Architecture and integration points
- Performance characteristics
- Expected accuracy and limitations

**Audience:** Engineers, architects, technical leads

---

### delivery-phases.md
**Temporary delivery tracking document**

- Phase-by-phase breakdown (5 phases)
- Current status and completion metrics
- Deliverables and acceptance criteria
- Risk mitigation strategies
- Success metrics

**Audience:** Project managers, team leads

**Note:** This document will be archived after feature launch.

---

### implementation-guide.md
**Bespoke code patterns and implementation details**

- Enum handling pattern (avoiding AttributeError)
- DynamoDB serialization/deserialization
- Circular encoding for temporal features
- Week-of-month pattern detection
- Confidence score calculation
- Performance monitoring patterns
- Access control patterns
- Common pitfalls and solutions

**Audience:** Engineers implementing the feature

---

## Quick Start

**Want to understand the feature?** Start with overview.md

**Need technical details?** Read design.md

**Implementing the code?** Use implementation-guide.md for patterns

**Tracking progress?** Check delivery-phases.md

---

## Feature Status

**Current Phase:** Phase 1 Complete, Phase 2 In Progress

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Infrastructure | Complete | 100% |
| Phase 2: ML Services | In Progress | 40% |
| Phase 3: API Layer | Planned | 0% |
| Phase 4: Frontend | Planned | 0% |
| Phase 5: Testing | Planned | 0% |

---

**Last Updated:** November 7, 2025
