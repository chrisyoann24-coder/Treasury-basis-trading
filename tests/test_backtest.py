import sys
import os
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from treasury_basis.strategy import calculate_zscore, generate_signals, calculate_pnl


def test_zscore_mean_is_zero():
    """Le z-score doit avoir une moyenne proche de 0 sur une longue série."""
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 500))
    zscore = calculate_zscore(series, window=60)
    assert abs(zscore.dropna().mean()) < 0.1


def test_zscore_std_is_one():
    """Le z-score doit avoir un écart-type proche de 1."""
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 500))
    zscore = calculate_zscore(series, window=60)
    assert abs(zscore.dropna().std() - 1.0) < 0.1


def test_signals_only_valid_values():
    """Les signaux ne doivent contenir que -1, 0 ou +1."""
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 200))
    zscore = calculate_zscore(series, window=60)
    signals = generate_signals(zscore)
    assert set(signals.unique()).issubset({-1, 0, 1})


def test_no_lookahead_bias():
    """
    Le P&L d'un jour ne doit pas utiliser le signal du même jour.
    On vérifie que calculate_pnl utilise bien shift(1) sur les signaux.
    """
    basis = pd.Series([0.0, 0.1, 0.2, 0.3, 0.4])
    signals = pd.Series([0, 1, 1, 1, 0])
    results = calculate_pnl(basis, signals, nominal=100, transaction_cost_bps=0)

    # Le premier jour de P&L doit être 0 car le signal précédent est 0
    assert results["pnl_daily"].iloc[1] == 0.0


def test_transaction_costs_reduce_pnl():
    """Ajouter des coûts de transaction doit réduire le P&L."""
    np.random.seed(42)
    # On crée une série avec des changements de position fréquents
    # pour s'assurer que les coûts de transaction s'appliquent
    basis = pd.Series(np.linspace(0, 1, 100))
    # Signal qui alterne pour forcer des changements de position
    signals = pd.Series([1, -1] * 50)

    pnl_sans_cout = calculate_pnl(
        basis, signals, nominal=1_000_000, transaction_cost_bps=0
    )["pnl_cumulative"].iloc[-1]

    pnl_avec_cout = calculate_pnl(
        basis, signals, nominal=1_000_000, transaction_cost_bps=5
    )["pnl_cumulative"].iloc[-1]

    assert pnl_sans_cout > pnl_avec_cout