"""
TenderSight v2.0 — FastAPI REST Backend
Decoupled API for the evaluation pipeline.

Endpoints:
  POST /tenders/        — Upload tender doc, extract criteria
  POST /evaluate/{id}   — Evaluate a bidder against stored tender criteria
  POST /evaluate_all/{id} — Evaluate ALL bidders concurrently
  GET  /evaluate_stream/{id} — SSE stream of live evaluation progress
  POST /chat            — Ask questions about evaluation results
  GET  /                — Health check
"""
import uuid
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from agents.orchestrator import OrchestratorAgent
from agents.chat_agent import chat_about_report
from utils.anomaly_detector import detect_financial_anomalies
from utils.cartel_detector import detect_cartels_via_graph

logger = logging.getLogger(__name__)

# Thread pool for parallel bidder evaluations
_eval_executor = ThreadPoolExecutor(max_workers=5)

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

import json
import os

# --- Persistence Layer (survives Render cold starts) ---
DATA_DIR = os.path.join(os.path.dirname(__file__), ".data")
os.makedirs(DATA_DIR, exist_ok=True)
TENDERS_FILE = os.path.join(DATA_DIR, "tenders.json")
EVALUATIONS_FILE = os.path.join(DATA_DIR, "evaluations.json")

def _load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# Load persisted state on startup
tenders_db: Dict[str, dict] = _load_json(TENDERS_FILE)
evaluations_db: Dict[str, dict] = _load_json(EVALUATIONS_FILE)

def save_tenders():
    _save_json(TENDERS_FILE, tenders_db)

