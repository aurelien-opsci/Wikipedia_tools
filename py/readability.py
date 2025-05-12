# readability.py
"""
Readability analysis using the WMF **readability:predict** model

L’API Lift Wing attend désormais **rev_id** (identifiant de révision) au lieu
du titre de page. Ce module :
    1. Récupère le dernier `rev_id` pour chaque article.
    2. Interroge l’end‑point :`https://api.wikimedia.org/service/lw/inference/v1/models/readability:predict`
       avec payload `{"rev_id": rev_id, "lang": lang}`.
    3. Renvoie un score 0‑1 (float) par page dans un `pd.Series`.

Fonction exposée :
    get_readability_score(pages: list[str], lang: str = "en") -> pd.Series
"""

from __future__ import annotations
from typing import List
import pandas as pd  # Required for returning results as a Series
import requests
import json
import sys

# --- 1. User Parameters ---
lang = "fr"

def _latest_rev_id(title: str, lang: str = "fr", verbose: bool = True) -> int | None:
    page_api_url = f'https://{lang}.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'format': 'json',
        'titles': title,
        'prop': 'revisions',
        'rvprop': 'ids',
        'rvlimit': 1
    }
    resp = requests.get(page_api_url, params=params)
    resp.raise_for_status()
    data = resp.json()

    pages = data.get('query', {}).get('pages', {})
    page = next(iter(pages.values()))

    if 'missing' in page:
        raise ValueError(f"L’article « {title} » n’existe pas sur {lang}.wikipedia.org")

    rev_id = page['revisions'][0]['revid']
    if verbose:
        print(f"Dernier rev_id pour « {title} » : {rev_id}")
    return rev_id

def get_readability_score(pages: List[str], lang: str = "fr"):
    inference_url = 'https://api.wikimedia.org/service/lw/inference/v1/models/readability:predict'
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'TalkPageSizeBot/1.0 (mailto:alefichoux@gmail.com)',
    }
    scores = {}
    for page in pages:
        rev_id = _latest_rev_id(page, lang, verbose=False)  # Set verbose to False
        payload = {
            "rev_id": rev_id,
            "lang": lang
        }
        response = requests.post(inference_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        full = response.json()
        output = full.get("output", {})
        scores[page] = output.get("score")
    score_series = pd.Series(scores)
    return f"Le score de lisibilité est de : {score_series.iloc[0]}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python readability.py <article1> <article2> ...")
        sys.exit(1)

    articles = sys.argv[1:]
    for article in articles:
        print(_latest_rev_id(article, lang))  # This will print the message
        print(get_readability_score([article], lang))

if __name__ == "__main__":
    main()

