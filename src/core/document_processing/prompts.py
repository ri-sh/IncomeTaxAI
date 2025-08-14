import json
import langextract as lx

# Define schemas for each document type
SCHEMAS = {
    "form_16": {
        "type": "object",
        "properties": {
            "gross_salary": {"type": "number"},
            "tax_deducted": {"type": "number"},
        },
        "required": ["gross_salary", "tax_deducted"],
    },
    "payslip": {
        "type": "object",
        "properties": {
            "employee_name": {"type": "string"},
            "pan": {"type": "string"},
            "employer_name": {"type": "string"},
            "gross_salary": {"type": "number"},
            "basic_salary": {"type": "number"},
            "hra_received": {"type": "number"},
            "special_allowance": {"type": "number"},
            "other_allowances": {"type": "number"},
            "tax_deducted": {"type": "number"},
            "epf_amount": {"type": "number"},
            "financial_year": {"type": "string"},
        },
        "required": ["gross_salary", "tax_deducted"],
    },
    "bank_interest_certificate": {
        "type": "object",
        "properties": {
            "bank_name": {"type": "string"},
            "account_number": {"type": "string"},
            "pan": {"type": "string"},
            "interest_amount": {"type": "number"},
            "accrued_interest": {"type": "number"},
            "tds_amount": {"type": "number"},
            "principal_amount": {"type": "number"},
            "financial_year": {"type": "string"},
        },
        "required": ["interest_amount", "tds_amount"],
    },
    "capital_gains": {
        "type": "object",
        "properties": {
            "total_capital_gains": {"type": "number"},
            "long_term_capital_gains": {"type": "number"},
            "short_term_capital_gains": {"type": "number"},
            "number_of_transactions": {"type": "integer"},
            "financial_year": {"type": "string"},
        },
        "required": ["total_capital_gains"],
    },
    "investment": { # NEW
        "type": "object",
        "properties": {
            "epf_amount": {"type": "number"},
            "ppf_amount": {"type": "number"},
            "life_insurance": {"type": "number"},
            "elss_amount": {"type": "number"},
            "health_insurance": {"type": "number"},
            "financial_year": {"type": "string"},
        },
        "required": [],
    },
    "nps_statement": { # NEW
        "type": "object",
        "properties": {
            "nps_tier1_contribution": {"type": "number"},
            "nps_80ccd1b": {"type": "number"},
            "nps_employer_contribution": {"type": "number"},
            "financial_year": {"type": "string"},
        },
        "required": [],
    },
    "unknown": {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "nps_statement", "unknown"]
            }
        }
    }
}

def _get_prompt_and_schema(doc_type: str, text_content: str):
    """Determines the prompt and response schema based on the document type."""
    if doc_type == "unknown":
        # Prompt for initial document type identification
        JSON_SCHEMA = {
            "document_type": {
                "type": "string",
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "nps_statement", "unknown"]
            }
        }
        prompt = f"""
        You are an expert document analyzer for Indian financial documents.
        Your task is to identify the type of the following document.
        Please analyze the text and respond with ONLY a valid JSON object that strictly adheres to the following schema.
        Do not include any explanations or apologies.

        TEXT TO ANALYZE:
        {text_content[:4000]}  # Truncate for performance

        CRITICAL RULE: The 'document_type' MUST be one of the values specified in the enum: {JSON_SCHEMA['document_type']['enum']}.
        """
        
        return prompt, JSON_SCHEMA

        JSON_SCHEMA = {
            "document_type": {
                "type": "string",
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "nps_statement", "unknown"]
            }
        }
        
        return prompt, JSON_SCHEMA
    else:
        # Prompt for data extraction based on identified document type
        schema = SCHEMAS.get(doc_type.lower().replace(" ", "_").replace("-", "_"), SCHEMAS["unknown"])
        if doc_type == "bank_interest_certificate":
            return _create_structured_prompt_with_example(doc_type, schema, text_content, 
                example_text="""Bank of India
Interest Certificate
Period : 01/04/2023 To 31/03/2024

Deposit Number Branch Name Principal Amount Interest Amount Accrued Interest Tax Deducted
1234567890 MUMBAI 100000.00 5000.00 100.00 510.00
Total 100000.00 5000.00 100.00 510.00""",
                example_json="""{
  "bank_name": "Bank of India",
  "account_number": "",
  "pan": "",
  "interest_amount": 5000.00,
  "accrued_interest": 100.00,
  "tds_amount": 510.00,
  "principal_amount": 100000.00,
  "financial_year": "2023-24"
} """ ), schema
        elif doc_type == "nps_statement":
            return _create_structured_prompt_with_example(doc_type, schema, text_content,
                example_text="""NPS Transaction Statement\nFor the Financial Year 2024-25\n\nContribution Details\nBy Voluntary Contributions 50000.00\nTotal Contribution 250000.00""",
                example_json="""{\n  \"nps_tier1_contribution\": 250000.00,\n  \"nps_80ccd1b\": 50000.00,\n  \"nps_employer_contribution\": 0.00,\n  \"financial_year\": \"2024-25\"\n}""" ), schema
        else:
            return _create_structured_prompt(doc_type, schema, text_content), schema

