import numpy as np


def price_bond_simple(face_value: float, coupon_rate: float,
                      yield_rate: float, periods: int) -> float:
    """
    Calcule le prix dirty d'une obligation à coupon fixe.

    Paramètres
    ----------
    face_value : float
        Valeur nominale (généralement 100).
    coupon_rate : float
        Taux de coupon annuel en décimal (ex: 0.04 pour 4%).
    yield_rate : float
        Rendement annuel du marché en décimal.
    periods : int
        Nombre de périodes semestrielles restantes.

    Retourne
    --------
    float
        Prix dirty de l'obligation pour 100 de nominal.
    """
    coupon = face_value * coupon_rate / 2
    y = yield_rate / 2

    pv_coupon = coupon * (1 - (1 + y) ** (-periods)) / y
    pv_face = face_value / (1 + y) ** periods

    dirty_price = pv_coupon + pv_face

    return dirty_price


def accrued_interest(face_value: float, coupon_rate: float,
                     days_since_coupon: int,
                     days_in_period: int = 182) -> float:
    """
    Calcule les intérêts courus selon la convention Actual/Actual.

    Paramètres
    ----------
    face_value : float
        Valeur nominale.
    coupon_rate : float
        Taux de coupon annuel en décimal.
    days_since_coupon : int
        Nombre de jours écoulés depuis le dernier coupon.
    days_in_period : int
        Nombre de jours dans la période de coupon (≈182 pour semestriel).

    Retourne
    --------
    float
        Intérêts courus pour 100 de nominal.
    """
    coupon_semestriel = face_value * coupon_rate / 2
    accrued_interest = coupon_semestriel * (days_since_coupon / days_in_period)
    return accrued_interest


def dv01(face_value: float, coupon_rate: float,
         yield_rate: float, periods: int) -> float:
    """
    Calcule le DV01 par choc numérique de ±1 point de base.

    Retourne
    --------
    float
        Variation de prix pour une hausse de 1bp du rendement.
        Valeur positive (convention : prix baisse quand taux monte).
    """
    bp = 0.0001

    price_up = price_bond_simple(face_value, coupon_rate, yield_rate + bp, periods)
    price_down = price_bond_simple(face_value, coupon_rate, yield_rate - bp, periods)
    dv01 = (price_down - price_up) / 2

    return dv01

def calcul_cf(coupon_rate: float, periods: int) -> float:
    """
    Calcule le facteur de conversion CME d'une obligation livrable.

    Le CF est le prix coté de l'obligation par dollar de nominal
    en supposant un rendement de 6% en capitalisation semestrielle,
    avec la maturité arrondie au trimestre le plus proche.

    Paramètres
    ----------
    coupon_rate : float
        Taux de coupon annuel en décimal (ex: 0.10 pour 10%).
    periods : int
        Nombre de périodes semestrielles restantes.

    Retourne
    --------
    float
        Facteur de conversion CME.
    """
    r = 0.06 / 2        # taux de référence CME : 3% par période semestrielle
    coupon = coupon_rate / 2  # coupon semestriel par dollar de nominal

    # Valeur actuelle des coupons
    pv_coupons = sum(coupon / (1 + r) ** i for i in range(1, periods + 1))

    # Valeur actuelle du nominal
    pv_face = 1 / (1 + r) ** periods

    return round(pv_coupons + pv_face, 4)