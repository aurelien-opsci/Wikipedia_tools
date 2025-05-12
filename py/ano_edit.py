# ano_edit.py
"""
Part d’éditions anonymes (IP) sur une période
===========================================

Fonction clé
------------
`get_anon_edit_share(pages, start, end, lang="en") -> pandas.Series`
    • `pages`  : liste de titres d’articles.
    • `start`, `end` : chaînes `YYYY-MM-DD` (inclusives).
    • `lang`   : code langue wiki (`en`, `fr`, …).

Retourne une `pd.Series` *ratio* (0‑1) d’éditions anonymes.

Implémentation :
  * Requêtes paginées à l’API MediaWiki (`prop=revisions`).
  * Compte les révisions où le champ `anon` est présent.
  * Respecte les limites de l’API (`rvlimit=max`, pauses 100 ms entre pages).
"""

from __future__ import annotations
from typing import List, Tuple
import pandas as pd
import requests, time

UA = "AnonEditStatBot/1.1 (opsci)"
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": UA})


def _anon_share_single(title: str, start: str, end: str, lang: str) -> Tuple[float, int, int]:
    """Retourne (ratio, nb_anon, nb_total)."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvstart": f"{end}T23:59:59Z",
        "rvend":   f"{start}T00:00:00Z",
        "rvprop": "user|flags|timestamp",
        "rvlimit": "max",
    }
    total = anon = 0
    while True:
        r = _SESSION.get(api, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for page in data.get("query", {}).get("pages", {}).values():
            for rev in page.get("revisions", []):
                total += 1
                if "anon" in rev:
                    anon += 1
        if "continue" in data:
            params.update(data["continue"])
        else:
            break
    ratio = anon / total if total else 0.0
    return ratio, anon, total


def get_anon_edit_share(pages: List[str], start: str, end: str, lang: str = "en") -> pd.Series:
    """pd.Series ratio anon/total (0-1)."""
    shares = {}
    for p in pages:
        ratio, _, _ = _anon_share_single(p, start, end, lang)
        shares[p] = ratio
        time.sleep(0.1)  # politesse API
    return pd.Series(shares, name="anon_share")


# ─────────────────────────── CLI rapide ─────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="% d’éditions anonymes (IP) sur une période")
    ap.add_argument("pages", nargs="+", help="Titres d’articles")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end",   required=True, help="YYYY-MM-DD")
    ap.add_argument("--lang",  default="fr", help="Code langue wiki (fr, en, …)")
    ns = ap.parse_args()

    ratios = get_anon_edit_share(ns.pages, ns.start, ns.end, ns.lang)
    for page, ratio in ratios.items():
        pct = ratio * 100
        print(f"{page}: {pct:.1f}% d’éditions anonymes")
