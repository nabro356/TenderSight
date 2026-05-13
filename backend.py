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
from utils.tender_metadata import extract_tender_metadata

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
from db.surreal_client import db_client

# Load persisted state on startup
@app.on_event("startup")
async def startup_event():
    await db_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db_client.close()

orchestrator = OrchestratorAgent()


@app.get("/")
async def health_check():
    tenders = await db_client.get_all_tenders()
    return {
        "status": "ok",
        "service": "TenderSight AI",
        "version": "2.0.0",
        "db_connected": db_client.connected,
        "active_tenders": len(tenders),
    }


@app.post("/tenders/")
async def create_tender(
    files: List[UploadFile] = File(...),
    api_key: Optional[str] = Form(None),
):
    """Upload one or more tender documents and extract bundle criteria."""
    tender_id = f"TND-{uuid.uuid4().hex[:8].upper()}"

    try:
        payloads = []
        for tender_file in files:
            payloads.append(
                {
                    "filename": tender_file.filename,
                    "bytes": await tender_file.read(),
                }
            )

        # Offload synchronous LangChain work to a thread so we don't
        # block the FastAPI event loop for other concurrent requests.
        result = await run_in_threadpool(
            orchestrator.process_tender_bundle,
            files=payloads,
            api_key=api_key,
        )

        metadata = extract_tender_metadata(
            result["raw_text"],
            [doc["name"] for doc in result.get("bundle_documents", [])],
        )

        tender_data = {
            "filename": payloads[0]["filename"],
            "bundle_documents": result.get("bundle_documents", []),
            "criteria": result["criteria"],
            "raw_text": result["raw_text"],
            "ocr_engine": result["ocr_engine"],
            "pages": result.get("pages", 0),
            "metadata": metadata,
        }
        await db_client.save_tender(tender_id, tender_data)

        return {
            "status": "created",
            "tender_id": tender_id,
            "filename": payloads[0]["filename"],
            "bundle_documents": result.get("bundle_documents", []),
            "ocr_engine": result["ocr_engine"],
            "confidence": result["confidence"],
            "pages": result.get("pages", 0),
            "criteria_count": len(result["criteria"]),
            "criteria": result["criteria"],
            "raw_text": result["raw_text"],
            "metadata": metadata,
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
    tender = await db_client.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    file_bytes_list = []
    file_names_list = []
    for f in files:
        content = await f.read()
        file_bytes_list.append(content)
        file_names_list.append(f.filename)
        
    criteria = tender["criteria"]

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
        await db_client.save_evaluation(tender_id, bidder_id, evaluation)

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
    await db_client.save_evaluation(tender_id, bidder_id, evaluation)
    return {"status": "success", "message": "Evaluation updated successfully."}


@app.post("/detect_anomalies/{tender_id}")
async def detect_anomalies_endpoint(
    tender_id: str,
    api_key: Optional[str] = Body(None),
):
    """Run statistical anomaly detection on all bidders for a tender."""
    evals = await db_client.get_evaluations(tender_id)
    if not evals:
        raise HTTPException(status_code=404, detail="No evaluations found for this tender.")
    
    # Offload to threadpool
    updated_evals = await run_in_threadpool(
        detect_financial_anomalies, evals, api_key=api_key,
    )
    
    # Save back to DB
    for bidder, data in updated_evals.items():
        await db_client.save_evaluation(tender_id, bidder, data)
        
    return {"status": "success", "evaluations": updated_evals}


@app.post("/detect_cartels/{tender_id}")
async def detect_cartels_endpoint(
    tender_id: str,
    api_key: Optional[str] = Body(None),
):
    """Run cartel detection using the graph database."""
    evals = await db_client.get_evaluations(tender_id)
    if not evals:
        raise HTTPException(status_code=404, detail="No evaluations found for this tender.")
        
    # In Phase 2, we query the graph directly for links created during evaluation saves
    cartel_alerts = await db_client.query_cartel_graph()
    
    # Optional: if no graph backend connection, fall back to the in-memory detector
    if not db_client.connected:
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
    tender = await db_client.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    criteria = tender["criteria"]

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

    # Store all evaluations in DB
    for name, result in results.items():
        await db_client.save_evaluation(tender_id, name, result)

    # --- Run anomaly + cartel detection on the full set ---
    db_evals = await db_client.get_evaluations(tender_id)
    try:
        updated_evals = await run_in_threadpool(
            detect_financial_anomalies,
            db_evals,
            api_key=api_key,
        )
        for bidder, data in updated_evals.items():
            await db_client.save_evaluation(tender_id, bidder, data)
    except Exception as e:
        logger.warning("Anomaly detection failed: %s", e)
        updated_evals = db_evals

    try:
        cartel_alerts = await db_client.query_cartel_graph()
        if not db_client.connected:
            cartel_alerts = await run_in_threadpool(
                detect_cartels_via_graph,
                tender_id, updated_evals, api_key,
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
    tender = await db_client.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    async def event_generator():
        """Yield SSE events as evaluations are stored."""
        import json as _json
        evals = await db_client.get_evaluations(tender_id)
        known = set(evals.keys())

        # Send current state first
        yield f"data: {_json.dumps({'type': 'init', 'completed': list(known)})}\n\n"

        # Poll for new completions (max 10 min timeout)
        for _ in range(600):
            await asyncio.sleep(1)
            current_evals = await db_client.get_evaluations(tender_id)
            current = set(current_evals.keys())
            new_bidders = current - known
            for bidder in new_bidders:
                ev = current_evals[bidder]
                yield f"data: {_json.dumps({'type': 'bidder_complete', 'bidder': bidder, 'status': ev.get('overall_status', 'UNKNOWN')})}\n\n"
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
    tender = await db_client.get_tender(req.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {req.tender_id} not found")

    context = {
        "criteria": tender["criteria"],
        "evaluations": await db_client.get_evaluations(req.tender_id),
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
    tender = await db_client.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")
        
    criteria = tender["criteria"]
    evaluations = await db_client.get_evaluations(tender_id)
    
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


@app.get("/tenders/summary")
async def get_tenders_summary():
    """Get a high-level summary of all active tenders for the mobile dashboard."""
    tenders = await db_client.get_all_tenders()
    summary = []
    
    # Get all cartel alerts in the graph
    all_cartel_alerts = await db_client.query_cartel_graph()
    
    for t_id, t_data in tenders.items():
        evals = await db_client.get_evaluations(t_id)
        
        # Calculate L1 Bidder
        l1_bidder = "Pending Evaluation"
        l1_amount = float('inf')
        
        for bidder, ev in evals.items():
            if ev.get("overall_status") in ["ELIGIBLE", "MANUAL_REVIEW"] and ev.get("financial_bid"):
                try:
                    bid = float(ev["financial_bid"])
                    if bid < l1_amount:
                        l1_amount = bid
                        l1_bidder = bidder
                except:
                    pass
                    
        # Filter alerts that apply to bidders in this specific tender
        tender_alerts = [
            a for a in all_cartel_alerts 
            if a.get("bidder1") in evals or a.get("bidder2") in evals
        ]
        
        summary.append({
            "id": t_id,
            "title": t_data.get("filename", f"Tender {t_id}"),
            "l1_bidder": l1_bidder,
            "l1_amount": l1_amount if l1_amount != float('inf') else None,
            "has_alert": len(tender_alerts) > 0,
            "cartel_alerts": tender_alerts
        })
        
    return {"tenders": summary}


@app.get("/tenders/{tender_id}")
async def get_tender_details(tender_id: str):
    """Get full details of a specific tender including all bidder evaluations."""
    tender = await db_client.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")
        
    evals = await db_client.get_evaluations(tender_id)
    return {
        "tender_id": tender_id,
        "filename": tender.get("filename"),
        "criteria_count": len(tender.get("criteria", [])),
        "metadata": tender.get("metadata"),
        "bundle_documents": tender.get("bundle_documents", []),
        "evaluations": evals
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
