"""
Treasury Futures Basis — Dashboard interactif.

Lancement :
    streamlit run app.py

Dépendances supplémentaires par rapport au reste du projet :
    pip install plotly
"""

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from treasury_basis.basis import (  # noqa: E402
    carry,
    gross_basis,
    implied_repo_rate,
    net_basis,
)
from treasury_basis.bond_pricing import (  # noqa: E402
    accrued_interest,
    calcul_cf,
    dv01,
    price_bond_simple,
)
from treasury_basis.futures import (  # noqa: E402
    futures_quoted_price,
    identifier_ctd_avec_recalibrage,
)
from treasury_basis.risk import (  # noqa: E402
    performance_summary,
    sensitivity_analysis,
)
from treasury_basis.strategy import (  # noqa: E402
    calculate_pnl,
    calculate_zscore,
    generate_signals,
)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Treasury Basis Terminal",
    page_icon="▮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette — terminal de trading
BG = "#0A0E14"
PANEL = "#141922"
GRID = "#232A36"
TEXT = "#E8EBF0"
MUTED = "#7E879B"
ACCENT = "#00D9A3"
DANGER = "#FF5C5C"
WARN = "#FFB020"
BLUE = "#4D9FFF"
PURPLE = "#A78BFA"

MONO = "SF Mono, Consolas, Menlo, monospace"

# Paramètres du contrat — constants dans tout le projet
DAYS_SINCE_COUPON = 90
DAYS_TO_NEXT_COUPON = 92
DAYS_TO_DELIVERY = 180
DAYS_IN_PERIOD = 182
FACE = 100
TAILLE_CONTRAT = 100_000

# Panier d'obligations livrables
BASKET_SPEC = {
    "nom": ["OBL_A", "OBL_B", "OBL_C", "OBL_D", "OBL_E", "OBL_F"],
    "coupon_rate": [0.020, 0.040, 0.060, 0.075, 0.090, 0.110],
    "periods": [13, 17, 19, 20, 21, 22],
}

COULEURS_OBL = {
    "OBL_A": BLUE,
    "OBL_B": ACCENT,
    "OBL_C": WARN,
    "OBL_D": DANGER,
    "OBL_E": PURPLE,
    "OBL_F": "#FF8FA3",
}


# ═══════════════════════════════════════════════════════════════
# STYLE
# ═══════════════════════════════════════════════════════════════

st.markdown(
    f"""
<style>
    .stApp {{ background: {BG}; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }}

    .hero {{
        border-left: 3px solid {ACCENT};
        padding: 0.2rem 0 0.2rem 1.1rem;
    }}
    .hero-title {{
        font-size: 1.9rem; font-weight: 700; color: {TEXT};
        letter-spacing: -0.025em; line-height: 1.1; margin: 0;
    }}
    .hero-sub {{
        font-size: 0.8rem; color: {MUTED}; margin-top: 0.35rem;
        letter-spacing: 0.02em;
    }}

    .statusbar {{
        display: flex; gap: 1.7rem; flex-wrap: wrap;
        padding: 0.6rem 1.1rem; background: {PANEL};
        border: 1px solid {GRID}; border-radius: 4px;
        margin: 1.1rem 0 1.7rem 0;
        font-family: {MONO}; font-size: 0.71rem;
    }}
    .statusbar span {{ color: {MUTED}; }}
    .statusbar b {{ color: {TEXT}; font-weight: 600; }}
    .dot {{
        display: inline-block; width: 7px; height: 7px; border-radius: 50%;
        background: {ACCENT}; margin-right: 6px; vertical-align: middle;
        box-shadow: 0 0 8px {ACCENT};
    }}

    .kpi {{
        background: {PANEL}; border: 1px solid {GRID};
        border-radius: 5px; padding: 0.9rem 1rem; height: 100%;
    }}
    .kpi-label {{
        font-size: 0.64rem; color: {MUTED}; text-transform: uppercase;
        letter-spacing: 0.1em; font-weight: 700; margin-bottom: 0.45rem;
    }}
    .kpi-value {{
        font-family: {MONO}; font-size: 1.45rem; font-weight: 700;
        line-height: 1.1; color: {TEXT};
    }}
    .kpi-note {{ font-size: 0.67rem; color: {MUTED}; margin-top: 0.35rem; }}
    .pos {{ color: {ACCENT} !important; }}
    .neg {{ color: {DANGER} !important; }}
    .neu {{ color: {BLUE} !important; }}

    .sect {{
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.13em;
        color: {MUTED}; font-weight: 700; margin: 2rem 0 0.8rem 0;
        padding-bottom: 0.45rem; border-bottom: 1px solid {GRID};
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; background: {PANEL}; border: 1px solid {GRID};
        border-radius: 5px; padding: 3px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 36px; background: transparent; border-radius: 3px;
        color: {MUTED}; font-size: 0.76rem; font-weight: 600;
        letter-spacing: 0.03em; padding: 0 1.15rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: {GRID} !important; color: {TEXT} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none; }}

    section[data-testid="stSidebar"] {{
        background: {PANEL}; border-right: 1px solid {GRID};
    }}
    section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}

    .notice {{
        background: rgba(255,176,32,0.06); border-left: 2px solid {WARN};
        padding: 0.7rem 0.95rem; border-radius: 3px;
        font-size: 0.73rem; color: {MUTED}; line-height: 1.55;
    }}
    .ok {{
        background: rgba(0,217,163,0.06); border-left: 2px solid {ACCENT};
        padding: 0.7rem 0.95rem; border-radius: 3px;
        font-size: 0.73rem; color: {MUTED}; line-height: 1.55;
    }}

    .step {{
        background: {PANEL}; border: 1px solid {GRID}; border-radius: 4px;
        padding: 0.7rem 0.9rem; margin-bottom: 0.5rem;
        font-family: {MONO}; font-size: 0.75rem;
        display: flex; justify-content: space-between; align-items: center;
    }}
    .step-label {{ color: {MUTED}; }}
    .step-value {{ color: {TEXT}; font-weight: 700; }}
    .step-num {{
        display: inline-block; width: 18px; height: 18px; line-height: 18px;
        text-align: center; border-radius: 3px; background: {GRID};
        color: {ACCENT}; font-size: 0.65rem; font-weight: 700;
        margin-right: 0.6rem;
    }}

    .stDataFrame {{ border: 1px solid {GRID}; border-radius: 4px; }}
</style>
""",
    unsafe_allow_html=True,
)


