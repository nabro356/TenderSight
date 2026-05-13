"""
Build the sample tender ZIP bundle for testing TenderSight v3.0 features.

Run:  python sample_bundle/create_bundle_zip.py

Creates:
  - sample_bundle/CRPF_BOP_Rajasthan_Tender_Bundle.zip
    (Contains RFP, BOQ, ATC, and Corrigendum — ready for ZIP upload)
"""
import zipfile
import os

BUNDLE_DIR = os.path.join(os.path.dirname(__file__), "tender_bundle")
OUTPUT_ZIP = os.path.join(os.path.dirname(__file__), "CRPF_BOP_Rajasthan_Tender_Bundle.zip")

FILES = [
    "RFP_NIT_Border_Outpost_Construction.txt",
    "BOQ_Price_Schedule.csv",
    "ATC_Additional_Terms.txt",
    "Corrigendum_1.txt",
]

def main():
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in FILES:
            fpath = os.path.join(BUNDLE_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)
                print(f"  [OK] Added: {fname}")
            else:
                print(f"  [!!] Missing: {fname}")

    size_kb = os.path.getsize(OUTPUT_ZIP) / 1024
    print(f"\n[BUNDLE] Created: {OUTPUT_ZIP} ({size_kb:.1f} KB)")
    print(f"   Contains {len(FILES)} documents (RFP, BOQ, ATC, Corrigendum)")
    print(f"\n   Upload this ZIP to TenderSight to test bundle processing.")

if __name__ == "__main__":
    main()
