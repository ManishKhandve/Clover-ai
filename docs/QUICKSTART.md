# txtai Quick Start

## Installation

Already installed with:
```powershell
pip install -e .
```

## Running Tests

### 1. Basic Semantic Search
```powershell
python test_basic.py
```
Tests semantic search across documents with different queries.

### 2. Search with Content Storage
```powershell
python test_search.py
```
Demonstrates embeddings with content retrieval enabled.

### 3. RAG (Retrieval-Augmented Generation)
```powershell
python test_rag.py
```
**Note:** Requires additional dependencies and an LLM backend.

To install RAG dependencies:
```powershell
pip install -e .[pipeline]
```

## What Just Worked

- **test_basic.py** - Semantic search over 6 documents  
- **test_search.py** - Content-enabled search with full text retrieval

## Next Steps

- Install pipeline extras for QA: `pip install -e .[pipeline]`
- Install API support: `pip install -e .[api]`
- Check `setup.py` for all available extras
