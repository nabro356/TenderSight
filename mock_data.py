"""
Pre-built mock results for TenderSight demo — bypasses LLM calls entirely.
"""

MOCK_CRITERIA = [
    {
        "id": "FIN-001",
        "text": "The bidder must have an average annual turnover of at least Rs. 5,00,00,000 (Rupees Five Crore Only) during the last three financial years (2022-23, 2023-24, and 2024-25), certified by a Chartered Accountant.",
        "type": "Financial",
        "mandatory": True,
        "sub_conditions": [
            {"parameter": "average_annual_turnover", "operator": ">=", "threshold": "Rs. 5,00,00,000", "unit": "INR"},
            {"parameter": "financial_years", "operator": "in", "threshold": "2022-23, 2023-24, 2024-25", "unit": ""},
            {"parameter": "ca_certification", "operator": "exists", "threshold": "Chartered Accountant", "unit": ""}
        ],
        "source_section": "4.1.1"
    },
    {
        "id": "EXP-001",
        "text": "The bidder must have successfully completed at least 3 similar construction works during the last 5 years. Similar works shall mean construction of residential/institutional buildings for Central/State Government or PSUs. Each work must have minimum value of Rs. 2,00,00,000.",
        "type": "Experience",
        "mandatory": True,
        "sub_conditions": [
            {"parameter": "similar_works_count", "operator": ">=", "threshold": "3", "unit": "projects"},
            {"parameter": "work_period", "operator": "within", "threshold": "last 5 years", "unit": ""},
            {"parameter": "minimum_work_value", "operator": ">=", "threshold": "Rs. 2,00,00,000", "unit": "INR per project"},
            {"parameter": "client_type", "operator": "in", "threshold": "Central Govt, State Govt, PSU", "unit": ""}
        ],
        "source_section": "4.2.1"
    },
    {
        "id": "COMP-001",
        "text": "The bidder must possess a valid Goods and Services Tax (GST) Registration Certificate. The GSTIN must be active as on the date of submission.",
        "type": "Compliance",
        "mandatory": True,
        "sub_conditions": [
            {"parameter": "gst_registration", "operator": "exists", "threshold": "Valid GSTIN", "unit": ""},
            {"parameter": "gst_status", "operator": "==", "threshold": "Active", "unit": ""}
        ],
        "source_section": "4.3.1"
    },
    {
        "id": "COMP-002",
        "text": "The bidder must hold a valid ISO 9001:2015 Quality Management System Certification from an accredited certification body, covering construction/civil engineering services.",
        "type": "Compliance",
        "mandatory": True,
        "sub_conditions": [
            {"parameter": "iso_certification", "operator": "exists", "threshold": "ISO 9001:2015", "unit": ""},
            {"parameter": "iso_validity", "operator": "valid_on_date", "threshold": "date of submission", "unit": ""},
            {"parameter": "iso_scope", "operator": "includes", "threshold": "construction/civil engineering", "unit": ""}
        ],
        "source_section": "4.3.2"
    },
    {
        "id": "TECH-001",
        "text": "The bidder must have a minimum in-house civil engineering team of 10 qualified engineers (B.E./B.Tech in Civil Engineering or equivalent), with at least 3 having experience exceeding 5 years.",
        "type": "Technical",
        "mandatory": True,
        "sub_conditions": [
            {"parameter": "total_engineers", "operator": ">=", "threshold": "10", "unit": "engineers"},
            {"parameter": "senior_engineers", "operator": ">=", "threshold": "3", "unit": "engineers with >5yr exp"}
        ],
        "source_section": "4.4.1"
    }
]


def _make_verdict(crit, status, confidence, reasoning, evidence, review_reason=None, reviewer_agreed=True):
    return {
        "criterion_id": crit["id"],
        "criterion_text": crit["text"],
        "criterion_type": crit["type"],
        "status": status,
        "confidence": confidence,
        "reasoning": reasoning,
        "review_reason": review_reason,
        "reviewer_agreed": reviewer_agreed,
        "evidence_used": evidence,
    }


