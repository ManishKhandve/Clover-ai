"""
Flask API Server for Real Estate RAG System
Provides REST API endpoints for the web UI
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global RAG instance
rag_system = None
INDEX_PATH = "realestate_index"


def initialize_rag():
    """Initialize or load RAG system"""
    global rag_system
    
    # Lazy import to avoid slow startup
    from realestate_rag import RealEstateRAG
    
    if os.path.exists(INDEX_PATH):
        print("Loading existing index...")
        rag_system = RealEstateRAG(use_llm=True)
        print(f"   Before load: {len(rag_system.documents)} documents")
        rag_system.load_index(INDEX_PATH)
        print(f"   After load: {len(rag_system.documents)} documents")
        print(f"Loaded {len(rag_system.documents)} documents")
    else:
        print("WARNING: No index found. Please ingest documents first.")
        print("   Run: python realestate_chatbot.py ingest <folder>")
        rag_system = None


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status, document count, and memory usage"""
    if rag_system:
        # Get memory usage for large dataset monitoring
        import sys
        memory_info = {}
        try:
            import psutil
            process = psutil.Process()
            memory_info = {
                'memory_mb': round(process.memory_info().rss / (1024 * 1024), 1),
                'memory_percent': round(process.memory_percent(), 1)
            }
        except ImportError:
            memory_info = {'memory_mb': 'N/A (install psutil for monitoring)'}
        
        return jsonify({
            'status': 'ready',
            'documents': len(rag_system.documents),
            'chunks': len(rag_system.chunk_to_doc),
            'llm_available': rag_system.llm is not None,
            'memory': memory_info,
            'scalability': {
                'max_recommended_docs': 10000,
                'current_load_percent': round(len(rag_system.documents) / 100, 1)  # Percentage of 10k
            }
        })
    else:
        return jsonify({
            'status': 'no_index',
            'documents': 0,
            'message': 'No documents indexed. Please ingest documents using the button below.'
        })


@app.route('/api/usage', methods=['GET'])
def get_api_usage():
    """Get API usage statistics"""
    if not rag_system or not rag_system.llm:
        return jsonify({
            'error': 'LLM not available',
            'usage': None
        })
    
    try:
        usage = rag_system.llm.get_usage_stats()
        return jsonify({
            'success': True,
            'usage': usage
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'usage': None
        })


