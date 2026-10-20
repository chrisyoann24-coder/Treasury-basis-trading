import numpy as np
import pandas as pd
from treasury_basis.bond_pricing import price_bond_simple, accrued_interest


def _gross_basis(p_clean: float, F: float, CF: float) -> float:
    """Calcul interne du gross basis — évite l'import circulaire avec basis.py."""
    return p_clean - F * CF


def _implied_repo_rate(p_dirty: float, F: float, CF: float,
                       ai_delivery: float, days: int) -> float:
    """Calcul interne de l'IRR — évite l'import circulaire avec basis.py."""
    invoice_price = F * CF + ai_delivery
    return (invoice_price - p_dirty) / p_dirty * (360 / days)


def futures_quoted_price(
    clean_price: float,
    coupon: float,
    CF: float,
    days_since_coupon: int,
    days_to_next_coupon: int,
    days_to_delivery: int,
    days_in_period: int,
    rate: float
) -> dict:
    """
    Calcule le prix futures coté selon la méthode Hull
    (capitalisation continue, VA des coupons).

    Paramètres
    ----------
    clean_price : float
        Prix clean coté de l'obligation CTD aujourd'hui.
    coupon : float
        Montant du coupon semestriel.
    CF : float
        Facteur de conversion CME.
    days_since_coupon : int
        Jours écoulés depuis le dernier coupon.
    days_to_next_coupon : int
        Jours jusqu'au prochain coupon.
    days_to_delivery : int
        Jours jusqu'à la livraison du future.
    days_in_period : int
        Jours dans la période de coupon.
    rate : float
        Taux sans risque annuel en décimal (capitalisation continue).

    Retourne
    --------
    dict
        Étapes intermédiaires + prix futures coté final.
    """
    accrued_today = (days_since_coupon / days_in_period) * coupon
    dirty_price = clean_price + accrued_today

    t_coupon = days_to_next_coupon / 365
    pv_coupon = coupon * np.exp(-rate * t_coupon)

    T = days_to_delivery / 365
    futures_cash_price = (dirty_price - pv_coupon) * np.exp(rate * T)

    days_since_coupon_at_delivery = days_to_delivery - days_to_next_coupon
    days_next_period = 365 - days_in_period
    accrued_at_delivery = (days_since_coupon_at_delivery / days_next_period) * coupon

    futures_clean_price = futures_cash_price - accrued_at_delivery
    futures_quoted = futures_clean_price / CF

    return {
        "accrued_today": round(accrued_today, 3),
        "dirty_price": round(dirty_price, 3),
        "pv_coupon": round(pv_coupon, 3),
        "futures_cash_price": round(futures_cash_price, 3),
        "accrued_at_delivery": round(accrued_at_delivery, 3),
        "futures_clean_price": round(futures_clean_price, 3),
        "futures_quoted_price": round(futures_quoted, 3),
    }


def identifier_ctd(
    obligations: pd.DataFrame,
    rate: float,
    days_since_coupon: int = 90,
    days_to_next_coupon: int = 92,
    days_to_delivery: int = 180,
    days_in_period: int = 182,
    face: float = 100
) -> pd.DataFrame:
    """
    Calcule le prix, le gross basis et le coût de livraison de chaque
    obligation du panier et identifie la CTD comme celle qui minimise
    le coût de livraison : p_clean - F * CF.

    Paramètres
    ----------
    obligations : pd.DataFrame
        Colonnes requises : nom, coupon_rate, periods, CF.
    rate : float
        Taux de marché annuel en décimal.

    Retourne
    --------
    pd.DataFrame
        DataFrame enrichi avec colonnes p_clean, p_dirty, F,
        gross_basis, cout_livraison, irr, is_CTD.
    """
    resultats = []

    for _, obl in obligations.iterrows():
        p_dirty = price_bond_simple(
            face, obl["coupon_rate"], rate, obl["periods"]
        )
        ai = accrued_interest(
            face, obl["coupon_rate"], days_since_coupon, days_in_period
        )
        p_clean = p_dirty - ai

        coupon_sem = face * obl["coupon_rate"] / 2
        res_future = futures_quoted_price(
            clean_price=p_clean,
            coupon=coupon_sem,
            CF=obl["CF"],
            days_since_coupon=days_since_coupon,
            days_to_next_coupon=days_to_next_coupon,
            days_to_delivery=days_to_delivery,
            days_in_period=days_in_period,
            rate=rate
        )
        F = res_future["futures_quoted_price"]

        # Coût de livraison : prix coté - (prix de règlement × CF)
        cout_livraison = p_clean - F * obl["CF"]

        # Intérêts courus à la livraison pour l'IRR
        days_since_at_delivery = days_to_delivery - days_to_next_coupon
        ai_delivery = accrued_interest(
            face, obl["coupon_rate"],
            days_since_at_delivery,
            days_in_period
        )

        irr = _implied_repo_rate(
            p_dirty, F, obl["CF"], ai_delivery, days_to_delivery
        )

        resultats.append({
            "nom":           obl["nom"],
            "coupon_rate":   obl["coupon_rate"],
            "p_clean":       round(p_clean, 4),
            "p_dirty":       round(p_dirty, 4),
            "F":             round(F, 4),
            "cout_livraison": round(cout_livraison, 4),
            "irr":           round(irr, 4),
        })

    df_result = pd.DataFrame(resultats)

    # La CTD est celle qui minimise le coût de livraison
    idx_ctd = df_result["cout_livraison"].idxmin()
    df_result["is_CTD"] = False
    df_result.loc[idx_ctd, "is_CTD"] = True

    return df_result