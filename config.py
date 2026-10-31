"""Central configuration for VanMitra AI (BioNexis)."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = os.environ.get("VANMITRA_DB", str(ROOT / "data" / "vanmitra.db"))
APP_NAME = "VanMitra AI"
TEAM = "BioNexis"
DEFAULT_QR_BASE_URL = "http://localhost:8501"

PRODUCTS = {"Tamarind": "Fruit / pulp NTFP", "Honey": "Forest honey (animal-derived NTFP)",
            "Other NTFP": "Other non-timber forest product (generic rules only)"}
UNIT_TO_KG = {"kg": 1.0, "g": 0.001, "quintal": 100.0, "tonne": 1000.0}
STORAGE_TYPES = ["Raised platform, ventilated room", "Ground-level room", "Open air / uncovered",
                 "Sealed dry container", "Cool store"]
PACKAGING_TYPES = ["Open / loose", "Jute sack", "Lined HDPE bag", "Airtight food-grade container"]
PROVENANCE_STATUSES = ["unavailable", "user-reported", "documented", "verified"]
GRADES = ["Ungraded", "Grade A", "Grade B", "Grade C"]

DISCLAIMER = ("Screening results and projections are decision-support estimates, not laboratory tests, "
              "certification, or food-safety approval. Records marked SAMPLE are illustrative demonstration "
              "data, not real field data or market quotations. A QR code only points to a record; it does not "
              "prove authenticity, safety or sustainable harvesting.")