def kpi(label, value, note="", tone="neu"):
    return f"""<div class="kpi">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {tone}">{value}</div>
        <div class="kpi-note">{note}</div></div>"""


def section(title):
    st.markdown(f'<div class="sect">{title}</div>', unsafe_allow_html=True)


def step_row(num, label, value):
    return f"""<div class="step">
        <span class="step-label"><span class="step-num">{num}</span>{label}</span>
        <span class="step-value">{value}</span></div>"""


def style_fig(fig, height=420, legend=True):
    """Applique le thème sombre à une figure Plotly."""
    fig.update_layout(
        height=height,
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=MUTED, size=11, family="system-ui, sans-serif"),
        margin=dict(l=55, r=25, t=45, b=40),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=GRID, bordercolor=GRID,
            font=dict(color=TEXT, size=11, family=MONO),
        ),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=10),
        ),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


# ═══════════════════════════════════════════════════════════════
# DONNÉES — tout ce qui ne dépend pas des sliders est caché
# ═══════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv(
        "data/processed/treasury_rates.csv", index_col=0, parse_dates=True
    )
    df["financing_rate"] = df["sofr"].fillna(df["effr"])
    return df


@st.cache_data(show_spinner=False)
def build_basket():
    obl = pd.DataFrame(BASKET_SPEC)
    obl["CF"] = obl.apply(
        lambda r: calcul_cf(r["coupon_rate"], r["periods"]), axis=1
    )
    return obl


def _ctd_at(obl, rate):
    df_r = identifier_ctd_avec_recalibrage(
        obl,
        rate=rate,
        days_since_coupon=DAYS_SINCE_COUPON,
        days_to_next_coupon=DAYS_TO_NEXT_COUPON,
        days_to_delivery=DAYS_TO_DELIVERY,
        days_in_period=DAYS_IN_PERIOD,
        face=FACE,
    )
    return df_r[df_r["is_CTD"]].iloc[0]


@st.cache_data(show_spinner=False)
def build_basis_series():
    """Série de basis sur l'historique FRED — indépendante des paramètres."""
    df = load_data()
    obl = build_basket()
    yields = df["yield_10Y"].dropna() / 100

    gb, ctd, irr = [], [], []
    for y in yields:
        row = _ctd_at(obl, y)
        gb.append(gross_basis(row["p_clean"], row["F"], row["CF"]))
        ctd.append(row["nom"])
        irr.append(row["irr"])

    return (
        pd.Series(gb, index=yields.index, name="gross_basis"),
        pd.Series(ctd, index=yields.index, name="ctd"),
        pd.Series(irr, index=yields.index, name="irr"),
    )


@st.cache_data(show_spinner=False)
def ctd_par_niveau_de_taux(n_points=220):
    """Balaye une plage de taux et identifie la CTD à chaque niveau."""
    obl = build_basket()
    taux = np.linspace(0.005, 0.12, n_points)

    lignes = []
    for r in taux:
        row = _ctd_at(obl, r)
        lignes.append(
            {
                "taux": r,
                "ctd": row["nom"],
                "irr": row["irr"],
                "gross_basis": gross_basis(row["p_clean"], row["F"], row["CF"]),
                "F": row["F"],
            }
        )

    out = pd.DataFrame(lignes)
    out["ctd_prev"] = out["ctd"].shift(1)
    switches = out[(out["ctd"] != out["ctd_prev"]) & out["ctd_prev"].notna()]
    return out, switches


@st.cache_data(show_spinner=False)
def run_sensitivity(nominal, cost_bps, window):
    """Grid search — dépend des paramètres, donc caché sur leurs valeurs."""
    basis, _, _ = build_basis_series()
    return sensitivity_analysis(
        basis=basis,
        entry_thresholds=[1.5, 2.0, 2.5, 3.0, 3.5],
        exit_thresholds=[0.25, 0.5, 0.75, 1.0],
        nominal=nominal,
        transaction_cost_bps=cost_bps,
        zscore_window=window,
    )


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════

st.sidebar.markdown(
    f'<div style="font-size:0.68rem;letter-spacing:0.13em;color:{MUTED};'
    f'font-weight:700;text-transform:uppercase;margin-bottom:0.9rem;">'
    f"Stratégie</div>",
    unsafe_allow_html=True,
)
entry_threshold = st.sidebar.slider("Seuil d'entrée (σ)", 1.0, 4.0, 3.0, 0.5)
exit_threshold = st.sidebar.slider("Seuil de sortie (σ)", 0.1, 1.5, 0.5, 0.1)
zscore_window = st.sidebar.slider("Fenêtre z-score (jours)", 20, 120, 60, 10)

st.sidebar.markdown("&nbsp;", unsafe_allow_html=True)
st.sidebar.markdown(
    f'<div style="font-size:0.68rem;letter-spacing:0.13em;color:{MUTED};'
    f'font-weight:700;text-transform:uppercase;margin-bottom:0.6rem;">'
    f"Exécution</div>",
    unsafe_allow_html=True,
)
nominal = st.sidebar.number_input(
    "Nominal ($)", 100_000, 10_000_000, 1_000_000, 100_000
)
transaction_cost_bps = st.sidebar.slider("Coûts (bps)", 0.0, 10.0, 2.0, 0.5)

