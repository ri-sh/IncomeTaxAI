import fitz
import camelot
from io import BytesIO
import tempfile
import os

def extract_pdf_text(file_bytes, filename="temp.pdf"):
    """Extract text from PDF using PyMuPDF and tables using Camelot from bytes"""
    full_text = []
    camelot_tables_text = []

    # Camelot requires a file path, so we'll write to a temporary file
    # This is a necessary evil for Camelot, but the file is immediately deleted.
    temp_pdf_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_bytes)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Ensure it's fully written to disk
            temp_file.close()  # Close before Camelot reads it
            temp_pdf_file = temp_file.name

        # Limit to first 10 pages to cover full Form16 (9 pages) and other documents
        tables = camelot.read_pdf(temp_pdf_file, pages='1-10', flavor='lattice', suppress_stdout=True)
        if not tables:
            tables = camelot.read_pdf(temp_pdf_file, pages='1-10', flavor='stream', suppress_stdout=True)

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
    finally:
        if temp_pdf_file and os.path.exists(temp_pdf_file):
            os.remove(temp_pdf_file)

    try:
        # PyMuPDF can open from bytes directly
        doc = fitz.open("pdf", file_bytes)
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


