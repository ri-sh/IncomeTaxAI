import json


# Define schemas for each document type
SCHEMAS = {
    "form_16": {
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
            "perquisites": {"type": "number"},
            "total_gross_salary": {"type": "number"},
            "tax_deducted": {"type": "number"},
            "epf_amount": {"type": "number"},
            "professional_tax": {"type": "number"},
            "financial_year": {"type": "string"},
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
    "mutual_fund_elss_statement": {
        "type": "object",
        "properties": {
            "elss_amount": {"type": "number"},
            "total_investment": {"type": "number"},
            "fund_name": {"type": "string"},
            "folio_number": {"type": "string"},
            "financial_year": {"type": "string"},
        },
        "required": ["elss_amount"],
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
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "mutual_fund_elss_statement", "nps_statement", "unknown"]
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
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "mutual_fund_elss_statement", "nps_statement", "unknown"]
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
                "enum": ["form_16", "payslip", "bank_interest_certificate", "capital_gains", "investment", "mutual_fund_elss_statement", "nps_statement", "unknown"]
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
        elif doc_type == "form_16":
            return _create_structured_prompt_with_example(doc_type, schema, text_content,
                example_text="""FORM 16
CERTIFICATE UNDER SECTION 203
XYZ COMPANY LIMITED
Employee Name: SAMPLE EMPLOYEE
PAN: SAMPLEF1234

PART A - Summary
Total amount paid/credited: ₹12,50,000
Total tax deducted: ₹1,50,000

PART B - Annexure
1. Gross Salary
(a) Salary as per provisions contained in section 17(1): ₹11,00,000
(b) Value of perquisites under section 17(2): ₹1,50,000
(d) Total: ₹12,50,000

4. Less: Deductions under section 16
(a) Standard deduction under section 16(ia): ₹50,000
(c) Tax on employment under section 16(iii): ₹2,400""",
                example_json="""{\n  \"employee_name\": \"SAMPLE EMPLOYEE\",\n  \"pan\": \"SAMPLEF1234\",\n  \"employer_name\": \"XYZ COMPANY LIMITED\",\n  \"basic_salary\": 1100000.0,\n  \"perquisites\": 150000.0,\n  \"gross_salary\": 1250000.0,\n  \"total_gross_salary\": 1250000.0,\n  \"tax_deducted\": 150000.0,\n  \"professional_tax\": 2400.0,\n  \"financial_year\": \"2024-25\"\n}""" ), schema
        elif doc_type == "mutual_fund_elss_statement":
            return _create_structured_prompt_with_example(doc_type, schema, text_content,
                example_text="""Tax Investment Confirmation
Name: SAMPLE NAME
PAN: SAMPLE1234P
Financial Year: FY 2024-25
Total amount invested in ELSS is RS 120000

S no. Mutual Fund Transaction Date Amount(INR)
1 Xyz ELSS Tax Saver Fund Direct Plan Growth DD MM YYY  30000 
2 ABcd ELSS Tax Saver Fund Direct Growth DD MM YYY      60000
3 Quant ELSS Tax Saver Fund Direct Growth DD MM YYY     30000

As stated in the offer document, the investments are eligible for Tax benefit u/s 80C as per the Income Tax laws.""",
                example_json="""{\n  \"elss_amount\": 120000.05,\n  \"total_investment\": 120000.05,\n  \"fund_name\": \"Multiple ELSS Funds\",\n  \"financial_year\": \"2024-25\"\n}""" ), schema
        else:
            return _create_structured_prompt(doc_type, schema, text_content), schema

def _create_structured_prompt(doc_type: str, schema, text_content: str):
    """Creates a standardized prompt for structured JSON extraction."""
    json_schema_str = json.dumps(schema, indent=2)
    
    specific_instructions = ""
    if doc_type == "form_16":
        specific_instructions = f"""
        For Form 16 documents, carefully extract ALL financial data from the complete document:
        
        **SALARY EXTRACTION (CRITICAL - Use ANNUAL totals only, NOT quarterly amounts):**
        - **gross_salary:** Use "Total" from Part A summary OR "Income chargeable under the head 'Salaries'" in Part B
        - **total_gross_salary:** Same as gross_salary - the final annual total after all inclusions  
        - **basic_salary:** Look for "Salary as per provisions contained in section 17(1)" in Part B Annexure
        - **perquisites:** Look for "Value of perquisites under section 17(2)" in Part B Annexure - includes ESOP/stock options
        - **hra_received:** Look for "House rent allowance under section 10(13A)" in exemptions section
        
        **CRITICAL: DO NOT sum quarterly amounts from Part A. Use the ANNUAL TOTALS from Part B.**
        
        **TAX & DEDUCTIONS:**
        - **tax_deducted:** Find "Total tax deducted" OR quarterly TDS amounts
        - **epf_amount:** Look for "Employee Provident Fund" OR "contributions to provident fund etc. under section 80C"
        - **professional_tax:** Look for "Tax on employment under section 16(iii)" OR "Professional Tax"
        
        **EMPLOYEE DETAILS:**
        - **employee_name:** Employee name from the form header
        - **pan:** Employee PAN number
        - **employer_name:** Employer/Company name
        - **financial_year:** Extract the assessment year (e.g., "2024-25")
        
        **IMPORTANT EXTRACTION RULES:**
        1. Read the ENTIRE document - Form16 can be 8-10 pages long
        2. Look for EXACT section references like "section 17(1)", "section 16(iii)", "section 80C"
        3. **NEVER add quarterly amounts** - Part A shows quarterly breakdowns, Part B shows annual totals
        4. **Use Part B Annexure values** for salary components: 17(1), 17(2), 16(ia), etc.
        5. **gross_salary should equal basic_salary + perquisites** (17(1) + 17(2))
        6. Professional Tax is usually ₹200-2400 annually (section 16(iii))
        7. EPF is typically 12% of basic salary, capped at ₹1.8L annually (section 80C)
        8. Return 0.0 for numeric fields not found, "" for missing strings
        9. **VALIDATE: gross_salary should match the sum of 17(1) + 17(2) components**
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
        - **Tax Deducted (TDS) - STEP-BY-STEP GUIDE:**
          
          **STEP 1: Look for Common TDS Phrases**
          Search for these COMMON phrases in Form16 and extract numbers near them:
          • "Tax deducted and deposited" (usually in Part A)
          • "Total tax deducted" or "Tax deducted at source"
          • "Amount of tax deducted" in tables
          • "Tax payable" (but verify it's TDS, not total tax liability)
          • Lines containing both "tax" and "deducted" together
          
          **STEP 2: Check Monthly/Quarterly TDS Tables**
          Look for tables with columns like:
          | Month | Salary | Tax Deducted |
          |-------|---------|--------------|
          | Apr   | 500000  | 45000       |
          | May   | 500000  | 45000       |
          If found, ADD UP all "Tax Deducted" amounts.
          
          **STEP 3: Search Part A Section**
          In "Part A - Details of Salary Paid", look for:
          • Any line containing "tax deducted" followed by a number
          • Pattern: "₹[digits with commas]" near words "tax", "deducted", "TDS"
          
          **STEP 4: If No Direct Amount, Calculate**
          Look for:
          • "Tax payable on total income: ₹[X]"
          • "Tax payable after rebate: ₹[Y]" 
          • TDS = X - Y (if both found)
          
          **STEP 5: Validation**
          • TDS amount should be POSITIVE and reasonable (not 0 for substantial salaries)
          • TDS is typically 10-30% of gross salary depending on income level
          • If you find 0 for high salaries, re-examine document carefully
          • TDS amounts are usually 5-7 digit numbers for salaried employees
          
          **EXTRACTION PATTERNS TO MATCH:**
          - Numbers with commas: "₹15,50,000" → extract 1550000
          - Without rupee symbol: "15,50,000" → extract 1550000  
          - With decimal: "15,50,000.00" → extract 1550000
          - In parentheses: "(15,50,000)" → extract 1550000
        - **Deductions (Chapter VI-A):** Extract amounts for 80C, 80CCD(1B), 80D, etc. Look for sections like "Deductions under Chapter VI-A". Sum up all applicable deductions.
        - **Perquisites:** Extract from "Value of perquisites under section 17(2)" - commonly includes ESOP/ESPP stock option gains, company car benefits, etc.
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
