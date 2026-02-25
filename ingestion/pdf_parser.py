import fitz

class PDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    def iterate_pages(self, start_page: int = 0):
        """Iterates through pages starting from start_page."""
        for page_num in range(start_page, len(self.doc)):
            page = self.doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            yield page_num, blocks
