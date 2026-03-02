# Architecture Decision Records (ADRs)

This folder contains Architecture Decision Records documenting significant architectural decisions that affect the system's functionality, structure, or implementation approach.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR should follow this structure:

```markdown
# ADR-NNNN: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded]
**Date:** YYYY-MM-DD
**Deciders:** [List of people involved]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Trade-off 2

## Alternatives Considered

What other options were evaluated and why were they not chosen?
```

## Current ADRs

| Number | Title | Status | Date |
|--------|-------|--------|------|
| [0001](./adr-0001-decorator-based-db-architecture.md) | Decorator-Based Database Architecture | Proposed | 2025-11-02 |
| [0002](./adr-0002-react-router-data-api.md) | React Router Data API Migration | Accepted | 2025-11-30 |
| [0003](./adr-0003-component-organization-pattern.md) | Four-Layer Component Organization Pattern | Accepted | 2025-11-30 |
| [0004](./adr-0004-unsupervised-ml-recurring-charge-detection.md) | Unsupervised ML for Recurring Charge Detection | Accepted | 2025-11-03 |

## Guidelines

1. **Number ADRs sequentially** starting from 0001
2. **Use descriptive titles** that clearly indicate the decision
3. **Keep ADRs immutable** - don't edit after acceptance, create new ADRs instead
4. **Reference related ADRs** when decisions build on or supersede previous ones
5. **Document the "why"** not just the "what" - context is critical
6. **Include implementation details** when they affect the decision
7. **Update this README** when adding new ADRs