def _create_structured_prompt(doc_type: str, schema, text_content: str):
    """Creates a standardized prompt for structured JSON extraction."""
    json_schema_str = json.dumps(schema, indent=2)
    
    specific_instructions = ""
    if doc_type == "form_16":
        specific_instructions = f"""
        For Form 16 documents, extract all relevant financial figures.
        - **Gross Salary:** Look for "Gross Salary" or "Income chargeable under the head 'Salaries'" in Part B. If multiple salary figures are present, prioritize the total gross salary for the financial year.
        - **Tax Deducted:** Find the "Tax payable" or "Total tax deducted" amount.
        - **Deductions (Chapter VI-A):** Extract amounts for 80C, 80CCD(1B), 80D, etc. Look for sections like "Deductions under Chapter VI-A". Sum up all applicable deductions.
        - **Perquisites:** Extract from "Value of perquisites under section 17(2)".
        - **Employee/Employer Details:** Extract Employee Name, PAN, Employer Name, Employer TAN.
        - If a specific field is not found, return 0.0 for numeric values and "" for strings.
        """

    elif doc_type == "payslip":
        specific_instructions = f"""
        For Payslip documents, extract:
        - Employee Name, PAN, Employer Name.
        - Gross Salary, Basic Pay, HRA, Special Allowance, Other Allowances.
        - Tax Deducted (Income Tax).
        - EPF Contribution.
        """
    
    elif doc_type == "bank_interest_certificate":
        specific_instructions = f"""
        You are an expert financial analyst. Your task is to extract specific information from the text of a Bank Interest Certificate.

        The provided text contains a table of interest transactions and a summary row at the end. The summary row is the most important part.

        Find the line that starts with the word 'Total'. From this line, extract the 'Interest Amount', 'Accrued Interest', and 'Tax Deducted' values.

        Provide the output in a clean JSON format with the following keys: "interest_amount", "accrued_interest", "tds_amount".
        """
    
    elif doc_type == "capital_gains":
        specific_instructions = f"""
        For Capital Gains reports (from mutual funds or stocks), extract the following:
        - **Total Capital Gains:** Sum of all long-term and short-term capital gains. Look for "Total Capital Gains", "Net Profit/Loss", or similar summary figures.
        - **Long Term Capital Gains (LTCG):** Look for "LTCG", "Long Term Capital Gain", or similar. Sum up all LTCG entries if multiple are present.
        - **Short Term Capital Gains (STCG):** Look for "STCG", "Short Term Capital Gain", or similar. Sum up all STCG entries if multiple are present.
        - **Number of Transactions:** Count the number of individual buy/sell transactions if available.
        - If the document contains a table, prioritize extracting values from the summary rows or summing up the relevant columns.
        - If a specific field is not found, return 0.0 for numeric values.
        """

    return f"""
    You are an expert document analyzer for Indian financial documents.
    Your task is to extract information from the following {doc_type} document.
    Please analyze the text and respond with ONLY a valid JSON object that strictly adheres to the following schema.
    Do not include any explanations or apologies.

    TEXT TO ANALYZE:
    {text_content[:15000]}  # Truncate for performance

    JSON SCHEMA:
    ```json
    {json_schema_str}
    ```

    CRITICAL RULES:
    1.  Provide only the JSON object as the output.
    2.  All string values must be enclosed in double quotes.
    3.  All numerical values should be numbers (int or float), not strings. Use 0.0 or 0 if a value is not found.
    4.  If a string value (like a name or PAN) is not found, use an empty string "".
    5.  STRICTLY adhere to the provided JSON SCHEMA, including exact field names and data types.
    6.  Map extracted data to the following exact field names: `gross_salary`, `tax_deducted`, `employee_name`, `pan`, `employer_name`, `interest_amount`, `tds_amount`, `total_capital_gains`, `long_term_capital_gains`, `short_term_capital_gains`, `number_of_transactions`, `epf_amount`, `ppf_amount`, `life_insurance`, `elss_amount`, `health_insurance`.
    7.  Do not include any fields that are not in the JSON SCHEMA.
    {specific_instructions}
    """

