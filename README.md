# GitLab Ticker

A Python project for tracking and analyzing GitLab repositories using Domain-Driven Development (DDD) architecture.

## Overview

GitLab Ticker is designed to provide tools and services for working with GitLab repositories, including validation utilities and analysis capabilities. The project follows a clean architecture pattern with clear separation of concerns.

## Features

### Current Features

- **Commit Validation Script**: A utility script (`validate_commits.py`) that validates git repository parameters:
  - Validates repository path and ensures it's a valid git repository
  - Validates branch existence
  - Validates commit hashes
  - Ensures commit ordering (commit B must be more recent than commit A)
  - Automatically uses the latest commit on a branch if commit B is not specified

## Requirements

- Python 3.12+
- Poetry (for dependency management)
- Git (for repository operations)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd gitlab-ticker
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

## Usage

### Commit Validation Script

The `validate_commits.py` script validates git repository parameters for commit comparison:

```bash
python validate_commits.py <repo_path> <branch_name> <commit_a> [commit_b]
```

**Parameters:**
- `repo_path`: Path to the git repository directory
- `branch_name`: Name of the branch to validate
- `commit_a`: Hash of the older commit (commit A)
- `commit_b`: (Optional) Hash of the newer commit (commit B). If not provided, defaults to the latest commit on the specified branch

**Example:**
```bash
python validate_commits.py /path/to/repo main abc123 def456
```

Or without specifying commit B (uses latest commit on branch):
```bash
python validate_commits.py /path/to/repo main abc123
```

**Exit Codes:**
- `0`: All parameters are valid
- `1`: Validation failed with error message

## Project Structure

The project follows a Domain-Driven Development (DDD) architecture:

```
gitlab_ticker/
  <domain_name>/
    domain/          # Domain entities and value objects
    repositories/    # Repository interfaces and implementations
    services/        # Business services
```

See `.cursorrules` for detailed architecture guidelines.

## Development

### Using Poetry

- Install dependencies: `poetry install`
- Add a dependency: `poetry add <package>`
- Add a development dependency: `poetry add --group dev <package>`
- Activate virtual environment: `poetry shell`
- Run commands in virtual environment: `poetry run <command>`
- Update dependencies: `poetry update`

### Code Standards

- All code, documentation, and comments must be in English
- Follow DDD architecture principles
- Write unit tests for domains, repositories, and services
- Keep README.md updated when adding new features
- **All code must be fully typed** with type hints (annotations)

### Code Quality Tools

The project uses **mypy** for type checking and **ruff** for linting and code formatting.

#### Type Checking with mypy

Check type correctness:
```bash
poetry run mypy .
```

All code must pass mypy type checks before committing. The project is configured with strict type checking enabled.

#### Linting and Formatting with ruff

Check code quality and style:
```bash
poetry run ruff check .
```

Format code:
```bash
poetry run ruff format .
```

**Important**: Every code change must be validated by both mypy and ruff before completion. Fix all errors and warnings before committing code.

## License

[Add license information here]

## Authors

- Pierre Rossinès <pierre.rossines@gmail.com>