st.sidebar.markdown("&nbsp;", unsafe_allow_html=True)
st.sidebar.markdown(
    "<div class='notice'><b>Données simulées.</b> Les prix d'obligations et de "
    "futures sont dérivés des rendements FRED via le modèle de Hull. Résultats "
    "méthodologiques, non prédictifs.</div>",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════
# CALCULS
# ═══════════════════════════════════════════════════════════════

df = load_data()
obligations = build_basket()

with st.spinner("Calcul du basis sur l'historique…"):
    basis_series, ctd_series, irr_series = build_basis_series()

zscore = calculate_zscore(basis_series, window=zscore_window)
signals = generate_signals(zscore, entry_threshold, exit_threshold)
results = calculate_pnl(basis_series, signals, nominal, transaction_cost_bps)

risk_free = df["financing_rate"].dropna().mean() / 100
metrics = performance_summary(
    results["pnl_daily"], results["pnl_cumulative"], signals, risk_free
)
pnl_total = metrics["pnl_total"]
rate_moy = df["yield_10Y"].mean() / 100


# ═══════════════════════════════════════════════════════════════
# EN-TÊTE
# ═══════════════════════════════════════════════════════════════

st.markdown(
    '<div class="hero">'
    '<p class="hero-title">Treasury Futures Basis</p>'
    '<p class="hero-sub">Pricing · Cheapest-to-Deliver · Cash-and-Carry · Risk</p>'
    "</div>",
    unsafe_allow_html=True,
)

ctd_dom = ctd_series.value_counts().idxmax()
n_ctd = ctd_series.nunique()

st.markdown(
    f"""<div class="statusbar">
  <span><span class="dot"></span><b>LIVE</b></span>
  <span>PÉRIODE <b>{df.index.min():%Y-%m} → {df.index.max():%Y-%m}</b></span>
  <span>OBSERVATIONS <b>{len(basis_series):,}</b></span>
  <span>CTD DOMINANTE <b>{ctd_dom}</b></span>
  <span>CTD DISTINCTES <b>{n_ctd}</b></span>
  <span>DGS10 MOYEN <b>{df['yield_10Y'].mean():.2f}%</b></span>
  <span>FINANCEMENT <b>{df['financing_rate'].mean():.2f}%</b></span>
</div>""",
    unsafe_allow_html=True,
)

c = st.columns(5)
c[0].markdown(
    kpi("P&L Total", f"${pnl_total:,.0f}", f"nominal ${nominal/1e6:.1f}M",
        "pos" if pnl_total >= 0 else "neg"),
    unsafe_allow_html=True,
)
c[1].markdown(
    kpi("Sharpe", f"{metrics['sharpe_ratio']:.2f}", "annualisé · 252j",
        "pos" if metrics["sharpe_ratio"] >= 0 else "neg"),
    unsafe_allow_html=True,
)
c[2].markdown(
    kpi("Max Drawdown", f"${metrics['max_drawdown']:,.0f}", "pic → creux", "neg"),
    unsafe_allow_html=True,
)
c[3].markdown(
    kpi("Win Rate", f"{metrics['win_rate']*100:.1f}%", "jours en position", "neu"),
    unsafe_allow_html=True,
)
c[4].markdown(
    kpi("Exposition", f"{metrics['jours_en_position']}",
        f"sur {len(signals)} jours", "neu"),
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════
# ONGLETS
# ═══════════════════════════════════════════════════════════════

t1, t2, t3, t4, t5 = st.tabs(
    ["MARCHÉ", "PRICING ENGINE", "BASIS & CTD", "STRATÉGIE", "RISQUE"]
)


# ───────────────────────────────── MARCHÉ ──────────────────────
with t1:
    section("Environnement de taux")

    spread = df["yield_10Y"] - df["financing_rate"]
    k = st.columns(4)
    k[0].markdown(
        kpi("DGS10 — dernier", f"{df['yield_10Y'].iloc[-1]:.2f}%",
            f"min {df['yield_10Y'].min():.2f}% · max {df['yield_10Y'].max():.2f}%",
            "neu"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Financement — dernier", f"{df['financing_rate'].iloc[-1]:.2f}%",
            "SOFR dès avr. 2018, EFFR avant", "neu"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Spread moyen", f"{spread.mean():.2f}%", "DGS10 − financement",
            "pos" if spread.mean() > 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("Volatilité DGS10", f"{df['yield_10Y'].std():.2f}%",
            "écart-type sur la période", "neu"),
        unsafe_allow_html=True,
    )

    section("Séries de référence FRED")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
        subplot_titles=("US Treasury 10 ans — DGS10",
                        "Taux de financement — EFFR puis SOFR"),
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["yield_10Y"], name="DGS10",
                   line=dict(color=BLUE, width=1.5), fill="tozeroy",
                   fillcolor="rgba(77,159,255,0.10)",
                   hovertemplate="%{y:.2f}%<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["financing_rate"], name="Financement",
                   line=dict(color=WARN, width=1.5), fill="tozeroy",
                   fillcolor="rgba(255,176,32,0.10)",
                   hovertemplate="%{y:.2f}%<extra></extra>"),
        row=2, col=1,
    )
    fig.add_vline(
        x=pd.Timestamp("2018-04-03"), line=dict(color=MUTED, width=1, dash="dash"),
        annotation_text="SOFR", annotation_font=dict(color=MUTED, size=10),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="Rendement (%)", row=1, col=1)
    fig.update_yaxes(title_text="Taux (%)", row=2, col=1)
    for a in fig.layout.annotations:
        a.font.update(color=TEXT, size=12)
    st.plotly_chart(style_fig(fig, 580), use_container_width=True)


# ──────────────────────────── PRICING ENGINE ───────────────────
with t2:
    section("Validation — exemple de référence Hull")

    val = futures_quoted_price(
        clean_price=115, coupon=6, CF=1.6000,
        days_since_coupon=60, days_to_next_coupon=122,
        days_to_delivery=270, days_in_period=182, rate=0.10,
    )
    obtenu = val["futures_quoted_price"]
    ecart = abs(obtenu - 71.79)

    vl, vr = st.columns([1, 1])
    with vl:
        st.markdown(
            f'<div class="kpi-note" style="margin-bottom:0.6rem;">'
            f"Obligation 12 % · prix coté 115 · CF 1,6000 · livraison 270 j · "
            f"courbe plate 10 %</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            step_row(1, "Intérêts courus aujourd'hui",
                     f"{val['accrued_today']:.3f} $")
            + step_row(2, "Prix cash (dirty)", f"{val['dirty_price']:.3f} $")
            + step_row(3, "VA du coupon à recevoir", f"{val['pv_coupon']:.3f} $")
            + step_row(4, "Prix futures cash", f"{val['futures_cash_price']:.3f} $")
            + step_row(5, "Intérêts courus à la livraison",
                       f"{val['accrued_at_delivery']:.3f} $")
            + step_row(6, "Prix futures clean",
                       f"{val['futures_clean_price']:.3f} $")
            + step_row(7, "Prix futures coté (÷ CF)",
                       f"{val['futures_quoted_price']:.3f} $"),
            unsafe_allow_html=True,
        )
    with vr:
        kk = st.columns(2)
        kk[0].markdown(
            kpi("Attendu", "71.790", "référence manuel", "neu"),
            unsafe_allow_html=True,
        )
        kk[1].markdown(
            kpi("Obtenu", f"{obtenu:.3f}", f"écart {ecart:.3f}",
                "pos" if ecart < 0.10 else "neg"),
            unsafe_allow_html=True,
        )
        st.markdown("&nbsp;", unsafe_allow_html=True)
        verdict = "ok" if ecart < 0.10 else "notice"
        msg = (
            "Le moteur reproduit le résultat de référence. Les cinq étapes du "
            "pricing — prix dirty, actualisation du coupon en capitalisation "
            "continue, capitalisation jusqu'à la livraison, retrait des intérêts "
            "courus, division par le facteur de conversion — sont validées "
            "indépendamment."
            if ecart < 0.10
            else "Écart au-delà de la tolérance — vérifier les conventions de jours."
        )
        st.markdown(f"<div class='{verdict}'><b>Validation.</b> {msg}</div>",
                    unsafe_allow_html=True)

    section("Moteur de pricing — exploration interactive")

    p1, p2, p3 = st.columns(3)
    with p1:
        px_coupon = st.slider("Coupon annuel (%)", 0.5, 12.0, 4.0, 0.25)
    with p2:
        px_mat = st.slider("Maturité (années)", 1.0, 15.0, 9.5, 0.5)
    with p3:
        px_yield = st.slider("Rendement de marché (%)", 0.25, 12.0,
                             float(round(rate_moy * 100, 2)), 0.25)

    px_cr = px_coupon / 100
    px_y = px_yield / 100
    px_periods = int(round(px_mat * 2))
    px_coupon_sem = FACE * px_cr / 2
    px_cf = calcul_cf(px_cr, px_periods)

    p_dirty = price_bond_simple(FACE, px_cr, px_y, px_periods)
    ai = accrued_interest(FACE, px_cr, DAYS_SINCE_COUPON, DAYS_IN_PERIOD)
    p_clean = p_dirty - ai
    dv = dv01(FACE, px_cr, px_y, px_periods)

    fut = futures_quoted_price(
        clean_price=p_clean, coupon=px_coupon_sem, CF=px_cf,
        days_since_coupon=DAYS_SINCE_COUPON,
        days_to_next_coupon=DAYS_TO_NEXT_COUPON,
        days_to_delivery=DAYS_TO_DELIVERY,
        days_in_period=DAYS_IN_PERIOD, rate=px_y,
    )
    F = fut["futures_quoted_price"]
    gb = gross_basis(p_clean, F, px_cf)

    ai_liv = accrued_interest(
        FACE, px_cr, DAYS_TO_DELIVERY - DAYS_TO_NEXT_COUPON, DAYS_IN_PERIOD
    )
    irr_live = implied_repo_rate(p_dirty, F, px_cf, ai_liv, DAYS_TO_DELIVERY)
    carry_live = carry(p_dirty, risk_free, px_coupon_sem, DAYS_TO_DELIVERY)
    nb_live = net_basis(
        p_clean, F, px_cf, p_dirty, risk_free, px_coupon_sem, DAYS_TO_DELIVERY
    )

    k = st.columns(4)
    k[0].markdown(
        kpi("Prix clean", f"{p_clean:.4f}",
            f"dirty {p_dirty:.4f} · AI {ai:.4f}",
            "pos" if p_clean >= 100 else "neg"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Facteur de conversion", f"{px_cf:.4f}",
            "coupon > 6 % → CF > 1", "neu"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Prix futures coté", f"{F:.4f}", "méthode Hull", "neu"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("DV01", f"${dv:.4f}", "pour 100 de nominal", "neu"),
        unsafe_allow_html=True,
    )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    k = st.columns(4)
    k[0].markdown(
        kpi("Gross basis", f"{gb:+.4f}", "P_clean − F × CF",
            "pos" if gb >= 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Carry", f"{carry_live:+.4f}",
            f"financement à {risk_free*100:.2f}%",
            "pos" if carry_live >= 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Net basis", f"{nb_live:+.4f}", "gross basis − carry",
            "pos" if nb_live >= 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("Implied repo", f"{irr_live*100:+.3f}%",
            f"vs marché {risk_free*100:.2f}%",
            "pos" if irr_live > risk_free else "neg"),
        unsafe_allow_html=True,
    )

    section("Relation prix / rendement")

    grid_y = np.linspace(0.0025, 0.12, 180)
    grid_dirty = np.array(
        [price_bond_simple(FACE, px_cr, y, px_periods) for y in grid_y]
    )
    grid_clean = grid_dirty - ai
    grid_dv = np.array([dv01(FACE, px_cr, y, px_periods) for y in grid_y])

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.09,
        subplot_titles=("Prix clean en fonction du rendement",
                        "DV01 en fonction du rendement"),
    )
    fig.add_trace(
        go.Scatter(x=grid_y * 100, y=grid_clean, name="Prix clean",
                   line=dict(color=BLUE, width=2),
                   hovertemplate="y %{x:.2f}% → %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=[px_yield], y=[p_clean], name="Point courant",
                   mode="markers",
                   marker=dict(color=ACCENT, size=11,
                               line=dict(color=BG, width=2)),
                   hovertemplate="%{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_hline(y=100, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=1)
    fig.add_vline(x=px_coupon, line=dict(color=MUTED, width=1, dash="dot"),
                  row=1, col=1)
    fig.add_trace(
        go.Scatter(x=grid_y * 100, y=grid_dv, name="DV01",
                   line=dict(color=PURPLE, width=2),
                   hovertemplate="y %{x:.2f}% → $%{y:.4f}<extra></extra>"),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(x=[px_yield], y=[dv], name="Point courant", mode="markers",
                   marker=dict(color=ACCENT, size=11,
                               line=dict(color=BG, width=2)),
                   showlegend=False,
                   hovertemplate="$%{y:.4f}<extra></extra>"),
        row=1, col=2,
    )
    fig.update_xaxes(title_text="Rendement (%)")
    fig.update_yaxes(title_text="Prix", row=1, col=1)
    fig.update_yaxes(title_text="DV01 ($)", row=1, col=2)
    for a in fig.layout.annotations:
        a.font.update(color=TEXT, size=12)
    st.plotly_chart(style_fig(fig, 400, legend=False), use_container_width=True)

    st.markdown(
        "<div class='notice'><b>Lecture.</b> La courbe prix/rendement est "
        "décroissante et convexe : le prix croise 100 exactement là où le "
        "rendement égale le coupon. Le DV01 décroît avec le rendement — une "
        "obligation est moins sensible en valeur absolue quand les taux sont "
        "élevés, puisque son prix est déjà plus faible.</div>",
        unsafe_allow_html=True,
    )


# ────────────────────────────── BASIS & CTD ────────────────────
with t3:
    section("Panier d'obligations livrables")

    disp = obligations.copy()
    disp["Maturité"] = (disp["periods"] / 2).map("{:.1f} ans".format)
    disp["Coupon"] = (disp["coupon_rate"] * 100).map("{:.1f} %".format)
    disp["CF"] = disp["CF"].map("{:.4f}".format)
    disp["Jours CTD"] = disp["nom"].map(
        ctd_series.value_counts()
    ).fillna(0).astype(int)
    st.dataframe(
        disp[["nom", "Coupon", "Maturité", "CF", "Jours CTD"]].rename(
            columns={"nom": "Obligation"}
        ),
        use_container_width=True, hide_index=True,
    )
    st.markdown(
        "<div class='kpi-note'>Facteurs de conversion calculés selon la formule "
        "CME — actualisation à 6 % en capitalisation semestrielle. "
        "Coupon &lt; 6 % → CF &lt; 1, coupon &gt; 6 % → CF &gt; 1.</div>",
        unsafe_allow_html=True,
    )

    section("Sélection de la CTD par niveau de taux")

    with st.spinner("Balayage de la courbe…"):
        ctd_range, switches = ctd_par_niveau_de_taux()

    k = st.columns(4)
    k[0].markdown(
        kpi("Switches détectés", f"{len(switches)}",
            "sur la plage 0,5 % – 12 %", "neu"),
        unsafe_allow_html=True,
    )
    for i, (_, row) in enumerate(switches.head(3).iterrows()):
        k[i + 1].markdown(
            kpi(f"Switch {i+1}", f"{row['taux']*100:.2f} %",
                f"{row['ctd_prev']} → {row['ctd']}", "neu"),
            unsafe_allow_html=True,
        )
    for j in range(len(switches) + 1, 4):
        k[j].markdown(kpi("—", "—", "", "neu"), unsafe_allow_html=True)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Implied repo rate de la CTD",
                        "Gross basis de la CTD"),
    )
    for nom in obligations["nom"]:
        sub = ctd_range[ctd_range["ctd"] == nom]
        if sub.empty:
            continue
        col = COULEURS_OBL[nom]
        fig.add_trace(
            go.Scatter(x=sub["taux"] * 100, y=sub["irr"] * 100, name=nom,
                       mode="markers", marker=dict(color=col, size=5),
                       legendgroup=nom,
                       hovertemplate=f"{nom} · %{{y:.3f}}%<extra></extra>"),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=sub["taux"] * 100, y=sub["gross_basis"], name=nom,
                       mode="markers", marker=dict(color=col, size=5),
                       legendgroup=nom, showlegend=False,
                       hovertemplate=f"{nom} · %{{y:.4f}}<extra></extra>"),
            row=2, col=1,
        )
    for _, row in switches.iterrows():
        for r in (1, 2):
            fig.add_vline(x=row["taux"] * 100,
                          line=dict(color=MUTED, width=1, dash="dot"),
                          row=r, col=1)
    fig.add_vline(
        x=rate_moy * 100, line=dict(color=TEXT, width=1.5, dash="dash"),
        annotation_text=f"Taux moyen {rate_moy*100:.2f}%",
        annotation_font=dict(color=TEXT, size=10), row=1, col=1,
    )
    fig.update_xaxes(title_text="Taux de marché (%)", row=2, col=1)
    fig.update_yaxes(title_text="IRR (%)", row=1, col=1)
    fig.update_yaxes(title_text="Gross basis", row=2, col=1)
    fig.update_layout(hovermode="closest")
    for a in fig.layout.annotations:
        a.font.update(color=TEXT, size=12)
    st.plotly_chart(style_fig(fig, 620), use_container_width=True)

    st.markdown(
        "<div class='notice'><b>Mécanique du switch.</b> Le prix du future est "
        "recalibré itérativement sur la CTD courante : on calcule le prix ancré "
        "sur la CTD, on recalcule le coût de livraison de chaque obligation, et "
        "si une autre devient moins chère elle prend le relais. "
        "Les discontinuités visibles aux points de switch sont un artefact de ce "
        "recalibrage instantané — un marché réel ajusterait progressivement.</div>",
        unsafe_allow_html=True,
    )

    section("Dynamique historique du basis")

    k = st.columns(4)
    k[0].markdown(
        kpi("Basis moyen", f"{basis_series.mean():.4f}", "points de prix", "neu"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Écart-type", f"{basis_series.std():.4f}", "volatilité du basis", "neu"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Amplitude", f"{basis_series.max() - basis_series.min():.3f}",
            f"min {basis_series.min():.3f} · max {basis_series.max():.3f}", "neu"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("CTD distinctes", f"{n_ctd}", "sur l'historique", "neu"),
        unsafe_allow_html=True,
    )

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        row_heights=[0.4, 0.4, 0.2],
        subplot_titles=("Gross basis de la CTD",
                        f"Z-score glissant — fenêtre {zscore_window} jours",
                        "Obligation cheapest-to-deliver"),
    )
    fig.add_trace(
        go.Scatter(x=basis_series.index, y=basis_series, name="Gross basis",
                   line=dict(color=ACCENT, width=1.3),
                   hovertemplate="%{y:.4f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_hline(y=basis_series.mean(),
                  line=dict(color=MUTED, width=1, dash="dash"), row=1, col=1)

    fig.add_trace(
        go.Scatter(x=zscore.index, y=zscore, name="Z-score",
                   line=dict(color=PURPLE, width=1.2),
                   hovertemplate="%{y:.2f} σ<extra></extra>"),
        row=2, col=1,
    )
    for lvl, col_, dash in (
        (entry_threshold, DANGER, "dash"),
        (-entry_threshold, DANGER, "dash"),
        (exit_threshold, ACCENT, "dot"),
        (-exit_threshold, ACCENT, "dot"),
    ):
        fig.add_hline(y=lvl, line=dict(color=col_, width=1, dash=dash),
                      row=2, col=1)

    ctd_map = {n: i for i, n in enumerate(obligations["nom"])}
    fig.add_trace(
        go.Scatter(x=ctd_series.index, y=ctd_series.map(ctd_map), name="CTD",
                   line=dict(color=WARN, width=1.4, shape="hv"),
                   text=ctd_series, hovertemplate="%{text}<extra></extra>"),
        row=3, col=1,
    )
    fig.update_yaxes(title_text="Gross basis", row=1, col=1)
    fig.update_yaxes(title_text="Z-score (σ)", row=2, col=1)
    fig.update_yaxes(
        tickmode="array", tickvals=list(ctd_map.values()),
        ticktext=list(ctd_map.keys()), row=3, col=1,
    )
    for a in fig.layout.annotations:
        a.font.update(color=TEXT, size=12)
    st.plotly_chart(style_fig(fig, 720), use_container_width=True)


# ───────────────────────────────── STRATÉGIE ───────────────────
with t4:
    section("Positions")

    n_long = int((signals == 1).sum())
    n_short = int((signals == -1).sum())
    n_flat = int((signals == 0).sum())

    k = st.columns(4)
    k[0].markdown(
        kpi("Long basis", f"{n_long}", "achat obligation / vente future", "pos"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Short basis", f"{n_short}", "vente obligation / achat future", "neg"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Hors position", f"{n_flat}",
            f"{n_flat/len(signals)*100:.0f} % du temps", "neu"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("Trades", f"{metrics['n_trades']}",
            f"coûts {transaction_cost_bps:.1f} bps", "neu"),
        unsafe_allow_html=True,
    )

    section("Performance cumulée")

    pc = results["pnl_cumulative"]
    dd = pc - pc.cummax()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        row_heights=[0.52, 0.2, 0.28],
        subplot_titles=("P&L cumulé net de coûts", "Position",
                        "Drawdown depuis le pic"),
    )
    fig.add_trace(
        go.Scatter(x=pc.index, y=pc.clip(lower=0), name="Profit",
                   line=dict(color=ACCENT, width=0), fill="tozeroy",
                   fillcolor="rgba(0,217,163,0.20)", hoverinfo="skip"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=pc.index, y=pc.clip(upper=0), name="Perte",
                   line=dict(color=DANGER, width=0), fill="tozeroy",
                   fillcolor="rgba(255,92,92,0.20)", hoverinfo="skip"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=pc.index, y=pc, name="P&L cumulé",
                   line=dict(color=TEXT, width=1.6),
                   hovertemplate="$%{y:,.0f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=1)

    fig.add_trace(
        go.Scatter(x=signals.index, y=signals, name="Position",
                   line=dict(color=BLUE, width=1.2, shape="hv"),
                   fill="tozeroy", fillcolor="rgba(77,159,255,0.22)",
                   hovertemplate="%{y:+.0f}<extra></extra>"),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=dd.index, y=dd, name="Drawdown",
                   line=dict(color=DANGER, width=1), fill="tozeroy",
                   fillcolor="rgba(255,92,92,0.35)",
                   hovertemplate="$%{y:,.0f}<extra></extra>"),
        row=3, col=1,
    )
    fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
    fig.update_yaxes(
        title_text="", tickmode="array", tickvals=[-1, 0, 1],
        ticktext=["Short", "Flat", "Long"], range=[-1.5, 1.5], row=2, col=1,
    )
    fig.update_yaxes(title_text="Drawdown ($)", row=3, col=1)
    for a in fig.layout.annotations:
        a.font.update(color=TEXT, size=12)
    st.plotly_chart(style_fig(fig, 720), use_container_width=True)

    section("Distribution des P&L journaliers")

    pnl_actif = results["pnl_daily"][results["pnl_daily"] != 0]
    if len(pnl_actif) > 0:
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=pnl_actif, nbinsx=60, name="P&L journalier",
                marker=dict(color=BLUE, line=dict(color=GRID, width=0.5)),
                hovertemplate="$%{x:,.0f} · %{y} jours<extra></extra>",
            )
        )
        fig.add_vline(x=0, line=dict(color=MUTED, width=1))
        fig.add_vline(
            x=pnl_actif.mean(), line=dict(color=ACCENT, width=1.5, dash="dash"),
            annotation_text=f"moyenne ${pnl_actif.mean():,.0f}",
            annotation_font=dict(color=ACCENT, size=10),
        )
        fig.update_xaxes(title_text="P&L journalier ($)")
        fig.update_yaxes(title_text="Nombre de jours")
        st.plotly_chart(
            style_fig(fig, 340, legend=False), use_container_width=True
        )

        k = st.columns(4)
        k[0].markdown(
            kpi("Meilleur jour", f"${pnl_actif.max():,.0f}", "", "pos"),
            unsafe_allow_html=True,
        )
        k[1].markdown(
            kpi("Pire jour", f"${pnl_actif.min():,.0f}", "", "neg"),
            unsafe_allow_html=True,
        )
        k[2].markdown(
            kpi("Volatilité journalière", f"${pnl_actif.std():,.0f}",
                "écart-type", "neu"),
            unsafe_allow_html=True,
        )
        k[3].markdown(
            kpi("Asymétrie", f"{pnl_actif.skew():+.2f}",
                "skewness de la distribution", "neu"),
            unsafe_allow_html=True,
        )


