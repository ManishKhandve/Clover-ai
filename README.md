CloverAI Real Estate Compliance Assistant
This project helps real estate companies check their agreements for compliance with MahaRERA regulations using AI and rule-based analysis.

Features
Upload and analyze real estate agreements (PDF)
Detect red flags and missing compliance clauses
Compare user documents with MahaRERA circulars and orders
Batch processing for multiple documents
Download compliance reports as PDF
Simple web interface
How to Run
Place your PDF documents in the folder specified in config.json (pdf_folder).

Install requirements:
pip install -r requirements_realestate.txt

Start the server:
python api_server.py

Open your browser at http://localhost:5000
Configuration
Edit config.json to set folders, OCR language, and LLM API key.

Usage
Select your agreement(s) and MahaRERA docs in the web UI.
Click "Check Compliance" or "Batch Process".
View results and download reports.
