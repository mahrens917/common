# Common

Shared Python utilities library used across multiple trading system repositories.

## Installation

This package is designed to be used as a local dependency. Clone the repository and add it to your PYTHONPATH or install in development mode.

## Structure

```
common/
├── src/common/           # Source code
├── tests/                # Test suite
├── config/               # Configuration files
├── scripts/              # CI and utility scripts
├── CLAUDE.md             # Claude Code guide
├── Makefile              # Build automation
└── pyproject.toml        # Project configuration
```

## Usage

```python
from common import <module>
```

## Development

### Prerequisites
- Python 3.12+
- ci_shared repository cloned to `~/ci_shared`

### Running CI
```bash
make check
# or
./scripts/ci.sh
```

### Running Tests
```bash
pytest tests/ --cov=src --cov-fail-under=80
```

## License

Private - All rights reserved.
