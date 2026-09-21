# DocuFlow

A Windows desktop application for document processing and conversion, developed in Python with a WebView-based interface.

DocuFlow brings together document handling, image processing and PDF conversion in a single desktop workflow. The project has evolved through a series of versioned iterations, currently reaching **v1.0.0.8**.

## Capabilities

- Document processing for Word and PDF workflows.
- Reading and manipulation of `.docx` and `.xlsx` files.
- PDF generation and conversion workflows.
- PDF-to-image processing.
- Image processing and sanitization.
- Metadata and PDF optimization.
- Environment detection for Microsoft Office and LibreOffice conversion.
- Native desktop interface with HTML5 through pywebview.

## Architecture

    Python application
          │
          ├── Core services
          ├── Document processing
          ├── File and environment utilities
          └── Python ↔ JavaScript bridge
                         │
                         ▼
                 HTML5 / CSS / JS UI

The application separates core processing from the user interface and uses a Python-to-JavaScript bridge to expose native functionality to the WebView interface.

## Technology

- Python 3.9+
- pywebview
- python-docx
- openpyxl
- Pillow
- PyMuPDF
- docx2pdf
- PyPDF2
- pikepdf
- requests
- Windows desktop APIs

## Project structure

The repository keeps the development history organized by version:

    DocuFLow/
    ├── DocuFlow-1.0.0.0/
    ├── DocuFlow-1.0.0.1/
    ├── ...
    └── DocuFlow-1.0.0.8/

The latest version contains the current application source under `src/`, together with tests, resources, dependency definitions and project documentation.

## Running the latest version

    cd DocuFlow-1.0.0.8
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    python src\initial_test.py

## Development

DocuFlow is a continuing desktop-software project focused on document automation, file processing and the integration of native Python functionality with web-based interfaces.

## Author

**Leonardo Merchán — lewopxd**

[GitHub](https://github.com/lewopxd) · [0zdev](https://github.com/0zdev)