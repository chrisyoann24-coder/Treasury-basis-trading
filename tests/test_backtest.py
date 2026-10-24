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


def test_sharpe_positive_for_profitable_strategy():
    """Une stratégie profitable doit avoir un Sharpe positif."""
    from treasury_basis.risk import sharpe_ratio
    pnl = pd.Series([100, 200, 150, 300, 250, 400])
    assert sharpe_ratio(pnl) > 0


def test_max_drawdown_is_negative():
    """Le maximum drawdown doit toujours être négatif ou nul."""
    from treasury_basis.risk import max_drawdown
    pnl_cumulative = pd.Series([0, 100, 200, 150, 100, 250])
    assert max_drawdown(pnl_cumulative) <= 0


def test_win_rate_between_zero_and_one():
    """Le win rate doit être entre 0 et 1."""
    from treasury_basis.risk import win_rate
    pnl = pd.Series([100, -50, 200, -30, 150])
    wr = win_rate(pnl)
    assert 0 <= wr <= 1


def test_sensitivity_analysis_returns_dataframe():
    """L'analyse de sensibilité doit retourner un DataFrame non vide."""
    from treasury_basis.risk import sensitivity_analysis
    np.random.seed(42)
    basis = pd.Series(np.random.normal(0, 0.1, 500))
    result = sensitivity_analysis(
        basis,
        entry_thresholds=[2.0, 3.0],
        exit_thresholds=[0.5],
        nominal=1_000_000
    )
    assert len(result) > 0
    assert "sharpe_ratio" in result.columns