MOCK_EVALUATIONS = {
    "Bharat Constructions": {
        "bidder_name": "M/s Bharat Constructions Pvt. Ltd.",
        "overall_status": "ELIGIBLE",
        "eligible_count": 5,
        "not_eligible_count": 0,
        "manual_review_count": 0,
        "verdicts": [
            _make_verdict(MOCK_CRITERIA[0], "ELIGIBLE", 0.97,
                "Average annual turnover is Rs. 8.21 Cr (FY22-23: Rs. 7.45 Cr + FY23-24: Rs. 8.92 Cr + FY24-25: Rs. 8.25 Cr = avg Rs. 8.21 Cr), which comfortably exceeds the Rs. 5 Cr threshold. CA Certificate issued by CA Rajesh Kumar Agarwal (Membership No: 045231) on 5th April 2026. All three financial years covered. Pass 1 deterministic check: Rs. 8.21 Cr >= Rs. 5 Cr -> PASS.",
                [{"criterion_id": "FIN-001", "value": "Rs. 8,20,66,667 (Average Annual Turnover)", "source_document": "CA Certificate", "source_section": "Document 1", "confidence": 0.98, "raw_excerpt": "Financial Year 2022-23: Rs. 7,45,00,000... Financial Year 2023-24: Rs. 8,92,00,000... Financial Year 2024-25: Rs. 8,25,00,000... Average Annual Turnover: Rs. 8,20,66,667"}]),
            _make_verdict(MOCK_CRITERIA[1], "ELIGIBLE", 0.96,
                "Bidder has completed 5 similar construction works in the last 5 years, all for Central Government paramilitary forces (BSF, CISF, ITBP, CRPF). Each work exceeds the Rs. 2 Cr minimum value threshold. All completion certificates are from government clients with valid certificate numbers. The works are directly comparable - BOP infrastructure, residential quarters, training centres, and mess blocks for armed forces. Similarity score: Scope 0.95, Scale 0.88, Complexity 0.90, Client Type 1.0.",
                [{"criterion_id": "EXP-001", "value": "5 similar works completed (BSF Jodhpur Rs. 3.85Cr, CISF Jaisalmer Rs. 2.90Cr, ITBP Bikaner Rs. 2.15Cr, BSF Barmer Rs. 4.50Cr, CRPF Ajmer Rs. 2.75Cr)", "source_document": "Experience Certificates", "source_section": "Document 2", "confidence": 0.97, "raw_excerpt": "Work 1: Construction of Administrative Building for BSF, Jodhpur Sector... Contract Value: Rs. 3,85,00,000... Status: Successfully completed... Work 5: Construction of Mess and Kitchen Block for CRPF, Ajmer... Contract Value: Rs. 2,75,00,000"}]),
            _make_verdict(MOCK_CRITERIA[2], "ELIGIBLE", 0.99,
                "Valid GST Registration found. GSTIN: 08AADCB4523K1Z5, registered since 01/07/2017, Status: Active, State: Rajasthan. Pass 1 deterministic check: GST status == 'Active' -> PASS.",
                [{"criterion_id": "COMP-001", "value": "GSTIN: 08AADCB4523K1Z5 - Status: Active", "source_document": "GST Registration Certificate", "source_section": "Document 3", "confidence": 0.99, "raw_excerpt": "GSTIN: 08AADCB4523K1Z5, Legal Name: Bharat Constructions Private Limited, Date of Registration: 01/07/2017, Status: Active"}]),
            _make_verdict(MOCK_CRITERIA[3], "ELIGIBLE", 0.98,
                "Valid ISO 9001:2015 certificate from Bureau Veritas (NABCB accredited). Certificate No: QMS-2024-IN-78432. Valid from 15/01/2024 to 14/01/2027 - certificate is currently valid. Scope explicitly covers 'Design, Construction and Project Management of Civil Engineering and Building Construction Projects', which matches the tender requirement.",
                [{"criterion_id": "COMP-002", "value": "ISO 9001:2015 - Valid until 14 Jan 2027 (Bureau Veritas, NABCB accredited)", "source_document": "ISO Certificate", "source_section": "Document 4", "confidence": 0.98, "raw_excerpt": "Standard: ISO 9001:2015, Scope: Design, Construction and Project Management of Civil Engineering and Building Construction Projects, Valid Until: 14th January 2027"}]),
            _make_verdict(MOCK_CRITERIA[4], "ELIGIBLE", 0.97,
                "Bidder has 15 in-house civil engineers (requirement: 10). Of these, 7 engineers have >5 years experience (requirement: 3). All engineers hold B.E./B.Tech in Civil Engineering from recognised institutions (IIT Roorkee, NIT Jaipur, BITS Pilani, etc.). Pass 1 deterministic check: 15 >= 10 engineers, 7 >= 3 senior engineers -> PASS.",
                [{"criterion_id": "TECH-001", "value": "15 engineers total, 7 with >5 years experience", "source_document": "Engineering Team List", "source_section": "Document 5", "confidence": 0.97, "raw_excerpt": "Total Engineers: 15, Engineers with >5 years experience: 7 (Er. Rathore 12yr, Er. Sharma 8yr, Er. Choudhary 9yr, Er. Meena 6yr, Er. Prasad 7yr, Er. Patel 6yr, Er. Arun Kumar 8yr)"}]),
        ]
    },

    "Sharma Sons": {
        "bidder_name": "M/s Sharma & Sons Construction Co.",
        "overall_status": "NOT_ELIGIBLE",
        "eligible_count": 3,
        "not_eligible_count": 1,
        "manual_review_count": 1,
        "verdicts": [
            _make_verdict(MOCK_CRITERIA[0], "ELIGIBLE", 0.96,
                "Average annual turnover is Rs. 6.12 Cr (FY22-23: Rs. 5.80 Cr + FY23-24: Rs. 6.45 Cr + FY24-25: Rs. 6.10 Cr = avg Rs. 6.12 Cr), which exceeds the Rs. 5 Cr threshold. CA Certificate issued by CA Mahendra Sharma (Membership No: 067892). Pass 1 deterministic check: Rs. 6.12 Cr >= Rs. 5 Cr -> PASS.",
                [{"criterion_id": "FIN-001", "value": "Rs. 6,11,66,667 (Average Annual Turnover)", "source_document": "CA Certificate", "source_section": "Document 1", "confidence": 0.97, "raw_excerpt": "Financial Year 2022-23: Rs. 5,80,00,000... Financial Year 2023-24: Rs. 6,45,00,000... Financial Year 2024-25: Rs. 6,10,00,000... Average Annual Turnover: Rs. 6,11,66,667"}]),
            _make_verdict(MOCK_CRITERIA[1], "NOT_ELIGIBLE", 0.92,
                "Bidder has completed only 2 qualifying similar works (Rajasthan Police Housing Corporation Rs. 3.20 Cr and Kendriya Vidyalaya Sangathan Rs. 2.45 Cr). The tender requires minimum 3 similar works. The bidder mentions 'several other private construction projects' but these do not qualify as the tender specifies Central/State Government or PSU clients only. Pass 1 deterministic check: 2 < 3 required -> FAIL. This is a clear shortfall, not a borderline case.",
                [{"criterion_id": "EXP-001", "value": "2 similar works (required: 3) - Rajasthan Police Rs. 3.20Cr, KVS Rs. 2.45Cr", "source_document": "Experience Certificates", "source_section": "Document 2", "confidence": 0.95, "raw_excerpt": "Work 1: Construction of Staff Quarters for Rajasthan Police, Udaipur... Contract Value: Rs. 3,20,00,000... Work 2: Construction of School Building for KVS, Mount Abu... Contract Value: Rs. 2,45,00,000... Note: several other private construction projects but certificates not enclosed"}]),
            _make_verdict(MOCK_CRITERIA[2], "ELIGIBLE", 0.99,
                "Valid GST Registration found. GSTIN: 08AAHFS7832L1Z9, registered since 15/08/2017, Status: Active.",
                [{"criterion_id": "COMP-001", "value": "GSTIN: 08AAHFS7832L1Z9 - Status: Active", "source_document": "GST Registration Certificate", "source_section": "Document 3", "confidence": 0.99, "raw_excerpt": "GSTIN: 08AAHFS7832L1Z9, Status: Active, State: Rajasthan"}]),
            _make_verdict(MOCK_CRITERIA[3], "MANUAL_REVIEW", 0.55,
                "ISO 9001:2015 certificate (TUV SUD) is valid until 28th February 2026. The tender submission date is 11th April 2026, meaning the certificate EXPIRED approximately 6 weeks before submission. However, the certificate was valid within the recent past and renewal may be in progress. The Reviewer Agent flagged this for human review rather than automatic rejection - an expired certificate with recent validity is qualitatively different from having no certification at all.",
                [{"criterion_id": "COMP-002", "value": "ISO 9001:2015 - EXPIRED (valid until 28 Feb 2026, submission on 11 Apr 2026)", "source_document": "ISO Certificate", "source_section": "Document 4", "confidence": 0.90, "raw_excerpt": "Standard: ISO 9001:2015, Valid From: 1st March 2023, Valid Until: 28th February 2026, Certification Body: TUV SUD South Asia"}],
                review_reason="ISO certificate expired ~6 weeks before submission. No evidence of renewal application submitted. Officer should verify if the bidder has applied for renewal and whether a recently-expired certificate should be accepted under the circumstances.",
                reviewer_agreed=False),
            _make_verdict(MOCK_CRITERIA[4], "ELIGIBLE", 0.95,
                "Bidder has 12 in-house engineers (requirement: 10) and 5 with >5 years experience (requirement: 3). All engineers hold recognised B.E./B.Tech qualifications. Pass 1 deterministic check: 12 >= 10, 5 >= 3 -> PASS.",
                [{"criterion_id": "TECH-001", "value": "12 engineers total, 5 with >5 years experience", "source_document": "Engineering Team List", "source_section": "Document 5", "confidence": 0.96, "raw_excerpt": "Total Engineers: 12, Engineers with >5 years experience: 5"}]),
        ]
    },

    "Pacific Infra": {
        "bidder_name": "M/s Pacific Infrastructure Ltd.",
        "overall_status": "MANUAL_REVIEW",
        "eligible_count": 2,
        "not_eligible_count": 0,
        "manual_review_count": 3,
        "verdicts": [
            _make_verdict(MOCK_CRITERIA[0], "MANUAL_REVIEW", 0.52,
                "Average annual construction turnover is Rs. 4.82 Cr, which is BELOW the Rs. 5 Cr threshold. However, the CA certificate notes that total company turnover including real estate exceeds Rs. 10 Cr annually. The tender specifies 'turnover from construction/civil engineering works only', so the real estate turnover should not count. At Rs. 4.82 Cr vs Rs. 5 Cr threshold (96.3% of requirement), this is a borderline case. The Reviewer Agent escalated this to manual review rather than automatic rejection.",
                [{"criterion_id": "FIN-001", "value": "Rs. 4,81,66,667 construction turnover (Rs. 10 Cr+ total including real estate)", "source_document": "CA Certificate", "source_section": "Document 1", "confidence": 0.85, "raw_excerpt": "Average Annual Turnover: Rs. 4,81,66,667... Note: The company also has turnover from its real estate development division which is not included above. Total company turnover including real estate exceeds Rs. 10 Crore annually."}],
                review_reason="Turnover Rs. 4.82 Cr is 96.3% of Rs. 5 Cr threshold - borderline shortfall. The bidder's total turnover exceeds Rs. 10 Cr but includes non-construction (real estate) revenue. Officer must determine: (a) whether real estate development counts as 'construction/civil engineering works' under the tender definition, and (b) whether a 3.7% shortfall warrants rejection given the bidder's overall financial capacity.",
                reviewer_agreed=False),
            _make_verdict(MOCK_CRITERIA[1], "ELIGIBLE", 0.94,
                "Bidder has completed 4 similar works in the last 5 years: CPWD Chandigarh Rs. 5.80 Cr, MES Ambala Rs. 3.90 Cr, HAL Bangalore Rs. 2.50 Cr, DRDO Gurgaon Rs. 2.20 Cr. All are for Central Government organisations or PSUs. All exceed Rs. 2 Cr minimum. Similarity taxonomy scores: Scope 0.92 (all construction), Scale 0.85 (values proportionate), Complexity 0.88, Client Type 1.0 (all govt/PSU).",
                [{"criterion_id": "EXP-001", "value": "4 similar works - CPWD Rs. 5.80Cr, MES Rs. 3.90Cr, HAL Rs. 2.50Cr, DRDO Rs. 2.20Cr", "source_document": "Experience Certificates", "source_section": "Document 2", "confidence": 0.96, "raw_excerpt": "Work 1: Construction of Office Complex for CPWD, Chandigarh, Contract Value: Rs. 5,80,00,000... Work 4: Renovation of Administrative Block for DRDO, Gurgaon, Contract Value: Rs. 2,20,00,000"}]),
            _make_verdict(MOCK_CRITERIA[2], "ELIGIBLE", 0.99,
                "Valid GST Registration. GSTIN: 06AABCP9876H1Z2, Status: Active, State: Haryana.",
                [{"criterion_id": "COMP-001", "value": "GSTIN: 06AABCP9876H1Z2 - Status: Active", "source_document": "GST Registration Certificate", "source_section": "Document 3", "confidence": 0.99, "raw_excerpt": "GSTIN: 06AABCP9876H1Z2, Status: Active, State: Haryana"}]),
            _make_verdict(MOCK_CRITERIA[3], "MANUAL_REVIEW", 0.40,
                "ISO 9001:2015 certificate (Certificate No: QMS-2021-IN-43256) EXPIRED on 9th June 2024 - nearly 10 months before the submission date. The bidder states that a 'renewal application has been submitted to Bureau Veritas' and the renewed certificate is 'expected by end of April 2026'. No proof of the renewal application was found in the submission documents beyond the bidder's own statement. This is a more serious expiry than a recent lapse.",
                [{"criterion_id": "COMP-002", "value": "ISO 9001:2015 - EXPIRED since June 2024 (renewal claimed but unverified)", "source_document": "ISO Certificate", "source_section": "Document 4", "confidence": 0.75, "raw_excerpt": "Valid Until: 9th June 2024... STATUS: EXPIRED... Note: Renewal application has been submitted to Bureau Veritas. The renewed certificate is expected by end of April 2026."}],
                review_reason="ISO certificate expired 10 months ago. Bidder claims renewal is in progress but no documentary proof of renewal application was submitted - only a self-declaration. Officer must verify: (a) whether the renewal application has actually been filed, (b) whether a certificate expired for 10 months should be treated differently from one expired for weeks, and (c) whether to allow conditional eligibility pending receipt of renewed certificate.",
                reviewer_agreed=False),
            _make_verdict(MOCK_CRITERIA[4], "MANUAL_REVIEW", 0.45,
                "Bidder lists 8 engineers, but one (Er. Pallavi Gupta) is currently on maternity leave, leaving only 7 available. The threshold is 10 engineers. Additionally, only 4 engineers have >5 years experience (requirement: 3 - this sub-condition is met). The headcount shortfall is significant: 7-8 available vs 10 required. However, the Reviewer notes that the bidder could potentially hire additional engineers before project commencement if awarded.",
                [{"criterion_id": "TECH-001", "value": "8 engineers (7 available due to maternity leave), 4 with >5yr experience", "source_document": "Engineering Team List", "source_section": "Document 5", "confidence": 0.90, "raw_excerpt": "Total Engineers: 8 (one currently on maternity leave, effectively 7 available), Engineers with >5 years experience: 4"}],
                review_reason="Only 8 engineers listed (7 currently available) vs 10 required - a 20-30% shortfall. This is not borderline. However, the bidder may argue they can recruit before project start. Officer must decide if the criterion requires engineers to be on-roll at submission date or at project commencement.",
                reviewer_agreed=False),
        ]
    },

    "Delhi Buildtech": {
        "bidder_name": "M/s Delhi BuildTech Corporation",
        "overall_status": "ELIGIBLE",
        "eligible_count": 5,
        "not_eligible_count": 0,
        "manual_review_count": 0,
        "verdicts": [
            _make_verdict(MOCK_CRITERIA[0], "ELIGIBLE", 0.99,
                "Average annual turnover is Rs. 12.07 Cr (FY22-23: Rs. 11.50 Cr + FY23-24: Rs. 12.80 Cr + FY24-25: Rs. 11.90 Cr). This is 2.4x the Rs. 5 Cr threshold. CA Certificate by CA Anand Prakash Gupta (Membership No: 034567). The turnover is exclusively from construction and civil engineering works as required. Pass 1 deterministic check: Rs. 12.07 Cr >= Rs. 5 Cr -> PASS.",
                [{"criterion_id": "FIN-001", "value": "Rs. 12,06,66,667 (Average Annual Turnover - 2.4x threshold)", "source_document": "CA Certificate", "source_section": "Document 1", "confidence": 0.99, "raw_excerpt": "Financial Year 2022-23: Rs. 11,50,00,000... Financial Year 2023-24: Rs. 12,80,00,000... Financial Year 2024-25: Rs. 11,90,00,000... Average: Rs. 12,06,66,667... exclusively from construction and civil engineering works"}]),
            _make_verdict(MOCK_CRITERIA[1], "ELIGIBLE", 0.98,
                "Bidder has completed 6 similar works in the last 5 years, all for Central Government armed forces/paramilitary organisations (MHA, CRPF, SSB, BSF, ITBP, NSG). Work values range from Rs. 4.75 Cr to Rs. 9.10 Cr - all well above the Rs. 2 Cr minimum. Notably, Work 4 (BSF Border Outposts, Punjab) is almost identical in scope to the current tender. Similarity score: Scope 0.98, Scale 0.92, Complexity 0.95, Client Type 1.0.",
                [{"criterion_id": "EXP-001", "value": "6 similar works - MHA Rs. 8.50Cr, CRPF Rs. 6.20Cr, SSB Rs. 4.75Cr, BSF Rs. 7.30Cr, ITBP Rs. 5.40Cr, NSG Rs. 9.10Cr", "source_document": "Experience Certificates", "source_section": "Document 2", "confidence": 0.98, "raw_excerpt": "Work 1: Construction of CAPF Institute, Greater Noida (MHA), Rs. 8.50 Cr... Work 4: Construction of BSF Border Outposts (3 Nos.), Punjab, Rs. 7.30 Cr... Work 6: Construction of NSG Training Facility, Manesar, Rs. 9.10 Cr"}]),
            _make_verdict(MOCK_CRITERIA[2], "ELIGIBLE", 0.99,
                "Valid GST Registration. GSTIN: 07AADCD5678M1Z8, Status: Active, State: Delhi.",
                [{"criterion_id": "COMP-001", "value": "GSTIN: 07AADCD5678M1Z8 - Status: Active", "source_document": "GST Registration Certificate", "source_section": "Document 3", "confidence": 0.99, "raw_excerpt": "GSTIN: 07AADCD5678M1Z8, Status: Active, State: Delhi"}]),
            _make_verdict(MOCK_CRITERIA[3], "ELIGIBLE", 0.99,
                "Valid ISO 9001:2015 certificate from DNV GL (NABCB + JAS-ANZ dual accreditation). Certificate No: QMS-2025-IN-91024. Valid from 01/01/2025 to 31/12/2027. Scope explicitly covers 'Government and Defence Construction', which is a direct match. Recently renewed - no expiry concerns.",
                [{"criterion_id": "COMP-002", "value": "ISO 9001:2015 - Valid until 31 Dec 2027 (DNV GL, NABCB + JAS-ANZ accredited)", "source_document": "ISO Certificate", "source_section": "Document 4", "confidence": 0.99, "raw_excerpt": "Standard: ISO 9001:2015, Scope: Design, Engineering, Construction and Project Management... including Government and Defence Construction, Valid Until: 31st December 2027, Certification Body: DNV GL"}]),
            _make_verdict(MOCK_CRITERIA[4], "ELIGIBLE", 0.98,
                "Bidder has 20 in-house civil engineers (2x the requirement of 10). Of these, 9 have >5 years experience (3x the requirement of 3). Chief Engineer Er. Rajiv Khanna has 18 years experience from IIT Delhi. The team includes M.Tech holders in Structural Engineering and Construction Management. Pass 1 deterministic check: 20 >= 10, 9 >= 3 -> PASS.",
                [{"criterion_id": "TECH-001", "value": "20 engineers total (2x threshold), 9 with >5yr experience (3x threshold)", "source_document": "Engineering Team List", "source_section": "Document 5", "confidence": 0.98, "raw_excerpt": "Total Engineers: 20, Engineers with >5 years experience: 9, Chief Engineer: Er. Rajiv Khanna, B.Tech (Civil) IIT Delhi, 18 years experience"}]),
        ]
    }
}
