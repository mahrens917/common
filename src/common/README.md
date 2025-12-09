# Common Module

Shared infrastructure, utilities, and cross-domain primitives live here. Anything that is reused by multiple services should be implemented in this package. Key areas:
- `config/` centralizes environment and configuration helpers.
- `redis_protocol/` defines Redis connection, persistence, and schema tooling.
- `websocket/` implements shared sequencing, validation, and streaming helpers.

When adding new shared functionality, document public APIs here and surface any domain-specific guidance in the relevant domain README.
