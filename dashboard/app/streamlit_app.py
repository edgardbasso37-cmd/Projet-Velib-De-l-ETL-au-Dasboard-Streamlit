"""
Dashboard admin - Vélib Demand Pipeline.

Page unique (pas de sidebar) qui affiche :
  - Statut de la dernière collecte (Vélib + Météo)
  - Aperçu et stats de la couche Bronze
  - Aperçu et stats de la couche Gold
  - Heatmap des stations Vélib (taux d'occupation coloré)
  - Historique d'occupation d'une station sur une période choisie
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def precip_color(mm: float) -> str:
    """Couleur rgba pour une barre de précipitations selon l'intensité (fenêtre 15 min).

    Paliers (mm/15 min) :
      0          → transparent
      ]0 – 2]    → bleu très clair  (sky-100)
      ]2 – 5]    → bleu clair       (sky-300)
      ]5 – 15]   → bleu moyen       (sky-500)
      > 15       → bleu foncé       (sky-700)
    """
    if not mm or mm <= 0:
        return "rgba(0,0,0,0)"
    if mm <= 2:
        return "rgba(186, 230, 253, 0.28)"
    if mm <= 5:
        return "rgba(125, 211, 252, 0.32)"
    if mm <= 15:
        return "rgba(14, 165, 233, 0.36)"
    return "rgba(3, 105, 161, 0.42)"

# ─── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Vélib Pipeline · Dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS global ───────────────────────────────────────────────────────────────
# st.markdown reste nécessaire ici : c'est le seul endroit où on injecte
# du CSS global. st.html() est réservé au contenu HTML (cards, sections…).

st.markdown("""
<style>
/* ── Masquer le chrome Streamlit ──────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Variable d'alignement global ────────────────── */
/* Une seule valeur contrôle le padding latéral de la navbar ET
   du block-container : les deux s'alignent automatiquement. */
:root { --layout-gap: 2rem; }

/* ── Base ─────────────────────────────────────────── */
.stApp { background-color: #f1f5f9; }

/* Supprimer le padding-top (géré par le spacer), imposer --layout-gap
   sur les côtés, et étendre la largeur max */
.main .block-container,
[data-testid="stMainBlockContainer"],
.stMainBlockContainer {
    padding-top: 0 !important;
    padding-left: var(--layout-gap) !important;
    padding-right: var(--layout-gap) !important;
    max-width: 100% !important;
}

/* ── Header principal (navbar pleine largeur) ─────── */
/* position:fixed + left/right:0 garantit une largeur 100vw indépendamment
   des containers Streamlit. Un spacer (.dash-header-spacer) compense la
   hauteur pour que le contenu ne passe pas derrière la navbar. */
.dash-header {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 20px var(--layout-gap);
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 9999;
    box-sizing: border-box;
}
.dash-header-spacer {
    height: 80px;
}
.dash-title {
    color: #f8fafc;
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
}
.dash-subtitle {
    color: #64748b;
    font-size: 0.82rem;
    margin-top: 4px;
}
.dash-live-badge {
    background: #22c55e1a;
    color: #22c55e;
    border: 1px solid #22c55e33;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.dash-ts {
    color: #475569;
    font-size: 0.78rem;
    margin-top: 6px;
    text-align: right;
}

/* ── Contenu de la page ───────────────────────────── */
.page-content { padding: 36px 48px; }

/* ── Titre de section ─────────────────────────────── */
.section-title {
    font-size: 0.7rem;
    font-weight: 800;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 0 0 14px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e2e8f0;
}

/* ── Cards statut (collecte) ──────────────────────── */
.status-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 36px;
}
.status-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 26px 30px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
    border-top: 4px solid var(--accent-color);
    position: relative;
}
.status-card.velib { --accent-color: #4f46e5; }
.status-card.meteo { --accent-color: #f59e0b; }

.status-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 22px;
}
.status-card-name {
    font-size: 1rem;
    font-weight: 700;
    color: #1e293b;
}
.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 0 4px #22c55e22;
    flex-shrink: 0;
}
.status-dot.warn  { background: #f59e0b; box-shadow: 0 0 0 4px #f59e0b22; }
.status-dot.error { background: #ef4444; box-shadow: 0 0 0 4px #ef444422; }

.status-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}
.sm-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94a3b8;
    margin-bottom: 4px;
}
.sm-value {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
}
.sm-sub {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 3px;
}

