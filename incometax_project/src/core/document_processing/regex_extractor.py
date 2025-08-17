import re

def preprocess_bank_interest_certificate_text(raw_text: str) -> str:
    """
    Pre-processes the raw text of a bank interest certificate to extract the summary table.
    This helps the LLM to focus on the correct values.
    """
    try:
        # Regex to find the table from "Deposit Number" to "Total"
        table_pattern = re.compile(r"(Deposit Number.*?Total\s+[\d,]+\.?\d*\s+[\d,]+\.?\d*\s+[\d,]+\.?\d*\s+[\d,]+\.?\d*)", re.IGNORECASE | re.DOTALL)
        table_match = table_pattern.search(raw_text)

        if table_match:
            return table_match.group(1) # Return the captured group
        else:
            # Fallback if the specific table isn't found
            return raw_text
    except Exception as e:
        print(f"Error in preprocessing bank interest certificate: {e}")
        return raw_text

def extract_form16_perquisites_regex(json_data):
    """Extract perquisites and basic salary from Form12BA using regex"""
    try:
        raw_text = json_data.get('raw_text', '')
        if not raw_text:
            print("⚠️ No raw text available for perquisites extraction")
            return None
        
        print("🔍 Attempting perquisites extraction from Form 16 Part B...")

        basic_salary_pattern = r"Salary as per provisions contained in section 17\(1\)\s*([\d,]+\.\d{2})"
        perquisites_pattern = r"Value of perquisites under section 17\(2\).*?([\d,]+\.\d{2})"
        total_gross_salary_pattern = r"Gross Salary.*Total\s*([\d,]+\.\d{2})"
        
        # Additional patterns for HRA and deductions based on actual Form16 format
        hra_pattern = r"House rent allowance under section 10\(13A\)[\s\S]*?([\d,]+\.?\d*)"
        professional_tax_pattern = r"Tax on employment under section 16\(iii\)[\s\S]*?([\d,]+\.?\d*)"
        
        # Enhanced EPF patterns to catch various formats
        epf_patterns = [
            r"contributions to provident fund etc\. under section 80C[\s\S]*?([\d,]+\.?\d*)",
            r"Employee Provident Fund[\s\S]*?([\d,]+\.?\d*)",
            r"Provident Fund contribution[\s\S]*?([\d,]+\.?\d*)",
            r"EPF contribution[\s\S]*?([\d,]+\.?\d*)",
            r"PF deduction[\s\S]*?([\d,]+\.?\d*)",
            r"Employees Provident Fund[\s\S]*?([\d,]+\.?\d*)",
            r"section 80C.*?provident fund[\s\S]*?([\d,]+\.?\d*)",
            r"Deduction under section 16.*?provident fund[\s\S]*?([\d,]+\.?\d*)"
        ]

        basic_match = re.search(basic_salary_pattern, raw_text, re.IGNORECASE)
        perquisites_match = re.search(perquisites_pattern, raw_text, re.IGNORECASE)
        total_gross_match = re.search(total_gross_salary_pattern, raw_text, re.IGNORECASE | re.DOTALL)
        hra_match = re.search(hra_pattern, raw_text, re.IGNORECASE)
        professional_tax_match = re.search(professional_tax_pattern, raw_text, re.IGNORECASE)
        
        # Try multiple EPF patterns
        epf_match = None
        for epf_pattern in epf_patterns:
            epf_match = re.search(epf_pattern, raw_text, re.IGNORECASE)
            if epf_match:
                print(f"✅ Found EPF using pattern: {epf_pattern[:50]}...")
                break

        if basic_match and perquisites_match and total_gross_match:
            basic_salary = float(basic_match.group(1).replace(',', ''))
            perquisites = float(perquisites_match.group(1).replace(',', ''))
            total_gross_salary = float(total_gross_match.group(1).replace(',', ''))

            # Extract additional fields
            hra_received = float(hra_match.group(1).replace(',', '')) if hra_match else 0.0
            professional_tax = float(professional_tax_match.group(1).replace(',', '')) if professional_tax_match else 0.0
            epf_amount = float(epf_match.group(1).replace(',', '')) if epf_match else 0.0

            print(f"✅ Found Form 16 Part B data by regex:")
            print(f"   Basic Salary: ₹{basic_salary:,.2f}")
            print(f"   Perquisites: ₹{perquisites:,.2f}")
            print(f"   Total Gross Salary: ₹{total_gross_salary:,.2f}")
            print(f"   HRA Received: ₹{hra_received:,.2f}")
            print(f"   Professional Tax: ₹{professional_tax:,.2f}")
            print(f"   EPF Amount: ₹{epf_amount:,.2f}")

            return {
                'basic_salary': basic_salary,
                'perquisites': perquisites,
                'total_gross_salary': total_gross_salary,
                'gross_salary': total_gross_salary,
                'hra_received': hra_received,
                'professional_tax': professional_tax,
                'epf_amount': epf_amount
            }
        else:
            print("❌ Could not find all required fields in Form 16 Part B using regex.")
            return None
        
    except Exception as e:
        print(f"❌ Error in Form 16 Part B extraction: {str(e)}")
        return None

