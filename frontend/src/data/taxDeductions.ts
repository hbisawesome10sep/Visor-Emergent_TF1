/**
 * Comprehensive Tax Deductions Data
 * Based on Chapter VI-A of the Indian Income Tax Act
 * FY 2025-26 / AY 2026-27
 */

export type TaxDeduction = {
  id: string;
  section: string;
  name: string;
  shortDescription: string;
  fullDescription: string;
  limit: number | null; // null means no limit
  example: string;
  eligibility: string;
  documents: string[];
  icon: string;
  category: 'investments' | 'insurance' | 'savings' | 'loans' | 'donations' | 'housing' | 'medical' | 'other';
  popular: boolean;
};

export const TAX_DEDUCTIONS: TaxDeduction[] = [
  // ════════════════════════════════════════
  // Section 80C - ₹1.5 Lakh Limit
  // ════════════════════════════════════════
  {
    id: '80c_ppf',
    section: '80C',
    name: 'Public Provident Fund (PPF)',
    shortDescription: 'Long-term savings with tax-free interest',
    fullDescription: 'PPF is a government-backed savings scheme with a 15-year lock-in period. Interest earned and maturity amount are completely tax-free. Current interest rate is around 7.1% p.a., compounded annually. You can invest ₹500 to ₹1.5 lakh per year.',
    limit: 150000,
    example: 'If you invest ₹1,50,000 in PPF and are in the 30% tax bracket, you save ₹46,800 in taxes (₹1,50,000 × 30% + 4% cess).',
    eligibility: 'Any Indian resident individual. Can also open for minor child.',
    documents: ['PPF passbook', 'Bank statement showing PPF deposits'],
    icon: 'bank',
    category: 'savings',
    popular: true,
  },
  {
    id: '80c_elss',
    section: '80C',
    name: 'ELSS Mutual Funds',
    shortDescription: 'Tax-saving mutual funds with 3-year lock-in',
    fullDescription: 'Equity Linked Savings Scheme (ELSS) funds invest primarily in equities with a mandatory 3-year lock-in - the shortest among all 80C investments. Returns are market-linked and potentially higher than traditional instruments. LTCG above ₹1.25 lakh is taxed at 12.5%.',
    limit: 150000,
    example: 'Invest ₹12,500/month via SIP in ELSS. Annual investment of ₹1.5L qualifies for full 80C deduction, saving up to ₹46,800 in taxes.',
    eligibility: 'Any individual or HUF. Can invest via lump sum or SIP.',
    documents: ['Mutual fund statement', 'CAS (Consolidated Account Statement)'],
    icon: 'chart-line',
    category: 'investments',
    popular: true,
  },
  {
    id: '80c_nps',
    section: '80C',
    name: 'NPS (Tier I)',
    shortDescription: 'Retirement savings with market-linked returns',
    fullDescription: 'National Pension System is a voluntary retirement savings scheme regulated by PFRDA. Contributions up to ₹1.5 lakh qualify under 80C. Additional ₹50,000 deduction available under 80CCD(1B). Partial withdrawal allowed after 3 years for specific purposes.',
    limit: 150000,
    example: 'Contribute ₹1.5L to NPS Tier I for 80C + ₹50K more for 80CCD(1B) = Total deduction of ₹2L, saving up to ₹62,400 in taxes.',
    eligibility: 'Any Indian citizen between 18-70 years.',
    documents: ['NPS statement', 'PRAN card'],
    icon: 'account-clock',
    category: 'savings',
    popular: true,
  },
  {
    id: '80c_epf',
    section: '80C',
    name: 'Employee Provident Fund (EPF)',
    shortDescription: 'Mandatory retirement savings for salaried employees',
    fullDescription: 'EPF is a mandatory retirement benefit for employees earning up to ₹15,000/month (basic + DA). Both employee and employer contribute 12% each. Interest rate is declared by EPFO annually (around 8.1%). Employee contribution qualifies for 80C deduction.',
    limit: 150000,
    example: 'Your monthly EPF contribution of ₹1,800 (12% of ₹15,000 basic) = ₹21,600/year automatically counts toward your 80C limit.',
    eligibility: 'Salaried employees in establishments with 20+ workers.',
    documents: ['EPF passbook', 'Form 16'],
    icon: 'briefcase',
    category: 'savings',
    popular: true,
  },
  {
    id: '80c_life_insurance',
    section: '80C',
    name: 'Life Insurance Premium',
    shortDescription: 'Premium paid for life insurance policies',
    fullDescription: 'Premium paid for life insurance policies for self, spouse, and children qualifies for deduction. The policy sum assured should be at least 10x the annual premium for policies issued after April 2012. Includes term insurance, endowment, and whole life policies.',
    limit: 150000,
    example: 'Pay ₹50,000 annual premium for a term insurance plan with ₹1 crore cover. This ₹50K is deductible under 80C.',
    eligibility: 'Individual taxpayers. Policy must be on self, spouse, or children.',
    documents: ['Premium receipt', 'Policy document'],
    icon: 'shield-account',
    category: 'insurance',
    popular: true,
  },
  {
    id: '80c_ulip',
    section: '80C',
    name: 'ULIP (Unit Linked Insurance Plan)',
    shortDescription: 'Insurance + investment hybrid product',
    fullDescription: 'ULIPs combine life insurance with investment in equity/debt funds. 5-year lock-in period. Premium allocation charges apply in initial years. Maturity proceeds are tax-free if annual premium is less than ₹2.5 lakh (for policies issued after Feb 2021).',
    limit: 150000,
    example: 'Invest ₹1 lakh annually in ULIP for 10 years. Each year\'s premium is deductible under 80C, and maturity amount is tax-free.',
    eligibility: 'Individual taxpayers seeking insurance + investment combo.',
    documents: ['Premium receipt', 'ULIP statement'],
    icon: 'chart-box',
    category: 'insurance',
    popular: false,
  },
  {
    id: '80c_nsc',
    section: '80C',
    name: 'National Savings Certificate (NSC)',
    shortDescription: 'Government-backed fixed income savings',
    fullDescription: 'NSC is a Post Office savings scheme with 5-year maturity. Interest rate is around 7.7% p.a., compounded annually but payable at maturity. Interest earned (except in final year) is deemed reinvested and qualifies for fresh 80C deduction each year.',
    limit: 150000,
    example: 'Invest ₹1 lakh in NSC. After 5 years, you get ~₹1.45 lakh. The reinvested interest each year adds to your 80C deduction.',
    eligibility: 'Indian residents. Can be held singly or jointly.',
    documents: ['NSC certificate', 'Post office passbook'],
    icon: 'certificate',
    category: 'savings',
    popular: false,
  },
  {
    id: '80c_ssy',
    section: '80C',
    name: 'Sukanya Samriddhi Yojana',
    shortDescription: 'Savings scheme for girl child\'s future',
    fullDescription: 'SSY is a government scheme for parents of girl children below 10 years. Offers one of the highest interest rates (~8.2% p.a.) among small savings. Account matures when girl turns 21. Minimum ₹250/year, maximum ₹1.5 lakh/year.',
    limit: 150000,
    example: 'Open SSY for your 5-year-old daughter with ₹1.5L/year. By age 21, the corpus grows to ~₹65 lakh tax-free.',
    eligibility: 'Parents/guardians of girl child under 10 years. Max 2 accounts.',
    documents: ['SSY passbook', 'Deposit receipts'],
    icon: 'baby-face-outline',
    category: 'savings',
    popular: true,
  },
  {
    id: '80c_fd',
    section: '80C',
    name: '5-Year Tax Saver FD',
    shortDescription: 'Bank fixed deposit with 5-year lock-in',
    fullDescription: 'Tax-saving FDs have a 5-year lock-in period with no premature withdrawal. Interest rates are typically 6-7% p.a., taxable annually. Senior citizens get 0.5% higher rate. Interest earned is taxable, unlike PPF.',
    limit: 150000,
    example: 'Deposit ₹1.5 lakh in Tax Saver FD at 7% for 5 years. Get 80C deduction immediately, but interest of ~₹10,500/year is taxable.',
    eligibility: 'Any individual or HUF.',
    documents: ['FD receipt', 'Bank statement'],
    icon: 'safe',
    category: 'savings',
    popular: true,
  },
  {
    id: '80c_tuition',
    section: '80C',
    name: 'Children\'s Tuition Fees',
    shortDescription: 'School/college tuition fees for children',
    fullDescription: 'Tuition fees paid for full-time education of up to 2 children qualifies for deduction. Includes schools, colleges, and universities in India. Does not cover coaching classes, development fees, transport, or hostel charges.',
    limit: 150000,
    example: 'Pay ₹75,000 tuition fee for each of your 2 children = ₹1.5 lakh deduction under 80C, saving up to ₹46,800 in taxes.',
    eligibility: 'Parents paying tuition for children. Max 2 children.',
    documents: ['Fee receipts from institution', 'School/college ID'],
    icon: 'school',
    category: 'other',
    popular: true,
  },
  {
    id: '80c_home_loan_principal',
    section: '80C',
    name: 'Home Loan Principal Repayment',
    shortDescription: 'Principal portion of home loan EMI',
    fullDescription: 'The principal component of your home loan EMI qualifies for 80C deduction. This is part of the overall ₹1.5 lakh limit shared with other 80C investments. Note: Interest portion is separately deductible under Section 24(b).',
    limit: 150000,
    example: 'If your annual home loan EMI is ₹6 lakh with ₹2 lakh as principal repayment, this ₹2 lakh counts toward 80C (subject to ₹1.5L cap).',
    eligibility: 'Individuals with self-occupied or let-out property.',
    documents: ['Loan statement', 'Interest certificate from bank'],
    icon: 'home',
    category: 'housing',
    popular: true,
  },
  {
    id: '80c_stamp_duty',
    section: '80C',
    name: 'Stamp Duty & Registration',
    shortDescription: 'Property registration expenses',
    fullDescription: 'Stamp duty and registration charges paid for purchase of a new residential property qualify for 80C deduction in the year of payment. This is a one-time benefit available in the year of property purchase.',
    limit: 150000,
    example: 'Buy a ₹80 lakh flat, pay ₹4.8 lakh as stamp duty (6%) + ₹80K registration. This ₹5.6 lakh qualifies for 80C (up to ₹1.5L limit).',
    eligibility: 'First-time home buyers or those purchasing new property.',
    documents: ['Stamp duty receipt', 'Sale deed', 'Registration receipt'],
    icon: 'file-document',
    category: 'housing',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80CCD(1B) - Additional ₹50,000
  // ════════════════════════════════════════
  {
    id: '80ccd1b',
    section: '80CCD(1B)',
    name: 'NPS Additional Contribution',
    shortDescription: 'Extra ₹50,000 NPS deduction over 80C limit',
    fullDescription: 'This is an ADDITIONAL deduction of up to ₹50,000 for contributions to NPS Tier I account, OVER AND ABOVE the ₹1.5 lakh limit of 80C. This means you can claim up to ₹2 lakh total deduction (₹1.5L under 80C + ₹50K under 80CCD(1B)).',
    limit: 50000,
    example: 'Already maxed out ₹1.5L in 80C? Contribute ₹50K more to NPS and get additional deduction, saving ₹15,600 more in 30% bracket.',
    eligibility: 'Any individual contributing to NPS Tier I.',
    documents: ['NPS statement', 'Contribution receipt'],
    icon: 'cash-plus',
    category: 'savings',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 80CCD(2) - Employer NPS Contribution
  // ════════════════════════════════════════
  {
    id: '80ccd2',
    section: '80CCD(2)',
    name: 'Employer NPS Contribution',
    shortDescription: 'Employer\'s contribution to your NPS',
    fullDescription: 'If your employer contributes to your NPS account, that contribution is deductible (up to 14% of basic + DA for government employees, 10% for others). This is IN ADDITION to 80C and 80CCD(1B) limits - no cap on the deduction amount!',
    limit: null,
    example: 'Basic salary ₹10L. Employer contributes 10% (₹1L) to NPS. This entire ₹1L is deductible under 80CCD(2), over your personal limits.',
    eligibility: 'Employees whose employers contribute to NPS.',
    documents: ['Form 16', 'NPS statement'],
    icon: 'briefcase-account',
    category: 'savings',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80D - Health Insurance
  // ════════════════════════════════════════
  {
    id: '80d_self',
    section: '80D',
    name: 'Health Insurance - Self & Family',
    shortDescription: 'Medical insurance premium for self, spouse, children',
    fullDescription: 'Premium paid for health insurance for self, spouse, and dependent children qualifies for deduction up to ₹25,000 (₹50,000 if you\'re a senior citizen). Includes preventive health check-up up to ₹5,000. Does not include GST on premium.',
    limit: 25000,
    example: 'Pay ₹18,000/year for family floater health insurance + ₹5,000 for health check-up = ₹23,000 deduction under 80D.',
    eligibility: 'Individual taxpayers. Family includes spouse and dependent children.',
    documents: ['Premium receipt', 'Policy document', 'Health check-up bills'],
    icon: 'hospital-box',
    category: 'insurance',
    popular: true,
  },
  {
    id: '80d_parents',
    section: '80D',
    name: 'Health Insurance - Parents',
    shortDescription: 'Medical insurance premium for parents',
    fullDescription: 'Premium paid for health insurance of parents (whether dependent or not) qualifies for ADDITIONAL deduction - ₹25,000 if parents are below 60, ₹50,000 if either parent is 60+. This is over and above the self/family limit.',
    limit: 50000,
    example: 'Pay ₹25K for your family + ₹45K for senior citizen parents = Total ₹70K deduction (₹25K + ₹50K max for senior parents).',
    eligibility: 'Anyone paying health insurance for parents.',
    documents: ['Premium receipt', 'Parent\'s policy document'],
    icon: 'account-heart',
    category: 'insurance',
    popular: true,
  },
  {
    id: '80d_preventive',
    section: '80D',
    name: 'Preventive Health Check-up',
    shortDescription: 'Annual health check-up expenses',
    fullDescription: 'Expenses on preventive health check-up for self, spouse, children, or parents are deductible up to ₹5,000. This is NOT an additional limit - it\'s part of the overall 80D limit. Even if you don\'t have insurance, you can claim this.',
    limit: 5000,
    example: 'No health insurance but did a full body check-up for ₹5,000? You can still claim this amount under 80D.',
    eligibility: 'Any individual. Can be claimed for family members too.',
    documents: ['Medical bills', 'Receipt from diagnostic center'],
    icon: 'clipboard-pulse',
    category: 'medical',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80DD - Disabled Dependent
  // ════════════════════════════════════════
  {
    id: '80dd',
    section: '80DD',
    name: 'Disabled Dependent Care',
    shortDescription: 'Expenses for disabled dependent\'s care',
    fullDescription: 'Deduction for expenses incurred on medical treatment, training, and rehabilitation of a disabled dependent (spouse, children, parents, siblings). ₹75,000 for disability, ₹1.25 lakh for severe disability (80%+). Fixed deduction regardless of actual expense.',
    limit: 125000,
    example: 'Care for a severely disabled sibling (80%+ disability) allows you to claim flat ₹1.25 lakh deduction, irrespective of actual spending.',
    eligibility: 'Resident individuals with disabled dependent.',
    documents: ['Form 10-IA', 'Disability certificate from medical authority'],
    icon: 'wheelchair-accessibility',
    category: 'medical',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80DDB - Medical Treatment
  // ════════════════════════════════════════
  {
    id: '80ddb',
    section: '80DDB',
    name: 'Specified Disease Treatment',
    shortDescription: 'Treatment of specified diseases',
    fullDescription: 'Deduction for medical treatment of specified diseases like cancer, AIDS, neurological diseases, chronic renal failure, etc. Up to ₹40,000 for non-senior citizens, ₹1 lakh for senior citizens. Actual expense or limit, whichever is lower.',
    limit: 100000,
    example: 'Spend ₹2 lakh on cancer treatment for your 65-year-old parent. Claim ₹1 lakh deduction under 80DDB.',
    eligibility: 'Treatment of self or dependent for specified diseases.',
    documents: ['Form 10-I from specialist doctor', 'Medical bills', 'Prescription'],
    icon: 'medical-bag',
    category: 'medical',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80E - Education Loan Interest
  // ════════════════════════════════════════
  {
    id: '80e',
    section: '80E',
    name: 'Education Loan Interest',
    shortDescription: 'Interest paid on education loan',
    fullDescription: 'ENTIRE interest paid on education loan is deductible - NO UPPER LIMIT! Loan must be from bank/financial institution for higher education of self, spouse, or children. Deduction available for 8 years from when you start repaying or until interest is fully paid.',
    limit: null,
    example: 'Education loan of ₹20 lakh at 10% = ₹2 lakh interest/year. ENTIRE ₹2 lakh is deductible under 80E with no cap!',
    eligibility: 'Individual who has taken education loan for self, spouse, or children.',
    documents: ['Loan statement', 'Interest certificate from bank'],
    icon: 'school-outline',
    category: 'loans',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 80EE/80EEA - Home Loan Interest (First-time Buyers)
  // ════════════════════════════════════════
  {
    id: '80eea',
    section: '80EEA',
    name: 'Affordable Housing Loan Interest',
    shortDescription: 'Additional interest deduction for affordable housing',
    fullDescription: 'Additional deduction of up to ₹1.5 lakh for interest on home loan for affordable housing (stamp duty value up to ₹45 lakh). This is OVER AND ABOVE the ₹2 lakh limit under Section 24(b). Loan must be sanctioned between April 2019 and March 2022.',
    limit: 150000,
    example: 'Buy a ₹40 lakh flat. Pay ₹4 lakh interest. Claim ₹2L under Sec 24(b) + ₹1.5L under 80EEA = ₹3.5L total interest deduction!',
    eligibility: 'First-time home buyers. Property value up to ₹45 lakh.',
    documents: ['Loan sanction letter', 'Interest certificate', 'Property documents'],
    icon: 'home-city',
    category: 'housing',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 80G - Donations
  // ════════════════════════════════════════
  {
    id: '80g_100',
    section: '80G',
    name: 'Donations (100% Deduction)',
    shortDescription: 'Donations to specified funds with full deduction',
    fullDescription: 'Donations to certain funds qualify for 100% deduction: PM CARES Fund, National Defence Fund, PM National Relief Fund, National Children\'s Fund. Cash donations above ₹2,000 are not allowed for deduction.',
    limit: null,
    example: 'Donate ₹1 lakh to PM CARES Fund. Get full ₹1 lakh deduction, saving ₹31,200 in 30% bracket.',
    eligibility: 'Any taxpayer making qualifying donations.',
    documents: ['Donation receipt with 80G certificate number'],
    icon: 'hand-heart',
    category: 'donations',
    popular: false,
  },
  {
    id: '80g_50',
    section: '80G',
    name: 'Donations (50% Deduction)',
    shortDescription: 'Donations to other eligible organizations',
    fullDescription: 'Donations to other approved NGOs, charitable trusts, temples qualify for 50% deduction (some without limit, others with 10% of adjusted gross total income as limit). Organization must have valid 80G registration.',
    limit: null,
    example: 'Donate ₹50,000 to a registered NGO. Get ₹25,000 deduction (50%), saving ₹7,800 in 30% bracket.',
    eligibility: 'Donations to 80G registered organizations.',
    documents: ['Donation receipt', '80G registration details of organization'],
    icon: 'gift-heart',
    category: 'donations',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // Section 80GG - Rent Paid (No HRA)
  // ════════════════════════════════════════
  {
    id: '80gg',
    section: '80GG',
    name: 'Rent Paid (No HRA Received)',
    shortDescription: 'Rent deduction for those without HRA',
    fullDescription: 'If you don\'t receive HRA from employer but pay rent, claim deduction under 80GG. Least of: (a) ₹5,000/month, (b) 25% of total income, (c) Rent paid minus 10% of total income. You/spouse/minor child should not own property in the city.',
    limit: 60000,
    example: 'Self-employed paying ₹20K rent/month with ₹8L income. Deduction = least of ₹60K, ₹2L (25% of 8L), or ₹1.6L (20K×12 - 80K).',
    eligibility: 'Self-employed or salaried not receiving HRA.',
    documents: ['Rent receipts', 'Rent agreement', 'Form 10BA'],
    icon: 'home-account',
    category: 'housing',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 80TTA/80TTB - Savings Interest
  // ════════════════════════════════════════
  {
    id: '80tta',
    section: '80TTA',
    name: 'Savings Account Interest',
    shortDescription: 'Interest earned on savings account',
    fullDescription: 'Interest earned on savings bank account is deductible up to ₹10,000 per year. Applies to savings accounts in banks, post office, and cooperative societies. Does not cover FD interest or recurring deposit interest.',
    limit: 10000,
    example: 'Earn ₹12,000 interest from savings accounts across banks. Claim ₹10,000 deduction under 80TTA.',
    eligibility: 'Individuals and HUFs (not senior citizens who claim 80TTB).',
    documents: ['Bank statements showing interest credited'],
    icon: 'bank-outline',
    category: 'savings',
    popular: true,
  },
  {
    id: '80ttb',
    section: '80TTB',
    name: 'Senior Citizen Interest Income',
    shortDescription: 'Interest for senior citizens',
    fullDescription: 'Senior citizens (60+) can claim deduction up to ₹50,000 on interest from savings account, FDs, RDs, and post office deposits. This is much better than 80TTA which only covers savings interest up to ₹10K.',
    limit: 50000,
    example: 'A 65-year-old earns ₹80K from FDs + ₹5K from savings = ₹85K total. Claim ₹50K deduction under 80TTB.',
    eligibility: 'Senior citizens (60 years or above) only.',
    documents: ['Bank statements', 'FD interest certificates'],
    icon: 'account-supervisor',
    category: 'savings',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 80U - Self Disability
  // ════════════════════════════════════════
  {
    id: '80u',
    section: '80U',
    name: 'Self Disability',
    shortDescription: 'Deduction for person with disability',
    fullDescription: 'Fixed deduction for individuals suffering from disability - ₹75,000 for disability, ₹1.25 lakh for severe disability (80%+). No need to show actual expenses; just disability certificate is sufficient.',
    limit: 125000,
    example: 'If you have a certified disability of 70%, claim flat ₹75,000 deduction. For 80%+ disability, claim ₹1.25 lakh.',
    eligibility: 'Resident individual with certified disability.',
    documents: ['Form 10-IA', 'Disability certificate from medical authority'],
    icon: 'human-wheelchair',
    category: 'medical',
    popular: false,
  },
  
  // ════════════════════════════════════════
  // HRA - House Rent Allowance (Section 10)
  // ════════════════════════════════════════
  {
    id: 'hra',
    section: 'HRA (Sec 10)',
    name: 'House Rent Allowance',
    shortDescription: 'Tax exemption on HRA received from employer',
    fullDescription: 'HRA exemption is the MINIMUM of: (a) Actual HRA received, (b) 50% of salary (metro) or 40% (non-metro), (c) Rent paid minus 10% of salary. Salary = Basic + DA. Only available if you receive HRA as part of salary and pay rent.',
    limit: null,
    example: 'Basic ₹50K, HRA ₹25K, Rent ₹20K (Mumbai). Exemption = min of ₹25K, ₹25K (50% of 50K), ₹15K (20K-5K) = ₹15K/month or ₹1.8L/year.',
    eligibility: 'Salaried employees receiving HRA and paying rent.',
    documents: ['Rent receipts', 'Rent agreement', 'Landlord PAN (if rent >₹1L/year)'],
    icon: 'home-import-outline',
    category: 'housing',
    popular: true,
  },
  
  // ════════════════════════════════════════
  // Section 24(b) - Home Loan Interest
  // ════════════════════════════════════════
  {
    id: 'sec24b',
    section: 'Section 24(b)',
    name: 'Home Loan Interest (Self-Occupied)',
    shortDescription: 'Interest on home loan for self-occupied property',
    fullDescription: 'Deduct interest paid on home loan up to ₹2 lakh per year for self-occupied property. If property is let out, NO LIMIT on interest deduction! Construction must be completed within 5 years from end of FY of loan disbursal.',
    limit: 200000,
    example: 'Pay ₹3 lakh interest on home loan for self-occupied house. Claim ₹2 lakh deduction under Sec 24(b).',
    eligibility: 'Individuals with home loan. Property must be completed.',
    documents: ['Interest certificate from bank', 'Property documents'],
    icon: 'home-heart',
    category: 'housing',
    popular: true,
  },
];

// Get popular deductions for quick display
export const getPopularDeductions = () => TAX_DEDUCTIONS.filter(d => d.popular);

// Get deductions by category
export const getDeductionsByCategory = (category: TaxDeduction['category']) => 
  TAX_DEDUCTIONS.filter(d => d.category === category);

// Get all unique sections
export const getAllSections = () => [...new Set(TAX_DEDUCTIONS.map(d => d.section))];

// Get deductions by section
export const getDeductionsBySection = (section: string) => 
  TAX_DEDUCTIONS.filter(d => d.section === section);

// Search deductions
export const searchDeductions = (query: string) => {
  const q = query.toLowerCase();
  return TAX_DEDUCTIONS.filter(d => 
    d.name.toLowerCase().includes(q) ||
    d.section.toLowerCase().includes(q) ||
    d.shortDescription.toLowerCase().includes(q) ||
    d.category.toLowerCase().includes(q)
  );
};
