# Tech Stack
- Backend: Flask + SQLite
- Frontend: Vanilla JS (HTML/CSS)
- Deployment: <yet to decide>

# Key Design Decisions

## 1. Money Representation
I chose to store monetary values as integers in paise (smallest currency unit) instead of floating point.

Alternatives considered:
- Floating point (e.g., 123.45)
  - Pros: simple, intuitive
  - Cons: precision errors due to binary representation
- Decimal types
  - Pros: exact arithmetic
  - Cons: added complexity for this time-constrained task

Chosen approach:
- Integer (paise)
  - Pros: exact arithmetic, simple aggregation, avoids rounding errors
  - Cons: requires conversion at API/UI boundary

This approach mirrors production systems like Expensify and ensures correctness in calculations.

## 2. Idempotency Handling
To handle retries and duplicate submissions, I implemented idempotency using an `Idempotency-Key` header.

Alternatives considered:
- Client request ID in body (simpler but mixes concerns)
- Payload-based deduplication (unreliable and incorrect if identical expenses are submitted intentionally)

Chosen approach:
- Header-based idempotency
  - Ensures correctness under retries
  - Aligns with real-world API design patterns (e.g., Stripe)
  - Keeps business data separate from transport metadata

- Idempotency records are stored only after successful expense creation to ensure failed requests can be safely retried.

## 3. Persistence Strategy

I chose SQLite as the persistence layer.

Alternatives considered:
- In-memory store
  - Pros: fastest to implement
  - Cons: data loss on restart, not realistic for production
- JSON/file storage
  - Pros: simple
  - Cons: poor concurrency handling, harder querying
- Full relational DB (Postgres)
  - Pros: production-ready
  - Cons: setup overhead not justified for time constraint

Chosen approach:
- SQLite
  - Pros: persistent, supports transactions, minimal setup
  - Cons: limited scalability (acceptable for this scope)

This balances production realism with speed of development.

## 4. Validation Strategy

Validation is performed primarily at the backend.

Key rules:
- Amount must be positive, numeric, ≤ 1,000,000,000.00, and have at most two decimal places
- Category and description must be non-empty
- Date must be valid ISO format (YYYY-MM-DD)

Alternatives considered:
- Frontend-only validation
  - Pros: faster feedback
  - Cons: unsafe, easily bypassed

Chosen approach:
- Backend validation (with minimal frontend checks if time permits)
  - Ensures correctness regardless of client behavior

## 5. Error Handling Strategy

All API errors follow a consistent response schema:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable explanation"
}
```

## 6. Request Deduplication Strategy
To detect conflicting idempotent requests, I compute a deterministic hash of the normalized request payload.

- Payload is normalized (trimmed, canonicalized, sorted JSON)
- Then hashed to compare equality across retries

Alternatives considered:
- Direct JSON comparison (sensitive to ordering/formatting)
- Storing raw payload (less efficient and harder to compare)

Chosen approach:
- Deterministic hashing (SHA-256)
  - Ensures consistent comparison
  - Avoids false mismatches due to JSON formatting differences

# Tradeoffs
- Chose SQLite over a production DB (e.g., Postgres) to reduce setup time, accepting limited scalability.
- Stored money as integer paise instead of using Decimal for simplicity, while still ensuring correctness.
- Implemented header-based idempotency instead of more complex distributed approaches due to single-instance scope.
- Kept frontend minimal (no framework) to prioritize backend correctness and reduce development overhead.
- Limited error and loading UI states to basic handling due to time constraints.

# What I did not do
- No authentication or user accounts (assumed single-user system)
- No pagination for expenses list
- No advanced UI states (loading indicators, retries, optimistic updates)
- No cleanup/TTL mechanism for idempotency keys
- No currency conversion or multi-currency support
- No comprehensive automated test suite (only minimal validation tests if time permits)