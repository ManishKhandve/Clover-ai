"""
Real Estate Agreement RAG System - Document Processor
Handles PDF ingestion with OCR support for scanned documents (English + Marathi)
"""
import os
import json
from typing import List, Dict, Tuple
from ocr_engine import FolderOCR


class DocumentProcessor:
    """Process PDFs and extract text with OCR"""
    
    def __init__(self, ocr_engine=None):
        self.ocr = ocr_engine or FolderOCR()
        
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for better retrieval"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
                
        return chunks
    
    def process_pdf(self, pdf_path: str) -> Dict:
        """
        Extract text from PDF using OCR and chunk it
        
        Returns:
            {
                'filename': str,
                'text': str (full text),
                'chunks': List[str],
                'metadata': Dict
            }
        """
        print(f"\nProcessing: {os.path.basename(pdf_path)}")
        
        # Check file exists and size
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")
            
        file_size = os.path.getsize(pdf_path)
        max_size = 50 * 1024 * 1024  # 50MB limit
        if file_size > max_size:
            raise ValueError(f"File too large ({file_size / 1024 / 1024:.1f}MB > 50MB): {pdf_path}")
        
        # Extract text using OCR with error handling
        try:
            full_text = self.ocr.extract_pdf(pdf_path)
        except Exception as e:
            print(f"   ERROR: OCR extraction failed: {e}")
            raise
        
        # Chunk the text
        chunks = self.chunk_text(full_text, chunk_size=400, overlap=50)
        
        return {
            'filename': os.path.basename(pdf_path),
            'path': pdf_path,
            'text': full_text,
            'chunks': chunks,
            'metadata': {
                'num_chunks': len(chunks),
                'text_length': len(full_text)
            }
        }
    
    def process_folder(self, folder_path: str) -> List[Dict]:
        """Process all PDFs in a folder"""
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("ERROR: No PDF files found in folder")
            return []
        
        documents = []
        for pdf_name in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_name)
            doc = self.process_pdf(pdf_path)
            documents.append(doc)
            print(f"Processed: {pdf_name} ({len(doc['chunks'])} chunks)")
        
        return documents
    
    def save_processed_data(self, documents: List[Dict], output_path: str):
        """Save processed documents to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        print(f"\nSaved processed data to: {output_path}")


if __name__ == "__main__":
    # Test the processor
    processor = DocumentProcessor()
    
    # Example usage - use environment variable or default
    test_folder = os.getenv("RAG_PDF_FOLDER", r"C:\Users\manis\Downloads\cloverrag")
    print(f"Processing folder: {test_folder}")
    docs = processor.process_folder(test_folder)
    
    if docs:
        processor.save_processed_data(docs, "processed_documents.json")
        print(f"\nSummary:")
        print(f"   Total documents: {len(docs)}")
        print(f"   Total chunks: {sum(d['metadata']['num_chunks'] for d in docs)}")