def save_evaluations():
    _save_json(EVALUATIONS_FILE, evaluations_db)

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
        # Offload synchronous LangChain work to a thread so we don't
        # block the FastAPI event loop for other concurrent requests.
        result = await run_in_threadpool(
            orchestrator.process_tender,
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
        save_tenders()

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
        # Offload synchronous orchestrator to threadpool
        evaluation = await run_in_threadpool(
            orchestrator.evaluate_single_bidder,
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
        save_evaluations()

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
    save_evaluations()
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
    
    # Offload to threadpool
    updated_evals = await run_in_threadpool(
        detect_financial_anomalies, evals, api_key=api_key,
    )
    
    # Save back to DB
    evaluations_db[tender_id] = updated_evals
    save_evaluations()
    return {"status": "success", "evaluations": updated_evals}


@app.post("/detect_cartels/{tender_id}")
async def detect_cartels_endpoint(
    tender_id: str,
    api_key: Optional[str] = Body(None),
):
    """Run cartel detection on all bidders."""
    if tender_id not in evaluations_db:
        raise HTTPException(status_code=404, detail="No evaluations found for this tender.")
        
    evals = evaluations_db[tender_id]
    
    # Offload to threadpool
    cartel_alerts = await run_in_threadpool(
        detect_cartels_via_graph, tender_id, evals, api_key,
    )
    
    return {"status": "success", "cartel_alerts": cartel_alerts}


# ═══════════════════════════════════════════════
# NEW: Concurrent Bulk Evaluation + SSE Stream
# ═══════════════════════════════════════════════

class BulkEvaluateRequest(BaseModel):
    """Request body for bulk evaluation."""
    bidders: List[Dict[str, Any]]  # [{"name": "...", "file_keys": [...]}]
    api_key: Optional[str] = None


@app.post("/evaluate_all/{tender_id}")
async def evaluate_all_bidders(
    tender_id: str,
    files: List[UploadFile] = File(...),
    bidder_names: List[str] = Form(...),
    bidder_file_counts: List[int] = Form(...),
    api_key: Optional[str] = Form(None),
):
    """
    Evaluate ALL bidders concurrently using a thread pool.

    The frontend sends:
      - files: all bidder files flattened into one list
      - bidder_names: ["Bidder A", "Bidder B", ...]
      - bidder_file_counts: [2, 1, ...]  (how many files belong to each bidder)

    This endpoint splits them up, evaluates all bidders in parallel,
    then runs anomaly + cartel detection.
    """
    if tender_id not in tenders_db:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    criteria = tenders_db[tender_id]["criteria"]

    # --- Split the flat file list into per-bidder groups ---
    all_file_bytes = []
    all_file_names = []
    for f in files:
        content = await f.read()
        all_file_bytes.append(content)
        all_file_names.append(f.filename)

    bidder_files = {}  # {name: [(bytes, filename), ...]}
    idx = 0
    for name, count in zip(bidder_names, bidder_file_counts):
        bidder_files[name] = [
            (all_file_bytes[idx + i], all_file_names[idx + i])
            for i in range(count)
        ]
        idx += count

    # --- Evaluate all bidders concurrently via ThreadPoolExecutor ---
    loop = asyncio.get_event_loop()
    futures = {}
    for name, file_pairs in bidder_files.items():
        bytes_list = [fp[0] for fp in file_pairs]
        names_list = [fp[1] for fp in file_pairs]
        futures[name] = loop.run_in_executor(
            _eval_executor,
            orchestrator.evaluate_single_bidder,
            criteria, name, bytes_list, names_list, api_key,
        )

    # Await all evaluations in parallel
    results = {}
    errors = {}
    for name, future in futures.items():
        try:
            results[name] = await future
        except Exception as e:
            logger.error("Evaluation failed for %s: %s", name, e)
            errors[name] = str(e)
            results[name] = {
                "bidder_name": name,
                "overall_status": "MANUAL_REVIEW",
                "verdicts": [],
                "eligible_count": 0,
                "not_eligible_count": 0,
                "manual_review_count": len(criteria),
                "error": str(e),
            }

    # Store all evaluations
    if tender_id not in evaluations_db:
        evaluations_db[tender_id] = {}
    evaluations_db[tender_id].update(results)
    save_evaluations()

    # --- Run anomaly + cartel detection on the full set ---
    try:
        updated_evals = await run_in_threadpool(
            detect_financial_anomalies,
            evaluations_db[tender_id],
            api_key=api_key,
        )
        evaluations_db[tender_id] = updated_evals
        save_evaluations()
    except Exception as e:
        logger.warning("Anomaly detection failed: %s", e)
        updated_evals = evaluations_db[tender_id]

    try:
        cartel_alerts = await run_in_threadpool(
            detect_cartels_via_graph,
            tender_id, evaluations_db[tender_id], api_key,
        )
    except Exception as e:
        logger.warning("Cartel detection failed: %s", e)
        cartel_alerts = []

    return {
        "status": "success",
        "evaluations": updated_evals,
        "cartel_alerts": cartel_alerts,
        "errors": errors if errors else None,
    }


@app.get("/evaluate_stream/{tender_id}")
async def evaluate_stream(
    tender_id: str,
):
    """
    Server-Sent Events (SSE) endpoint for live evaluation progress.

    The frontend connects to this endpoint via EventSource.
    The backend pushes events as each bidder finishes evaluation.
    """
    if tender_id not in tenders_db:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    async def event_generator():
        """Yield SSE events as evaluations are stored."""
        import json as _json
        evals = evaluations_db.get(tender_id, {})
        known = set(evals.keys())

        # Send current state first
        yield f"data: {_json.dumps({'type': 'init', 'completed': list(known)})}"
        yield "\n\n"

        # Poll for new completions (max 10 min timeout)
        for _ in range(600):
            await asyncio.sleep(1)
            current = set(evaluations_db.get(tender_id, {}).keys())
            new_bidders = current - known
            for bidder in new_bidders:
                ev = evaluations_db[tender_id][bidder]
                yield f"data: {_json.dumps({'type': 'bidder_complete', 'bidder': bidder, 'status': ev.get('overall_status', 'UNKNOWN')})}"
                yield "\n\n"
            known = current

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
        # Offload synchronous LLM call to threadpool
        answer = await run_in_threadpool(
            chat_about_report,
            req.question, context,
            req.api_key,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        # Offload PDF generation to threadpool
        pdf_bytes = await run_in_threadpool(
            generate_pdf_report, criteria, evaluations,
        )
        
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
