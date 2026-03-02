import fitz
import glob

pdfs = glob.glob("pdfs/*.pdf")
if not pdfs:
    print("No PDFs found")
    exit(1)

doc = fitz.open(pdfs[0])
print(f"Total pages: {len(doc)} in {pdfs[0]}")
for page_num in range(15, 60):
    page = doc.load_page(page_num)
    tabs = page.find_tables()
    if tabs:
        text = page.get_text()
        print(f"\n--- PAGE {page_num} HAS TABLES ---")
        lines = text.split("\n")
        # Print first few lines to see what context is there
        print("\n".join(lines[:10]))
        break
doc.close()
