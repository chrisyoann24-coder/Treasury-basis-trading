import numpy as np
import pandas as pd

def sharpe_ratio(pnl_daily: pd.Series, risk_free_rate: float=0.0) -> float:
    """
    Calcule le Sharpe ratio annualisé.

    Paramètres
    ----------
    pnl_daily : pd.Series
        P&L journalier en dollars.
    risk_free_rate : float
        Taux sans risque annuel en décimal (défaut : 0).

    Retourne
    --------
    float
        Sharpe ratio annualisé.
    """

    #On considère uniquement les jours où on est en position
    pnl_actif = pnl_daily[pnl_daily != 0]

    if len(pnl_actif) == 0 or pnl_actif.std() == 0:
        return 0.0

    dail_rf = risk_free_rate / 252
    excess_return = pnl_actif.mean() - dail_rf
    return (excess_return / pnl_actif.std()) * np.sqrt(252)

def max_drawdown(pnl_cumulative: pd.Series) -> float:
    """
    Calcule le maximum drawdown en dollars.

    Paramètres
    ----------
    pnl_cumulative : pd.Series
        P&L cumulé en dollars.

    Retourne
    --------
    float
        Maximum drawdown en dollars (valeur négative).
    """
    rolling_max = pnl_cumulative.cummax()
    drawdown = pnl_cumulative - rolling_max
    return drawdown.min()

def calmar_ratio(pnl_daily: pd.Series, pnl_cumulative: pd.Series) -> float:
    """
    Calcule le Calmar ratio.

    Paramètres
    ----------
    pnl_daily : pd.Series
        P&L journalier en dollars.
    pnl_cumulative : pd.Series
        P&L cumulé en dollars.

    Retourne
    --------
    float
        Calmar ratio (rendement annualisé / |max drawdown|).
    """
    mdd = max_drawdown(pnl_cumulative)
    if mdd == 0:
        return 0.0

    # Rendement annualisé
    n_days = len(pnl_daily[pnl_daily != 0])
    if n_days == 0:
        return 0.0

    annual_pnl = pnl_daily.sum() * (252 / len(pnl_daily))
    return annual_pnl / abs(mdd)

def win_rate(pnl_daily: pd.Series) -> float:
    """
    Calcule le taux de jours profitables parmi les jours en position.

    Paramètres
    ----------
    pnl_daily : pd.Series
        P&L journalier en dollars.

    Retourne
    --------
    float
        Win rate entre 0 et 1.
    """
    pnl_actif = pnl_daily[pnl_daily != 0]
    if len(pnl_actif) == 0:
        return 0.0
    return (pnl_actif > 0).sum() / len(pnl_actif)

def performance_summary(
    pnl_daily: pd.Series,
    pnl_cumulative: pd.Series,
    signals: pd.Series,
    risk_free_rate: float = 0.0
) -> dict:
    """
    Calcule toutes les métriques de performance en une fois.

    Retourne
    --------
    dict
        Dictionnaire de toutes les métriques.
    """
    mdd = max_drawdown(pnl_cumulative)
    sr = sharpe_ratio(pnl_daily, risk_free_rate)
    cr = calmar_ratio(pnl_daily, pnl_cumulative)
    wr = win_rate(pnl_daily)

    n_trades = (signals.diff().abs() > 0).sum()
    jours_en_position = (signals != 0).sum()

    return {
        "pnl_total":         round(pnl_cumulative.iloc[-1], 2),
        "sharpe_ratio":      round(sr, 3),
        "max_drawdown":      round(mdd, 2),
        "calmar_ratio":      round(cr, 3),
        "win_rate":          round(wr, 3),
        "n_trades":          int(n_trades),
        "jours_en_position": int(jours_en_position),
    }


def sensitivity_analysis(
    basis: pd.Series,
    entry_thresholds: list,
    exit_thresholds: list,
    nominal: float = 1_000_000,
    transaction_cost_bps: float = 2.0,
    zscore_window: int = 60
) -> pd.DataFrame:
    """
    Analyse de sensibilité sur les seuils d'entrée et de sortie.

    Teste toutes les combinaisons de seuils et retourne
    les métriques de performance pour chacune.

    Paramètres
    ----------
    basis : pd.Series
        Série temporelle du gross basis.
    entry_thresholds : list
        Liste des seuils d'entrée à tester.
    exit_thresholds : list
        Liste des seuils de sortie à tester.
    nominal : float
        Nominal de la position en dollars.
    transaction_cost_bps : float
        Coûts de transaction en points de base.
    zscore_window : int
        Fenêtre du z-score glissant.

    Retourne
    --------
    pd.DataFrame
        DataFrame avec les métriques pour chaque combinaison.
    """
    from treasury_basis.strategy import calculate_zscore, generate_signals, calculate_pnl

    zscore = calculate_zscore(basis, window=zscore_window)
    resultats = []

    for entry in entry_thresholds:
        for exit_ in exit_thresholds:
            # On ignore les combinaisons où sortie > entrée
            if exit_ >= entry:
                continue

            signals = generate_signals(zscore, entry, exit_)
            pnl_df = calculate_pnl(basis, signals, nominal, transaction_cost_bps)

            metrics = performance_summary(
                pnl_df["pnl_daily"],
                pnl_df["pnl_cumulative"],
                signals
            )
            metrics["entry_threshold"] = entry
            metrics["exit_threshold"] = exit_
            resultats.append(metrics)

    return pd.DataFrame(resultats).sort_values("sharpe_ratio", ascending=False)


def stress_test(
    basis: pd.Series,
    signals: pd.Series,
    scenarios: dict,
    nominal: float = 1_000_000
) -> pd.DataFrame:
    """
    Simule l'impact d'un choc instantané sur un jour où
    la stratégie est effectivement en position.
    """
    from treasury_basis.strategy import calculate_pnl

    # Trouver les index des jours en position
    jours_en_position = signals[signals != 0].index

    if len(jours_en_position) == 0:
        return pd.DataFrame()

    # On applique le choc au milieu des jours en position
    choc_date = jours_en_position[len(jours_en_position) // 2]
    choc_idx = basis.index.get_loc(choc_date)
    signal_au_choc = signals.loc[choc_date]

    print(f"Choc appliqué le : {choc_date.date()}")
    print(f"Signal ce jour   : {signal_au_choc} "
          f"({'short basis' if signal_au_choc == -1 else 'long basis'})")
    print()

    resultats = []

    for nom, choc in scenarios.items():
        # Choc instantané sur un seul jour en position
        basis_stresse = basis.copy()
        basis_stresse.iloc[choc_idx] += choc

        pnl_df = calculate_pnl(
            basis=basis_stresse,
            signals=signals,
            nominal=nominal,
            transaction_cost_bps=0
        )

        pnl_total = pnl_df["pnl_cumulative"].iloc[-1]
        mdd = max_drawdown(pnl_df["pnl_cumulative"])
        pnl_choc = pnl_df["pnl_daily"].iloc[choc_idx]

        resultats.append({
            "scenario":      nom,
            "choc_basis":    choc,
            "signal":        signal_au_choc,
            "pnl_jour_choc": round(pnl_choc, 2),
            "pnl_total":     round(pnl_total, 2),
            "max_drawdown":  round(mdd, 2)
        })

    return pd.DataFrame(resultats)

