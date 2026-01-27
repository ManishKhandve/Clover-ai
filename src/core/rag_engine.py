"""
Real Estate Agreement RAG System - Core RAG Engine
Multilingual embeddings and retrieval system for real estate documents
"""
import json
import os
from typing import List, Dict, Tuple, Optional
from txtai import Embeddings
from gemini_llm import GeminiLLM


class RealEstateRAG:
    """RAG system for real estate agreement documents with multilingual support"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", use_llm: bool = True):
        """
        Initialize RAG system with multilingual model
        
        Args:
            model_name: Hugging Face model for embeddings
                      Default supports 50+ languages including English and Marathi
            use_llm: Whether to use Gemini for answer generation
        """
        print("Initializing Real Estate RAG System...")
        
        # Load config
        self.config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                self.config = json.load(f)
        
        # Configure embeddings with content storage and multilingual model
        # Optimized for 1000+ documents
        self.embeddings = Embeddings({
            "path": model_name,
            "content": True,  # Store full text for retrieval
            "backend": "faiss",  # FAISS handles millions of vectors efficiently
            "faiss": {
                "quantize": True,  # 4x compression - critical for 1000+ docs (reduces memory ~75%)
                "sample": 0.1,  # 10% sample for IVF training (balances accuracy & speed)
                "nprobe": 6  # Search 6 clusters (good balance for 1000+ docs)
            },
            "batch": 64,  # Batch size for embedding generation
            "normalize": True  # Normalize vectors for cosine similarity
        })
        
        self.documents = []
        self.chunk_to_doc = {}  # Map chunk ID to document info
        
        # Initialize LLM
        self.use_llm = use_llm
        self.llm = None
        if use_llm:
            llm_settings = self.config.get("llm_settings", {})
            
            # Default to Gemini
            api_key = llm_settings.get("gemini_api_key")
            model = llm_settings.get("model", "gemini-1.5-flash")
            
            if api_key:
                self.llm = GeminiLLM(api_key, model)
                if self.llm.is_available():
                    print(f"LLM connected via Gemini ({model})")
                else:
                    print("WARNING: Gemini not available, falling back to simple synthesis")
                    self.llm = None
            else:
                print("WARNING: No Gemini API key found in config.json")
                self.llm = None
    
    def delete_document(self, filename: str) -> bool:
        """
        Delete a document and its chunks from the index
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        print(f"Deleting document: {filename}")
        
        # Find chunks to delete
        chunks_to_delete = []
        for chunk_id, info in self.chunk_to_doc.items():
            if info.get('filename') == filename:
                chunks_to_delete.append(chunk_id)
        
        if not chunks_to_delete:
            print(f"WARNING: No chunks found for {filename}")
            # Even if no chunks found, check if it's in documents list and remove it
            initial_doc_count = len(self.documents)
            self.documents = [doc for doc in self.documents if doc.get('filename') != filename]
            if len(self.documents) < initial_doc_count:
                print(f"Removed {filename} from documents list (no chunks found)")
                return True
            return False
            
        print(f"Found {len(chunks_to_delete)} chunks to delete")
        
        # Delete from embeddings
        try:
            self.embeddings.delete(chunks_to_delete)
        except Exception as e:
            print(f"ERROR: Failed to delete from embeddings: {e}")
            # Continue to clean up metadata even if embeddings fail
        
        # Clean up metadata
        for chunk_id in chunks_to_delete:
            if chunk_id in self.chunk_to_doc:
                del self.chunk_to_doc[chunk_id]
                
        # Remove from documents list
        self.documents = [doc for doc in self.documents if doc.get('filename') != filename]
        
        print(f"Successfully deleted {filename}")
        return True
        
    def index_documents(self, documents: List[Dict]):
        """
        Index processed documents into the embeddings database
        
        Args:
            documents: List of processed document dicts from DocumentProcessor
        """
        if not documents:
            print("WARNING: No documents to index")
            return
            
        print(f"\nIndexing {len(documents)} documents...")
        
        # Validate all documents before processing
        valid_documents = []
        for idx, doc in enumerate(documents):
            # Check required fields
            if not isinstance(doc, dict):
                print(f"   WARNING: Skipping document {idx}: not a dictionary")
                continue
            if not doc.get('filename'):
                print(f"   WARNING: Skipping document {idx}: missing filename")
                continue
            if not doc.get('text'):
                print(f"   WARNING: Skipping document {idx} ({doc['filename']}): no text content")
                continue
            if not doc.get('chunks') or not isinstance(doc.get('chunks'), list):
                print(f"   WARNING: Skipping document {idx} ({doc['filename']}): no valid chunks")
                continue
            if len(doc.get('text', '')) < 50:
                print(f"   WARNING: Skipping document {idx} ({doc['filename']}): text too short ({len(doc['text'])} chars)")
                continue
            valid_documents.append(doc)
        
        if not valid_documents:
            print("ERROR: No valid documents to index after validation")
            return
            
        print(f"   Validated {len(valid_documents)}/{len(documents)} documents")
        
        # Determine start offsets for appending
        start_doc_idx = len(self.documents)
        
        # Find the next available chunk_id
        start_chunk_id = 0
        if self.chunk_to_doc:
            start_chunk_id = max(self.chunk_to_doc.keys()) + 1
            
        print(f"   Using start_doc_idx={start_doc_idx}, start_chunk_id={start_chunk_id}")
        
        # Prepare data for indexing: (id, text, metadata)
        data = []
        chunk_id = start_chunk_id
        
        for i, doc in enumerate(valid_documents):
            doc_idx = start_doc_idx + i
            
            # Calculate total character count for this document
            doc_char_count = len(doc.get('text', ''))
            
            for chunk_idx, chunk in enumerate(doc['chunks']):
                # Skip empty or invalid chunks
                if not chunk or not isinstance(chunk, str) or len(chunk.strip()) < 10:
                    print(f"   WARNING: Skipping empty chunk {chunk_idx} in {doc['filename']}")
                    continue
                    
                # Store metadata for each chunk
                chunk_meta = {
                    'doc_id': doc_idx,
                    'filename': doc['filename'],
                    'chunk_idx': chunk_idx,
                    'char_count': doc_char_count
                }
                # Optional authority metadata per chunk (if present on document)
                if 'source_type' in doc:
                    chunk_meta['source_type'] = doc.get('source_type')
                if 'doc_type' in doc:
                    chunk_meta['doc_type'] = doc.get('doc_type')
                if 'precedence' in doc:
                    chunk_meta['precedence'] = doc.get('precedence')
                # Keep authority name if provided (e.g., MahaRERA)
                if 'authority' in doc:
                    chunk_meta['authority'] = doc.get('authority')
                self.chunk_to_doc[chunk_id] = chunk_meta
                
                # txtai expects metadata as None or simple types, not dict
                data.append({
                    'id': chunk_id,
                    'text': chunk.strip(),
                    'filename': doc['filename'],
                    'chunk_idx': chunk_idx
                })
                chunk_id += 1
        
        # Index all chunks - optimized for large datasets
        if data:
            total_chunks = len(data)
            print(f"\nBuilding FAISS index with {total_chunks} vectors...")
            
            # For large datasets (1000+ docs, ~10k+ chunks), use batched indexing
            if total_chunks > 5000:
                print(f"   Large dataset detected - using batched indexing...")
                batch_size = 2000
                for i in range(0, total_chunks, batch_size):
                    batch = data[i:i+batch_size]
                    progress = min(100, int((i + len(batch)) / total_chunks * 100))
                    print(f"   Indexing batch {i//batch_size + 1}: {progress}% ({i+len(batch)}/{total_chunks})")
                    if i == 0:
                        self.embeddings.index(batch)
                    else:
                        self.embeddings.upsert(batch)
            else:
                self.embeddings.index(data)
            
            # Append new documents to the master list
            self.documents.extend(valid_documents)
            print(f"[OK] Indexed {total_chunks} chunks from {len(valid_documents)} documents")
            print(f"   Total documents in system: {len(self.documents)}")
        else:
            print("WARNING: No chunks to index.")
        
        # Store document stats for display
        for doc in self.documents:
            doc['char_count'] = len(doc.get('text', ''))
        
        print(f"Indexed {chunk_id - start_chunk_id} chunks from {len(valid_documents)} documents")
    
    def search(self, query: str, top_k: int = 5, file_filter: list = None, authority_filter: list = None) -> List[Dict]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query (English or Marathi)
            top_k: Number of results to return
            file_filter: Optional list of user doc filenames to include
            authority_filter: Optional list of authority doc filenames to include
            
        Returns:
            List of search results with metadata
        """
        # Normalize file_filter to list
        if file_filter and isinstance(file_filter, str):
            file_filter = [file_filter]
        
        # Determine if we need filtering
        has_file_filter = file_filter and len(file_filter) > 0
        has_authority_filter = authority_filter and len(authority_filter) > 0
        needs_filtering = has_file_filter or has_authority_filter
        
        if needs_filtering:
            print(f"Searching with filters: user_docs={len(file_filter) if file_filter else 0}, authority_docs={len(authority_filter) if authority_filter else 0}")
            # Post-filtering strategy:
            # Fetch more results than needed to ensure we find enough matches
            search_limit = top_k * 15  # Fetch 15x results for better coverage
            results = self.embeddings.search(query, search_limit)
            
            # Filter results
            filtered_results = []
            for result in results:
                try:
                    chunk_id = result.get('id')
                    if chunk_id is None:
                        continue
                    # Handle string IDs
                    if isinstance(chunk_id, str):
                        chunk_id = int(chunk_id)
                    elif not isinstance(chunk_id, int):
                        continue
                    
                    chunk_info = self.chunk_to_doc.get(chunk_id, {})
                    chunk_filename = chunk_info.get('filename', '')
                    chunk_source_type = chunk_info.get('source_type', 'USER')
                    
                    # Check if this chunk matches our filters
                    include_chunk = False
                    
                    # Handle user documents (source_type != 'AUTHORITY')
                    if chunk_source_type != 'AUTHORITY':
                        if has_file_filter:
                            # If file_filter specified, include matching user docs
                            if chunk_filename in file_filter:
                                include_chunk = True
                        else:
                            # No specific user doc filter - include all user docs
                            include_chunk = True
                    
                    # Handle authority documents
                    if chunk_source_type == 'AUTHORITY':
                        if has_authority_filter and chunk_filename in authority_filter:
                            include_chunk = True
                    
                    if include_chunk:
                        filtered_results.append(result)
                        
                    if len(filtered_results) >= top_k:
                        break
                except (ValueError, TypeError, KeyError) as e:
                    print(f"   WARNING: Error filtering result: {e}")
                    continue
            
            results = filtered_results
        else:
            results = self.embeddings.search(query, top_k)
        
        print(f"   Found {len(results)} results after filtering")
        
        formatted_results = []
        for result in results:
            try:
                chunk_id = result['id']
                # Convert to int if it's a string (txtai sometimes returns string IDs)
                if isinstance(chunk_id, str):
                    chunk_id = int(chunk_id)
                elif not isinstance(chunk_id, int):
                    print(f"   WARNING: Skipping result with invalid ID type")
                    continue
            except (ValueError, TypeError, KeyError) as e:
                print(f"   WARNING: Error converting chunk ID: {e}")
                continue
            
            chunk_info = self.chunk_to_doc.get(chunk_id)
            if not chunk_info:
                print(f"   WARNING: No metadata for chunk {chunk_id}, skipping")
                continue
                
            chunk_idx = chunk_info.get('chunk_idx', 0)
            filename = chunk_info.get('filename', 'Unknown')
            
            # Validate text content exists
            text_content = result.get('text', '').strip()
            if not text_content:
                print(f"   WARNING: Empty text in chunk {chunk_id}, skipping")
                continue
            
            # Create descriptive section label
            section = f"Section {chunk_idx + 1}"
            
            formatted_results.append({
                'id': chunk_id,
                'text': text_content,
                'score': result.get('score', 0.0),
                'filename': filename,
                'chunk_idx': chunk_idx,
                'section': section,
                'source_type': chunk_info.get('source_type', 'USER')
            })
        
        return formatted_results
    
    def get_context(self, query: str, top_k: int = 3, file_filter: list = None, authority_filter: list = None) -> Tuple[str, List[Dict]]:
        """
        Get context for RAG generation
        
        Args:
            query: Search query
            top_k: Number of results
            file_filter: Optional list of user doc filenames to include
            authority_filter: Optional list of authority doc filenames to include
        
        Returns:
            (context_text, source_documents)
        """
        results = self.search(query, top_k, file_filter, authority_filter)
        
        # Combine top results into context
        context_parts = []
        for idx, result in enumerate(results, 1):
            section = result.get('section', f"Section {result['chunk_idx'] + 1}")
            context_parts.append(
                f"[Source {idx}: {result['filename']} - {section}]\n"
                f"{result['text']}"
            )
        
        context = "\n\n".join(context_parts)
        
        # Debug: Print retrieved context
        print(f"\nContext retrieved for query: '{query}'")
        print("-" * 50)
        print(context[:500] + "..." if len(context) > 500 else context)
        print("-" * 50)
        
        return context, results
    
    def answer_query(self, query: str, top_k: int = 3, language: str = 'auto', file_filter: list = None, authority_filter: list = None, compliance_check: bool = False) -> Dict:
        """
        Answer a query using RAG with Llama 3
        
        Args:
            query: The question to answer
            top_k: Number of results to retrieve
            language: Language preference ('auto', 'english', 'marathi')
            file_filter: Optional list of user doc filenames to include
            authority_filter: Optional list of authority doc filenames to include
            compliance_check: If True, run comprehensive red flag detection
        
        Returns:
            {
                'query': str,
                'context': str,
                'sources': List[Dict],
                'answer': str (from Llama 3 or synthesized)
            }
        """
        context, sources = self.get_context(query, top_k, file_filter, authority_filter)

        # Check if user is asking about red flags in their query
        red_flag_keywords = ['red flag', 'redflag', 'red flags', 'redflags', 'violation', 'violations', 
                             'non-compliant', 'noncompliant', 'issue', 'issues', 'problem', 'problems',
                             'check compliance', 'compliance check', 'verify compliance']
        query_lower = query.lower()
        is_red_flag_query = any(kw in query_lower for kw in red_flag_keywords)
        
        # Run compliance check if explicitly requested OR if user is asking about red flags
        should_run_compliance = compliance_check or is_red_flag_query

        # Red flag detection layer - runs on explicit compliance checks OR red flag queries
        red_flags = []
        compliance_results = []
        compliance_summary = {}
        is_red = False
        has_any_flags = False
        
        if should_run_compliance:
            print(f"   Running compliance check (explicit: {compliance_check}, query-triggered: {is_red_flag_query})...")
            try:
                from .red_flag_detector import detect_red_flags, check_compliance, get_compliance_summary
            except ImportError:
                from red_flag_detector import detect_red_flags, check_compliance, get_compliance_summary  # fallback import

            # Separate user doc chunks from authority chunks (from search results)
            retrieved_user_chunks = [s for s in (sources or []) if s.get('source_type') != 'AUTHORITY']
            authority_chunks = [s for s in (sources or []) if s.get('source_type') == 'AUTHORITY']
            
            # IMPORTANT: For comprehensive red flag detection, scan ALL chunks of selected user documents
            # not just the semantically retrieved ones (problematic clauses may not match search query)
            all_user_chunks = []
            full_user_doc_text = ""  # Combine all text for compliance check
            if file_filter:
                for doc in self.documents:
                    if doc.get('filename') in file_filter and doc.get('source_type', 'USER') != 'AUTHORITY':
                        # Get full document text for compliance verification
                        full_user_doc_text += " " + doc.get('text', '')
                        # Get all chunks from this document
                        doc_chunks = doc.get('chunks', [])
                        for idx, chunk_text in enumerate(doc_chunks):
                            all_user_chunks.append({
                                'text': chunk_text,
                                'filename': doc.get('filename'),
                                'section': f"Section {idx + 1}",
                                'chunk_idx': idx,
                                'source_type': 'USER'
                            })
                print(f"   Red flag scan: {len(all_user_chunks)} chunks from {len(file_filter)} user doc(s)")
            else:
                # Fallback to retrieved chunks if no file filter
                all_user_chunks = retrieved_user_chunks
                for chunk in all_user_chunks:
                    full_user_doc_text += " " + chunk.get('text', '')
            
            # Run COMPLIANCE VERIFICATION - check for required clauses
            print("   Running compliance verification (checking required clauses)...")
            compliance_results = check_compliance(full_user_doc_text)
            compliance_summary = get_compliance_summary(compliance_results)
            print(f"   Compliance: {compliance_summary['compliant_count']}/{compliance_summary['total_checks']} checks passed")
            
            # Run red flag detection on ALL user document chunks against authority
            all_red_flags = []
            for user_chunk in all_user_chunks:
                clause_text = user_chunk.get('text', '')
                if not clause_text:
                    continue
                flags = detect_red_flags(clause_text, authority_chunks)
                for flag in flags:
                    # Attach source info to each flag
                    flag['clause_source'] = {
                        'filename': user_chunk.get('filename', 'unknown'),
                        'section': user_chunk.get('section', ''),
                        'excerpt': clause_text[:200]
                    }
                    all_red_flags.append(flag)
            
            # Also check the query itself in case user pastes a clause directly
            query_flags = detect_red_flags(query, authority_chunks)
            for flag in query_flags:
                flag['clause_source'] = {'filename': 'user_query', 'section': '', 'excerpt': query[:200]}
                all_red_flags.append(flag)
            
            # Deduplicate by rule_id + clause excerpt
            seen = set()
            for f in all_red_flags:
                key = (f['rule_id'], f.get('clause_source', {}).get('excerpt', '')[:50])
                if key not in seen:
                    seen.add(key)
                    red_flags.append(f)

            is_red = any(f.get('severity') in ('HIGH', 'CRITICAL') for f in red_flags)
            has_any_flags = len(red_flags) > 0

        # Prepare LLM input based on red flag status
        llm_query = query
        llm_context = context
        
        if should_run_compliance and is_red:
            llm_query = "Explain why the clause is non-compliant based on the red flags and authority excerpts."
            # Augment context with structured flags and authority excerpts for explanation-only
            parts = [context, "\nTriggered Red Flags:"]
            for f in red_flags:
                parts.append(f"- [{f['severity']}] {f['rule_id']} ({f['domain']}): {f['reason']}")
                for sup in f.get('authority_support', [])[:3]:
                    parts.append(f"  - {sup['filename']}: {sup['excerpt']}")
            # Add compliance summary
            if compliance_summary:
                parts.append(f"\nCompliance Summary: {compliance_summary['compliant_count']}/{compliance_summary['total_checks']} required clauses found")
            llm_context = "\n".join(parts)
        elif should_run_compliance and has_any_flags:
            # Low/Medium severity flags - still mention them
            parts = [context, "\nPotential Issues (Low/Medium Severity):"]
            for f in red_flags:
                parts.append(f"- [{f['severity']}] {f['rule_id']} ({f['domain']}): {f['reason']}")
            if compliance_summary:
                parts.append(f"\nCompliance Summary: {compliance_summary['compliant_count']}/{compliance_summary['total_checks']} required clauses found")
            llm_context = "\n".join(parts)
        elif should_run_compliance:
            # Build compliance context for LLM
            user_doc_names = list(set(s.get('filename', '') for s in sources if s.get('source_type') != 'AUTHORITY'))
            parts = [context]
            if compliance_summary:
                parts.append(f"\n[Compliance Check Result for {', '.join(user_doc_names) if user_doc_names else 'the user document'}]")
                parts.append(f"Required Clauses: {compliance_summary['compliant_count']}/{compliance_summary['total_checks']} found")
                if compliance_summary['critical_missing']:
                    parts.append("CRITICAL Missing: " + ", ".join(r['description'] for r in compliance_summary['critical_missing']))
                if compliance_summary['high_missing']:
                    parts.append("HIGH Priority Missing: " + ", ".join(r['description'] for r in compliance_summary['high_missing']))
                if len(red_flags) == 0:
                    parts.append("Red Flags: None detected")
            llm_context = "\n".join(parts)

        # Generate explanation/answer
        if self.llm:
            answer = self.llm.multilingual_answer(llm_query, llm_context)
        else:
            answer = f"Based on the documents:\n\n{llm_context}"

        return {
            'query': query,
            'context': context,
            'sources': sources,
            'red_flags': red_flags,
            'compliance_results': compliance_results,
            'compliance_summary': compliance_summary,
            'decision': {
                'is_red_flag': is_red,
                'has_any_flags': has_any_flags,
                'compliance_check': should_run_compliance,  # True if compliance check or red flag query
                'is_compliant': compliance_summary.get('is_compliant', True) if compliance_summary else True,
                'override_llm_decision': is_red
            },
            'answer': answer
        }
    
    def save_index(self, path: str = "realestate_index"):
        """Save embeddings index and metadata - optimized for large document sets"""
        import time
        start_time = time.time()
        
        print(f"   Saving FAISS index ({len(self.documents)} documents)...")
        self.embeddings.save(path)
        
        # For large document sets, don't store full text in metadata (it's in FAISS content store)
        # Only store essential metadata to reduce JSON size
        print(f"   Saving metadata...")
        metadata_path = f"{path}_metadata.json"
        
        # Optimize: Create lightweight document list without full text for large sets
        if len(self.documents) > 500:
            print(f"   Optimizing metadata for {len(self.documents)} documents...")
            lightweight_docs = []
            for doc in self.documents:
                # Keep essential fields, exclude full text (it's stored in FAISS)
                light_doc = {
                    'filename': doc.get('filename'),
                    'char_count': doc.get('char_count', len(doc.get('text', ''))),
                    'chunks': doc.get('chunks', []),  # Keep chunks for compliance checking
                    'source_type': doc.get('source_type', 'USER'),
                    'text': doc.get('text', '')[:5000] if len(self.documents) > 1000 else doc.get('text', ''),  # Truncate for very large sets
                }
                # Copy optional metadata
                for key in ['title', 'date', 'doc_type', 'precedence', 'authority', 'url']:
                    if key in doc:
                        light_doc[key] = doc[key]
                lightweight_docs.append(light_doc)
            save_docs = lightweight_docs
        else:
            save_docs = self.documents
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                'documents': save_docs,
                'chunk_to_doc': {str(k): v for k, v in self.chunk_to_doc.items()},  # Ensure string keys
                'doc_count': len(self.documents),
                'chunk_count': len(self.chunk_to_doc)
            }, f, ensure_ascii=False)  # Remove indent for faster save on large files
        
        elapsed = time.time() - start_time
        print(f"   Saved index to: {path} ({elapsed:.1f}s)")
    
    def load_index(self, path: str = "realestate_index"):
        """Load a saved embeddings index"""
        self.embeddings.load(path)
        
        # Load document metadata
        metadata_path = f"{path}_metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"   JSON loaded: {len(data['documents'])} documents")
            self.documents = data['documents']
            print(f"   After assignment: {len(self.documents)} documents")
            
            # Backfill source_type on documents if missing (default to USER)
            docs_backfilled = 0
            for doc in self.documents:
                if 'source_type' not in doc:
                    doc['source_type'] = 'USER'
                    docs_backfilled += 1
            if docs_backfilled > 0:
                print(f"   Backfilled source_type='USER' for {docs_backfilled} documents")
            
            # Build doc filename -> source_type map for chunk backfilling
            doc_source_map = {}
            for doc in self.documents:
                fname = doc.get('filename', '')
                doc_source_map[fname] = doc.get('source_type', 'USER')
            
            # Safely convert keys to integers with validation
            self.chunk_to_doc = {}
            backfilled = 0
            for k, v in data['chunk_to_doc'].items():
                try:
                    chunk_data = v.copy() if isinstance(v, dict) else {}
                    # Backfill source_type if missing
                    if 'source_type' not in chunk_data:
                        fname = chunk_data.get('filename', '')
                        chunk_data['source_type'] = doc_source_map.get(fname, 'USER')
                        backfilled += 1
                    self.chunk_to_doc[int(k)] = chunk_data
                except (ValueError, TypeError) as e:
                    print(f"WARNING: Skipping invalid chunk ID '{k}': {e}")
            
            if backfilled > 0:
                print(f"   Backfilled source_type for {backfilled} chunks")
        
        print(f"Loaded index from: {path}")


if __name__ == "__main__":
    # Test the RAG system
    rag = RealEstateRAG()
    
    # Load processed documents
    if os.path.exists("processed_documents.json"):
        with open("processed_documents.json", 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        # Index documents
        rag.index_documents(documents)
        
        # Save index
        rag.save_index()
        
        # Test queries
        test_queries = [
            "What is the property address?",
            "What are the payment terms?",
            "What is the possession date?"  # Replaced Marathi query
        ]
        
        print("\nTesting queries:")
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = rag.answer_query(query, top_k=2)
            print(f"   Found {len(result['sources'])} relevant chunks")
            for src in result['sources']:
                print(f"   - {src['filename']} (Score: {src['score']:.4f})")
    else:
        print("ERROR: No processed_documents.json found. Run document_processor.py first.")
