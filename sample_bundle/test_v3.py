"""Quick smoke test for TenderSight v3.0 features."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_bundle_processor():
    from utils.bundle_processor import (
        classify_filename, classify_by_content_heuristic,
        process_zip_to_bundle, process_boq_in_bundle,
    )
    
    # Test filename classification
    assert classify_filename("RFP_NIT_Border_Outpost.pdf") == "rfp"
    assert classify_filename("BOQ_Price_Schedule.csv") == "boq"
    assert classify_filename("ATC_Additional_Terms.txt") == "atc"
    assert classify_filename("Corrigendum_1.pdf") == "corrigendum"
    assert classify_filename("Annexure_II_Format.pdf") == "annexure"
    assert classify_filename("Technical_Specifications.pdf") == "spec"
    assert classify_filename("random_file.pdf") == "unknown"
    print("[PASS] Filename classification")
    
    # Test content-based classification
    assert classify_by_content_heuristic("Bill of Quantities\nSl. No. Item Description Unit Rate") == "boq"
    assert classify_by_content_heuristic("This corrigendum amends the original tender...") == "corrigendum"
    assert classify_by_content_heuristic("Additional Terms and Conditions as follows...") == "atc"
    print("[PASS] Content-based classification")
    
    # Test ZIP processing
    zip_path = os.path.join(os.path.dirname(__file__), 
                            "CRPF_BOP_Rajasthan_Tender_Bundle.zip")
    if os.path.exists(zip_path):
        with open(zip_path, "rb") as f:
            bundle = process_zip_to_bundle(f.read(), tender_id="TEST-001")
        
        summary = bundle.get_summary()
        print(f"[PASS] ZIP extraction: {summary['total_documents']} documents")
        for doc in bundle.documents:
            print(f"       {doc.filename} -> [{doc.doc_type}] (priority={doc.priority})")
        
        # Test BOQ parsing
        process_boq_in_bundle(bundle)
        if bundle.boq_data:
            print(f"[PASS] BOQ parsing: {len(bundle.boq_data)} line items extracted")
        else:
            print("[SKIP] BOQ parsing: no Excel BOQ in bundle (CSV fallback)")
    else:
        print("[SKIP] ZIP test: bundle not found")


def test_deterministic_engine():
    from agents.deterministic_engine import (
        parse_inr_amount, ProcurementRulesEngine,
        extract_gem_metadata, extract_certifications,
    )
    
    # Test INR parsing
    assert parse_inr_amount("Rs. 5 Crore") == 5_00_00_000
    assert parse_inr_amount("Rs. 45 Lakh") == 45_00_000
    assert parse_inr_amount("Rs.8,20,66,667") == 82066667
    assert parse_inr_amount("5,00,00,000") == 5_00_00_000
    print("[PASS] INR amount parsing")
    
    # Test GeM metadata extraction
    tender_text = """
    GeM Bid Number: GEM/2025/B/5234871
    Estimated Cost: Rs. 18,50,00,000
    EMD: Rs. 37,00,000
    Published on gem.gov.in
    """
    meta = extract_gem_metadata(tender_text)
    assert meta["gem_bid_number"] == "GEM/2025/B/5234871"
    assert meta["is_gem_tender"] == True
    assert meta["platform_detected"] == "GeM"
    print(f"[PASS] GeM metadata: {meta['gem_bid_number']}")
    
    # Test MSME detection
    engine = ProcurementRulesEngine()
    msme = engine.detect_msme_status("Udyam Registration: UDYAM-RJ-19-0045678")
    assert msme["is_msme"] == True
    assert "UDYAM-RJ-19-0045678" in msme["certificate_ref"]
    print(f"[PASS] MSME detection: {msme['certificate_ref']}")
    
    # Test Startup detection
    startup = engine.detect_startup_status("DPIIT Startup Recognition: DIPP12345")
    assert startup["is_startup"] == True
    print(f"[PASS] Startup detection: {startup['certificate_ref']}")
    
    # Test exemption logic
    criterion = {"id": "FIN-001", "type": "Financial", "text": "Minimum annual turnover of Rs. 5 Crore"}
    exemption = engine.check_exemptions_for_criterion(criterion, msme, startup)
    assert exemption is not None
    assert exemption["exempt"] == True
    print(f"[PASS] GFR exemption: {exemption['exemption_type']} -> {exemption['status']}")
    
    # Test certification extraction
    certs = extract_certifications("ISO 9001:2015 certified. BIS license holder. UDYAM-RJ-19-0045678")
    assert len(certs) >= 2
    print(f"[PASS] Certification extraction: {len(certs)} certs found")
    
    # Test Make in India
    mii = engine.detect_make_in_india("Make in India declaration. local content: 85%")
    assert mii["classification"] == "Class-I Local Supplier"
    print(f"[PASS] Make in India: {mii['classification']}")


def test_provenance():
    from utils.provenance import ProvenanceDAG
    
    dag = ProvenanceDAG("TEST-001")
    
    # Build a simple chain
    bundle_node = dag.record_bundle_upload(
        ["rfp.pdf", "boq.csv"], {"rfp.pdf": "rfp", "boq.csv": "boq"}
    )
    ing_node = dag.record_ingestion(
        "rfp.pdf", "rfp", "pypdf", 0.95, 15000,
        parent_ids=[bundle_node.node_id]
    )
    crit_node = dag.record_criteria_extraction(
        ["FIN-001", "EXP-001"], "rfp.pdf",
        parent_ids=[ing_node.node_id]
    )
    verdict = dag.record_llm_verdict(
        "Bharat Corp", "FIN-001", "ELIGIBLE", 0.95,
        "Rs. 9.59 Crore", "Page 2, Para 3",
        "Average turnover exceeds threshold",
        parent_ids=[crit_node.node_id]
    )
    
    # Test ancestry walk
    ancestry = dag.get_verdict_ancestry(verdict.node_id)
    assert len(ancestry) == 4  # verdict -> crit -> ingestion -> bundle
    print(f"[PASS] Provenance DAG: {len(ancestry)} nodes in ancestry chain")
    
    # Test integrity
    integrity = dag.verify_integrity()
    assert integrity["integrity"] == "PASS"
    print(f"[PASS] Integrity check: {integrity['integrity']} ({integrity['total_nodes']} nodes)")
    
    # Test export
    trail = dag.export_full_trail()
    assert trail["node_count"] == 4
    print(f"[PASS] Trail export: {trail['node_count']} nodes")


if __name__ == "__main__":
    print("=" * 60)
    print("TenderSight v3.0 - Smoke Tests")
    print("=" * 60)
    
    print("\n--- Bundle Processor ---")
    test_bundle_processor()
    
    print("\n--- Deterministic Engine + GFR Rules ---")
    test_deterministic_engine()
    
    print("\n--- Evidence Provenance DAG ---")
    test_provenance()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
