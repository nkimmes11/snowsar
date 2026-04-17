# Contributing to SnowSAR

Thank you for your interest in contributing to SnowSAR! This document provides guidelines for contributing.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/<owner>/snowsar.git
   cd snowsar
   ```

2. Install [uv](https://docs.astral.sh/uv/):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Install dependencies:
   ```bash
   uv sync --extra dev
   ```

4. Run the test suite:
   ```bash
   uv run pytest
   ```

## Development Workflow

1. Create a feature branch from `develop`:
   ```bash
   git checkout -b feature/your-feature develop
   ```

2. Make your changes, ensuring:
   - Tests pass: `uv run pytest`
   - Linting passes: `uv run ruff check .`
   - Formatting is correct: `uv run ruff format .`
   - Types check: `uv run mypy snowsar`

3. Submit a pull request to the `develop` branch.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Use type annotations for all public function signatures
- Code is formatted and linted with [Ruff](https://docs.astral.sh/ruff/)
- Type checking is enforced with [mypy](https://mypy-lang.org/) in strict mode

## Reporting Issues

Use GitHub Issues to report bugs or request features. Please include:
- A clear description of the issue
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