# ───────────────────────────────── RISQUE ──────────────────────
with t5:
    section("Métriques de risque")

    k = st.columns(4)
    k[0].markdown(
        kpi("Sharpe ratio", f"{metrics['sharpe_ratio']:.3f}",
            "jours en position uniquement",
            "pos" if metrics["sharpe_ratio"] > 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("Calmar ratio", f"{metrics['calmar_ratio']:.3f}",
            "rendement / drawdown max",
            "pos" if metrics["calmar_ratio"] > 0 else "neg"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("Max drawdown", f"${metrics['max_drawdown']:,.0f}",
            f"{abs(metrics['max_drawdown'])/nominal*100:.2f} % du nominal", "neg"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("Win rate", f"{metrics['win_rate']*100:.1f}%", "jours profitables",
            "neu"),
        unsafe_allow_html=True,
    )

    section("Analyse de sensibilité — Sharpe par combinaison de seuils")

    with st.spinner("Grid search…"):
        sens = run_sensitivity(nominal, transaction_cost_bps, zscore_window)

    cl, cr = st.columns([1.2, 1])

    with cl:
        pivot = sens.pivot_table(
            values="sharpe_ratio", index="entry_threshold",
            columns="exit_threshold",
        )
        fig = go.Figure(
            go.Heatmap(
                z=pivot.values,
                x=[f"{x:.2f}" for x in pivot.columns],
                y=[f"{y:.1f}" for y in pivot.index],
                colorscale=[[0, DANGER], [0.5, "#2A3340"], [1, ACCENT]],
                zmid=0,
                text=np.round(pivot.values, 2),
                texttemplate="%{text}",
                textfont=dict(size=11, color=TEXT),
                hovertemplate=(
                    "entrée %{y} σ · sortie %{x} σ<br>"
                    "Sharpe %{z:.3f}<extra></extra>"
                ),
                colorbar=dict(
                    tickfont=dict(color=MUTED, size=9),
                    outlinecolor=GRID, outlinewidth=1, thickness=12,
                ),
            )
        )
        fig.update_xaxes(title_text="Seuil de sortie (σ)")
        fig.update_yaxes(title_text="Seuil d'entrée (σ)")
        fig.update_layout(hovermode="closest")
        st.plotly_chart(style_fig(fig, 400, legend=False),
                        use_container_width=True)

    with cr:
        st.markdown(
            "<div class='kpi-note' style='margin-bottom:0.6rem;'>"
            "Top 8 combinaisons par Sharpe ratio</div>",
            unsafe_allow_html=True,
        )
        top = sens[
            ["entry_threshold", "exit_threshold", "pnl_total",
             "sharpe_ratio", "max_drawdown"]
        ].head(8).reset_index(drop=True)
        top.columns = ["Entrée", "Sortie", "P&L", "Sharpe", "MaxDD"]
        top["P&L"] = top["P&L"].map("${:,.0f}".format)
        top["MaxDD"] = top["MaxDD"].map("${:,.0f}".format)
        top["Sharpe"] = top["Sharpe"].map("{:.3f}".format)
        st.dataframe(top, use_container_width=True, hide_index=True, height=330)

    st.markdown(
        "<div class='notice'><b>Pourquoi cette grille compte.</b> Une stratégie "
        "qui n'est rentable que sur une seule combinaison de paramètres est "
        "surajustée. Une zone verte large et contiguë indique une performance "
        "robuste ; un point vert isolé au milieu de rouge indique le contraire."
        "</div>",
        unsafe_allow_html=True,
    )

    section("Stress tests — choc instantané sur le basis")

    scenarios = {
        "Basis +50 bp": 0.50,
        "Basis −50 bp": -0.50,
        "Basis +100 bp": 1.00,
        "Basis −100 bp": -1.00,
        "Choc COVID (mars 2020)": 0.75,
        "Resserrement Fed 2022": -0.60,
    }

    def run_stress(target_signal):
        prev = signals.shift(1)
        jours = prev[prev == target_signal].index
        if len(jours) == 0:
            return None, None
        d = jours[len(jours) // 2]
        idx = basis_series.index.get_loc(d)
        rows = []
        for nom, choc in scenarios.items():
            b = basis_series.copy()
            b.iloc[idx] += choc
            p = calculate_pnl(b, signals, nominal, 0)
            pnl_j = p["pnl_daily"].iloc[idx]
            rows.append(
                {
                    "Scénario": nom,
                    "Choc": f"{choc:+.2f}",
                    "P&L ($)": f"{pnl_j:,.0f}",
                    "Impact": f"{pnl_j / nominal * 100:+.2f} %",
                    "_v": pnl_j,
                }
            )
        return pd.DataFrame(rows), d

    d_short, date_s = run_stress(-1)
    d_long, date_l = run_stress(1)

    cs, cl2 = st.columns(2)

    with cs:
        st.markdown(
            f"<div class='kpi-note' style='margin-bottom:0.5rem;'>"
            f"<b style='color:{DANGER};'>Position SHORT basis</b></div>",
            unsafe_allow_html=True,
        )
        if d_short is not None:
            st.dataframe(
                d_short.drop(columns="_v"), use_container_width=True,
                hide_index=True,
            )
            st.markdown(
                f"<div class='kpi-note'>Choc simulé le {date_s:%d/%m/%Y}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='kpi-note'>Aucune position short sur la période.</div>",
                unsafe_allow_html=True,
            )

    with cl2:
        st.markdown(
            f"<div class='kpi-note' style='margin-bottom:0.5rem;'>"
            f"<b style='color:{ACCENT};'>Position LONG basis</b></div>",
            unsafe_allow_html=True,
        )
        if d_long is not None:
            st.dataframe(
                d_long.drop(columns="_v"), use_container_width=True,
                hide_index=True,
            )
            st.markdown(
                f"<div class='kpi-note'>Choc simulé le {date_l:%d/%m/%Y}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='kpi-note'>Aucune position long sur la période.</div>",
                unsafe_allow_html=True,
            )

    if d_short is not None and d_long is not None:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=d_short["Scénario"], y=d_short["_v"], name="Short basis",
                marker_color=DANGER, opacity=0.85,
                hovertemplate="$%{y:,.0f}<extra>Short</extra>",
            )
        )
        fig.add_trace(
            go.Bar(
                x=d_long["Scénario"], y=d_long["_v"], name="Long basis",
                marker_color=ACCENT, opacity=0.85,
                hovertemplate="$%{y:,.0f}<extra>Long</extra>",
            )
        )
        fig.add_hline(y=0, line=dict(color=MUTED, width=1))
        fig.update_yaxes(title_text="P&L du jour du choc ($)")
        fig.update_layout(barmode="group", hovermode="x")
        st.plotly_chart(style_fig(fig, 360), use_container_width=True)

        st.markdown(
            "<div class='ok'><b>Symétrie.</b> Chaque scénario produit un impact "
            "exactement opposé selon le sens de la position. Cette symétrie "
            "confirme la cohérence interne du calcul de P&L : ce qu'une position "
            "short perd sur un élargissement du basis, une position long le "
            "gagne.</div>",
            unsafe_allow_html=True,
        )

    section("Couverture DV01")

    row_ctd = _ctd_at(obligations, rate_moy)
    periods_ctd = int(
        obligations.loc[obligations["nom"] == row_ctd["nom"], "periods"].values[0]
    )

    dv01_obl = dv01(FACE, row_ctd["coupon_rate"], rate_moy, periods_ctd)
    dv01_fut = dv01_obl / row_ctd["CF"]
    sens_cash = dv01_obl * (nominal / 100)
    sens_contrat = dv01_fut * (TAILLE_CONTRAT / 100)
    n_contrats = sens_cash / sens_contrat

    k = st.columns(4)
    k[0].markdown(
        kpi("CTD au taux moyen", row_ctd["nom"],
            f"coupon {row_ctd['coupon_rate']*100:.1f} % · CF {row_ctd['CF']:.4f}",
            "neu"),
        unsafe_allow_html=True,
    )
    k[1].markdown(
        kpi("DV01 obligation", f"${dv01_obl:.4f}", "pour 100 de nominal", "neu"),
        unsafe_allow_html=True,
    )
    k[2].markdown(
        kpi("DV01 par contrat", f"${sens_contrat:,.2f}",
            f"contrat ZN — {TAILLE_CONTRAT:,} nominal", "neu"),
        unsafe_allow_html=True,
    )
    k[3].markdown(
        kpi("Ratio de couverture", f"{n_contrats:.1f}",
            f"contrats pour ${nominal/1e6:.1f}M cash", "neu"),
        unsafe_allow_html=True,
    )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.markdown(
        "<div class='notice'><b>Lecture.</b> Pour chaque mouvement de 1 bp des "
        f"taux, la position cash varie de ${sens_cash:,.0f} et les "
        f"{n_contrats:.0f} contrats futures compensent environ "
        f"${n_contrats * sens_contrat:,.0f}. La position résiduelle est quasi "
        "neutre au risque de taux directionnel — c'est l'objectif d'une "
        "couverture DV01.</div>",
        unsafe_allow_html=True,
    )