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

# Tradeoffs

# What I did not do?