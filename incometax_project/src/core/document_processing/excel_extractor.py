import pandas as pd
import re

def find_header_row(df, keywords, min_matches=3):
    best_match_idx = None
    max_matches = 0
    for idx, row in df.iterrows():
        row_text = ' '.join(str(cell).lower() for cell in row if pd.notna(cell))
        current_matches = sum(1 for keyword in keywords if keyword in row_text)
        if current_matches > max_matches:
            max_matches = current_matches
            best_match_idx = idx
    if max_matches >= min_matches:
        return best_match_idx
    return None

def extract_excel_text(file_path):
    """Extract text representation and structured data from Excel file."""
    try:
        df = pd.read_excel(file_path, header=None)
        text_content = f"Excel file: {file_path.name}\n\n"
        sections = {}
        processed_df = None

        if any(term in file_path.name.lower() for term in ['capital', 'gains', 'profit', 'trading']):
            print("📊 Processing capital gains Excel file...")

            header_row_index = None
            # Check for mutual fund report headers
            mf_keywords = ['scheme name', 'purchase date', 'redeem date', 'long term-capital gain']
            header_row_index = find_header_row(df, mf_keywords)

            if header_row_index is None:
                # Check for stock report headers
                stock_keywords = ['stock name', 'buy date', 'sell date', 'realised p&l']
                header_row_index = find_header_row(df, stock_keywords)

            if header_row_index is not None:
                print(f"✅ Found header row at index: {header_row_index}")
                header = df.iloc[header_row_index]
                processed_df = pd.read_excel(file_path, header=header_row_index)
                
                # Clean column names
                cleaned_columns = [re.sub(r'[^A-Za-z0-9_]+', '', str(col).strip().replace('\n', '_').replace(' ', '_')) for col in processed_df.columns]
                processed_df.columns = cleaned_columns
                
                print("📊 Cleaned column names:", processed_df.columns.tolist())
                
                processed_df = processed_df.dropna(how='all')
                print(f"✅ Loaded data with {len(processed_df)} rows")

                text_content += "COLUMNS:\n"
                text_content += f"{processed_df.columns.tolist()}\n\n"
                text_content += "DATA:\n"
                text_content += processed_df.to_string(index=False)
                
                # Simple section extraction for context
                for idx, row in df.iterrows():
                    row_text = ' '.join(str(cell) for cell in row if pd.notna(cell)).lower()
                    if 'summary' in row_text:
                        sections['summary'] = df.iloc[idx:idx+5] # grab a few lines for summary
                        break

                return text_content, processed_df, sections

            else:
                print("⚠️ Could not find specific header row, using generic processing.")
                # Fallback to original generic logic if specific headers are not found
                text_content, sections = generic_excel_processing(df, file_path)
                return text_content, None, sections

        else:
            # Generic processing for other excel files
            text_content, sections = generic_excel_processing(df, file_path)
            return text_content, None, sections

    except Exception as e:
        print(f"Error extracting Excel text: {e}")
        return "", None, {}

def generic_excel_processing(df, file_path):
    text_content = f"Excel file: {file_path.name}\n\n"
    processed_df = pd.read_excel(file_path)
    text_content += "COLUMNS:\n"
    text_content += f"{processed_df.columns.tolist()}\n\n"
    text_content += "DATA:\n"
    text_content += processed_df.to_string(index=False)
    return text_content, {}