def _create_structured_prompt_with_example(doc_type: str, schema, text_content: str, example_text: str, example_json: str):
    """Creates a standardized prompt for structured JSON extraction with a few-shot example."""
    
    json_schema_str = json.dumps(schema, indent=2)
    
    specific_instructions = ""
    if doc_type == "form_16":
        specific_instructions = f"""
        For Form 16 documents, extract all relevant financial figures.
        - **Gross Salary:** Look for "Gross Salary" or "Income chargeable under the head 'Salaries'" in Part B. If multiple salary figures are present, prioritize the total gross salary for the financial year.
        - **Tax Deducted:** Find the "Tax payable" or "Total tax deducted" amount.
        - **Deductions (Chapter VI-A):** Extract amounts for 80C, 80CCD(1B), 80D, etc. Look for sections like "Deductions under Chapter VI-A". Sum up all applicable deductions.
        - **Perquisites:** Extract from "Value of perquisites under section 17(2)".
        - **Employee/Employer Details:** Extract Employee Name, PAN, Employer Name, Employer TAN.
        - If a specific field is not found, return 0.0 for numeric values and "" for strings.
        """

    elif doc_type == "payslip":
        specific_instructions = f"""
        For Payslip documents, extract:
        - Employee Name, PAN, Employer Name.
        - Gross Salary, Basic Pay, HRA, Special Allowance, Other Allowances.
        - Tax Deducted (Income Tax).
        - EPF Contribution.
        """
    
    elif doc_type == "bank_interest_certificate":
        specific_instructions = f"""
        You are an expert financial analyst. Your task is to extract specific information from the text of a Bank Interest Certificate.

        The provided text contains a table of interest transactions and a summary row at the end. The summary row is the most important part.

        Find the line that starts with the word 'Total'. From this line, extract the 'Interest Amount', 'Accrued Interest', and 'Tax Deducted' values.

        Provide the output in a clean JSON format with the following keys: "interest_amount", "accrued_interest", "tds_amount".
        """
    
    elif doc_type == "capital_gains":
        specific_instructions = f"""
        For Capital Gains reports (from mutual funds or stocks), extract the following:
        - **Total Capital Gains:** Sum of all long-term and short-term capital gains. Look for "Total Capital Gains", "Net Profit/Loss", or similar summary figures.
        - **Long Term Capital Gains (LTCG):** Look for "LTCG", "Long Term Capital Gain", or similar. Sum up all LTCG entries if multiple are present.
        - **Short Term Capital Gains (STCG):** Look for "STCG", "Short Term Capital Gain", or similar. Sum up all STCG entries if multiple are present.
        - **Number of Transactions:** Count the number of individual buy/sell transactions if available.
        - If the document contains a table, prioritize extracting values from the summary rows or summing up the relevant columns.
        - If a specific field is not found, return 0.0 for numeric values.
        """

    return f"""
    You are an expert document analyzer for Indian financial documents.
    Your task is to extract information from the following {doc_type} document.
    Please analyze the text and respond with ONLY a valid JSON object that strictly adheres to the following schema. 
    Do not include any explanations or apologies.

    HERE IS AN EXAMPLE:
    TEXT:
    {example_text}
    JSON:
    ```json
    {example_json}
    ```

    TEXT TO ANALYZE:
    {text_content[:15000]}  # Truncate for performance

    JSON SCHEMA:
    ```json
    {json_schema_str}
    ```

    CRITICAL RULES:
    1.  Provide only the JSON object as the output.
    2.  All string values must be enclosed in double quotes.
    3.  All numerical values should be numbers (int or float), not strings. Use 0.0 or 0 if a value is not found.
    4.  If a string value (like a name or PAN) is not found, use an empty string "".
    5.  STRICTLY adhere to the provided JSON SCHEMA, including exact field names and data types.
    6.  Map extracted data to the following exact field names: `gross_salary`, `tax_deducted`, `employee_name`, `pan`, `employer_name`, `interest_amount`, `tds_amount`, `total_capital_gains`, `long_term_capital_gains`, `short_term_capital_gains`, `number_of_transactions`, `epf_amount`, `ppf_amount`, `life_insurance`, `elss_amount`, `health_insurance`.
    7.  Do not include any fields that are not in the JSON SCHEMA.
    {specific_instructions}
    """

def _get_langextract_prompt_and_examples(doc_type: str):
    """Determines the prompt and examples for langextract based on the document type."""
    if doc_type == "form_16":
        prompt_description = "Extract the gross salary and tax deducted from the document."
        examples = [
            lx.data.ExampleData(
                text="Gross Salary: 1,200,000.00, Tax Deducted: 120,000.00",
                extractions=[
                    lx.data.Extraction(extraction_class="gross_salary", extraction_text="1,200,000.00"),
                    lx.data.Extraction(extraction_class="tax_deducted", extraction_text="120,000.00"),
                ],
            )
        ]
        return prompt_description, examples
    # Default case if doc_type is not form_16
    return "Extract all key-value pairs.", [
        lx.data.ExampleData(
            text="Name: John Doe, Age: 30",
            extractions=[
                lx.data.Extraction(extraction_class="name", extraction_text="John Doe"),
                lx.data.Extraction(extraction_class="age", extraction_text="30"),
            ],
        )
    ] 
