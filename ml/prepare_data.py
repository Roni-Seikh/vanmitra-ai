"""Reproducibly fetch the real dataset used by the price model.
Source: github.com/herrrickshaw/india-mandi-arrivals -> data/agmarknet/state_monthly.csv.gz, a GODL-India re-publication of
Agmarknet 'statewise_price_arrival_sp' (Govt. of India, Dept. of Agriculture & Farmers Welfare, DMI).
    python -m ml.prepare_data     (needs internet once; the file is already shipped in data/real/)"""
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
URL = "https://raw.githubusercontent.com/herrrickshaw/india-mandi-arrivals/main/data/agmarknet/state_monthly.csv.gz"
OUT = ROOT / "data" / "real" / "agmarknet_state_monthly_all.csv.gz"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, OUT); print("saved", OUT, OUT.stat().st_size, "bytes")
