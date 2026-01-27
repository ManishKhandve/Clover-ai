"""
Automatic Document Indexer
Monitors a folder and automatically indexes new PDFs on startup
Prevents duplicate indexing by tracking processed documents
"""
import os
import json
import hashlib
from pathlib import Path
from realestate_rag import RealEstateRAG
from document_processor import DocumentProcessor
from ocr_engine import FolderOCR
from scraper import MahaRERA_FullScraper

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration - Priority: Environment Variable > Config File > Default
def load_config():
    """Load configuration from file or environment variables"""
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    
    # Try loading from config file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"WARNING: Error loading config.json: {e}")
    
    # Return defaults
    return {
        "pdf_folder": r"C:\Users\manis\Downloads\cloverrag",
        "index_path": "realestate_index",
        "tracking_file": "indexed_documents.txt"
    }

config = load_config()

# Configuration with environment variable override
PDF_FOLDER = os.getenv("RAG_PDF_FOLDER", config.get("pdf_folder", r"C:\Users\manis\Downloads\cloverrag"))
INDEX_PATH = os.path.join(SCRIPT_DIR, config.get("index_path", "realestate_index"))
TRACKING_FILE = os.path.join(SCRIPT_DIR, config.get("tracking_file", "indexed_documents.txt"))


class AutoIndexer:
    """Automatically index new documents and prevent duplicates"""
    
    def __init__(self, pdf_folder, index_path, tracking_file):
        self.pdf_folder = pdf_folder
        self.index_path = index_path
        self.tracking_file = tracking_file
        self.indexed_files = self.load_indexed_files()
        
    def load_indexed_files(self):
        """Load the list of already indexed files"""
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def save_indexed_files(self):
        """Save the list of indexed files"""
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            for filename in sorted(self.indexed_files):
                f.write(f"{filename}\n")
    
    def get_file_hash(self, filepath):
        """Get hash of file to detect changes"""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_pdf_files(self):
        """Get all PDF files from the folder"""
        if not os.path.exists(self.pdf_folder):
            print(f"WARNING: Folder not found: {self.pdf_folder}")
            return []
        
        pdf_files = []
        for file in Path(self.pdf_folder).glob("*.pdf"):
            pdf_files.append(str(file))
        return pdf_files
    
    def get_new_documents(self):
        """Get list of new documents that haven't been indexed"""
        all_pdfs = self.get_pdf_files()
        new_docs = []
        
        for pdf_path in all_pdfs:
            filename = os.path.basename(pdf_path)
            file_hash = self.get_file_hash(pdf_path)
            file_id = f"{filename}:{file_hash}"
            
            if file_id not in self.indexed_files:
                new_docs.append({
                    'path': pdf_path,
                    'filename': filename,
                    'hash': file_hash,
                    'id': file_id
                })
        
        return new_docs
    
    def index_new_documents(self):
        """Index only new documents"""
        print("="*70)
        print("Scanning for new documents...")
        print("="*70)
        
        # Initialize processor early (needed for both user docs and authority docs)
        processor = DocumentProcessor(ocr_engine=FolderOCR())
        
        # Get new user documents
        new_docs = self.get_new_documents()
        
        if new_docs:
            print(f"Found {len(new_docs)} new user document(s) to index:")
            for doc in new_docs:
                print(f"   - {doc['filename']}")
            print()
        else:
            print("No new user documents to index")
        
        # Load existing documents metadata
        existing_docs = []
        metadata_path = f"{self.index_path}_metadata.json"
        if os.path.exists(metadata_path):
            print("Loading existing documents metadata...")
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_docs = data.get('documents', [])
                print(f"Loaded {len(existing_docs)} existing documents")
            except Exception as e:
                print(f"WARNING: Error loading metadata: {e}")
                existing_docs = []
        
        # Separate existing user docs from authority docs
        existing_user_docs = [d for d in existing_docs if d.get('source_type') != 'AUTHORITY']
        existing_authority_docs = [d for d in existing_docs if d.get('source_type') == 'AUTHORITY']
        existing_authority_filenames = {d['filename'] for d in existing_authority_docs}
        
        print(f"   Existing user docs: {len(existing_user_docs)}")
        print(f"   Existing authority docs: {len(existing_authority_docs)}")
        
        # Process new user documents
        new_processed_docs = []
        if new_docs:
            print("\nProcessing new user documents...")
            total_new = len(new_docs)
            
            for idx, doc_info in enumerate(new_docs, 1):
                try:
                    print(f"\nProcessing [{idx}/{total_new}]: {doc_info['filename']}")
                    processed_doc = processor.process_pdf(doc_info['path'])
                    
                    if processed_doc and processed_doc.get('text'):
                        text_length = len(processed_doc['text'])
                        if text_length < 50:
                            print(f"   WARNING: Text too short ({text_length} chars), skipping")
                            continue
                        
                        doc_data = {
                            'filename': doc_info['filename'],
                            'text': processed_doc['text'],
                            'chunks': processed_doc['chunks'],
                            'source_type': 'USER',  # Mark as user document for filtering
                            'metadata': {
                                'num_chunks': len(processed_doc['chunks']),
                                'text_length': text_length,
                                'file_hash': doc_info['hash']
                            }
                        }
                        new_processed_docs.append(doc_data)
                        print(f"   Extracted {len(processed_doc['chunks'])} chunks ({text_length} chars)")
                    else:
                        print(f"   WARNING: No text extracted")
                        
                except Exception as e:
                    print(f"   ERROR: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        # ALWAYS check for new MahaRERA documents on startup
        print("\n" + "="*70)
        print("Checking for new MahaRERA authority documents...")
        print("="*70)
        
        new_authority_docs = []
        updated_authority_filenames = set()  # Track which docs are being updated
        
        try:
            scraper = MahaRERA_FullScraper()
            scraped = scraper.run(dry_run=False) or []
            
            if scraped:
                print(f"Scraper returned {len(scraped)} document(s)")
                
                for adoc in scraped:
                    try:
                        if not adoc.get('text') or not adoc.get('filename'):
                            continue
                        
                        chunks = processor.chunk_text(adoc['text'])
                        if not chunks:
                            continue
                        
                        # Track this filename - if it exists in old index, it will be replaced
                        if adoc['filename'] in existing_authority_filenames:
                            updated_authority_filenames.add(adoc['filename'])
                            print(f"   [UPD] Updating: {adoc['filename']} ({len(chunks)} chunks)")
                        else:
                            print(f"   [+] New: {adoc['filename']} ({len(chunks)} chunks)")
                        
                        new_authority_docs.append({
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
                        print(f"   WARNING: Failed to prepare {adoc.get('filename','unknown')}: {e}")
                
                if new_authority_docs:
                    new_count = len(new_authority_docs) - len(updated_authority_filenames)
                    print(f"\nNew authority docs: {new_count}, Updated: {len(updated_authority_filenames)}")
                else:
                    print("\nNo new authority documents from scraper")
            else:
                print("No authority documents returned by scraper")
                
        except Exception as e:
            print(f"WARNING: Error running scraper: {e}")
            import traceback
            traceback.print_exc()
        
        # Check if anything new to index
        if not new_processed_docs and not new_authority_docs:
            print("\n" + "="*70)
            print("Index is up to date! No new documents to process.")
            print("="*70)
            print(f"Total indexed: {len(existing_docs)} documents")
            return 0
        
        # Initialize RAG system for indexing
        print("\nInitializing RAG system...")
        rag_system = RealEstateRAG(use_llm=True)

        # Remove old versions of updated authority docs (memory management)
        existing_authority_docs_filtered = [
            d for d in existing_authority_docs 
            if d['filename'] not in updated_authority_filenames
        ]
        
        if updated_authority_filenames:
            print(f"Removing {len(updated_authority_filenames)} outdated authority doc(s) from index")

        # Combine: existing user docs + new user docs + filtered existing authority + new authority
        all_docs = existing_user_docs + new_processed_docs + existing_authority_docs_filtered + new_authority_docs
        
        # Validate combined documents
        print(f"\nValidating {len(all_docs)} total documents...")
        for idx, doc in enumerate(all_docs):
            text_len = len(doc.get('text', ''))
            if text_len < 100:
                print(f"WARNING: Document {idx} has only {text_len} chars of text!")
                print(f"   Filename: {doc.get('filename', 'unknown')}")
        
        # Re-index everything from scratch (IMPORTANT: this creates fresh chunk IDs)
        # We don't append to existing index because:
        # 1. txtai doesn't support true incremental indexing
        # 2. Re-indexing ensures no chunk ID collisions
        # 3. Guarantees consistency between embeddings and metadata
        print(f"\nBuilding fresh index with {len(all_docs)} documents...")
        rag_system.index_documents(all_docs)
        rag_system.save_index(self.index_path)
        
        # Update tracking file for user docs
        for doc in new_docs:
            self.indexed_files.add(doc['id'])
        self.save_indexed_files()
        
        print("\n" + "="*70)
        print("Indexing complete!")
        print("="*70)
        print(f"New user documents: {len(new_processed_docs)}")
        print(f"New MahaRERA documents: {len(new_authority_docs) - len(updated_authority_filenames)}")
        print(f"Updated MahaRERA documents: {len(updated_authority_filenames)}")
        print(f"Total documents in index: {len(all_docs)}")
        print(f"   - User documents: {len(existing_user_docs) + len(new_processed_docs)}")
        print(f"   - Authority documents: {len(existing_authority_docs_filtered) + len(new_authority_docs)}")
        print(f"Index saved to: {self.index_path}")
        print("="*70)
        
        return len(new_processed_docs) + len(new_authority_docs)


def auto_index_on_startup():
    """Run auto-indexing on startup"""
    indexer = AutoIndexer(PDF_FOLDER, INDEX_PATH, TRACKING_FILE)
    return indexer.index_new_documents()


if __name__ == '__main__':
    print("""
========================================================================
                   Real Estate RAG - Auto Indexer                     
========================================================================
    """)
    
    print(f"Monitoring folder: {PDF_FOLDER}")
    print(f"Index location: {INDEX_PATH}")
    print()
    
    try:
        count = auto_index_on_startup()
        
        if count > 0:
            print("\nReady to use! Start the API server:")
            print("   python api_server.py")
        else:
            print("\nIndex is up to date! Start the API server:")
            print("   python api_server.py")
            
    except Exception as e:
        print(f"\nERROR: Error during indexing: {str(e)}")
        import traceback
        traceback.print_exc()
