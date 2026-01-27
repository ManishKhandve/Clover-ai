"""
MahaRERA Compliance Monitoring Scraper
1. Monitors regulatory documents from listing pages
2. Downloads and OCRs new compliance PDFs only
3. Saves all text to single combined file
4. Tracks metadata to prevent duplicates
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from typing import List, Dict, Optional
import json
from datetime import datetime
import time
import os
import logging
import numpy as np
from pdf2image import convert_from_bytes
from pathlib import Path
from paddleocr import PaddleOCR

class MahaRERA_FullScraper:
    """
    Combined scraper that discovers and processes PDFs
    """
    
    def __init__(self, output_dir="extracted_text", metadata_file="extracted_text/metadata.json"):
        # --- Setup Logging ---
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('compliance_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # --- Paths ---
        self.output_dir = Path(output_dir)
        self.metadata_file = Path(metadata_file)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.combined_file = self.output_dir / "all_documents_combined.txt"
        
        # --- Statistics ---
        self.stats = {
            'discovered': 0,
            'new_documents': 0,
            'skipped_existing': 0,
            'ocr_success': 0,
            'ocr_failed': 0,
            'download_failed': 0,
            'link_errors': []  # Track failed URLs for debugging
        }
        
        # --- Network Setup ---
        self.session = requests.Session()
        retries = Retry(
            total=3, 
            backoff_factor=1, 
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # --- Poppler Path (for PDF to image conversion) ---
        self.poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
        
        # Validate poppler path
        if not os.path.exists(os.path.join(self.poppler_path, 'pdftoppm.exe')):
            raise FileNotFoundError(f"Poppler not found at: {self.poppler_path}")
        
        # --- PaddleOCR Setup (multilingual support) ---
        self.logger.info("Initializing PaddleOCR for scraper...")
        self.ocr = PaddleOCR(lang="mr", use_angle_cls=True)  # Marathi includes English
        self.logger.info("PaddleOCR ready for scraper")
        self.max_pdf_size_mb = 50  # Skip PDFs larger than 50MB
        
        # --- Monitoring Pages ---
        # Note: regulations, forms, rules pages return 404 as of Dec 2024
        # Only circular and order pages are active on MahaRERA website
        self.monitoring_pages = {
            'circulars': 'https://maharera.maharashtra.gov.in/circular',
            'orders': 'https://maharera.maharashtra.gov.in/order'
        }
        
        # --- Static Documents ---
        # Note: Central Act PDFs from indiacode.nic.in and legislative.gov.in require authentication
        # The system will rely on MahaRERA circulars and orders for compliance documents
        # Users can manually add the RERA Act PDF to the documents folder if needed
        self.static_documents = []
        
        # --- Compliance Keywords (INCLUDE) ---
        self.compliance_keywords = [
            'circular', 'clarification', 'guidelines', 'direction',
            'form l', 'form m', 'form n', 'model agreement',
            'regulation', 'rule', 'notification'
        ]
        
        # --- Exclusion Keywords (EXCLUDE - case-specific) ---
        self.exclusion_keywords = [
            'judgment', 'complaint no', 'appeal no',
            'hearing date', 'case no', 'cc/', 'cc ', 'rc/', 'rc ', 
            'forc/', 'forc ', 'petition', 'respondent', 'appellant'
        ]
        
        # --- Load Metadata ---
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from JSON file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_checked": None,
            "documents": {}
        }
    
    def _save_metadata(self):
        """Save metadata to JSON file atomically."""
        self.metadata["last_checked"] = datetime.now().strftime("%Y-%m-%d")
        
        # Atomic write: write to temp file, then rename
        temp_file = self.metadata_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, indent=2, fp=f)
        
        # Atomic rename (replaces existing file)
        temp_file.replace(self.metadata_file)
        self.logger.info(f"Metadata saved to {self.metadata_file}")
    
    def _is_compliance_document(self, title, url):
        """Check if document is compliance-related (not case-specific)."""
        text = f"{title} {url}".lower()
        
        # First check exclusions
        for keyword in self.exclusion_keywords:
            if keyword in text:
                self.logger.debug(f"Excluding (case-specific): {title}")
                return False
        
        # Then check if it matches compliance keywords
        for keyword in self.compliance_keywords:
            if keyword in text:
                return True
        
        return False
    
    def _parse_date(self, date_str):
        """Parse date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        
        date_patterns = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d %B %Y",
            "%d %b %Y"
        ]
        
        for pattern in date_patterns:
            try:
                dt = datetime.strptime(date_str.strip(), pattern)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
    def _should_download(self, filename, date_str):
        """Check if document should be downloaded based on metadata."""
        if filename not in self.metadata["documents"]:
            return True
        
        existing_date = self.metadata["documents"][filename]
        if date_str and existing_date:
            return date_str > existing_date
        
        return False
    
    def _get_precedence(self, category):
        """Map document category to precedence level (higher = more authoritative)."""
        precedence_map = {
            'orders': 4,
            'regulatory_orders': 4,
            'rules': 3,
            'regulations': 3,
            'circulars': 2,
            'forms': 1,
            'central_law': 5  # Highest precedence for central legislation
        }
        return precedence_map.get(category, 0)
    
    def discover_documents(self, dry_run=False):
        """Discover compliance documents from monitoring pages."""
        self.logger.info("\n" + "="*80)
        self.logger.info("DISCOVERING COMPLIANCE DOCUMENTS")
        self.logger.info("="*80)
        
        discovered = []
        
        # Check static documents first
        self.logger.info("\nChecking static documents...")
        for doc in self.static_documents:
            if not self._should_download(doc['filename'], doc['date']):
                self.logger.info(f"  Skipping (exists): {doc['filename']}")
                self.stats['skipped_existing'] += 1
            else:
                discovered.append(doc)
                self.logger.info(f"  Found: {doc['title']} ({doc['date']})")
        
        for category, url in self.monitoring_pages.items():
            self.logger.info(f"\nScanning {category}: {url}")
            
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find table rows
                rows = soup.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Find PDF link (handle query parameters)
                    link = row.find('a', href=lambda x: x and ('.pdf' in x.lower()))
                    if not link:
                        continue
                    
                    # Verify it's actually a PDF link
                    href = link.get('href', '')
                    if '.pdf' not in href.lower():
                        continue
                    
                    pdf_url = href
                    if not pdf_url.startswith('http'):
                        # Ensure leading slash for relative URLs
                        if not pdf_url.startswith('/'):
                            pdf_url = '/' + pdf_url
                        pdf_url = 'https://maharera.maharashtra.gov.in' + pdf_url
                    elif 'maharera.maharashtra.gov.in' not in pdf_url:
                        # Skip external domain PDFs
                        self.logger.debug(f"Skipping external URL: {pdf_url}")
                        continue
                    
                    title = link.text.strip()
                    # Extract filename, removing query parameters
                    filename = pdf_url.split('/')[-1].split('?')[0].split('#')[0]
                    if not filename or not filename.endswith('.pdf'):
                        self.logger.debug(f"Invalid filename from URL: {pdf_url}")
                        continue
                    
                    # Extract date from first cell
                    date_str = cells[0].text.strip() if cells else None
                    parsed_date = self._parse_date(date_str)
                    
                    # Check if compliance document
                    if not self._is_compliance_document(title, pdf_url):
                        continue
                    
                    # Check if should download
                    if not self._should_download(filename, parsed_date):
                        self.logger.info(f"  Skipping (exists): {filename}")
                        self.stats['skipped_existing'] += 1
                        continue
                    
                    discovered.append({
                        'url': pdf_url,
                        'filename': filename,
                        'title': title,
                        'category': category,
                        'date': parsed_date
                    })
                    
                    self.logger.info(f"  Found: {title} ({parsed_date})")
                
            except Exception as e:
                self.logger.error(f"Error scanning {category}: {e}")
        
        self.stats['discovered'] = len(discovered)
        self.stats['new_documents'] = len(discovered)
        
        self.logger.info(f"\nDiscovered {len(discovered)} new compliance documents")
        return discovered
    
    # =========================================================================
    # PROCESSING LOGIC (Simplified Threading)
    # =========================================================================

    def download_and_ocr(self, document):
        """Download and OCR a single document, return structured dict for RAG system."""
        url = document.get('url', '')
        filename = document.get('filename', 'unknown')
        title = document.get('title', '')
        category = document.get('category', 'unknown')
        date = document.get('date', 'Unknown')
        
        self.logger.info(f"Processing: {filename}")
        
        # Helper to track failed links
        def track_failure(reason):
            self.stats['link_errors'].append({'filename': filename, 'url': url, 'reason': reason})
            self.stats['ocr_failed'] += 1
        
        # Download PDF with comprehensive error handling
        try:
            response = self.session.get(url, timeout=60, verify=True)
            response.raise_for_status()
        except requests.exceptions.SSLError as e:
            # SSL certificate issues - try without verification for known government domains
            known_domains = ['maharera.maharashtra.gov.in', 'indiacode.nic.in', 'legislative.gov.in']
            if any(domain in url for domain in known_domains):
                self.logger.warning(f"SSL error, retrying without verification: {filename}")
                try:
                    response = self.session.get(url, timeout=60, verify=False)
                    response.raise_for_status()
                except Exception as retry_e:
                    self.logger.error(f"[X] Failed after SSL retry {filename}: {retry_e}")
                    track_failure(f"SSL retry failed: {retry_e}")
                    return None
            else:
                self.logger.error(f"[X] SSL error for {filename}: {e}")
                track_failure(f"SSL error")
                return None
        except requests.exceptions.Timeout:
            self.logger.error(f"[X] Timeout downloading {filename} (URL: {url})")
            track_failure("Timeout (60s)")
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"[X] Connection error for {filename}: {e}")
            track_failure("Connection error")
            return None
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code == 404:
                self.logger.warning(f"[X] File not found (404): {filename} - URL may be outdated")
                track_failure("404 Not Found")
            elif status_code == 403:
                self.logger.warning(f"[X] Access forbidden (403): {filename}")
                track_failure("403 Forbidden")
            elif status_code >= 500:
                self.logger.warning(f"[X] Server error ({status_code}): {filename} - try again later")
                track_failure(f"Server error {status_code}")
            else:
                self.logger.error(f"[X] HTTP error ({status_code}) for {filename}: {e}")
                track_failure(f"HTTP {status_code}")
            return None
        except Exception as e:
            self.logger.error(f"[X] Unexpected download error for {filename}: {type(e).__name__}: {e}")
            track_failure(f"{type(e).__name__}")
            return None
        
        # Validate response content
        pdf_bytes = response.content
        if not pdf_bytes or len(pdf_bytes) < 1000:
            self.logger.warning(f"[X] Empty or too small response for {filename} ({len(pdf_bytes) if pdf_bytes else 0} bytes)")
            track_failure("Empty/small response")
            return None
        
        # Check content type - reject HTML responses (redirects/login pages)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' in content_type:
            self.logger.warning(f"[X] Received HTML instead of PDF for {filename}: {content_type}")
            self.logger.warning(f"  URL may require auth or has been moved: {url}")
            track_failure("Received HTML (redirect/login page)")
            return None
        if 'pdf' not in content_type and 'octet-stream' not in content_type:
            self.logger.warning(f"[X] Unexpected content type for {filename}: {content_type}")
            # Continue anyway - some servers misconfigure headers
        
        # Check file size
        size_mb = len(pdf_bytes) / (1024 * 1024)
        if size_mb > self.max_pdf_size_mb:
            self.logger.warning(f"[X] Skipping {filename}: too large ({size_mb:.1f}MB > {self.max_pdf_size_mb}MB)")
            track_failure(f"Too large ({size_mb:.1f}MB)")
            return None
        
        # OCR the PDF with error handling
        try:
            text = self._ocr_pdf_bytes(pdf_bytes)
        except Exception as ocr_error:
            self.logger.error(f"[X] OCR failed for {filename}: {type(ocr_error).__name__}: {ocr_error}")
            track_failure(f"OCR error: {type(ocr_error).__name__}")
            return None
        
        # Validate extracted text (at least 100 chars and some alphanumeric content)
        if not text or len(text.strip()) < 100 or not any(c.isalnum() for c in text):
            self.logger.warning(f"[X] Insufficient text from {filename} (length: {len(text.strip()) if text else 0})")
            track_failure("Insufficient text extracted")
            return None
        
        # Update metadata
        self.metadata["documents"][filename] = date
        
        # Build structured document for RAG system
        authority_doc = {
            'source_type': 'AUTHORITY',
            'authority': 'MahaRERA',
            'doc_type': category,
            'title': title,
            'filename': filename,
            'date': date,
            'url': url,
            'text': text,
            'precedence': self._get_precedence(category)
        }
        
        self.logger.info(f"[OK] Completed: {filename} ({size_mb:.1f}MB, {len(text)} chars)")
        self.stats['ocr_success'] += 1
        return authority_doc
    
    def _ocr_pdf_bytes(self, pdf_bytes):
        """Convert PDF bytes to text using PaddleOCR."""
        try:
            # Convert PDF to images
            images = convert_from_bytes(
                pdf_bytes,
                poppler_path=self.poppler_path,
                dpi=150,
                fmt='png',
                thread_count=2
            )
            
            if not images:
                self.logger.warning("No images extracted from PDF")
                return None
            
            # Limit pages to prevent very long processing times
            max_pages = 30
            if len(images) > max_pages:
                self.logger.warning(f"PDF has {len(images)} pages, processing first {max_pages}")
                images = images[:max_pages]
            
            text_parts = []
            for i, image in enumerate(images):
                try:
                    # Convert PIL Image to numpy array for PaddleOCR
                    img_array = np.array(image)
                    
                    # Run PaddleOCR
                    result = self.ocr.ocr(img_array)
                    
                    # Extract text from OCR result
                    page_lines = []
                    if result and len(result) > 0:
                        ocr_result = result[0]
                        # Handle new PaddleOCR OCRResult object
                        if hasattr(ocr_result, 'get'):
                            page_lines = ocr_result.get('rec_texts', [])
                        # Handle list format [[bbox, (text, confidence)], ...]
                        elif isinstance(ocr_result, list):
                            page_lines = [line[1][0] for line in ocr_result if line and len(line) > 1]
                    
                    page_text = "\n".join(page_lines)
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                except Exception as page_error:
                    self.logger.warning(f"Error OCR'ing page {i+1}: {page_error}")
                    text_parts.append(f"--- Page {i+1} [OCR Error] ---\n")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return None
    
    def process_all_documents(self, documents):
        """Process all discovered documents sequentially, return list of authority docs."""
        if not documents:
            self.logger.info("No documents to process.")
            return []
        
        total = len(documents)
        self.logger.info(f"\nProcessing {total} documents...")
        print(f"\n{'='*60}")
        print(f"Processing {total} MahaRERA documents")
        print(f"{'='*60}")
        
        authority_documents = []
        for idx, doc in enumerate(documents, 1):
            filename = doc.get('filename', 'unknown')
            
            # Progress bar
            progress = idx / total
            bar_length = 40
            filled = int(bar_length * progress)
            bar = '#' * filled + '-' * (bar_length - filled)
            percent = progress * 100
            
            print(f"\r[{bar}] {percent:5.1f}% ({idx}/{total}) - {filename[:30]:<30}", end='', flush=True)
            
            result = self.download_and_ocr(doc)
            if result is not None:
                authority_documents.append(result)
                print(f"\r[{bar}] {percent:5.1f}% ({idx}/{total}) - [OK] {filename[:30]:<30}")
            else:
                print(f"\r[{bar}] {percent:5.1f}% ({idx}/{total}) - [X] {filename[:30]:<30}")
        
        print(f"\n{'='*60}")
        print(f"Completed: {len(authority_documents)}/{total} documents processed successfully")
        print(f"{'='*60}\n")
        
        # Save metadata after processing
        self._save_metadata()
        
        return authority_documents
    
    def run(self, dry_run=False):
        """Main execution flow."""
        self.logger.info("\n" + "="*80)
        self.logger.info("MAHARERA COMPLIANCE MONITORING SYSTEM")
        self.logger.info("="*80)
        
        # Step 1: Discover documents
        documents = self.discover_documents(dry_run)
        
        if dry_run:
            self.logger.info(f"\nDRY RUN: Found {len(documents)} new compliance documents")
            for doc in documents:
                self.logger.info(f"  - {doc['title']} ({doc['date']})")
            return
        
        # Step 2: Process documents
        authority_documents = []
        if documents:
            authority_documents = self.process_all_documents(documents)
        else:
            self.logger.info("No new compliance documents to process")
        
        # Step 3: Print summary
        self.logger.info("\n" + "="*80)
        self.logger.info("SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Discovered: {self.stats['discovered']}")
        self.logger.info(f"New Documents: {self.stats['new_documents']}")
        self.logger.info(f"Skipped (Existing): {self.stats['skipped_existing']}")
        self.logger.info(f"OCR Success: {self.stats['ocr_success']}")
        self.logger.info(f"OCR/Download Failed: {self.stats['ocr_failed']}")
        
        # Show failed links if any
        if self.stats['link_errors']:
            self.logger.info(f"\nFailed URLs ({len(self.stats['link_errors'])})::")
            for err in self.stats['link_errors'][:10]:  # Show max 10
                self.logger.info(f"   - {err['filename']}: {err['reason']}")
            if len(self.stats['link_errors']) > 10:
                self.logger.info(f"   ... and {len(self.stats['link_errors']) - 10} more")
        
        self.logger.info(f"Metadata: {self.metadata_file}")
        
        return authority_documents

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='MahaRERA Compliance Monitoring System')
    parser.add_argument('--dry-run', action='store_true', help='Discover documents without downloading')
    args = parser.parse_args()
    
    try:
        scraper = MahaRERA_FullScraper()
        scraper.run(dry_run=args.dry_run)
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        logging.error(f"Fatal error: {e}")