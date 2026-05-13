"""
TenderSight Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── LLM Providers ───
# Primary: NVIDIA
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "moonshotai/kimi-k2-instruct")
VLM_MODEL_NAME = os.getenv("VLM_MODEL_NAME", "meta/llama-3.2-11b-vision-instruct")

# Fallback 1: Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

# Fallback 2: Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.1-70b-versatile")

LLM_CONFIG = {
    "temperature": 0.3,
    "top_p": 0.7,
    "max_tokens": 4096,
}

# ─── Rate Limiting ───
CALL_GAP = int(os.getenv("CALL_GAP", "6"))

# ─── Neo4j (optional) ───
ENABLE_NEO4J = os.getenv("ENABLE_NEO4J", "false").lower() == "true"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tendersight")

# Verdict Colors (light professional theme)
COLORS = {
    "eligible": "#16a34a",
    "not_eligible": "#dc2626",
    "manual_review": "#d97706",
    "primary": "#1e40af",
    "primary_light": "#3b82f6",
    "bg": "#f8fafc",
    "card_bg": "#ffffff",
    "border": "#e2e8f0",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "accent": "#7c3aed",
}
