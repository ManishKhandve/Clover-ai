# Configuration Guide

## Quick Start

Your RAG system now uses flexible configuration. Three ways to configure (in priority order):

### 1. Environment Variables (Highest Priority)
```bash
# Windows PowerShell
$env:RAG_PDF_FOLDER="C:\path\to\pdfs"
$env:POPPLER_PATH="C:\path\to\poppler\bin"

# Or create .env file (copy from .env.example)
```

### 2. config.json File
Edit `config.json` in the txtai directory:
```json
{
  "pdf_folder": "C:\\Users\\manis\\Downloads\\cloverrag",
  "index_path": "realestate_index",
  "tracking_file": "indexed_documents.txt"
}
```

### 3. Defaults (Fallback)
If no config is set, uses current paths.

## Configuration Options

### config.json Structure
```json
{
  "pdf_folder": "Path to PDF folder",
  "index_path": "Index directory name",
  "tracking_file": "MD5 tracking file name",
  "ocr_settings": {
    "dpi": 200,
    "batch_size": 10,
    "language": "mr"
  },
  "rag_settings": {
    "chunk_size": 400,
    "chunk_overlap": 50,
    "top_k": 3
  },
  "llm_settings": {
    "model": "llama3",
    "base_url": "http://localhost:11434",
    "temperature": 0.3,
    "max_tokens": 500
  }
}
```

## Bug Fixes Applied

- **Memory Efficiency**: Large PDFs now process in 10-page batches
- **Error Handling**: Safe type conversion for chunk IDs
- **Validation**: Minimum 50-char text length requirement
- **Path Safety**: Fixed filename handling with multiple dots
- **State Recovery**: Preserves RAG system on reindex failure
- **Flexible Config**: No more hardcoded paths

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_PDF_FOLDER` | PDF directory to monitor | `C:\Users\manis\Downloads\cloverrag` |
| `POPPLER_PATH` | Poppler binaries path | `C:\Program Files\poppler-24.08.0\Library\bin` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `llama3` |

## Usage

1. Edit `config.json` with your paths
2. Or set environment variables
3. Run server: `python api_server.py`
4. System auto-detects configuration

No code changes needed to use on different machines!
