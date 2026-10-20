import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from treasury_basis.bond_pricing import price_bond_simple, accrued_interest, dv01


def test_at_par():
    """Quand coupon = yield, le prix doit être exactement 100."""
    price = price_bond_simple(100, 0.04, 0.04, 20)
    assert abs(price - 100.0) < 0.0001


def test_price_increases_when_yield_falls():
    """Le prix doit augmenter quand le rendement baisse."""
    price_low = price_bond_simple(100, 0.04, 0.03, 20)
    price_high = price_bond_simple(100, 0.04, 0.05, 20)
    assert price_low > price_high


def test_accrued_interest_zero_at_coupon_date():
    """Les intérêts courus sont nuls juste après un coupon."""
    ai = accrued_interest(100, 0.04, days_since_coupon=0)
    assert ai == 0.0


def test_accrued_interest_half_period():
    """À mi-période, les intérêts courus doivent être la moitié du coupon semestriel."""
    ai = accrued_interest(100, 0.04, days_since_coupon=91, days_in_period=182)
    assert abs(ai - 1.0) < 0.01  # coupon semestriel = 2, moitié ≈ 1


def test_dv01_positive():
    """Le DV01 doit être positif (prix baisse quand taux monte)."""
    d = dv01(100, 0.04, 0.04, 20)
    assert d > 0


def test_calcul_cf_hull_example():
    """Reproduit l'exemple du cours : obligation 10% 20 ans, CF attendu 1.4623."""
    from treasury_basis.bond_pricing import calcul_cf
    cf = calcul_cf(coupon_rate=0.10, periods=40)
    assert abs(cf - 1.4623) < 0.001


def test_calcul_cf_at_par():
    """Une obligation avec un coupon de 6% doit avoir un CF proche de 1."""
    from treasury_basis.bond_pricing import calcul_cf
    cf = calcul_cf(coupon_rate=0.06, periods=20)
    assert abs(cf - 1.0) < 0.001