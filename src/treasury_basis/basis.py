import numpy as np

def gross_basis(
        p_clean: float,
        F: float,
        CF: float
) -> float:
    """
    Calcule le gross basis.

    Paramètres
    ----------
    p_clean : Prix clean de l'obligation (float)
    F : Prix du future coté (float)
    CF : Facteur de conversion CME (float)

    Retourne
    --------
    Gross basis en points de prix (float)

    """
    gross_basis_value = p_clean - F * CF
    return gross_basis_value

def carry(
        p_dirty: float,
        financing_rate: float,
        coupon_received: float,
        holding_days: int
) -> float:
    """
    Calcule le coût de portage sur la période de détention

    Paramètres
    ----------
    p_dirty : Prix dirty de l'obligation (float)
    financing_rate : Taux de financement annuel en décimal (float)
    coupon_received : Coupons reçus pendant la période (float)
    holding_days : Nombre de jours de détention (int)

    Retourne
    --------
    Carry en points de prix (positif = favorable)

    """
    financing_cost = p_dirty * financing_rate * (holding_days / 360)
    carry_value = coupon_received - financing_cost

    return carry_value

def net_basis(
        p_clean: float,
        F: float,
        CF: float,
        p_dirty: float,
        financing_rate: float,
        coupon_received: float,
        holding_days: int
) -> float:
    """
    Calcule le net basis (gross basis moins le carry)
    """
    gb = gross_basis(p_clean, F, CF)
    c = carry(p_dirty, financing_rate, coupon_received, holding_days)
    net_basis_value = gb - c
    return net_basis_value


def implied_repo_rate(
        p_dirty: float,
        F: float,
        CF: float,
        ai_delivery: float,
        days: int
) -> float:
    """
    Calcule de l'implied repo rate (IRR)

    Paramètres
    ----------
    p_dirty : Prix dirty de l'obligation (float)
    F : Prix du future coté (float)
    CF : Facteur de conversion CME (float)
    ai_delivery: Intérêts courus à la date de livraison (float)
    days: Nombre de jours jusquà la livraison

    Retourne
    --------
    IRR annualisé en décimal (float)
    """

    invoice_price = F  * CF + ai_delivery
    IRR_value = (invoice_price - p_dirty) / p_dirty * (360 / days)

    return IRR_value

def test_ctd_recalibrage_is_unique():
    """Une seule obligation est identifiée comme CTD avec recalibrage."""
    obligations = pd.DataFrame({
        "nom":         ["OBL_A", "OBL_B", "OBL_C", "OBL_D", "OBL_E", "OBL_F"],
        "coupon_rate": [0.020,   0.040,   0.060,   0.075,   0.090,   0.110  ],
        "periods":     [13,      17,      19,      20,      21,      22     ],
    })
    from treasury_basis.bond_pricing import calcul_cf
    obligations["CF"] = obligations.apply(
        lambda row: calcul_cf(row["coupon_rate"], row["periods"]), axis=1
    )
    from treasury_basis.futures import identifier_ctd_avec_recalibrage
    result = identifier_ctd_avec_recalibrage(obligations, rate=0.023)
    assert result["is_CTD"].sum() == 1


def test_ctd_recalibrage_minimises_delivery_cost():
    """La CTD avec recalibrage minimise bien le coût de livraison."""
    obligations = pd.DataFrame({
        "nom":         ["OBL_A", "OBL_B", "OBL_C", "OBL_D", "OBL_E", "OBL_F"],
        "coupon_rate": [0.020,   0.040,   0.060,   0.075,   0.090,   0.110  ],
        "periods":     [13,      17,      19,      20,      21,      22     ],
    })
    from treasury_basis.bond_pricing import calcul_cf
    obligations["CF"] = obligations.apply(
        lambda row: calcul_cf(row["coupon_rate"], row["periods"]), axis=1
    )
    from treasury_basis.futures import identifier_ctd_avec_recalibrage
    result = identifier_ctd_avec_recalibrage(obligations, rate=0.023)
    ctd_cost = result.loc[result["is_CTD"], "cout_livraison"].values[0]
    assert ctd_cost == result["cout_livraison"].min()

