# Income Tax Calculation Guide for FY 2024-25 (AY 2025-26)
## Complete Implementation Guide for Accurate Tax Computation

### TABLE OF CONTENTS
1. [Income Classification](#income-classification)
2. [Capital Gains Calculation](#capital-gains-calculation)
3. [Normal Income Tax Calculation](#normal-income-tax-calculation)
4. [Deduction Calculations](#deduction-calculations)
5. [Tax Computation Flow](#tax-computation-flow)
6. [Surcharge and Cess](#surcharge-and-cess)
7. [Rebates and Reliefs](#rebates-and-reliefs)
8. [Implementation Algorithm](#implementation-algorithm)

---

## INCOME CLASSIFICATION

### Step 1: Separate Income Types

**CRITICAL**: Income must be classified before tax calculation

```
TOTAL INCOME = Salary Income + Other Income + Business Income + Capital Gains

SEPARATE FOR TAX CALCULATION:
1. Normal Income = Salary + Other Income + Business Income
2. Short Term Capital Gains (STCG) - Section 111A
3. Long Term Capital Gains (LTCG) - Section 112A
4. Other Capital Gains - Section 112
```

### Income Sources Breakdown:

#### A. SALARY INCOME
- Basic Salary + DA
- HRA (taxable portion after exemption)
- Special Allowances
- Perquisites
- ESPP gains
- **Less**: Standard Deduction (₹75,000 in new regime, ₹50,000 in old regime)

#### B. OTHER INCOME
- Bank Interest (Savings + FD)
- Dividend Income
- Rental Income
- Any other income

#### C. BUSINESS/PROFESSION INCOME
- Net profit from business
- Professional income
- Speculation business income

#### D. CAPITAL GAINS (SEPARATE CALCULATION)
- **STCG (Section 111A)**: Equity shares held < 12 months with STT
- **LTCG (Section 112A)**: Equity shares held ≥ 12 months with STT  
- **Other LTCG (Section 112)**: Non-equity assets held > 24/36 months

---

## CAPITAL GAINS CALCULATION

### A. SHORT TERM CAPITAL GAINS (Section 111A)

**Applicable to**: Equity shares/mutual funds held < 12 months with STT paid

```
STCG Tax Rate = 15% (flat rate)
No exemption limit
No indexation benefit
```

**Calculation**:
```
STCG Amount = Sale Price - Purchase Price - Expenses
STCG Tax = STCG Amount × 15%
```

### B. LONG TERM CAPITAL GAINS (Section 112A)

**Applicable to**: Equity shares/mutual funds held ≥ 12 months with STT paid

**CRITICAL RULES**:
1. **Exemption Limit**: ₹1,25,000 per financial year
2. **Tax Rates**:
   - Sales before 23-July-2024: 10%
   - Sales on/after 23-July-2024: 12.5%
3. **No indexation benefit**
4. **Grandfathering**: Gains up to 31-Jan-2018 are exempt

**Calculation Algorithm**:
```
Step 1: Calculate total LTCG for the year
Step 2: Apply exemption
   Exempt Amount = Min(Total LTCG, ₹1,25,000)
   Taxable LTCG = Max(0, Total LTCG - ₹1,25,000)

Step 3: Apply appropriate tax rate
   For sales before 23-Jul-2024: Tax = Taxable LTCG × 10%
   For sales on/after 23-Jul-2024: Tax = Taxable LTCG × 12.5%

Step 4: If mixed dates, calculate separately and sum up
```

**Example**:
```
Total LTCG = ₹46,024
Exempt = Min(₹46,024, ₹1,25,000) = ₹46,024
Taxable LTCG = ₹46,024 - ₹46,024 = ₹0
LTCG Tax = ₹0 × 10% = ₹0
```

### C. OTHER LONG TERM CAPITAL GAINS (Section 112)

**Applicable to**: Non-equity assets, real estate, bonds, etc.

```
Tax Rate = 20% with indexation benefit
OR
Tax Rate = 10% without indexation (whichever is lower)
```

---

## NORMAL INCOME TAX CALCULATION

### STEP 1: Calculate Normal Taxable Income

```
Normal Taxable Income = (Salary + Other Income + Business Income) - Applicable Deductions
```

**IMPORTANT**: Do NOT include capital gains in normal income calculation

### STEP 2: Apply Tax Slabs

#### NEW TAX REGIME (Section 115BAC) - Default for FY 2024-25

```
₹0 to ₹3,00,000:     0%
₹3,00,001 to ₹7,00,000:    5%
₹7,00,001 to ₹10,00,000:   10%
₹10,00,001 to ₹12,00,000:  15%
₹12,00,001 to ₹15,00,000:  20%
Above ₹15,00,000:    30%
```

#### OLD TAX REGIME

```
₹0 to ₹2,50,000:     0%
₹2,50,001 to ₹5,00,000:    5%
₹5,00,001 to ₹10,00,000:   20%
Above ₹10,00,000:    30%
```

### Tax Calculation Algorithm:

```python
def calculate_normal_income_tax(taxable_income, regime):
    if regime == "new":
        slabs = [(300000, 0), (700000, 0.05), (1000000, 0.10), 
                 (1200000, 0.15), (1500000, 0.20), (float('inf'), 0.30)]
    else:
        slabs = [(250000, 0), (500000, 0.05), (1000000, 0.20), 
                 (float('inf'), 0.30)]
    
    tax = 0
    prev_limit = 0
    
    for limit, rate in slabs:
        if taxable_income <= prev_limit:
            break
        taxable_in_slab = min(taxable_income, limit) - prev_limit
        tax += taxable_in_slab * rate
        prev_limit = limit
        if taxable_income <= limit:
            break
    
    return tax
```

---

## DEDUCTION CALCULATIONS

### NEW REGIME DEDUCTIONS (Very Limited)

```
1. Standard Deduction: ₹75,000 (for salaried)
2. Employer NPS contribution under 80CCD(2): Up to 10% of salary
3. Deduction under 80CCH: Pension funds
4. Deduction under 80JJAA: Employment generation
```

### OLD REGIME DEDUCTIONS (Comprehensive)

#### A. HRA EXEMPTION (Section 10(13A))
```
HRA Exemption = Minimum of:
1. Actual HRA received
2. 50% of basic salary (metro) / 40% (non-metro)
3. (Rent paid - 10% of basic salary)
```

#### B. SECTION 80C (₹1,50,000 limit)
```
- EPF contribution
- PPF investment
- ELSS mutual funds
- Life insurance premium
- NSC
- SCSS
- Sukanya Samriddhi
- Home loan principal
- Tuition fees (2 children)
```

#### C. SECTION 80CCD(1B) (₹50,000 limit)
```
Additional NPS contribution beyond 80C
```

#### D. SECTION 80D (Health Insurance)
```
Self/Family:
- Below 60 years: ₹25,000
- Above 60 years: ₹50,000

Parents:
- Below 60 years: ₹25,000  
- Above 60 years: ₹50,000

Maximum combined: ₹1,00,000 (if any senior citizen)
```

#### E. SECTION 80TTA/80TTB (Interest Income)
```
80TTA (Below 60 years): ₹10,000 on savings interest
80TTB (Above 60 years): ₹50,000 on deposit interest
```

#### F. SECTION 80G (Donations)
```
50% of donation amount (most common)
100% of donation (specific funds)
Subject to 10% of adjusted gross total income limit
```

#### G. SECTION 80E (Education Loan Interest)
```
Full interest amount for 8 consecutive years
No upper limit
```

---

## TAX COMPUTATION FLOW

### COMPLETE CALCULATION SEQUENCE

```
1. INCOME CLASSIFICATION
   ├── Normal Income = Salary + Other Income + Business Income
   ├── STCG (Section 111A)
   ├── LTCG (Section 112A)  
   └── Other LTCG (Section 112)

2. DEDUCTION CALCULATION
   ├── Calculate applicable deductions based on regime
   └── Normal Taxable Income = Normal Income - Deductions

3. TAX CALCULATION
   ├── Normal Income Tax = Apply slabs to Normal Taxable Income
   ├── STCG Tax = STCG Amount × 15%
   ├── LTCG Tax = Calculate using 112A method
   └── Other LTCG Tax = Calculate using 112 method

4. TOTAL TAX BEFORE REBATE
   Total Tax = Normal Income Tax + STCG Tax + LTCG Tax + Other LTCG Tax

5. APPLY REBATE (Section 87A)
   ├── New Regime: If Normal Taxable Income ≤ ₹7,00,000
   │   Rebate = Min(Normal Income Tax, ₹25,000)
   └── Old Regime: If Normal Taxable Income ≤ ₹5,00,000  
       Rebate = Min(Normal Income Tax, ₹12,500)
   
   IMPORTANT: Rebate applies ONLY to Normal Income Tax, NOT to Capital Gains Tax

6. TAX AFTER REBATE
   Tax After Rebate = Total Tax - Rebate

7. SURCHARGE CALCULATION
   Calculate based on total income including capital gains

8. CESS CALCULATION
   Health & Education Cess = (Tax After Rebate + Surcharge) × 4%

9. FINAL TAX LIABILITY
   Final Tax = Tax After Rebate + Surcharge + Cess
```

---

## SURCHARGE AND CESS

### SURCHARGE CALCULATION

**Income Slabs for Surcharge** (based on Total Income including Capital Gains):

```
₹50,00,000 to ₹1,00,00,000:    10%
₹1,00,00,000 to ₹2,00,00,000:  15%  
₹2,00,00,000 to ₹5,00,00,000:  25%
Above ₹5,00,00,000:            37% (Old Regime) / 25% (New Regime)
```

**IMPORTANT**: Special surcharge rates for capital gains:
- STCG (111A), LTCG (112A): Maximum surcharge is 15%
- Other LTCG (112): Maximum surcharge is 15%

### CESS CALCULATION

```
Health & Education Cess = 4% of (Income Tax + Surcharge)
```

---

## REBATES AND RELIEFS

### SECTION 87A REBATE

#### New Regime:
```
If Normal Taxable Income ≤ ₹7,00,000:
Rebate = Min(Normal Income Tax, ₹25,000)
```

#### Old Regime:
```
If Normal Taxable Income ≤ ₹5,00,000:
Rebate = Min(Normal Income Tax, ₹12,500)
```

**CRITICAL**: Rebate applies ONLY to normal income tax, not capital gains tax

### RELIEF UNDER SECTION 89

For salary arrears or advance received in wrong year

---

## IMPLEMENTATION ALGORITHM

### MAIN TAX CALCULATION FUNCTION

```python
def calculate_total_tax_liability(income_data, regime="new"):
    # Step 1: Income Classification
    normal_income = income_data['salary'] + income_data['other_income'] + income_data['business_income']
    stcg_111a = income_data['stcg_111a']
    ltcg_112a = income_data['ltcg_112a']
    other_ltcg = income_data['other_ltcg']
    
    # Step 2: Calculate Deductions
    if regime == "new":
        deductions = calculate_new_regime_deductions(income_data)
    else:
        deductions = calculate_old_regime_deductions(income_data)
    
    # Step 3: Normal Taxable Income
    normal_taxable = max(0, normal_income - deductions)
    
    # Step 4: Calculate Normal Income Tax
    normal_tax = calculate_normal_income_tax(normal_taxable, regime)
    
    # Step 5: Calculate Capital Gains Tax
    stcg_tax = stcg_111a * 0.15  # 15% flat rate
    ltcg_tax = calculate_ltcg_112a_tax(ltcg_112a, income_data['ltcg_dates'])
    other_ltcg_tax = calculate_other_ltcg_tax(other_ltcg)
    
    # Step 6: Total Tax Before Rebate
    total_tax_before_rebate = normal_tax + stcg_tax + ltcg_tax + other_ltcg_tax
    
    # Step 7: Apply Rebate (only on normal income tax)
    rebate = calculate_section_87a_rebate(normal_taxable, normal_tax, regime)
    
    # Step 8: Tax After Rebate
    tax_after_rebate = total_tax_before_rebate - rebate
    
    # Step 9: Calculate Total Income for Surcharge
    total_income = normal_income + stcg_111a + ltcg_112a + other_ltcg
    
    # Step 10: Calculate Surcharge
    surcharge = calculate_surcharge(tax_after_rebate, total_income, regime)
    
    # Step 11: Calculate Cess
    cess = (tax_after_rebate + surcharge) * 0.04
    
    # Step 12: Final Tax Liability
    final_tax = tax_after_rebate + surcharge + cess
    
    return {
        'normal_taxable_income': normal_taxable,
        'normal_income_tax': normal_tax,
        'stcg_tax': stcg_tax,
        'ltcg_tax': ltcg_tax,
        'other_ltcg_tax': other_ltcg_tax,
        'total_tax_before_rebate': total_tax_before_rebate,
        'rebate_87a': rebate,
        'tax_after_rebate': tax_after_rebate,
        'surcharge': surcharge,
        'cess': cess,
        'final_tax_liability': final_tax,
        'regime': regime
    }

def calculate_ltcg_112a_tax(ltcg_amount, sale_dates):
    if ltcg_amount <= 125000:
        return 0  # Fully exempt
    
    taxable_ltcg = ltcg_amount - 125000
    
    # Apply different rates based on sale dates
    tax = 0
    for sale in sale_dates:
        if sale['date'] < datetime(2024, 7, 23):
            tax += sale['amount'] * 0.10  # 10% for pre-July 23, 2024
        else:
            tax += sale['amount'] * 0.125  # 12.5% for post-July 23, 2024
    
    return tax

def calculate_section_87a_rebate(normal_taxable_income, normal_income_tax, regime):
    if regime == "new" and normal_taxable_income <= 700000:
        return min(normal_income_tax, 25000)
    elif regime == "old" and normal_taxable_income <= 500000:
        return min(normal_income_tax, 12500)
    else:
        return 0
```

---

## VALIDATION RULES

### Input Validation:
1. Ensure all income amounts are non-negative
2. Validate that LTCG dates are within the financial year
3. Check that STT has been paid for 111A and 112A applicability
4. Verify holding period for LTCG classification

### Calculation Validation:
1. Normal income should not include capital gains
2. Capital gains should be calculated separately
3. Rebate should apply only to normal income tax
4. Surcharge should be calculated on total income
5. Maximum surcharge for capital gains should not exceed 15%

### Output Validation:
1. Final tax should never be negative
2. Sum of individual taxes should equal total tax before adjustments
3. Cess should always be 4% of (tax + surcharge)

---

## COMMON MISTAKES TO AVOID

1. **❌ WRONG**: Including LTCG in normal income calculation
   **✅ CORRECT**: Calculate LTCG separately under Section 112A

2. **❌ WRONG**: Applying rebate to total tax including capital gains
   **✅ CORRECT**: Apply rebate only to normal income tax

3. **❌ WRONG**: Using single tax rate for all LTCG sales
   **✅ CORRECT**: Apply 10% for pre-July 23, 2024 and 12.5% for post-July 23, 2024

4. **❌ WRONG**: Ignoring LTCG exemption limit
   **✅ CORRECT**: Apply ₹1,25,000 exemption before calculating LTCG tax

5. **❌ WRONG**: Applying enhanced surcharge to capital gains
   **✅ CORRECT**: Maximum 15% surcharge for capital gains income

---

## TEST CASES

### Test Case 1: CA Report Scenario
```
Input:
- Salary: ₹51,86,194
- Other Income: ₹97,385  
- LTCG (112A): ₹46,024
- Total Income: ₹53,29,603

Expected Output (New Regime):
- Normal Taxable Income: ₹52,83,580 (after ₹75,000 standard deduction)
- Normal Income Tax: ₹12,75,074
- LTCG Tax: ₹0 (below ₹1,25,000 exemption)
- Total Tax: ₹85,410 (after surcharge and cess)
```

This guide ensures your system calculates tax accurately according to Indian Income Tax laws for FY 2024-25.