def extract_bank_interest_regex(json_data):
    """Extract bank interest certificate data using regex as fallback"""
    try:
        raw_text = json_data.get('raw_text', '')
        if not raw_text:
            print("⚠️ No raw text available for bank interest extraction")
            return None
        
        print("🔍 Attempting bank interest extraction with robust regex...")
        
        # This regex is designed to find the totals in the structured table extracted by Camelot.
        # It looks for the word "Total" and then captures the next four numerical values.
        total_pattern = r"Total\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})"
        total_match = re.search(total_pattern, raw_text, re.IGNORECASE)
        
        if total_match:
            principal = float(total_match.group(1).replace(',', ''))
            interest_amount = float(total_match.group(2).replace(',', ''))
            accrued_interest = float(total_match.group(3).replace(',', ''))
            tds_amount = float(total_match.group(4).replace(',', ''))
            
            total_interest = interest_amount + accrued_interest

            print(f"✅ Found bank interest data by regex:")
            print(f"   Interest Amount: ₹{interest_amount:,.2f}")
            print(f"   Accrued Interest: ₹{accrued_interest:,.2f}")
            print(f"   Total Interest: ₹{total_interest:,.2f}")
            print(f"   TDS Amount: ₹{tds_amount:,.2f}")
            
            bank_pattern = r'Branch Name\s*\n([A-Z\s]+)'
            bank_match = re.search(bank_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            bank_name = bank_match.group(1).strip() if bank_match else "Unknown"
            
            if 'Principal' in bank_name or 'Amount' in bank_name:
                bank_name_pattern = r'IT PARK'
                bank_name_match = re.search(bank_name_pattern, raw_text, re.IGNORECASE)
                if bank_name_match:
                    bank_name = bank_name_match.group(0)
            
            pan_pattern = r'PAN:\s*([A-Z0-9]{10})'
            pan_match = re.search(pan_pattern, raw_text, re.IGNORECASE)
            pan = pan_match.group(1) if pan_match else None
            
            account_pattern = r'(\d{12,16})'
            account_match = re.search(account_pattern, raw_text)
            account_number = account_match.group(1) if account_match else None
            
            return {
                'bank_name': bank_name,
                'account_number': account_number,
                'pan': pan,
                'interest_amount': interest_amount, # Return the individual interest_amount
                'tds_amount': tds_amount,
                'principal_amount': principal,
                'accrued_interest': accrued_interest
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Error in bank interest extraction: {str(e)}")
        return None

def extract_capital_gains_regex(json_data):
    """Extract capital gains data using regex as fallback"""
    try:
        raw_text = json_data.get('raw_text', '')
        if not raw_text:
            print("⚠️ No raw text available for capital gains regex extraction")
            return None
        
        print(f"🔍 Attempting capital gains regex extraction on text length: {len(raw_text)}")
        
        patterns = {
            'short_term_capital_gains': [
                r'Short Term P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Short Term Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'STCG[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Short Term[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'ST P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'short term p&l[:\s]*([-+]?[\d,]+\.?\d*)',
                r'short term[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Short Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Short Term[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Short Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Short Term[:\s]*([-+]?[\d,]+\.?\d*)'
            ],
            'long_term_capital_gains': [
                r'Long Term P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Long Term Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'LTCG[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Long Term[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'LT P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'long term p&l[:\s]*([-+]?[\d,]+\.?\d*)',
                r'long term[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Long Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Long Term[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Long Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                r'Long Term[:\s]*([-+]?[\d,]+\.?\d*)'
            ],
            'intraday_capital_gains': [
                r'Intraday P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Intraday Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Intraday[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                r'Day Trading[:\s]*₹?([-+]?[\d,]+\.?\d*)'
            ],
            'dividend_income': [
                r'Dividends[:\s]*₹?([\d,]+\.?\d*)',
                r'Dividend Income[:\s]*₹?([\d,]+\.?\d*)',
                r'Dividend[:\s]*₹?([\d,]+\.?\d*)'
            ],
            'total_transactions': [
                r'Number of Transactions[:\s]*(\d+)',
                r'Total Transactions[:\s]*(\d+)',
                r'Transaction Count[:\s]*(\d+)',
                r'(\d+)\s*transactions',
                r'(\d+)\s*trades'
            ]
        }
        
        extracted_data = {}
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if field in ['short_term_capital_gains', 'long_term_capital_gains', 'intraday_capital_gains', 'dividend_income']:
                        try:
                            value = float(value.replace(',', ''))
                        except:
                            value = 0.0
                    elif field == 'total_transactions':
                        try:
                            value = int(value)
                        except:
                            value = 0
                    extracted_data[field] = value
                    print(f"✅ Extracted {field}: {value}")
                    break
        
        stcg = extracted_data.get('short_term_capital_gains', 0.0)
        ltcg = extracted_data.get('long_term_capital_gains', 0.0)
        intraday = extracted_data.get('intraday_capital_gains', 0.0)
        
        total_capital_gains = stcg + ltcg + intraday
        extracted_data['total_capital_gains'] = total_capital_gains
        print(f"✅ Calculated total_capital_gains: {total_capital_gains}")
        
        return extracted_data
        
    except Exception as e:
        print(f"⚠️ Error in capital gains regex extraction: {e}")
        return None

def extract_form16_tds_regex(raw_text: str) -> float:
    """
    Extract TDS amount from Form16 using regex patterns
    Returns the TDS amount or 0.0 if not found
    """
    if not raw_text:
        return 0.0
    
    print("🔍 Attempting Form16 TDS extraction with regex...")
    
    # Universal TDS extraction patterns for any Form16 format
    tds_patterns = [
        # Direct TDS phrases (most reliable)
        r'Tax deducted and deposited[^₹\d]*₹?\s*([\d,]{5,}\.?\d*)',
        r'Total tax deducted[:\s]*₹?\s*([\d,]{5,}\.?\d*)', 
        r'Tax deducted at source[:\s]*₹?\s*([\d,]{5,}\.?\d*)',
        r'Amount of tax deducted[^₹\d]*₹?\s*([\d,]{5,}\.?\d*)',
        
        # Common Form16 specific phrases
        r'Tax payable[^₹\d]*₹?\s*([\d,]{6,}\.?\d*)',
        r'Income tax[^₹\d]*deducted[^₹\d]*₹?\s*([\d,]{5,}\.?\d*)',
        
        # Table format quarterly TDS
        r'(?:Quarter|Q[1-4]).*?Tax.*?(\d{5,}\.?\d*)',
        r'(?:Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar).*?(\d{5,}\.?\d*)',
        
        # Part A/B section patterns
        r'Part A[^₹]*₹?\s*([\d,]{6,}\.?\d*)',
        r'deposited.*?Central Government.*?(\d{6,}\.?\d*)',
        
        # General tax amount patterns (with minimum thresholds)
        r'(?:TDS|tax.*deducted).*?(\d{5,}\.?\d*)',
    ]
    
    for i, pattern in enumerate(tds_patterns):
        matches = re.findall(pattern, raw_text, re.IGNORECASE | re.DOTALL)
        if matches:
            try:
                # Take the largest TDS amount found (most likely to be the total)
                tds_amounts = [float(match.replace(',', '')) for match in matches if match.replace(',', '').replace('.', '').isdigit()]
                if tds_amounts:
                    max_tds = max(tds_amounts)
                    if max_tds > 0:
                        print(f"✅ Found TDS amount using pattern {i+1}: ₹{max_tds:,.2f}")
                        return max_tds
            except (ValueError, AttributeError):
                continue
    
    print("❌ No TDS amount found using regex patterns")
    return 0.0


def extract_form16_quarterly_data_regex(json_data):
    """Extract Form16 quarterly data using regex."""
    raw_text = json_data.get('raw_text', '')
    if not raw_text:
        print("⚠️ No raw text available for quarterly data extraction")
        return None

    print("🔍 Attempting Form16 quarterly data extraction with regex...")
    quarterly_data = {}
    total_salary = 0.0
    total_tax = 0.0
    
    # First try direct TDS extraction patterns
    direct_tds_patterns = [
        r'Tax deducted and deposited[:\s]*₹?([\d,]+\.?\d*)',
        r'Total tax deducted[:\s]*₹?([\d,]+\.?\d*)', 
        r'TDS[:\s]*₹?([\d,]+\.?\d*)',
        r'Income Tax deducted[:\s]*₹?([\d,]+\.?\d*)',
        r'Tax payable on total income[:\s]*₹?([\d,]+\.?\d*)'
    ]
    
    for pattern in direct_tds_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            try:
                direct_tds = float(match.group(1).replace(',', ''))
                if direct_tds > 0:
                    print(f"✅ Found direct TDS amount: ₹{direct_tds:,.2f}")
                    return {
                        'total_salary': 0.0,  # Will be extracted separately
                        'total_tax': direct_tds,
                        'extraction_method': 'direct_tds_pattern'
                    }
            except ValueError:
                continue

    quarter_patterns = {
        "Q1": r"(?:Q1|Quarter 1|1st Quarter|first quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[\s,]*Tax[:\s]*₹?([\d,]+\.?\d*)",
        "Q2": r"(?:Q2|Quarter 2|2nd Quarter|second quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[\s,]*Tax[:\s]*₹?([\d,]+\.?\d*)",
        "Q3": r"(?:Q3|Quarter 3|3rd Quarter|third quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[\s,]*Tax[:\s]*₹?([\d,]+\.?\d*)",
        "Q4": r"(?:Q4|Quarter 4|4th Quarter|fourth quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[\s,]*Tax[:\s]*₹?([\d,]+\.?\d*)",
    }

    for quarter, pattern in quarter_patterns.items():
        match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                salary = float(match.group(1).replace(',', ''))
                tax = float(match.group(2).replace(',', ''))
                quarterly_data[quarter] = {"salary": salary, "tax": tax}
                total_salary += salary
                total_tax += tax
                print(f"✅ Extracted {quarter}: Salary ₹{salary:,.2f}, Tax ₹{tax:,.2f}")
            except ValueError:
                print(f"⚠️ Could not parse numeric values for {quarter}")
                continue

    if quarterly_data:
        print(f"✅ Total Salary from Quarterly Data: ₹{total_salary:,.2f}")
        print(f"✅ Total Tax from Quarterly Data: ₹{total_tax:,.2f}")
        return {
            'total_salary': total_salary,
            'total_tax': total_tax,
            'quarterly_breakdown': quarterly_data
        }
    else:
        print("❌ No quarterly data found using regex patterns.")
        return None

def extract_payslip_regex(json_data):
    """Extract payslip data using regex as fallback"""
    try:
        raw_text = json_data.get('raw_text', '')
        if not raw_text:
            print("⚠️ No raw text available for payslip regex extraction")
            return None

        print("🔍 Attempting payslip extraction with regex...")

        patterns = {
            'employee_name': [r'Employee Name[:\s]*([A-Za-z\s]+)'] ,
            'gross_salary': [r'Gross Salary[:\s]*₹?([\d,]+\.?\d*)'],
            'tax_deducted': [r'Tax Deduction[:\s]*₹?([\d,]+\.?\d*)', r'Income Tax[:\s]*₹?([\d,]+\.?\d*)'],
            'pan': [r'PAN[:\s]*([A-Z0-9]{10})'],
            'epf_amount': [r'EPF Contribution[:\s]*₹?([\d,]+\.?\d*)', r'EPF[:\s]*₹?([\d,]+\.?\d*)'],
        }

        extracted_data = {}

        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if field in ['gross_salary', 'tax_deducted', 'epf_amount']:
                        try:
                            value = float(value.replace(',', ''))
                        except:
                            value = 0.0
                    extracted_data[field] = value
                    print(f"✅ Extracted {field}: {value}")
                    break
        
        return extracted_data

    except Exception as e:
        print(f"❌ Error in payslip regex extraction: {str(e)}")
        return None