/* ── Card couche (Bronze / Gold) ──────────────────── */
.layer-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 26px 30px 20px 30px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
    margin-bottom: 22px;
}
.layer-card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 20px;
}
.layer-badge {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    white-space: nowrap;
    margin-top: 2px;
}
.layer-badge.bronze { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.layer-badge.gold   { background: #fef9c3; color: #713f12; border: 1px solid #fde047; }
.layer-badge.live   { background: #ede9fe; color: #5b21b6; border: 1px solid #c4b5fd; }

.layer-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e293b;
    font-family: monospace;
}
.layer-desc {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 3px;
}

/* ── Mini stats ───────────────────────────────────── */
.mini-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    background: #f8fafc;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    margin-bottom: 20px;
}
.mini-stat {
    padding: 14px 20px;
    border-right: 1px solid #e2e8f0;
    min-width: 120px;
}
.mini-stat:last-child { border-right: none; }
.ms-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 4px;
}
.ms-value {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
}
.ms-value.sm { font-size: 0.85rem; }

/* ── Preview label ────────────────────────────────── */
.preview-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 8px;
}

/* ── Carte / Heatmap ──────────────────────────────── */
.map-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 26px 30px 20px 30px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
    margin-bottom: 22px;
}

/* ── Card historique station ──────────────────────── */
.history-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 26px 30px 24px 30px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
    margin-bottom: 36px;
}
.history-legend {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.history-legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    color: #64748b;
}
.legend-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── Graphiques Plotly ────────────────────────────── */
[data-testid="stPlotlyChart"] {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
}

