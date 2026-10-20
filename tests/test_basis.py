import sys
import os
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from treasury_basis.basis import gross_basis, carry, net_basis, implied_repo_rate
from treasury_basis.futures import futures_quoted_price, identifier_ctd


def test_gross_basis_formula():
    """Vérifie que gross basis = p_clean - F * CF."""
    gb = gross_basis(p_clean=100.25, F=110.20, CF=0.90)
    assert abs(gb - (100.25 - 110.20 * 0.90)) < 0.0001


def test_carry_positive_when_coupon_exceeds_financing():
    """Le carry est positif quand le coupon dépasse le coût de financement."""
    c = carry(p_dirty=100.0, financing_rate=0.02,
              coupon_received=2.0, holding_days=180)
    assert c > 0


def test_carry_negative_when_financing_exceeds_coupon():
    """Le carry est négatif quand le financement dépasse le coupon."""
    c = carry(p_dirty=100.0, financing_rate=0.08,
              coupon_received=2.0, holding_days=180)
    assert c < 0


def test_net_basis_less_than_gross_when_carry_positive():
    """Le net basis est inférieur au gross basis quand le carry est positif."""
    gb = gross_basis(100.25, 110.20, 0.90)
    nb = net_basis(100.25, 110.20, 0.90, 101.25, 0.02, 2.0, 180)
    assert nb < gb


def test_irr_increases_with_future_price():
    """L'IRR augmente quand le prix du future augmente."""
    irr_low = implied_repo_rate(100.0, 100.0, 0.90, 0.5, 90)
    irr_high = implied_repo_rate(100.0, 102.0, 0.90, 0.5, 90)
    assert irr_high > irr_low


def test_futures_price_hull_example():
    """Reproduit l'exemple du cours Hull — résultat attendu : 71.79."""
    result = futures_quoted_price(
        clean_price=115,
        coupon=6,
        CF=1.6000,
        days_since_coupon=60,
        days_to_next_coupon=122,
        days_to_delivery=270,
        days_in_period=182,
        rate=0.10
    )
    assert abs(result["futures_quoted_price"] - 71.79) < 0.10


def test_ctd_is_unique():
    """Une seule obligation est identifiée comme CTD."""
    obligations = pd.DataFrame({
        "nom":         ["OBL_A", "OBL_B", "OBL_C"],
        "coupon_rate": [0.020,   0.030,   0.040  ],
        "periods":     [13,      17,      20     ],
        "CF":          [0.832,   0.892,   0.940  ]
    })
    result = identifier_ctd(obligations, rate=0.023)
    assert result["is_CTD"].sum() == 1


def test_ctd_same_by_cost_and_irr():
    """
    La CTD identifiée par le coût de livraison minimal et celle
    identifiée par l'IRR maximal doivent être la même obligation.
    """
    obligations = pd.DataFrame({
        "nom":         ["OBL_A", "OBL_B", "OBL_C", "OBL_D", "OBL_E", "OBL_F"],
        "coupon_rate": [0.020,   0.025,   0.030,   0.035,   0.040,   0.045  ],
        "periods":     [13,      15,      17,      19,      20,      21     ],
        "CF":          [0.832,   0.862,   0.892,   0.921,   0.940,   0.958  ]
    })

    result = identifier_ctd(obligations, rate=0.023)

    # CTD par coût de livraison minimal
    ctd_par_cout = result.loc[
        result["cout_livraison"].idxmin(), "nom"
    ]

    # CTD par IRR maximal
    ctd_par_irr = result.loc[
        result["irr"].idxmax(), "nom"
    ]

    print(f"CTD par coût de livraison minimal : {ctd_par_cout}")
    print(f"CTD par IRR maximal               : {ctd_par_irr}")

    assert ctd_par_cout == ctd_par_irr, (
        f"Incohérence : coût minimal → {ctd_par_cout}, "
        f"IRR maximal → {ctd_par_irr}"
    )