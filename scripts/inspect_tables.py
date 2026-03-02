import fitz

def print_tables():
    doc = fitz.open("pdfs/Compilación Programas 1er Ciclo - 2024.pdf")
    found = 0
    for page_num in range(20, 100):
        page = doc.load_page(page_num)
        tabs = page.find_tables()
        for tab in tabs:
            print(f"\n--- Page {page_num} Table ---")
            rows = tab.extract()
            # print first 3 rows
            for i, row in enumerate(rows[:3]):
                clean_row = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                print(f"Row {i}: {clean_row}")
            found += 1
            if found >= 10:
                doc.close()
                return

if __name__ == "__main__":
    print_tables()
