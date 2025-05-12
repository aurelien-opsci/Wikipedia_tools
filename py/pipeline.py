# wikipedia_scoring_pipeline.py  –  **light version**
"""
Pipeline v0.2 – ne s’appuie **que** sur les métriques déjà codées :

* **Heat**  :
    * `pageview_spike`   (pageviews.get_pageview_spikes)
    * `edit_spike`       (edit.get_edit_spikes)
    * `talk_intensity`   (taille_talk.get_talk_activity)
* **Quality** :
    * `citation_gap`     (ref.get_citation_gap)
    # TODO: ajouter plus tard article_quality, readability, source_age, unreliable_refs…
* **Actor Risk** :
    * `anon_share`       (ano_edit.get_anon_edit_share)
    # TODO: intégrer sockpuppet_score, micro_edits, automod_flag, author_revertrisk…

Métriques non implémentées pour l’instant sont **commentées**.

Étapes :
1. Appel des fonctions dispo.
2. Min‑max scaling.
3. Agrégation pondérée en Heat / Quality / Risk.
4. Score global.

"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np

# ───────────────────────────  Poids (modifiable) ────────────────
HEAT_WEIGHTS = {
    "pageview_spike": 0.4,
    "edit_spike":     0.4,
    "talk_intensity": 0.2,
}
QUALITY_WEIGHTS = {
    "citation_gap": -1.0,  # >0 = plus de gaps = moins bonne qualité
}
RISK_WEIGHTS = {
    "anon_share": 1.0,
}
GLOBAL_WEIGHTS = {"heat": 0.5, "quality": -0.2, "risk": 0.3}

# ───────────────────────────  Helpers ───────────────────────────

def _minmax(s: pd.Series) -> pd.Series:
    if s.empty:
        return s
    rng = s.max() - s.min()
    return (s - s.min()) / (rng if rng else 1)

@dataclass
class ScoringResult:
    heat: pd.Series
    quality: pd.Series
    risk: pd.Series
    global_score: pd.Series

# ───────────────────────────  Pipeline ──────────────────────────

def compute_scores(pages: List[str], start: str, end: str, lang: str = "fr") -> ScoringResult:
    # Imports (uniquement modules dispo)
    from pageviews   import get_pageview_spikes
    from edit        import get_edit_spikes
    from taille_talk import get_talk_activity
    from ref         import get_citation_gap
    from ano_editor import get_anon_edit_share

    raw: Dict[str, pd.Series] = {}

    # Heat
    raw["pageview_spike"] = get_pageview_spikes(pages, start, end, lang)
    raw["edit_spike"]     = get_edit_spikes(pages, start, end, lang)
    raw["talk_intensity"] = get_talk_activity(pages)  # taille fixe, pas de date

    # Quality
    raw["citation_gap"]   = get_citation_gap(pages)

    # Risk
    raw["anon_share"]     = get_anon_edit_share(pages, start, end, lang)

    df = pd.DataFrame(raw)
    df_norm = df.apply(_minmax, axis=0)

    heat    = (df_norm[HEAT_WEIGHTS.keys()]    * pd.Series(HEAT_WEIGHTS)).sum(axis=1)
    quality = (df_norm[QUALITY_WEIGHTS.keys()] * pd.Series(QUALITY_WEIGHTS)).sum(axis=1)
    risk    = (df_norm[RISK_WEIGHTS.keys()]    * pd.Series(RISK_WEIGHTS)).sum(axis=1)

    global_score = pd.concat([heat.rename("heat"), quality.rename("quality"), risk.rename("risk")], axis=1)
    global_score = (global_score * pd.Series(GLOBAL_WEIGHTS)).sum(axis=1)

    return ScoringResult(heat, quality, risk, global_score)

# ───────────────────────────  CLI  ─────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Score PROMPT simplifié (Heat / Quality / Risk).")
    ap.add_argument("pages", nargs="+", help="Titres d’articles")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end",   default="2024-12-31")
    ap.add_argument("--lang",  default="fr")
    ns = ap.parse_args()

    res = compute_scores(ns.pages, ns.start, ns.end, ns.lang)
    df = pd.DataFrame({
        "heat": res.heat.round(3),
        "quality": res.quality.round(3),
        "risk": res.risk.round(3),
        "global": res.global_score.round(3)
    })
    print(df.to_markdown())
