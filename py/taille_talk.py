# taille_talk.py
"""
Extraction de l’activité (proxy = taille brute) des pages de discussion Wikipédia.
Adapté depuis le notebook `taille_talk.ipynb`.

Fonction principale :
    get_talk_activity(pages: list[str], start: str, end: str) -> pandas.Series

• `pages` : titres d’articles sans préfixe « Discussion: »
• `start`, `end` : réservés pour une future version (filtrage temporel). Pour
  l’instant ignorés, mais gardés pour compatibilité avec le pipeline.

Retour :
    pd.Series indexés par titre de page, contenant la taille de la page de
    discussion en nombre de caractères (int). Les pages sans discussion
    renvoient 0.
"""

from __future__ import annotations
import requests
import pandas as pd
from typing import List

API_URL = "https://fr.wikipedia.org/w/api.php"
USER_AGENT = "TalkPageSizeBot/1.0 (mailto:alefichoux@gmail.com)"
_headers = {"User-Agent": USER_AGENT}


def _talk_size(title: str) -> int:
    talk_title = f"Discussion:{title}"
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": talk_title,
        "rvslots": "main",
        "rvprop": "content",
        "redirects": 1,
    }
    try:
        resp = requests.get(API_URL, params=params, headers=_headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        page = next(iter(data["query"]["pages"].values()))
        if "revisions" not in page:
            return 0  # pas de discussion → 0 caractères
        content = page["revisions"][0]["slots"]["main"].get("*", "")
        return len(content)
    except Exception:
        return 0  # fallback silencieux (peut logguer si besoin)


def get_talk_activity(pages: List[str], start: str | None = None, end: str | None = None):
    """Renvoie la taille (nb caractères) des pages de discussion."""
    data = {p: _talk_size(p) for p in pages}
    return pd.Series(data, name="talk_intensity")


if __name__ == "__main__":
    import sys
    pages = sys.argv[1:] or ["Pandémie de Covid-19"]
    print(get_talk_activity(pages))
