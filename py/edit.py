# edit.py
"""
Analyse de l’activité éditoriale (v2) – sans métriques de revert
===============================================================

Fonctionnalités principales
--------------------------
* **Séries temporelles** du nombre d’éditions quotidiennes via l’API REST
  `metrics/edits/per-page`.
* **Détection de pic d’éditions** (spike) : identifie le jour où l’activité
  atteint son maximum et calcule un score de surprise.
* **Convenience helper** `fetch_edit_pages` pour récupérer directement un
  DataFrame multi‑pages (pour graphiques Plotly, par exemple).

API appelée :
https://wikimedia.org/api/rest_v1/metrics/edits/per-page/<site>/<page>/<editor_type>/daily/<start>/<end>

Le module ne s’occupe PAS (volontairement) des scores de revert‑risk.
"""

from __future__ import annotations
from typing import List, Dict
import pandas as pd
import requests, time
from datetime import datetime, timedelta
import argparse

UA = "EditTrendBot/2.0 (opsci)"
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})

# ─────────────────────────── helpers ────────────────────────────

def _date_fmt(date: str | datetime) -> str:
    """YYYYMMDD pour l’API REST"""
    if isinstance(date, datetime):
        return date.strftime("%Y%m%d")
    return date.replace("-", "")


def _call_edit_api(site: str, page: str, start: str, end: str, editor_type: str) -> pd.Series:
    encoded = requests.utils.quote(page.replace(" ", "_"), safe="")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/edits/per-page/"
        f"{site}/{encoded}/{editor_type}/daily/{_date_fmt(start)}/{_date_fmt(end)}"
    )
    try:
        r = _SESSION.get(url, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items or not items[0].get("results"):
            return pd.Series(name=page)
        results = items[0]["results"]
        key = "count" if "count" in results[0] else "edits"
        data = {
            pd.to_datetime(r["timestamp"], utc=True): r.get(key, 0)
            for r in results
        }
        return pd.Series(data, name=page).sort_index()
    except Exception:
        return pd.Series(name=page)

# ─────────────────────────── API publiques ─────────────────────

def get_edit_timeseries(
    pages: List[str], start: str, end: str, lang: str = "en", editor_type: str = "user"
) -> Dict[str, pd.Series]:
    """Dict {page: Series(utc, edits)}"""
    site = f"{lang}.wikipedia.org"
    return {p: _call_edit_api(site, p, start, end, editor_type) for p in pages}


def get_edit_spike_detail(
    pages: List[str], start: str, end: str, lang: str = "en", editor_type: str = "user"
) -> pd.DataFrame:
    """DataFrame `[edit_spike, peak_day_edits, peak_edits]`"""
    rows: Dict[str, Dict[str, object]] = {}
    for p, serie in get_edit_timeseries(pages, start, end, lang, editor_type).items():
        if serie.empty:
            rows[p] = {"edit_spike": 0.0, "peak_day_edits": None, "peak_edits": 0}
            continue
        med, mx = serie.median(), serie.max()
        spike = (mx - med) / (med + 1)
        rows[p] = {
            "edit_spike": round(spike, 4),
            "peak_day_edits": serie.idxmax().date().isoformat(),
            "peak_edits": int(mx),
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def get_edit_spikes(pages: List[str], start: str, end: str, lang: str = "en", editor_type: str = "user") -> pd.Series:
    """Series spike seule — pour le pipeline."""
    return get_edit_spike_detail(pages, start, end, lang, editor_type)["edit_spike"]

# ---------- Convenience DataFrame -----------------------------------------

def fetch_edit_pages(site: str, pages: List[str], start: str, end: str, editor_type: str = "user") -> pd.DataFrame:
    """Retourne un DF concaténé (date, edits, page). Utilisable pour Plotly."""
    dfs = []
    for p in pages:
        serie = _call_edit_api(site, p, start, end, editor_type)
        if not serie.empty:
            df = serie.rename("edits").reset_index().rename(columns={"index": "date"})
            df["page"] = p
            dfs.append(df)
        time.sleep(0.1)  # politesse API
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=["date", "edits", "page"])

# ─────────────────────────── CLI & démo ─────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Analyse des edits (spike ou timeseries)")
    ap.add_argument("pages", nargs="+", help="Titres d’articles")
    ap.add_argument("--start", help="YYYY-MM-DD (défaut = aujourd’hui -30j)")
    ap.add_argument("--end",   help="YYYY-MM-DD (défaut = aujourd’hui)")
    ap.add_argument("--lang",  default="en", help="Code langue wiki (en, fr, …)")
    ap.add_argument("--metric", choices=["spike", "timeseries"], default="spike")
    ap.add_argument("--editor", default="user", help="editor_type (user, bot, anonymous, etc.)")
    ns = ap.parse_args()

    today = datetime.utcnow().date()
    end   = ns.end or today.isoformat()
    start = ns.start or (today - timedelta(days=30)).isoformat()

    if ns.metric == "spike":
        print(get_edit_spike_detail(ns.pages, start, end, ns.lang, ns.editor).to_markdown())
    else:
        site = f"{ns.lang}.wikipedia.org"
        df = fetch_edit_pages(site, ns.pages, start, end, ns.editor)
        print(df.head())  # à connecter avec Plotly si besoin
