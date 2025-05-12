# ref.py
"""
Calcul du **citation gap** pour un ensemble de pages Wikipédia.

Citation gap = `nb_pas_sourcés / nb_total_references`
  • `nb_pas_sourcés` = occurrences des templates "Citation needed" ou "{{cn}}"
  • `nb_total_references` = nombre de balises `<ref` dans le wikitext.

Fonction exposée :
    get_citation_gap(pages: list[str]) -> pandas.Series

Retour : Série indexée par titre d’article (float : 0 = tout sourcé, 1 = aucune ref).

Exemple :
    >>> get_citation_gap(["Transgender_rights", "Gender-affirming_care"])
"""

from __future__ import annotations
from typing import List
import pandas as pd
import requests
import re

API = "https://fr.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "CitationGapBot/1.0 (contact: opsci)"}

_PATTERN_CIT_NEEDED = re.compile(r'refnec', re.I)
_PATTERN_REF = re.compile(r"<ref[ >]", re.I)


def _fetch_wikitext(title: str) -> str:
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvslots": "main",
        "rvprop": "content",
        "redirects": 1,
    }
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        page = next(iter(data["query"]["pages"].values()))
        if "revisions" not in page:
            return
        return page["revisions"][0]["slots"]["main"].get("*", "")
    except Exception:
        return ""


def _citation_gap_from_text(wikitext: str) -> float:
    refs = len(_PATTERN_REF.findall(wikitext))
    needs = len(_PATTERN_CIT_NEEDED.findall(wikitext))
    if refs == 0:
        return 1.0  # aucun ref → gap maximal
    print(f'il y a {needs} citations needed pour {refs} citations au total')
    return min(1.0, needs / refs) 

def get_citation_gap(pages: List[str]):
    """Renvoie le ratio CitationNeeded / refs par page (0 - 1)."""
    data = {p: _citation_gap_from_text(_fetch_wikitext(p)) for p in pages}
    return pd.Series(data, name="citation_gap")


if __name__ == "__main__":

    import sys
    pages = sys.argv[1:] or ["Vladimir Poutine"]
    
    print(get_citation_gap(pages))
