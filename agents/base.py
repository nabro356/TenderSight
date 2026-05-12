"""
TenderSight Agent Framework — Base classes for all agents.
Ported from tender-vlm's OO pattern with Pydantic I/O contracts.
"""
from pydantic import BaseModel
from typing import Any, Dict, Optional


class AgentInput(BaseModel):
    """Standard input contract for all agents."""
    tender_id: str = ""
    bidder_id: str = ""
    payload: Dict[str, Any] = {}


class AgentOutput(BaseModel):
    """Standard output contract for all agents."""
    status: str  # "success" or "failed"
    result: Dict[str, Any] = {}
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None


class BaseAgent:
    """Abstract base class for all TenderSight agents."""
    def __init__(self, name: str):
        self.name = name

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        raise NotImplementedError(f"{self.name} must implement execute()")

    def execute_sync(self, input_data: AgentInput) -> AgentOutput:
        """Synchronous wrapper for use in Streamlit (which doesn't support async)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an existing event loop (e.g., Jupyter/Streamlit)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.execute(input_data)).result()
            return loop.run_until_complete(self.execute(input_data))
        except RuntimeError:
            return asyncio.run(self.execute(input_data))
