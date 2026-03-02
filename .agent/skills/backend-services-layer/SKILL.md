---
name: Backend Services Layer
description: Business logic orchestration, testing requirements, error throwing conventions, and general architecture.
---

# Backend Services & Architecture Conventions

## Core Component Interactions
All business logic is isolated within the `services/` layer. It must act as the orchestrator between handlers and actual backend systems:
- Receive deeply-validated DTOs and User constraints from `handlers/` decorators.
- Push validation rules into `models/` (Pydantic).
- Run complex logic, event throwing, or cross-model transaction loops inside the service.
- Outsource persistence directly to `utils/db_utils/`.

## Error Handling Philosophy
1. When encountering errors, immediately diagnose and fix the root causes instead of adding blanket defensive checks like `if not None:`.
2. Don't add generic defensive checks. Create a comprehensive failing unit test first, then fix the root cause behavior cleanly.
3. Always add a stack trace to broad exception-handling code to aid debugging.

## Unit Testing Strictness
1. Run all tests via `backend/run_tests.sh`.
2. Do not merge logic unless a corresponding failing unit test was created *first* and then solved by the commit.
3. Test edge cases explicitly: ensure `.value` attribute access works properly on nested enums without throwing `AttributeError`.

## Background / Event Execution Defaults
1. Always use Python 3.12 runtime.
2. Ensure the backend explicit `venv` is activated during all test or build scripts (do not rely on global system Python).
3. Use `python3` command prefix explicitly rather than just `python`.

## Batch Operations Pattern in Services
When bulk processing lists (e.g. `bulk_mark_transfers`):
Provide standard metric aggregations in the service response so handlers can cleanly return `successful`, `failed`, `successCount`, and `failureCount`. Wrap each list item in an independent try-except to avoid tearing down the batch processing entirely on one bad record.
