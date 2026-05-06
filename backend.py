"""
TenderSight v2.0 — FastAPI REST Backend
Decoupled API for the evaluation pipeline.

Endpoints:
  POST /tenders/        — Upload tender doc, extract criteria
  POST /evaluate/{id}   — Evaluate a bidder against stored tender criteria
  POST /chat            — Ask questions about evaluation results
  GET  /                — Health check
"""
import uuid
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from agents.orchestrator import OrchestratorAgent
from agents.chat_agent import chat_about_report
from utils.anomaly_detector import detect_financial_anomalies
from utils.kuzu_client import detect_cartels_via_graph
from typing import List
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TenderSight AI API",
    version="2.0.0",
    description="AI-Powered Tender Evaluation for Government Procurement",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for tender data between API calls
tenders_db: Dict[str, dict] = {}
evaluations_db: Dict[str, dict] = {}

orchestrator = OrchestratorAgent()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "TenderSight AI",
        "version": "2.0.0",
        "active_tenders": len(tenders_db),
    }


@app.post("/tenders/")
async def create_tender(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
):
    """Upload a tender document, extract criteria."""
    content = await file.read()
    tender_id = f"TND-{uuid.uuid4().hex[:8].upper()}"

    try:
        result = orchestrator.process_tender(
            file_bytes=content,
            filename=file.filename,
            api_key=api_key,
        )

        tenders_db[tender_id] = {
            "filename": file.filename,
            "criteria": result["criteria"],
            "raw_text": result["raw_text"],
            "ocr_engine": result["ocr_engine"],
        }

        return {
            "status": "created",
            "tender_id": tender_id,
            "ocr_engine": result["ocr_engine"],
            "confidence": result["confidence"],
            "criteria_count": len(result["criteria"]),
            "criteria": result["criteria"],
        }
    except Exception as e:
        logger.error("Tender processing failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e))


from typing import Optional, Dict, Any, List

@app.post("/evaluate/{tender_id}/{bidder_id}")
async def evaluate_bidder_endpoint(
    tender_id: str,
    bidder_id: str,
    files: List[UploadFile] = File(...),
    api_key: Optional[str] = Form(None),
):
    """Evaluate a bidder document against stored tender criteria."""
    if tender_id not in tenders_db:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    file_bytes_list = []
    file_names_list = []
    for f in files:
        content = await f.read()
        file_bytes_list.append(content)
        file_names_list.append(f.filename)
        
    criteria = tenders_db[tender_id]["criteria"]

    try:
        evaluation = orchestrator.evaluate_single_bidder(
            criteria=criteria,
            bidder_name=bidder_id,
            bidder_bytes_list=file_bytes_list,
            bidder_filenames=file_names_list,
            api_key=api_key,
        )

        # Store for chat context
        if tender_id not in evaluations_db:
            evaluations_db[tender_id] = {}
        evaluations_db[tender_id][bidder_id] = evaluation

        return {"status": "success", "result": evaluation}
    except Exception as e:
        logger.error("Evaluation failed for %s: %s", bidder_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update_evaluation/{tender_id}/{bidder_id}")
async def update_evaluation_endpoint(
    tender_id: str,
    bidder_id: str,
    evaluation: Dict[str, Any] = Body(...),
):
    """Overwrite an evaluation with human overrides."""
    if tender_id not in evaluations_db:
        evaluations_db[tender_id] = {}
        
    evaluations_db[tender_id][bidder_id] = evaluation
    return {"status": "success", "message": "Evaluation updated successfully."}


@app.post("/detect_anomalies/{tender_id}")
async def detect_anomalies_endpoint(
    tender_id: str,
    api_key: Optional[str] = Body(None),
):
    """Run statistical anomaly detection on all bidders for a tender."""
    if tender_id not in evaluations_db:
        raise HTTPException(status_code=404, detail="No evaluations found for this tender.")
        
    evals = evaluations_db[tender_id]
    
    # Run the detector (it updates the dict in-place with anomaly_flag and anomaly_reason)
    updated_evals = detect_financial_anomalies(evals, api_key=api_key)
    
    # Save back to DB
    evaluations_db[tender_id] = updated_evals
    return {"status": "success", "evaluations": updated_evals}


@app.post("/detect_cartels/{tender_id}")
async def detect_cartels_endpoint(
    tender_id: str,
    api_key: Optional[str] = Body(None),
):
    """Run Kuzu Graph DB cartel detection on all bidders."""
    if tender_id not in evaluations_db:
        raise HTTPException(status_code=404, detail="No evaluations found for this tender.")
        
    evals = evaluations_db[tender_id]
    
    # Run the graph detection
    cartel_alerts = detect_cartels_via_graph(tender_id, evals, api_key=api_key)
    
    return {"status": "success", "cartel_alerts": cartel_alerts}


class ChatRequest(BaseModel):
    tender_id: str
    question: str
    api_key: Optional[str] = None


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Ask questions about evaluation results."""
    if req.tender_id not in tenders_db:
        raise HTTPException(status_code=404, detail=f"Tender {req.tender_id} not found")

    context = {
        "criteria": tenders_db[req.tender_id]["criteria"],
        "evaluations": evaluations_db.get(req.tender_id, {}),
    }

    try:
        answer = chat_about_report(
            req.question, context,
            api_key=req.api_key,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import StreamingResponse
import io
from utils.report_generator import generate_pdf_report

@app.get("/report/{tender_id}")
async def get_pdf_report(tender_id: str):
    """Download the official PDF evaluation report."""
    if tender_id not in tenders_db:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")
        
    criteria = tenders_db[tender_id]["criteria"]
    evaluations = evaluations_db.get(tender_id, {})
    
    if not evaluations:
        raise HTTPException(status_code=400, detail="No evaluations completed yet for this tender.")
        
    try:
        pdf_bytes = generate_pdf_report(criteria, evaluations)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="TenderSight_Report_{tender_id}.pdf"'
            }
        )
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
