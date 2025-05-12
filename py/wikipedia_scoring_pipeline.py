# wikipedia_scoring_pipeline.py  –  **absolute v0.5**
"""
Calcule Heat / Quality / Risk + score global **par article**, sans dépendre des
valeurs des autres articles (pas de min‑max inter‑lignes).

Métriques / scripts disponibles
-------------------------------
* Heat    : pageview_spike, edit_spike, talk_intensity, protection_level
* Quality : citation_gap, readability
* Risk    : anon_share

Échelles absolues
-----------------
| Métrique                  | Normalisation f(x)                  | Sens |
|---------------------------|-------------------------------------|------|
| pageview_spike, edit_spike, talk_intensity |  x / (x + 1)     | ↗ = plus chaud |
| protection_level (0‑4)    |  x / 4                              | ↗ = plus chaud |
| citation_gap, readability, anon_share | 1 − x / (x + 1)       | ↘ = mieux |

Résultat : chaque signal est dans [0,1] indépendamment des autres pages.
"""

from __future__ import annotations
from typing import List, Dict, Tuple
from dataclasses import dataclass
import pandas as pd, re

# ───────────────────────────  Poids ────────────────────────────
HEAT_W = {"pageview_spike":.35,"edit_spike":.35,"talk_intensity":.1,"protection_level":.2}
QUAL_W = {"citation_gap":-.6,"readability":-.4}
RISK_W = {"anon_share":1.0}
GLOB_W = {"heat":.5,"quality":-.25,"risk":.25}

# ───────────────────────────  Scaling ─────────────────────────

def _scale(metric: str, s: pd.Series) -> pd.Series:
    pos = {"pageview_spike","edit_spike","talk_intensity"}
    neg = {"citation_gap","readability","anon_share"}
    if metric in pos:
        return s.apply(lambda x: x/(x+1))
    if metric in neg:
        return s.apply(lambda x: 1 - x/(x+1))
    if metric=="protection_level":
        return s/4
    return s  # déjà 0‑1

@dataclass
class ScoringResult:
    heat: pd.Series; quality: pd.Series; risk: pd.Series; global_score: pd.Series

# ───────────────────────────  Pipeline ─────────────────────────

def compute_scores(pages: List[str], start: str, end: str, lang="fr") -> Tuple[ScoringResult,pd.DataFrame]:
    from pageviews   import get_pageview_spikes
    from edit        import get_edit_spikes
    from taille_talk import get_talk_activity
    from protection  import protection_rating
    from ref         import get_citation_gap
    from readability import get_readability_score
    from ano_edit    import get_anon_edit_share

    # lecture readability par article
    def _readab(p):
        txt=get_readability_score([p],lang)
        m=re.search(r"([0-9]*\.?[0-9]+)",str(txt))
        return float(m.group(1)) if m else 0.0

    raw: Dict[str,pd.Series]={
        "pageview_spike":get_pageview_spikes(pages,start,end,lang),
        "edit_spike":    get_edit_spikes(pages,start,end,lang),
        "talk_intensity":get_talk_activity(pages),
        "protection_level":protection_rating(pages,lang)["Score"].astype(float),
        "citation_gap":  get_citation_gap(pages),
        "readability":   pd.Series({p:_readab(p) for p in pages}),
        "anon_share":    get_anon_edit_share(pages,start,end,lang)
    }

    metrics=pd.DataFrame(raw).apply(pd.to_numeric,errors="coerce").fillna(0)

    # normalisation absolue
    metrics_norm=pd.DataFrame({m:_scale(m,col) for m,col in metrics.items()})

    heat    = (metrics_norm[list(HEAT_W)] * pd.Series(HEAT_W)).sum(axis=1)
    quality = (metrics_norm[list(QUAL_W)] * pd.Series(QUAL_W)).sum(axis=1)
    risk    = (metrics_norm[list(RISK_W)] * pd.Series(RISK_W)).sum(axis=1)
    global_ = pd.concat([heat,quality,risk],axis=1).set_axis(["heat","quality","risk"],axis=1)
    global_=(global_*pd.Series(GLOB_W)).sum(axis=1)

    return ScoringResult(heat,quality,risk,global_),metrics

# ───────────────────────────  CLI ─────────────────────────────
if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Score PROMPT absolu (v0.5)")
    ap.add_argument("pages",nargs="+",help="Titres d’articles")
    ap.add_argument("--start",default="2024-01-01")
    ap.add_argument("--end",default="2024-12-31")
    ap.add_argument("--lang",default="fr")
    ns=ap.parse_args()

    scores,detail=compute_scores(ns.pages,ns.start,ns.end,ns.lang)
    print("\n### Détail métriques brutes\n");print(detail.round(3).to_markdown())
    final=pd.DataFrame({"heat":scores.heat.round(3),"quality":scores.quality.round(3),"risk":scores.risk.round(3),"global":scores.global_score.round(3)})
    print("\n### Tableau final\n");print(final.to_markdown())