/* ── États vides et erreurs ───────────────────────── */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #94a3b8;
    font-size: 0.88rem;
}
.empty-icon { font-size: 2rem; margin-bottom: 8px; }
.error-box {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 14px 18px;
    color: #dc2626;
    font-size: 0.83rem;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def api_get(path: str):
    """Appel GET vers l'API FastAPI. Retourne (data, error_message)."""
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Impossible de joindre l'API (FastAPI démarré ?)"
    except httpx.HTTPStatusError as exc:
        return None, f"Erreur API {exc.response.status_code}: {exc.response.text}"
    except Exception as exc:
        return None, str(exc)


def fmt_int(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{int(v):,}".replace(",", "\u202f")
    except (ValueError, TypeError):
        return str(v)


def fmt_float(v, decimals: int = 2) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.{decimals}f}"
    except (ValueError, TypeError):
        return str(v)


def fmt_dt(s) -> str:
    """Formate une date ISO string en JJ/MM/AAAA HH:MM, heure de Paris."""
    if not s:
        return "-"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(PARIS_TZ)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(s)


def freshness_dot(last_ingestion_str) -> str:
    """Retourne la classe CSS du point de statut selon la fraîcheur des données."""
    if not last_ingestion_str:
        return "error"
    try:
        dt = datetime.fromisoformat(str(last_ingestion_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        minutes_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 60
        if minutes_ago < 30:
            return ""
        elif minutes_ago < 120:
            return "warn"
        return "error"
    except Exception:
        return "error"


# ─── Header ───────────────────────────────────────────────────────────────────

now_str = datetime.now(PARIS_TZ).strftime("%d/%m/%Y %H:%M:%S")

# st.markdown (unsafe_allow_html) plutôt que st.html() : st.html() est rendu
# dans une iframe sandboxée (Streamlit ≥ 1.36), ce qui empêche le header de
# sortir du container. st.markdown injecte directement dans le DOM principal.
st.markdown(f"""
<div class="dash-header">
    <div>
        <div class="dash-title">🚲 Vélib Demand - Pipeline Dashboard</div>
        <div class="dash-subtitle">
            Architecture Médaillon · Bronze → Silver → Gold · FastAPI + Streamlit
        </div>
    </div>
    <div>
        <div style="text-align:right">
            <span class="dash-live-badge">● LIVE</span>
        </div>
        <div class="dash-ts">Actualisé le {now_str}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="dash-header-spacer"></div>', unsafe_allow_html=True)

st.html('<div class="page-content">')


# ─── Section Statut ───────────────────────────────────────────────────────────

st.html('<div class="section-title">Statut de la collecte</div>')

status, status_err = api_get("/api/status")

if status_err:
    st.html(f'<div class="error-box">⚠️ {status_err}</div>')
else:
    vs = status.get("velib") or {}
    ms = status.get("meteo") or {}

    st.html(f"""
    <div class="status-grid">

        <div class="status-card velib">
            <div class="status-card-header">
                <div class="status-card-name">🚲 Vélib - Stations</div>
                <div class="status-dot {freshness_dot(vs.get('last_ingestion'))}"></div>
            </div>
            <div class="status-metrics">
                <div>
                    <div class="sm-label">Dernière collecte</div>
                    <div class="sm-value" style="font-size:0.88rem">
                        {fmt_dt(vs.get('last_ingestion'))}
                    </div>
                </div>
                <div>
                    <div class="sm-label">Total enregistrements</div>
                    <div class="sm-value">{fmt_int(vs.get('total_rows'))}</div>
                    <div class="sm-sub">{fmt_int(vs.get('unique_stations'))} stations uniques</div>
                </div>
                <div>
                    <div class="sm-label">Dernière màj API</div>
                    <div class="sm-value" style="font-size:0.88rem">
                        {fmt_dt(vs.get('last_update'))}
                    </div>
                </div>
            </div>
        </div>

        <div class="status-card meteo">
            <div class="status-card-header">
                <div class="status-card-name">🌤 Météo - Paris</div>
                <div class="status-dot {freshness_dot(ms.get('last_ingestion'))}"></div>
            </div>
            <div class="status-metrics">
                <div>
                    <div class="sm-label">Dernière collecte</div>
                    <div class="sm-value" style="font-size:0.88rem">
                        {fmt_dt(ms.get('last_ingestion'))}
                    </div>
                </div>
                <div>
                    <div class="sm-label">Total mesures</div>
                    <div class="sm-value">{fmt_int(ms.get('total_rows'))}</div>
                </div>
                <div>
                    <div class="sm-label">Dernière mesure</div>
                    <div class="sm-value" style="font-size:0.88rem">
                        {fmt_dt(ms.get('last_measure'))}
                    </div>
                </div>
            </div>
        </div>

    </div>
    """)


# ─── Section Bronze ───────────────────────────────────────────────────────────

st.html('<div class="section-title">Couche Bronze - Données brutes</div>')

# ── Vélib bronze ──
v_stats, v_stats_err = api_get("/api/bronze/velib/stats")
v_preview, v_preview_err = api_get("/api/bronze/velib/preview?limit=10")

if v_stats_err:
    st.html(f'<div class="error-box">⚠️ {v_stats_err}</div>')
else:
    st.html(f"""
    <div class="layer-card">
        <div class="layer-card-header">
            <span class="layer-badge bronze">Bronze</span>
            <div>
                <div class="layer-name">bronze.velib_stations</div>
                <div class="layer-desc">
                    Snapshots bruts des stations · collecte toutes les 10 min · déduplication sur (stationcode, duedate)
                </div>
            </div>
        </div>
        <div class="mini-stats">
            <div class="mini-stat">
                <div class="ms-label">Lignes totales</div>
                <div class="ms-value">{fmt_int((v_stats or {}).get('total_rows'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Stations uniques</div>
                <div class="ms-value">{fmt_int((v_stats or {}).get('unique_stations'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Première mesure</div>
                <div class="ms-value sm">{fmt_dt((v_stats or {}).get('earliest_measure'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Dernière mesure</div>
                <div class="ms-value sm">{fmt_dt((v_stats or {}).get('latest_measure'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Première collecte</div>
                <div class="ms-value sm">{fmt_dt((v_stats or {}).get('earliest_ingestion'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Dernière collecte</div>
                <div class="ms-value sm">{fmt_dt((v_stats or {}).get('latest_ingestion'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Vélos dispo moy.</div>
                <div class="ms-value">{fmt_float((v_stats or {}).get('avg_bikes_available'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Capacité moy.</div>
                <div class="ms-value">{fmt_float((v_stats or {}).get('avg_capacity'))}</div>
            </div>
        </div>
        <div class="preview-label">Aperçu · 10 derniers enregistrements</div>
    </div>
    """)

    if v_preview_err:
        st.html(f'<div class="error-box">⚠️ {v_preview_err}</div>')
    elif v_preview:
        st.dataframe(pd.DataFrame(v_preview), width="stretch", hide_index=True)
    else:
        st.html('<div class="empty-state"><div class="empty-icon">📭</div>Aucune donnée</div>')

# ── Météo bronze ──
m_stats, m_stats_err = api_get("/api/bronze/meteo/stats")
m_preview, m_preview_err = api_get("/api/bronze/meteo/preview?limit=10")

if m_stats_err:
    st.html(f'<div class="error-box">⚠️ {m_stats_err}</div>')
else:
    st.html(f"""
    <div class="layer-card">
        <div class="layer-card-header">
            <span class="layer-badge bronze">Bronze</span>
            <div>
                <div class="layer-name">bronze.meteo_paris</div>
                <div class="layer-desc">
                    Mesures météo Open-Meteo · Paris (48.85°N, 2.35°E) · déduplication sur measured_at
                </div>
            </div>
        </div>
        <div class="mini-stats">
            <div class="mini-stat">
                <div class="ms-label">Mesures totales</div>
                <div class="ms-value">{fmt_int((m_stats or {}).get('total_rows'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Première mesure</div>
                <div class="ms-value sm">{fmt_dt((m_stats or {}).get('earliest_measure'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Dernière mesure</div>
                <div class="ms-value sm">{fmt_dt((m_stats or {}).get('latest_measure'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Première collecte</div>
                <div class="ms-value sm">{fmt_dt((m_stats or {}).get('earliest_ingestion'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Dernière collecte</div>
                <div class="ms-value sm">{fmt_dt((m_stats or {}).get('latest_ingestion'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Température moy.</div>
                <div class="ms-value">{fmt_float((m_stats or {}).get('avg_temperature'))} °C</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Humidité moy.</div>
                <div class="ms-value">{fmt_float((m_stats or {}).get('avg_humidity'))} %</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Vent moy.</div>
                <div class="ms-value">{fmt_float((m_stats or {}).get('avg_wind_speed'))} km/h</div>
            </div>
        </div>
        <div class="preview-label">Aperçu · 10 dernières mesures</div>
    </div>
    """)

    if m_preview_err:
        st.html(f'<div class="error-box">⚠️ {m_preview_err}</div>')
    elif m_preview:
        st.dataframe(pd.DataFrame(m_preview), width="stretch", hide_index=True)
    else:
        st.html('<div class="empty-state"><div class="empty-icon">📭</div>Aucune donnée</div>')


# ─── Section Gold ─────────────────────────────────────────────────────────────

st.html('<div style="height:4px"></div>')
st.html('<div class="section-title">Couche Gold - Données ML-ready</div>')

g_stats, g_stats_err = api_get("/api/gold/stats")
g_preview, g_preview_err = api_get("/api/gold/preview?limit=10")

if g_stats_err:
    st.html(f'<div class="error-box">⚠️ {g_stats_err}</div>')
else:
    st.html(f"""
    <div class="layer-card">
        <div class="layer-card-header">
            <span class="layer-badge gold">Gold</span>
            <div>
                <div class="layer-name">gold.fct_velib_meteo</div>
                <div class="layer-desc">
                    Table enrichie · jointure Vélib + Météo (±15 min) · features temporelles · taux d'occupation (target ML)
                </div>
            </div>
        </div>
        <div class="mini-stats">
            <div class="mini-stat">
                <div class="ms-label">Lignes totales</div>
                <div class="ms-value">{fmt_int((g_stats or {}).get('total_rows'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Stations</div>
                <div class="ms-value">{fmt_int((g_stats or {}).get('unique_stations'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Première entrée</div>
                <div class="ms-value sm">{fmt_dt((g_stats or {}).get('earliest_record'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Dernière entrée</div>
                <div class="ms-value sm">{fmt_dt((g_stats or {}).get('latest_record'))}</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Occupation moy.</div>
                <div class="ms-value">{fmt_float((g_stats or {}).get('avg_occupancy_rate'))} %</div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Min / Max occupation</div>
                <div class="ms-value sm">
                    {fmt_float((g_stats or {}).get('min_occupancy_rate'))} % /
                    {fmt_float((g_stats or {}).get('max_occupancy_rate'))} %
                </div>
            </div>
            <div class="mini-stat">
                <div class="ms-label">Température moy.</div>
                <div class="ms-value">{fmt_float((g_stats or {}).get('avg_temperature'))} °C</div>
            </div>
        </div>
        <div class="preview-label">Aperçu · 10 derniers enregistrements</div>
    </div>
    """)

    if g_preview_err:
        st.html(f'<div class="error-box">⚠️ {g_preview_err}</div>')
    elif g_preview:
        st.dataframe(pd.DataFrame(g_preview), width="stretch", hide_index=True)
    else:
        st.html("""
        <div class="empty-state">
            <div class="empty-icon">⭐</div>
            Aucune donnée - lancez <code>dbt run</code> pour alimenter la couche Gold
        </div>
        """)

    # ── Bouton de téléchargement CSV ──────────────────────────────────────────
    # Pattern deux étapes : on ne génère le CSV qu'au clic sur "Préparer",
    # jamais au rendu de la page. L'export complet de gold peut être lourd —
    # l'appeler à chaque rerender Streamlit laguerait l'interface inutilement.
    def _gold_csv() -> bytes:
        try:
            r = httpx.get(f"{API_BASE}/api/gold/export", timeout=1000.0)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return b""
        if not data:
            return b""
        return pd.DataFrame(data).to_csv(index=False).encode("utf-8")

    if (g_stats or {}).get("total_rows"):
        if st.button("⬇ Préparer le CSV Gold", key="prepare_csv"):
            with st.spinner("Export en cours…"):
                st.session_state["gold_csv"] = _gold_csv()
                st.session_state["gold_csv_ts"] = datetime.now(PARIS_TZ).strftime("%Y%m%d_%H%M")

        if "gold_csv" in st.session_state:
            st.download_button(
                label="⬇ Télécharger les données propres au format CSV",
                data=st.session_state["gold_csv"],
                file_name=f"gold_fct_velib_meteo_{st.session_state['gold_csv_ts']}.csv",
                mime="text/csv",
                key="dl_gold",
            )


# ─── Section Heatmap ─────────────────────────────────────────────────────────

st.html('<div style="height:4px"></div>')
st.html('<div class="section-title">Heatmap des stations Vélib</div>')

occ_data, occ_err = api_get("/api/stations/occupancy")

st.html("""
<div class="map-card">
    <div class="layer-card-header">
        <span class="layer-badge live">Live</span>
        <div>
            <div class="layer-name">Taux d'occupation par station</div>
            <div class="layer-desc">
                Dernière valeur connue · source : gold.fct_velib_meteo
            </div>
        </div>
    </div>
</div>
""")

if occ_err:
    st.html(f'<div class="error-box">⚠️ {occ_err}</div>')
elif not occ_data:
    st.html("""
    <div class="empty-state">
        <div class="empty-icon">🗺</div>
        Aucune donnée — lancez <code>dbt run</code> pour alimenter la couche Gold
    </div>
    """)
else:
    df_map = pd.DataFrame(occ_data).dropna(subset=["lat", "lon"])
    has_occ = "occupancy_rate" in df_map.columns and df_map["occupancy_rate"].notna().any()

    # Colonnes d'affichage dans le tooltip
    hover_data: dict = {
        "lat": False,
        "lon": False,
        "stationcode": True,
        "commune": True,
        "capacity": True,
    }
    if has_occ:
        hover_data["occupancy_rate"] = ":.1f"
        hover_data["bikes_available"] = True
        hover_data["docks_available"] = True

    fig_map = px.scatter_map(
        df_map,
        lat="lat",
        lon="lon",
        color="occupancy_rate" if has_occ else None,
        color_continuous_scale="RdYlGn",   # rouge = vide, vert = plein de vélos
        range_color=[0, 100],
        hover_name="station_name",
        hover_data=hover_data,
        map_style="open-street-map",
        zoom=12,
        center={"lat": 48.8566, "lon": 2.3522},
        height=520,
        labels={
            "occupancy_rate": "Occupation (%)",
            "bikes_available": "Vélos dispo",
            "docks_available": "Bornes libres",
            "capacity": "Capacité",
            "stationcode": "Code",
            "commune": "Commune",
        },
    )
    fig_map.update_traces(marker_size=9, marker_opacity=0.85)
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="Occupation (%)",
            ticksuffix=" %",
            len=0.7,
            thickness=14,
        ),
    )
    st.plotly_chart(fig_map, width="stretch", config={"scrollZoom": False, "displayModeBar": "hover"})
    st.html("""
    <div style="font-size:0.75rem;color:#94a3b8;margin-top:6px;padding:0 4px">
        🔴 <strong style="color:#64748b">Rouge</strong> = peu ou pas de vélos disponibles &nbsp;·&nbsp;
        🟢 <strong style="color:#64748b">Vert</strong> = beaucoup de vélos disponibles &nbsp;·&nbsp;
        Le taux affiché correspond à <code>vélos disponibles / capacité × 100</code>
        &nbsp;·&nbsp; Scroll pour zoomer
    </div>
    """)


# ─── Section Tendance Paris ──────────────────────────────────────────────────

st.html('<div style="height:4px"></div>')
st.html('<div class="section-title">Tendance globale Paris</div>')

CITY_PERIODS = {
    "Aujourd'hui": "today",
    "7 derniers jours": "7d",
    "30 derniers jours": "30d",
    "Choisir un mois": "month",
}

city_period_col, city_spacer = st.columns([2, 2])
with city_period_col:
    city_period_label = st.radio(
        "Période",
        list(CITY_PERIODS.keys()),
        horizontal=True,
        key="city_period_radio",
    )

city_period = CITY_PERIODS[city_period_label]

city_month_param: str | None = None
if city_period == "month":
    today = datetime.now(PARIS_TZ)
    cm1, cm2, _ = st.columns([1, 1, 2])
    with cm1:
        city_year = st.selectbox(
            "Année",
            list(range(2024, today.year + 1))[::-1],
            key="city_year",
        )
    with cm2:
        month_names = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ]
        city_month = st.selectbox(
            "Mois",
            list(range(1, 13)),
            format_func=lambda m: month_names[m - 1],
            index=today.month - 1,
            key="city_month",
        )
    city_month_param = f"{city_year}-{city_month:02d}"

city_trend_path = f"/api/city/trend?period={city_period}"
if city_month_param:
    city_trend_path += f"&month={city_month_param}"

city_trend, city_trend_err = api_get(city_trend_path)

if city_trend_err:
    st.html(f'<div class="error-box">⚠️ {city_trend_err}</div>')
elif not city_trend:
    st.html("""
    <div class="empty-state">
        <div class="empty-icon">📈</div>
        Aucune donnée gold sur cette période — lancez <code>dbt run</code>
    </div>
    """)
else:
    df_city = pd.DataFrame(city_trend)
    df_city["ts"] = pd.to_datetime(df_city["ts"])

    # Largeur des barres = intervalle médian entre points, en millisecondes.
    # Plotly interprète `width` en ms sur un axe datetime → barres toujours
    # pleines quel que soit l'étendue temporelle affichée.
    city_bar_ms = int(df_city["ts"].diff().median().total_seconds() * 1000) if len(df_city) > 1 else 3_600_000

    fig_city = go.Figure()

    # ── Précipitations en barres (arrière-plan visuel) ─────────────────────
    has_precip = "precipitation" in df_city.columns and df_city["precipitation"].notna().any()
    if has_precip:
        # Barres pleine hauteur (y=100 sur l'axe occupation 0-105) ; la couleur
        # encode l'intensité plutôt que la hauteur. Ajoutées en premier pour rester
        # derrière les lignes sans axe supplémentaire.
        precip_vals_city = df_city["precipitation"].fillna(0)
        fig_city.add_trace(go.Bar(
            x=df_city["ts"] - pd.Timedelta(minutes=7.5),
            y=[100] * len(df_city),
            name="Précipitations (mm)",
            marker_color=[precip_color(v) for v in precip_vals_city],
            marker_line_width=0,
            width=900_000,
            yaxis="y",
            customdata=precip_vals_city,
            hovertemplate="%{x|%d/%m %H:%M}<br>Précip. : %{customdata:.2f} mm<extra></extra>",
            text=[f"{v:.2f} mm" if v > 0 else "" for v in precip_vals_city],
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(size=9, color="rgba(3, 105, 161, 0.85)"),
        ))

    # ── Occupation moyenne Paris ───────────────────────────────────────────
    fig_city.add_trace(go.Scatter(
        x=df_city["ts"],
        y=df_city["avg_occupancy"],
        mode="lines",
        name="Occupation moy. Paris (%)",
        line=dict(color="#4f46e5", width=2),
        fill="tozeroy",
        fillcolor="rgba(79, 70, 229, 0.07)",
        yaxis="y",
        hovertemplate="%{x|%d/%m %H:%M}<br>Occupation : %{y:.1f} %<extra></extra>",
    ))

    # ── Température ───────────────────────────────────────────────────────
    has_temp = "temperature_2m" in df_city.columns and df_city["temperature_2m"].notna().any()
    if has_temp:
        fig_city.add_trace(go.Scatter(
            x=df_city["ts"],
            y=df_city["temperature_2m"],
            mode="lines",
            name="Température (°C)",
            line=dict(color="#f59e0b", width=1.5, dash="dot"),
            yaxis="y2",
            hovertemplate="%{x|%d/%m %H:%M}<br>Température : %{y:.1f} °C<extra></extra>",
        ))

    layout_city: dict = dict(
        height=380,
        margin=dict(l=0, r=60, t=10, b=0),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        hovermode="x unified",
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="system-ui, sans-serif", size=12, color="#475569"),
        yaxis=dict(
            title="Occupation moy. (%)",
            range=[0, 105],
            ticksuffix=" %",
            showgrid=True,
            gridcolor="#f1f5f9",
            showline=False,
        ),
        xaxis=dict(showgrid=False, showline=False),
    )
    if has_temp:
        layout_city["yaxis2"] = dict(
            title=dict(text="Température (°C)", font=dict(color="#f59e0b")),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color="#f59e0b"),
        )

    fig_city.update_layout(**layout_city)
    st.plotly_chart(fig_city, width="stretch", config={"displayModeBar": False})
    st.html("""
    <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;padding:0 4px">
        Occupation = moyenne de toutes les stations Vélib actives sur Paris ·
        Précipitations agrégées par heure depuis Open-Meteo
    </div>
    """)


# ─── Section Historique par station ──────────────────────────────────────────

st.html('<div style="height:4px"></div>')
st.html('<div class="section-title">Historique d\'une station</div>')

stations_list, stations_list_err = api_get("/api/stations/list")

if stations_list_err:
    st.html(f'<div class="error-box">⚠️ {stations_list_err}</div>')
elif not stations_list:
    st.html("""
    <div class="empty-state">
        <div class="empty-icon">📊</div>
        Aucune station disponible — lancez l'ingestion d'abord
    </div>
    """)
else:
    # Sélecteurs
    sorted_stations = sorted(stations_list, key=lambda s: s.get("capacity") or 0, reverse=True)
    options_map = {
        f"{s['station_name']} — {s.get('capacity', '?')} bornes": s["stationcode"]
        for s in sorted_stations
        if s.get("station_name")
    }

    PERIODS = {
        "Aujourd'hui": "today",
        "7 derniers jours": "7d",
        "30 derniers jours": "30d",
        "Choisir un mois": "month",
    }

    sel_col, period_col = st.columns([2, 2])
    with sel_col:
        selected_label = st.selectbox(
            "Station",
            list(options_map.keys()),
            key="station_select",
        )
    with period_col:
        period_label = st.radio(
            "Période",
            list(PERIODS.keys()),
            horizontal=True,
            key="period_radio",
        )

    selected_code = options_map[selected_label]
    period = PERIODS[period_label]

    month_param: str | None = None
    if period == "month":
        today = datetime.now(PARIS_TZ)
        m_col1, m_col2, _ = st.columns([1, 1, 2])
        with m_col1:
            year = st.selectbox(
                "Année",
                list(range(2024, today.year + 1))[::-1],
                key="hist_year",
            )
        with m_col2:
            month_names = [
                "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
            ]
            month_num = st.selectbox(
                "Mois",
                list(range(1, 13)),
                format_func=lambda m: month_names[m - 1],
                index=today.month - 1,
                key="hist_month",
            )
        month_param = f"{year}-{month_num:02d}"

    # Requête historique
    history_path = f"/api/station/{selected_code}/history?period={period}"
    if month_param:
        history_path += f"&month={month_param}"

    history, history_err = api_get(history_path)

    if history_err:
        st.html(f'<div class="error-box">⚠️ {history_err}</div>')
    elif not history:
        st.html("""
        <div class="empty-state">
            <div class="empty-icon">📭</div>
            Aucune donnée gold pour cette station sur cette période
            — lancez <code>dbt run</code> pour alimenter la couche Gold
        </div>
        """)
    else:
        df_hist = pd.DataFrame(history)
        df_hist["duedate"] = pd.to_datetime(df_hist["duedate"])
        # occupancy_rate est déjà en % (0–100) dans gold.fct_velib_meteo
        df_hist["occupancy_pct"] = df_hist["occupancy_rate"].round(1)

        # ── Métriques rapides ──────────────────────────────────────────────────
        avg_occ = df_hist["occupancy_pct"].mean()
        max_occ = df_hist["occupancy_pct"].max()
        min_occ = df_hist["occupancy_pct"].min()
        nb_points = len(df_hist)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Occupation moyenne", f"{avg_occ:.1f} %")
        m2.metric("Maximum", f"{max_occ:.1f} %")
        m3.metric("Minimum", f"{min_occ:.1f} %")
        m4.metric("Points de mesure", fmt_int(nb_points))

        st.html('<div style="height:16px"></div>')

        # ── Graphique principal : taux d'occupation ────────────────────────────
        fig_hist = go.Figure()

        fig_hist.add_trace(go.Scatter(
            x=df_hist["duedate"],
            y=df_hist["occupancy_pct"],
            mode="lines",
            name="Taux d'occupation (%)",
            line=dict(color="#4f46e5", width=2),
            fill="tozeroy",
            fillcolor="rgba(79, 70, 229, 0.08)",
            hovertemplate="%{x|%d/%m %H:%M}<br>Occupation : %{y:.1f} %<extra></extra>",
        ))

        has_precip_hist = "precipitation" in df_hist.columns and df_hist["precipitation"].notna().any()
        has_temp_hist = "temperature_2m" in df_hist.columns and df_hist["temperature_2m"].notna().any()

        hist_bar_ms = int(df_hist["duedate"].diff().median().total_seconds() * 1000) if len(df_hist) > 1 else 3_600_000

        # ── Précipitations en barres (arrière-plan) ────────────────────────
        if has_precip_hist:
            # Même logique que city : barres pleine hauteur, couleur = intensité.
            precip_vals_hist = df_hist["precipitation"].fillna(0)
            fig_hist.add_trace(go.Bar(
                x=df_hist["duedate"] - pd.Timedelta(minutes=7.5),
                y=[100] * len(df_hist),
                name="Précipitations (mm)",
                marker_color=[precip_color(v) for v in precip_vals_hist],
                marker_line_width=0,
                width=900_000,
                yaxis="y",
                customdata=precip_vals_hist,
                hovertemplate="%{x|%d/%m %H:%M}<br>Précip. : %{customdata:.2f} mm<extra></extra>",
                text=[f"{v:.1f} mm" if v > 0 else "" for v in precip_vals_hist],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(size=9, color="rgba(3, 105, 161, 0.85)"),
            ))

        # ── Température en axe secondaire ──────────────────────────────────
        if has_temp_hist:
            fig_hist.add_trace(go.Scatter(
                x=df_hist["duedate"],
                y=df_hist["temperature_2m"],
                mode="lines",
                name="Température (°C)",
                line=dict(color="#f59e0b", width=1.5, dash="dot"),
                yaxis="y2",
                hovertemplate="%{x|%d/%m %H:%M}<br>Température : %{y:.1f} °C<extra></extra>",
            ))

        layout_hist: dict = dict(
            height=380,
            margin=dict(l=0, r=60, t=10, b=0),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            hovermode="x unified",
            barmode="overlay",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
            ),
            font=dict(family="system-ui, sans-serif", size=12, color="#475569"),
            yaxis=dict(
                title="Taux d'occupation (%)",
                range=[0, 105],
                ticksuffix=" %",
                showgrid=True,
                gridcolor="#f1f5f9",
                showline=False,
            ),
            xaxis=dict(showgrid=False, showline=False),
        )
        if has_temp_hist:
            layout_hist["yaxis2"] = dict(
                title=dict(text="Température (°C)", font=dict(color="#f59e0b")),
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(color="#f59e0b"),
            )

        fig_hist.update_layout(**layout_hist)
        st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False})

st.html("</div>")  # .page-content
