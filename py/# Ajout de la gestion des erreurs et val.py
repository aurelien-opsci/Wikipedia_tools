# Ajout de la gestion des erreurs et validation des entrées

import requests
import time
import pandas as pd
from datetime import datetime
import plotly.express as px
import ipywidgets as w
from IPython.display import display
from dateutil import parser

# ── 2. Session avec User‑Agent ──────────────────────────────────────────────
UA = "PageviewsDemo/1.0 (https://github.com/aureliusLF; alefichoux@gmail.com)"
session = requests.Session()
session.headers.update({"User-Agent": UA})

# ──────────────────────────  Cellule 3 : fonction API edits ───────────────────────────────
def edits(site: str, page: str,
          start: str, end: str,
          editor_type: str = "all-editor-types",
          granularity: str = "daily") -> pd.DataFrame:
    """
    Renvoie un DataFrame (date, edits) pour `page` sur `site`.
      site         : 'fr.wikipedia.org', 'en.wikipedia.org', …
      page         : titre avec _ (ex. 'Tour_Eiffel')
      start / end  : 'YYYY-MM-DD'
      editor_type  : 'user'|'anonymous'|'bot'|'all-editor-types'
      granularity  : 'daily'|'monthly'
    """
    fmt_day  = "%Y%m%d"
    fmt_day0 = "%Y%m%d00"
    try:
        s = datetime.strptime(start, "%Y-%m-%d").strftime(fmt_day0)
        e = datetime.strptime(end,   "%Y-%m-%d").strftime(fmt_day)
    except ValueError as ve:
        raise ValueError("Les dates doivent être au format 'YYYY-MM-DD'.") from ve

    url = (f"https://wikimedia.org/api/rest_v1/metrics/edits/per-page/"
           f"{site}/{page}/{editor_type}/{granularity}/{s}/{e}")

    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()  # Lève une erreur HTTP si besoin
    except requests.exceptions.RequestException as ex:
        raise RuntimeError(f"Erreur lors de la requête API : {ex}") from ex

    items = r.json().get("items", [])
    if not items:
        return pd.DataFrame(columns=["date", "edits", "page"])

    return pd.DataFrame({
        "date":  pd.to_datetime([it["timestamp"] for it in items], format="YYYYMMDD00"),
        "edits": [it["edits"] for it in items],
        "page":  page
    })

# ──────────────────────────  Cellule 4 : agrégation multi‑pages ───────────────────────────
def fetch_edits(site, pages, start, end, editor_type="all-editor-types"):
    frames = []
    for p in pages:
        try:
            frames.append(edits(site, p, start, end, editor_type))
        except RuntimeError as e:
            print(f"Erreur pour la page {p} : {e}")
        time.sleep(0.1)  # Courtoisie : ≤10 requêtes / seconde
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ──────────────────────────  Cellule 5 : widgets d’entrée ─────────────────────────────────
site_w   = w.Text(value="fr.wikipedia.org", description="Wiki :")
pages_w  = w.Textarea(
    value="Tour_Eiffel\nMarie_Curie",
    description="Pages :", layout=w.Layout(width="50%")
)
etype_w  = w.Dropdown(
    options=[("Tous", "all-editor-types"),
             ("Utilisateurs inscrits", "user"),
             ("Anonymes", "anonymous"),
             ("Bots", "bot")],
    value="all-editor-types", description="Éditeurs :"
)
start_w  = w.DatePicker(value=datetime(2023, 1, 1), description="Start :")
end_w    = w.DatePicker(value=datetime(2023, 12, 31), description="End :")
btn      = w.Button(description="Mettre à jour", button_style="primary")

ui = w.VBox([w.HBox([site_w, etype_w]),
             pages_w,
             w.HBox([start_w, end_w]),
             btn])
display(ui)

# ──────────────────────────  Cellule 6 : callback + premier affichage ─────────────────────
out = w.Output()
display(out)

def refresh(_=None):
    with out:
        out.clear_output(wait=True)
        try:
            pages = [p.strip() for p in pages_w.value.splitlines() if p.strip()]
            if not pages:
                raise ValueError("La liste des pages ne peut pas être vide.")
            df = fetch_edits(site_w.value, pages,
                             start_w.value.strftime("%Y-%m-%d"),
                             end_w.value.strftime("%Y-%m-%d"),
                             etype_w.value)

            if df.empty:
                print("Aucune donnée disponible pour les paramètres donnés.")
                return

            fig = px.line(df, x="date", y="edits", color="page",
                          title=f"Éditions — {site_w.value} — {etype_w.label}",
                          labels={"edits": "nombre d’éditions"})
            fig.update_layout(legend_title_text="Page")
            fig.show()
        except Exception as e:
            print(f"Erreur : {e}")

btn.on_click(refresh)
refresh()  # Trace immédiatement lors du chargement