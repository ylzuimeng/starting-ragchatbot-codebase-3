# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Code Quality

This project uses automated code quality tools to maintain consistent code style and catch potential issues.

### Tools

- **Black**: Code formatter for consistent Python code style
- **isort**: Import statement organizer
- **ruff**: Fast Python linter for catching errors and style issues
- **pytest**: Testing framework

### Available Scripts

#### Check Code Quality (Read-only)

Run all quality checks without modifying files:
```bash
./scripts/check-quality.sh
```

This script checks:
- Code formatting with Black
- Import ordering with isort
- Linting with ruff
- Test suite with pytest

#### Format Code (Auto-fix)

Automatically fix formatting and import issues:
```bash
./scripts/format.sh
```

This script will:
- Format code with Black
- Organize imports with isort
- Fix auto-fixable ruff issues

#### Manual Tool Usage

You can also run individual tools:
```bash
# Check formatting
uv run black --check backend/*.py backend/tests/*.py main.py

# Format code
uv run black backend/*.py backend/tests/*.py main.py

# Check imports
uv run isort --check-only backend/*.py backend/tests/*.py main.py

# Fix imports
uv run isort backend/*.py backend/tests/*.py main.py

# Run linter
uv run ruff check backend/*.py backend/tests/*.py main.py

# Fix linter issues
uv run ruff check --fix backend/*.py backend/tests/*.py main.py

# Run tests
uv run pytest backend/tests/ -v
```

### Configuration

Code quality tools are configured in `pyproject.toml`:
- Line length: 100 characters
- Python version: 3.13
- Black, isort, and ruff profiles are coordinated for consistency

