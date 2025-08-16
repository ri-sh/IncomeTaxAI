import fitz
import camelot

def extract_pdf_text(file_path):
    """Extract text from PDF using PyMuPDF and tables using Camelot, preserving some layout information"""
    full_text = []
    camelot_tables_text = []

    try:
        # Limit to first 10 pages to cover full Form16 (9 pages) and other documents
        tables = camelot.read_pdf(str(file_path), pages='1-10', flavor='lattice', suppress_stdout=True)
        if not tables:
            tables = camelot.read_pdf(str(file_path), pages='1-10', flavor='stream', suppress_stdout=True)

        if tables:
            for i, table in enumerate(tables):
                camelot_tables_text.append(f"\n--- TABLE {i+1} ---")
                camelot_tables_text.append(table.df.to_string())
                camelot_tables_text.append("\n--- END TABLE ---")
        else:
            print("❌ Camelot found no tables or failed to extract.")

    except Exception as e:
        print(f"⚠️ Error during Camelot table extraction: {e}")
        pass

    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            full_text.append(f"\n--- Page {page_num + 1} ---")

            blocks = page.get_text("blocks")
            blocks.sort(key=lambda block: (block[1], block[0]))

            current_y = -1
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block

                if not text.strip():
                    continue

                if current_y == -1 or (y0 - current_y) > 15:
                    full_text.append("\n")

                indentation = " " * int(x0 / 10)
                full_text.append(f"{indentation}{text.strip()}")
                current_y = y1
            full_text.append("\n")
        doc.close()

        combined_text = "\n".join(full_text)
        if camelot_tables_text:
            combined_text = combined_text + "\n\n--- EXTRACTED TABLES ---" + "\n".join(camelot_tables_text)

        return combined_text, "\n".join(full_text)

    except Exception as e:
        print(f"Error extracting PDF text with layout (PyMuPDF): {e}")
        if camelot_tables_text:
            return "\n".join(camelot_tables_text), ""
        return "", ""
