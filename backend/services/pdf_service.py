from pathlib import Path
from typing import TypedDict

import fitz


class PDFPageText(TypedDict):
    """Structured text extracted from one PDF page."""

    page: int
    text: str


class PDFParsingError(Exception):
    """Raised when a PDF cannot be opened or parsed safely."""


class PDFService:
    """
    Service responsible for extracting text from PDF documents.

    Responsibility:
    - Open PDF files
    - Extract page-wise text
    - Handle PDF parsing errors

    This service does NOT:
    - Chunk text
    - Generate embeddings
    - Store vectors
    """

    def extract_text_from_pdf(self, pdf_path: str | Path) -> list[PDFPageText]:
        """
        Extract text from a PDF page by page.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of dictionaries containing page number and extracted text.

        Raises:
            FileNotFoundError:
                If the PDF file does not exist.

            PDFParsingError:
                If the PDF is encrypted, corrupted or unreadable.
        """

        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        pages: list[PDFPageText] = []

        try:
            with fitz.open(path) as document:

                if document.is_encrypted:
                    raise PDFParsingError(
                        "PDF is encrypted and cannot be parsed."
                    )

                for page_number, page in enumerate(document, start=1):

                    text = page.get_text("text").strip()

                    # Ignore completely empty pages.
                    if not text:
                        continue

                    pages.append(
                        {
                            "page": page_number,
                            "text": text,
                        }
                    )

        except PDFParsingError:
            raise

        except Exception as exc:
            raise PDFParsingError(
                "PDF could not be parsed. It may be corrupted or invalid."
            ) from exc

        return pages