@app.route('/api/usage/reset', methods=['POST'])
def reset_api_usage():
    """Reset API usage statistics"""
    if not rag_system or not rag_system.llm:
        return jsonify({'error': 'LLM not available'})
    
    try:
        rag_system.llm.reset_usage_stats()
        return jsonify({'success': True, 'message': 'Usage stats reset'})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Get list of indexed documents with character counts (excludes authority docs)"""
    if not rag_system:
        return jsonify({'documents': [], 'message': 'No documents loaded yet'})
    
    documents = []
    for doc in rag_system.documents:
        # Skip authority documents - they have their own endpoint
        if doc.get('source_type') == 'AUTHORITY':
            continue
        documents.append({
            'filename': doc['filename'],
            'char_count': doc.get('char_count', len(doc.get('text', ''))),
            'chunks': len(doc.get('chunks', []))
        })
    
    return jsonify({'documents': documents})


@app.route('/api/maharera', methods=['GET'])
def get_maharera_documents():
    """Get list of indexed MahaRERA/authority documents"""
    if not rag_system:
        return jsonify({'documents': [], 'message': 'No documents loaded yet'})
    
    documents = []
    for doc in rag_system.documents:
        # Only include authority documents
        if doc.get('source_type') != 'AUTHORITY':
            continue
        # Title and date are stored directly on document, not in metadata
        documents.append({
            'filename': doc.get('filename', 'Unknown'),
            'title': doc.get('title', doc.get('filename', 'Unknown')),
            'doc_type': doc.get('doc_type', 'unknown'),
            'date': doc.get('date', 'Unknown'),
            'char_count': doc.get('char_count', len(doc.get('text', ''))),
            'chunks': len(doc.get('chunks', [])),
            'precedence': doc.get('precedence', 0)
        })
    
    # Sort by precedence (highest first), then by date
    documents.sort(key=lambda x: (-x['precedence'], x['date'] or ''), reverse=False)
    
    return jsonify({'documents': documents})


@app.route('/api/maharera/update', methods=['POST'])
def update_maharera():
    """Trigger MahaRERA scraper to fetch new compliance documents"""
    try:
        from scraper import MahaRERA_FullScraper
        from document_processor import DocumentProcessor
        from auto_indexer import INDEX_PATH
        import json
        
        print("\nMahaRERA update triggered from frontend...")
        
        # Run scraper
        scraper = MahaRERA_FullScraper()
        scraped = scraper.run(dry_run=False) or []
        
        if not scraped:
            return jsonify({
                'success': True,
                'message': 'No new MahaRERA documents found',
                'new_docs': 0
            })
        
        # Process and add to index
        processor = DocumentProcessor()
        authority_docs = []
        
        for adoc in scraped:
            try:
                if not adoc.get('text') or not adoc.get('filename'):
                    continue
                chunks = processor.chunk_text(adoc['text'])
                if not chunks:
                    continue
                authority_docs.append({
                    'filename': adoc['filename'],
                    'text': adoc['text'],
                    'chunks': chunks,
                    'source_type': adoc.get('source_type'),
                    'authority': adoc.get('authority'),
                    'doc_type': adoc.get('doc_type'),
                    'precedence': adoc.get('precedence'),
                    'metadata': {
                        'title': adoc.get('title'),
                        'date': adoc.get('date'),
                        'url': adoc.get('url'),
                        'num_chunks': len(chunks),
                        'text_length': len(adoc['text'])
                    }
                })
            except Exception as e:
                print(f"WARNING: Failed to process {adoc.get('filename','unknown')}: {e}")
        
        if not authority_docs:
            return jsonify({
                'success': True,
                'message': 'No valid MahaRERA documents to add',
                'new_docs': 0
            })
        
        # Clear and reindex
        global rag_system
        
        # Get existing docs (excluding old authority docs with same filenames)
        new_filenames = {d['filename'] for d in authority_docs}
        existing_docs = [d for d in rag_system.documents if d['filename'] not in new_filenames]
        
        # Rebuild index with merged docs
        all_docs = existing_docs + authority_docs
        
        from realestate_rag import RealEstateRAG
        rag_system = RealEstateRAG(use_llm=True)
        rag_system.index_documents(all_docs)
        rag_system.save_index(INDEX_PATH)
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {len(authority_docs)} MahaRERA document(s)',
            'new_docs': len(authority_docs),
            'total_docs': len(all_docs)
        })
        
    except Exception as e:
        print(f"ERROR: MahaRERA update failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/maharera/delete', methods=['POST'])
def delete_all_maharera():
    """Delete all MahaRERA/authority documents from the index"""
    global rag_system
    
    try:
        from auto_indexer import INDEX_PATH
        from realestate_rag import RealEstateRAG
        
        if not rag_system:
            return jsonify({
                'success': False,
                'message': 'No RAG system loaded'
            }), 400
        
        print("\nDeleting all MahaRERA documents...")
        
        # Count authority docs before deletion
        authority_count = sum(1 for doc in rag_system.documents if doc.get('source_type') == 'AUTHORITY')
        
        if authority_count == 0:
            return jsonify({
                'success': True,
                'message': 'No MahaRERA documents to delete',
                'deleted': 0
            })
        
        # Filter out authority documents, keep only user docs
        user_docs = [doc for doc in rag_system.documents if doc.get('source_type') != 'AUTHORITY']
        
        print(f"Removing {authority_count} authority documents, keeping {len(user_docs)} user documents")
        
        # Rebuild index with only user documents
        rag_system = RealEstateRAG(use_llm=True)
        
        if user_docs:
            rag_system.index_documents(user_docs)
            rag_system.save_index(INDEX_PATH)
        else:
            # No docs left, just save empty state
            rag_system.documents = []
            rag_system.chunk_to_doc = {}
            rag_system.save_index(INDEX_PATH)
        
        # Also clear the scraper metadata so docs can be re-fetched
        scraper_metadata_path = 'extracted_text/metadata.json'
        if os.path.exists(scraper_metadata_path):
            try:
                with open(scraper_metadata_path, 'r', encoding='utf-8') as f:
                    scraper_meta = json.load(f)
                # Clear the documents tracking
                scraper_meta['documents'] = {}
                with open(scraper_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(scraper_meta, f, indent=2)
                print("Cleared scraper metadata for re-fetching")
            except Exception as e:
                print(f"WARNING: Could not clear scraper metadata: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {authority_count} MahaRERA document(s)',
            'deleted': authority_count,
            'remaining_docs': len(user_docs)
        })
        
    except Exception as e:
        print(f"ERROR: MahaRERA delete failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/reindex', methods=['POST'])
def reindex():
    """Trigger auto-indexing of new documents"""
    try:
        # Import here to avoid circular imports
        from auto_indexer import auto_index_on_startup
        
        print("\nManual reindex triggered...")
        
        # Run auto-indexing
        new_docs = auto_index_on_startup()
        
        # Reload RAG system if new documents were indexed
        global rag_system
        if new_docs > 0:
            print("[RELOAD] Reloading RAG system with new documents...")
            # Save current state in case of failure
            old_rag_system = rag_system
            try:
                initialize_rag()
            except Exception as reload_error:
                print(f"WARNING: Failed to reload RAG system: {reload_error}")
                rag_system = old_rag_system  # Restore previous state
                raise
        
        # Get current status
        if rag_system:
            total_docs = len(rag_system.documents)
            message = f"Indexing completed. {new_docs} new documents added." if new_docs > 0 else "No new documents found."
            return jsonify({
                'success': True,
                'message': message,
                'new_docs': new_docs,
                'total_docs': total_docs
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No documents in index',
                'new_docs': 0,
                'total_docs': 0
            })
    except Exception as e:
        print(f"ERROR: Error during reindex: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/query', methods=['POST'])
def query():
    """Process a query and return answer with sources"""
    if not rag_system:
        return jsonify({'error': 'No index loaded'}), 503
    
    data = request.json
    question = data.get('question', '')
    top_k = data.get('top_k', 3)
    language = data.get('language', 'auto')
    # Support both single doc (legacy) and multi-select
    selected_documents = data.get('selected_documents', [])  # List of user doc filenames
    if not selected_documents:
        # Fallback to legacy single doc param
        single_doc = data.get('selected_document')
        if single_doc:
            selected_documents = [single_doc]
    selected_maharera = data.get('selected_maharera', [])  # List of selected MahaRERA filenames
    compliance_check = data.get('compliance_check', False)  # Flag to trigger red flag detection
    
    # Input validation
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    if len(question) > 2000:  # Increased for compliance checks
        return jsonify({'error': 'Question too long (max 2000 characters)'}), 400
    
    if not isinstance(top_k, int) or top_k < 1 or top_k > 10:
        return jsonify({'error': 'Invalid top_k value (must be 1-10)'}), 400
    
    try:
        # Get answer from RAG system
        result = rag_system.answer_query(
            question, 
            top_k=top_k, 
            language=language,
            file_filter=selected_documents,  # Now accepts list of user docs
            authority_filter=selected_maharera,  # Pass selected MahaRERA docs
            compliance_check=compliance_check  # Only run red flag detection if True
        )
        
        return jsonify({
            'answer': result['answer'],
            'sources': result['sources'],
            'query': result['query'],
            'red_flags': result.get('red_flags', []),
            'compliance_results': result.get('compliance_results', []),
            'compliance_summary': result.get('compliance_summary', None),
            'decision': result.get('decision', {'is_red_flag': False, 'override_llm_decision': False, 'is_compliant': True})
        })
    except Exception as e:
        print(f"ERROR: Error processing query: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/batch-process', methods=['POST'])
def batch_process():
    """Process multiple documents for compliance in batch"""
    if not rag_system:
        return jsonify({'error': 'No index loaded'}), 503
    
    data = request.json
    document_ids = data.get('document_ids', [])
    maharera_ids = data.get('maharera_ids', [])
    options = data.get('options', {})
    
    check_red_flags = options.get('redFlags', True)
    check_compliance = options.get('compliance', True)
    
    if not document_ids:
        return jsonify({'error': 'No documents selected for batch processing'}), 400
    
    try:
        from red_flag_detector import detect_red_flags, check_compliance as verify_compliance, get_compliance_summary
        
        batch_results = []
        total_red_flags = 0
        total_critical = 0
        total_missing_clauses = 0
        documents_with_issues = 0
        
        for doc_id in document_ids:
            # Find document in index
            doc_data = None
            for doc in rag_system.documents:
                if doc.get('filename') == doc_id:
                    doc_data = doc
                    break
            
            if not doc_data:
                batch_results.append({
                    'filename': doc_id,
                    'status': 'error',
                    'error': 'Document not found in index'
                })
                continue
            
            # Get full document text from all chunks
            full_text = doc_data.get('text', '')
            if not full_text:
                chunks = doc_data.get('chunks', [])
                full_text = '\n'.join(c.get('text', '') if isinstance(c, dict) else str(c) for c in chunks)
            
            doc_result = {
                'filename': doc_id,
                'status': 'processed',
                'red_flags': [],
                'compliance_results': [],
                'compliance_summary': None
            }
            
            # Get authority chunks for red flag detection
            authority_chunks = []
            if maharera_ids:
                for adoc in rag_system.documents:
                    if adoc.get('source_type') == 'AUTHORITY' and adoc.get('filename') in maharera_ids:
                        for chunk in adoc.get('chunks', []):
                            chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
                            authority_chunks.append({
                                'text': chunk_text,
                                'filename': adoc.get('filename', ''),
                                'source_type': 'AUTHORITY'
                            })
            
            # Red flag detection
            if check_red_flags:
                all_red_flags = []
                seen_rules = set()  # Avoid duplicate flags for same rule
                
                for chunk in doc_data.get('chunks', []):
                    chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
                    if chunk_text:
                        flags = detect_red_flags(chunk_text, authority_chunks)
                        for flag in flags:
                            # Add clause source info
                            flag['clause_source'] = {
                                'filename': doc_id,
                                'excerpt': chunk_text[:200]
                            }
                            # Deduplicate by rule_id
                            if flag['rule_id'] not in seen_rules:
                                all_red_flags.append(flag)
                                seen_rules.add(flag['rule_id'])
                
                doc_result['red_flags'] = all_red_flags
                total_red_flags += len(all_red_flags)
                total_critical += len([f for f in all_red_flags if f.get('severity') == 'CRITICAL'])
            
            # Compliance verification
            if check_compliance:
                compliance_results = verify_compliance(full_text)
                compliance_summary = get_compliance_summary(compliance_results)
                doc_result['compliance_results'] = compliance_results
                doc_result['compliance_summary'] = compliance_summary
                missing = len([r for r in compliance_results if r.get('status') == 'MISSING'])
                total_missing_clauses += missing
            
            # Track documents with issues
            has_issues = len(doc_result.get('red_flags', [])) > 0 or \
                        (doc_result.get('compliance_summary') and not doc_result['compliance_summary'].get('is_compliant', True))
            if has_issues:
                documents_with_issues += 1
            
            batch_results.append(doc_result)
        
        return jsonify({
            'success': True,
            'summary': {
                'total_documents': len(document_ids),
                'processed': len([r for r in batch_results if r.get('status') == 'processed']),
                'documents_with_issues': documents_with_issues,
                'total_red_flags': total_red_flags,
                'total_critical': total_critical,
                'total_missing_clauses': total_missing_clauses
            },
            'results': batch_results
        })
        
    except Exception as e:
        print(f"ERROR: Batch processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """Search documents without LLM generation"""
    if not rag_system:
        return jsonify({'error': 'No index loaded'}), 503
    
    data = request.json
    query_text = data.get('query', '')
    top_k = data.get('top_k', 5)
    
    if not query_text:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        results = rag_system.search(query_text, top_k=top_k)
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ingest', methods=['POST'])
def ingest_documents():
    """Ingest new documents from a folder"""
    # Lazy imports
    from realestate_rag import RealEstateRAG
    from document_processor import DocumentProcessor
    from ocr_engine import FolderOCR
    
    data = request.json
    folder_path = data.get('folder_path', '')
    
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({'error': 'Invalid folder path'}), 400
    
    try:
        # Process documents
        processor = DocumentProcessor(ocr_engine=FolderOCR())
        documents = processor.process_folder(folder_path)
        
        if not documents:
            return jsonify({'error': 'No documents found'}), 400
        
        # Create or update RAG system
        global rag_system
        
        # Initialize new if not exists, otherwise use existing to preserve other docs (if intended)
        # For now, we'll reload existing index first to be safe
        if not rag_system and os.path.exists(INDEX_PATH):
             rag_system = RealEstateRAG(use_llm=True)
             rag_system.load_index(INDEX_PATH)
        elif not rag_system:
             rag_system = RealEstateRAG(use_llm=True)

        # Index new documents (this appends/updates)
        rag_system.index_documents(documents)
        rag_system.save_index(INDEX_PATH)
        
        return jsonify({
            'message': 'Documents ingested successfully',
            'document_count': len(documents),
            'chunk_count': sum(d['metadata']['num_chunks'] for d in documents)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete', methods=['POST'])
def delete_document():
    """Delete a document from index and disk"""
    if not rag_system:
        return jsonify({'error': 'No index loaded'}), 503
        
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
        
    try:
        # Delete from RAG system
        success = rag_system.delete_document(filename)
        
        if success:
            rag_system.save_index(INDEX_PATH)
            
            # Delete actual file
            # Try to get PDF folder from config or auto_indexer
            try:
                from auto_indexer import PDF_FOLDER, TRACKING_FILE
                
                file_path = os.path.join(PDF_FOLDER, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(f"WARNING: Failed to delete file {file_path}: {e}")
                else:
                    print(f"WARNING: File not found on disk: {file_path}")

                # Update tracking file (indexed_documents.txt)
                if os.path.exists(TRACKING_FILE):
                    try:
                        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
                            for line in lines:
                                # Check if it's the exact filename (format is filename:hash)
                                parts = line.strip().split(':')
                                if len(parts) >= 1 and parts[0] != filename:
                                     f.write(line)
                        print(f"Updated tracking file")
                    except Exception as e:
                        print(f"WARNING: Failed to update tracking file: {e}")
            except ImportError:
                print("WARNING: Could not import auto_indexer settings, skipping file deletion")

            return jsonify({'message': f'Document {filename} deleted successfully'})
        else:
            return jsonify({'error': f'Document {filename} not found in index'}), 404
            
    except Exception as e:
        print(f"ERROR: Error deleting document: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_index():
    """Clear the current index"""
    global rag_system
    rag_system = None
    
    return jsonify({'message': 'Index cleared'})


@app.route('/', methods=['GET'])
def index():
    """Serve the web UI"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    return send_from_directory('.', filename)


@app.route('/api', methods=['GET'])
def api_info():
    """API info"""
    return jsonify({
        'name': 'Real Estate RAG API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/status': 'Get server status',
            'GET /api/documents': 'List indexed documents',
            'POST /api/query': 'Ask a question',
            'POST /api/search': 'Search documents',
            'POST /api/ingest': 'Ingest new documents',
            'POST /api/clear': 'Clear index'
        }
    })


if __name__ == '__main__':
    print("="*70)
    print("Starting Real Estate RAG API Server")
    print("="*70)
    
    # Auto-index new documents on startup
    print("\nChecking for new documents to index...")
    try:
        from auto_indexer import auto_index_on_startup
        auto_index_on_startup()
    except Exception as e:
        print(f"WARNING: Auto-indexing skipped: {str(e)}")
    
    # Initialize RAG system
    print("\nLoading RAG system...")
    initialize_rag()
    
    print("\nServer starting on http://localhost:5000")
    print("API docs: http://localhost:5000/api")
    print("Web UI: http://localhost:5000")
    print("="*70 + "\n")
    
    # Run Flask server (debug=False to prevent auto-restart during long OCR operations)
    app.run(host='0.0.0.0', port=5000, debug=False)
