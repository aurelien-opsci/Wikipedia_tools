#!/usr/bin/env python3
"""
Évalue la sévérité de la protection de pages Wikipédia.

Usage  :
    python protection_rating.py <code_langue> "Titre 1" ["Titre 2" ...]
Exemple:
    python protection.py fr "Emmanuel Macron" "Paris"
"""

from __future__ import annotations
import requests, sys, time, pandas as pd

HEADERS = {"User-Agent": "ProtectionRating/1.2 (example@example.com)"}

LEVEL_SCORE = {
    "": 0,
    "autoconfirmed": 1,
    "editautopatrolprotected": 1,
    "editextendedsemiprotected": 2,
    "extendedconfirmed": 2,
    "templateeditor": 3,
    "editautoreviewprotected": 3,
    "sysop": 4,
}
LABEL = {0: "libre", 1: "semi", 2: "extended", 3: "spécialisé", 4: "plein"}

def _score(level: str) -> int:
    return LEVEL_SCORE.get(level, 2)

def _fetch_edit_protection(title: str, lang: str) -> tuple[str, int]:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "info",
        "inprop": "protection",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(api, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    pdata = r.json()["query"]["pages"][0]

    # ──> ne garder **que** les protections portant sur l'édition :
    prot_edit = [p for p in pdata.get("protection", []) if p["type"] == "edit"]

    if not prot_edit:
        return "aucune protection (edit)", 0

    desc = ", ".join(f"{p['type']}:{p['level']}" for p in prot_edit)
    max_score = max(_score(p["level"]) for p in prot_edit)
    return desc, max_score

def protection_rating(pages: list[str], lang: str = "fr") -> pd.DataFrame:
    rows = []
    for pg in pages:
        try:
            desc, score = _fetch_edit_protection(pg, lang)
        except Exception as e:
            desc, score = f"erreur ({e})", -1
        rows.append(
            {"Page": pg,
             "Protection (edit)": desc,
             "Score": score,
             "Sévérité": LABEL.get(score, "?")}
        )
        time.sleep(0.3)
    return pd.DataFrame(rows).set_index("Page")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    lang, *titles = sys.argv[1:]
    df = protection_rating(titles, lang)
    print(df.to_markdown())