# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials. It combines vector semantic search with AI-powered responses using Anthropic's Claude. The system uses FastAPI for the backend, ChromaDB for vector storage, and a vanilla JavaScript frontend.

## Development Setup

### Prerequisites
- Python 3.13+ (specified in `.python-version`)
- `uv` package manager (modern Python package manager)

### Initial Setup
```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY and ZHIPUAI_API_KEY
```

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application starts at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Architecture

### Core Components

**RAG System (`backend/rag_system.py`)**
- Main orchestrator that coordinates all components
- Handles document ingestion (single files or entire folders)
- Prevents duplicate course processing by checking existing titles
- Manages query flow through vector search → AI generation → response formatting

**Vector Store (`backend/vector_store.py`)**
- **Dual ChromaDB collections architecture:**
  - `course_catalog`: Stores course metadata (title, instructor, link, lessons) for semantic course name resolution
  - `course_content`: Stores text chunks with metadata (course_title, lesson_number, chunk_index)
- Search interface handles course name fuzzy matching via `course_catalog`, then filters content in `course_content`
- Uses ZhipuAI embeddings (`embedding-3`, 2048 dimensions) via `ZhipuEmbeddingFunction`

**Document Processor (`backend/document_processor.py`)**
- Parses structured course documents with expected format:
  ```
  Course Title: [title]
  Course Link: [url]
  Course Instructor: [instructor]
  Lesson 0: [lesson title]
  Lesson Link: [url]
  [lesson content...]
  ```
- Sentence-based chunking with configurable overlap (default: 800 chars, 100 char overlap)
- Each chunk gets context prefix (e.g., "Course [title] Lesson [N] content:")

**AI Generator (`backend/ai_generator.py`)**
- Interfaces with Anthropic's Claude API
- Static system prompt defines tool usage behavior and response protocol
- Handles tool execution flow: request → tool use → tool result → final response
- Temperature set to 0 for consistent responses

**Tool System (`backend/search_tools.py`)**
- Abstract `Tool` protocol for extensibility
- `CourseSearchTool`: Main search tool with course name and lesson filtering
- `ToolManager`: Registry pattern for tool management, source tracking, and execution
- Tools are exposed to Claude via Anthropic's tool calling API

**Session Manager (`backend/session_manager.py`)**
- In-memory conversation state management
- Maintains limited conversation history (configurable, default: 2 exchanges)

### Data Flow

**Query Processing:**
1. User submits query via frontend → `/api/query` endpoint
2. Query routed to `RAGSystem.query()` with session ID
3. AI generator calls Claude with search tool available
4. If Claude uses tool, `ToolManager` executes `CourseSearchTool`
5. Tool searches vector store (course name resolution → content search)
6. Tool results returned to Claude for final response generation
7. Sources extracted from tool and returned with response

**Document Ingestion:**
1. Documents loaded from `/docs` folder on startup
2. `DocumentProcessor` parses structure and extracts metadata
3. Course metadata added to `course_catalog` collection
4. Content chunked and added to `course_content` collection
5. Existing courses checked by title to prevent duplicates

### Key Design Patterns

- **Repository Pattern**: `VectorStore` abstracts ChromaDB operations
- **Strategy Pattern**: Pluggable document chunking via `DocumentProcessor`
- **Tool Pattern**: Extensible search tools with uniform interface
- **Protocol-based Design**: Abstract `Tool` base class using Python ABC
- **Dual Collection Architecture**: Separation of metadata and content for efficient filtering

## Configuration

All configuration in `backend/config.py`:
- `ANTHROPIC_API_KEY`: Required for Claude API access
- `ZHIPUAI_API_KEY`: Required for ZhipuAI embedding API access (get at https://open.bigmodel.cn/)
- `ZHIPUAI_MODEL`: "embedding-3" (2048-dimensional vectors)
- `CHUNK_SIZE`: 800 characters (text chunk size)
- `CHUNK_OVERLAP`: 100 characters (chunk overlap)
- `MAX_RESULTS`: 5 (search results limit)
- `MAX_HISTORY`: 2 (conversation exchanges to remember)
- `CHROMA_PATH`: "./chroma_db" (vector database location)
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"

## Frontend

Vanilla JavaScript application in `/frontend`:
- `index.html`: Main HTML structure
- `script.js`: API interaction and UI logic
- `style.css`: Dark theme with responsive design
- Features: suggested questions, collapsible sources, markdown rendering

## File Structure Notes

- `/docs`: Course material documents (auto-loaded on startup)
- `/backend`: All Python backend code
- `/frontend`: Static web assets
- `run.sh`: Development startup script
- `pyproject.toml`: Modern Python project configuration (no setup.py)
- `.python-version`: Specifies Python 3.13 requirement

## Development Notes

- **Package Manager**: Uses `uv` instead of pip/poetry
- **Python Version**: Requires Python 3.13+
- **Database**: ChromaDB with persistent storage in `./chroma_db`
- **Embedding Model**: ZhipuAI `embedding-3` (2048 dimensions, requires internet connection)
- **CORS**: Fully enabled for development
- **Static Files**: Served from `/frontend` with no-cache headers for development
- **Startup**: Automatically loads documents from `/docs` folder on server start
- **Network Dependency**: Application requires internet access for embedding generation

## Working with Tools

To add a new search capability:

1. Create new class inheriting from `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` returning Anthropic tool schema
3. Implement `execute(**kwargs)` method
4. Register in `RAGSystem.__init__`: `self.tool_manager.register_tool(NewTool(self.vector_store))`

The tool will automatically be available to Claude for use in queries.

