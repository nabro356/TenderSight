import os
import json
import logging
from typing import Dict, List, Optional
from surrealdb import Surreal

logger = logging.getLogger(__name__)

# --- Configuration ---
SURREAL_URI = os.environ.get("SURREAL_URI", "ws://localhost:8000/rpc")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
SURREAL_NS = os.environ.get("SURREAL_NS", "tendersight")
SURREAL_DB = os.environ.get("SURREAL_DB", "tendersight")


class DatabaseClient:
    """Async wrapper for SurrealDB."""

    def __init__(self):
        self.db: Optional[Surreal] = None
        self.connected = False
        
        # In-memory fallback for robust local dev when DB is offline
        self._fallback_tenders = {}
        self._fallback_evals = {}

    async def connect(self):
        """Initialize connection to SurrealDB."""
        if self.connected:
            return
            
        logger.info(f"Connecting to SurrealDB at {SURREAL_URI}...")
        try:
            self.db = Surreal(SURREAL_URI)
            await self.db.connect()
            await self.db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
            await self.db.use(SURREAL_NS, SURREAL_DB)
            self.connected = True
            logger.info("✅ Connected to SurrealDB successfully.")
        except Exception as e:
            logger.warning(f"⚠️ SurrealDB connection failed: {e}. Falling back to in-memory mode.")
            self.connected = False

    async def close(self):
        """Close connection."""
        if self.connected and self.db:
            await self.db.close()
            self.connected = False

    # ─── Tenders API ───

    async def save_tender(self, tender_id: str, data: dict):
        if not self.connected:
            self._fallback_tenders[tender_id] = data
            return

        try:
            # Upsert into 'tender' table
            await self.db.query("UPSERT type::thing('tender', $id) CONTENT $data", {
                "id": tender_id,
                "data": data
            })
        except Exception as e:
            logger.error(f"DB Error saving tender: {e}")
            self._fallback_tenders[tender_id] = data

    async def get_tender(self, tender_id: str) -> Optional[dict]:
        if not self.connected:
            return self._fallback_tenders.get(tender_id)

        try:
            res = await self.db.query("SELECT * FROM type::thing('tender', $id)", {"id": tender_id})
            # res is a list of results per query
            if res and len(res) > 0 and len(res[0].get('result', [])) > 0:
                return res[0]['result'][0]
        except Exception as e:
            logger.error(f"DB Error fetching tender: {e}")
        return self._fallback_tenders.get(tender_id)

    async def get_all_tenders(self) -> Dict[str, dict]:
        if not self.connected:
            return self._fallback_tenders

        try:
            res = await self.db.query("SELECT * FROM tender")
            if res and len(res) > 0 and 'result' in res[0]:
                tenders = res[0]['result']
                # The ID comes back as "tender:TND-XYZ". Strip the prefix.
                return {t["id"].split(":")[-1]: t for t in tenders if "id" in t}
        except Exception as e:
            logger.error(f"DB Error fetching all tenders: {e}")
        return self._fallback_tenders

    # ─── Evaluations API ───

    async def save_evaluation(self, tender_id: str, bidder_name: str, eval_data: dict):
        # Create a deterministic ID for this specific bidder's evaluation
        record_id = f"{tender_id}_{bidder_name.replace(' ', '_')}"
        
        if not self.connected:
            if tender_id not in self._fallback_evals:
                self._fallback_evals[tender_id] = {}
            self._fallback_evals[tender_id][bidder_name] = eval_data
            return

        try:
            await self.db.query("UPSERT type::thing('evaluation', $id) CONTENT $data", {
                "id": record_id,
                "data": {
                    "tender_id": tender_id,
                    "bidder_name": bidder_name,
                    "evaluation": eval_data
                }
            })
            
            # Phase 2 Graph Update: Upsert Corporate Nodes & Edges
            await self._upsert_corporate_graph(tender_id, bidder_name, eval_data)
            
        except Exception as e:
            logger.error(f"DB Error saving evaluation: {e}")
            if tender_id not in self._fallback_evals:
                self._fallback_evals[tender_id] = {}
            self._fallback_evals[tender_id][bidder_name] = eval_data

    async def get_evaluations(self, tender_id: str) -> Dict[str, dict]:
        if not self.connected:
            return self._fallback_evals.get(tender_id, {})

        try:
            res = await self.db.query("SELECT * FROM evaluation WHERE tender_id = $tender_id", {
                "tender_id": tender_id
            })
            if res and len(res) > 0 and 'result' in res[0]:
                evals = res[0]['result']
                return {e["bidder_name"]: e["evaluation"] for e in evals}
        except Exception as e:
            logger.error(f"DB Error fetching evaluations: {e}")
        return self._fallback_evals.get(tender_id, {})

    # ─── Phase 2 Graph Implementation (Cartel Detection) ───

    async def _upsert_corporate_graph(self, tender_id: str, bidder_name: str, eval_data: dict):
        """
        Creates nodes and edges in SurrealDB for cartel detection.
        Nodes: bidder, director, address
        Edges: bidder -> shares_director -> director
               bidder -> registered_at -> address
        """
        if not self.connected:
            return
            
        # Get extracted metadata from the evaluation data (added via anomaly/cartel detector)
        # Note: metadata extraction is handled by `cartel_detector.py`
        metadata = eval_data.get("corporate_metadata", {})
        director = metadata.get("director_name")
        address = metadata.get("address")
        
        bidder_id = bidder_name.replace(' ', '_').lower()
        
        try:
            # 1. Upsert Bidder node
            await self.db.query("UPSERT type::thing('bidder', $b_id) SET name = $b_name", {
                "b_id": bidder_id,
                "b_name": bidder_name
            })
            
            # 2. Upsert Director node and edge
            if director and director.strip():
                dir_id = director.replace(' ', '_').lower()
                await self.db.query("UPSERT type::thing('director', $d_id) SET name = $d_name", {
                    "d_id": dir_id,
                    "d_name": director
                })
                # Create edge (ignore if exists)
                await self.db.query(
                    "RELATE type::thing('bidder', $b_id)->shares_director->type::thing('director', $d_id) UNIQUE", 
                    {"b_id": bidder_id, "d_id": dir_id}
                )
                
            # 3. Upsert Address node and edge
            if address and address.strip():
                addr_id = address.replace(' ', '_').replace(',', '').lower()[:50] # sanitize
                await self.db.query("UPSERT type::thing('address', $a_id) SET location = $a_loc", {
                    "a_id": addr_id,
                    "a_loc": address
                })
                # Create edge
                await self.db.query(
                    "RELATE type::thing('bidder', $b_id)->registered_at->type::thing('address', $a_id) UNIQUE", 
                    {"b_id": bidder_id, "a_id": addr_id}
                )
        except Exception as e:
            logger.error(f"Graph update failed for {bidder_name}: {e}")

    async def query_cartel_graph(self) -> list:
        """
        Queries SurrealDB to find bidders sharing the same director or address.
        """
        if not self.connected:
            return []
            
        alerts = []
        try:
            # Find shared directors
            dir_res = await self.db.query("""
                SELECT 
                    in.name as bidders, 
                    out.name as director 
                FROM shares_director 
                GROUP BY director 
                HAVING count(in) > 1
            """)
            
            if dir_res and len(dir_res) > 0 and 'result' in dir_res[0]:
                for row in dir_res[0]['result']:
                    bidders = row.get("bidders", [])
                    director = row.get("director")
                    if len(bidders) >= 2:
                        alerts.append({
                            "bidder1": bidders[0],
                            "bidder2": bidders[1],
                            "shared_entity": director,
                            "link_type": "Director"
                        })
                        
            # Find shared addresses
            addr_res = await self.db.query("""
                SELECT 
                    in.name as bidders, 
                    out.location as address 
                FROM registered_at 
                GROUP BY address 
                HAVING count(in) > 1
            """)
            
            if addr_res and len(addr_res) > 0 and 'result' in addr_res[0]:
                for row in addr_res[0]['result']:
                    bidders = row.get("bidders", [])
                    address = row.get("address")
                    if len(bidders) >= 2:
                        alerts.append({
                            "bidder1": bidders[0],
                            "bidder2": bidders[1],
                            "shared_entity": address,
                            "link_type": "Address"
                        })
                        
        except Exception as e:
            logger.error(f"Cartel graph query failed: {e}")
            
        return alerts

# Global instance
db_client = DatabaseClient()
