import os
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

# Force PaddleOCR to use local models only (skip network checks)
os.environ["PADDLE_NO_DOWNLOAD"] = "1"
os.environ["HUB_HOME"] = os.path.expanduser("~/.paddlex")
os.environ["PADDLEX_NO_UPDATE"] = "1"  # Disable PaddleX updates

# Add poppler to PATH - use environment variable or default location
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\Program Files\poppler-24.08.0\Library\bin")
if os.path.exists(POPPLER_PATH) and POPPLER_PATH not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + POPPLER_PATH
elif not os.path.exists(POPPLER_PATH):
    # Check if poppler is already in PATH (simple check)
    import shutil
    if not shutil.which("pdftoppm"):
        print(f"WARNING: Poppler not found at {POPPLER_PATH} and not in PATH")
        print("   Set POPPLER_PATH environment variable or install poppler")

# Import PaddleOCR after setting environment variables
from paddleocr import PaddleOCR

class FolderOCR:
    def __init__(self, dpi=200):
        # Marathi model includes English by default (using local cached models)
        print("Initializing PaddleOCR (using local models)...")
        self.ocr = PaddleOCR(lang="mr", use_angle_cls=True)
        print("PaddleOCR ready")
        self.dpi = dpi

    # ----------------------------
    # Image Preprocessing
    # ----------------------------
    def preprocess_image(self, img_path):
        img = cv2.imread(img_path)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Light denoising only
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Upscale if needed for better OCR
        height, width = denoised.shape
        if height < 1500:
            denoised = cv2.resize(denoised, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

        # Use rsplit to safely handle filenames with multiple dots
        base, ext = img_path.rsplit('.', 1) if '.' in img_path else (img_path, '')
        processed_path = f"{base}_proc.{ext}" if ext else f"{base}_proc"
        cv2.imwrite(processed_path, denoised)

        return processed_path

    # ----------------------------
    # PDF -> Images (in memory)
    # ----------------------------
    def pdf_to_images(self, pdf_path):
        pages = convert_from_path(pdf_path, dpi=self.dpi)
        return pages

    # ----------------------------
    # OCR
    # ----------------------------
    def run_ocr(self, img):
        try:
            # Convert PIL Image to numpy array
            img_array = np.array(img)
            
            result = self.ocr.ocr(img_array)
            if not result or len(result) == 0:
                return ""
            
            # New PaddleOCR returns OCRResult object
            ocr_result = result[0]
            if hasattr(ocr_result, 'get'):
                texts = ocr_result.get('rec_texts', [])
                return "\n".join(texts)
            
            # Handle list format [[bbox, (text, confidence)], ...]
            if isinstance(ocr_result, list):
                texts = [line[1][0] for line in ocr_result if line and len(line) > 1]
                return "\n".join(texts)
            
            return ""
        except Exception as e:
            print(f"      WARNING: OCR error on this page: {str(e)}")
            return ""

    # ----------------------------
    # Extract text from PDF
    # ----------------------------
    def extract_pdf(self, pdf_path):
        print(f"\nProcessing: {pdf_path}")
        try:
            # Get page count first without loading all pages
            from pdf2image.pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(pdf_path)
            total_pages = info.get('Pages', 0)
            
            text_chunks = []
            
            # Process in batches of 10 pages to manage memory
            batch_size = 10
            for start_page in range(1, total_pages + 1, batch_size):
                end_page = min(start_page + batch_size - 1, total_pages)
                
                try:
                    # Load only current batch
                    pages = convert_from_path(
                        pdf_path, 
                        dpi=self.dpi,
                        first_page=start_page,
                        last_page=end_page
                    )
                    
                    for i, page in enumerate(pages, start_page):
                        try:
                            print(f"   -> OCR: Page {i}/{total_pages}")
                            text = self.run_ocr(page)
                            if text.strip():
                                text_chunks.append(text)
                        except Exception as e:
                            print(f"      WARNING: Skipping page {i} due to error: {str(e)}")
                            continue
                    
                    # Clear memory after each batch
                    del pages
                    
                except Exception as e:
                    print(f"   WARNING: Error processing batch {start_page}-{end_page}: {str(e)}")
                    continue
            
            if not text_chunks:
                print(f"   WARNING: No text extracted from any page")
                
            return "\n\n".join(text_chunks)
            
        except Exception as e:
            print(f"   ERROR: Error processing PDF: {str(e)}")
            raise

    # ----------------------------
    # Process entire folder
    # ----------------------------
    def process_folder(self, folder_path, output_folder="ocr_output"):
        os.makedirs(output_folder, exist_ok=True)

        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

        if not pdf_files:
            print("ERROR: No PDF files found.")
            return

        for pdf_name in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_name)
            extracted_text = self.extract_pdf(pdf_path)

            # Save text
            output_path = os.path.join(
                output_folder,
                pdf_name.replace(".pdf", ".txt")
            )
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)

            print(f"Saved: {output_path}")


if __name__ == "__main__":
    # Use environment variable or default
    folder_path = os.getenv("RAG_PDF_FOLDER", r"C:\Users\manis\Downloads\cloverrag")
    print(f"Processing folder: {folder_path}")
    engine = FolderOCR()
    engine.process_folder(folder_path)
