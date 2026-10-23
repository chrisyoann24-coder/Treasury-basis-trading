import numpy as np
import pandas as pd


def calculate_zscore(series: pd.Series, window: int = 60) -> pd.Series:
    """
    Calcule le z-score glissant d'une série temporelle.

    Paramètres
    ----------
    series : pd.Series
        Série temporelle du basis.
    window : int
        Fenêtre glissante en jours ouvrés (défaut : 60).

    Retourne
    --------
    pd.Series
        Z-score glissant.
    """
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    zscore = (series - rolling_mean) / rolling_std

    return zscore

def generate_signals(
        zscore: pd.Series,
        entry_threshold: float = 3.0,
        exit_threshold: float = 0.5
) -> pd.Series:
    """
    Génère les signaux de trading basés sur le z-score du basis.

    Signal :
    - +1 : acheter le basis (basis trop bas, z < -entry_threshold)
    - -1 : vendre le basis (basis trop élevé, z > +entry_threshold)
    -  0 : pas de position
    Acheter le basis c'est être long obligation et short Future; on souhaite que la valeur de l'obligation augmente relativement plus vite que celle du Future
    C'est notamment le cas lorsque la demande de collatéral de bonne qualité augmente pour les emprunts de cash sur le marché repo
    Etre short basis c'est l'inverse; ça arrive lorsque les investisseurs ne préfèrent pas immobiliser leur cash et préfèrent donc avoir de la liquidité


    Paramètres
    ----------
    zscore : pd.Series
        Z-score du basis.
    entry_threshold : float
        Seuil d'entrée en unités de z-score (défaut : 3.0).
    exit_threshold : float
        Seuil de sortie en unités de z-score (défaut : 0.5).

    Retourne
    --------
    pd.Series
        Série de signaux (-1, 0, +1).
    """
    position = pd.Series(0, index=zscore.index)
    current_position = 0

    for i in range(len(zscore)):
        z = zscore.iloc[i]

        #On gère les 59 premières valeurs de zscore qui ne pourront pas être calculées
        if np.isnan(z):
            position.iloc[i] = 0
            continue

        #Entrée en position
        if current_position == 0:
            if z > entry_threshold:
                current_position = -1 # Vendre le basis
            elif z < -entry_threshold:
                current_position = 1 # Acheter le basis

        elif current_position == -1:
            if abs(z) < exit_threshold:
                current_position = 0

        elif current_position == 1:
            if abs(z) > exit_threshold:
                current_position = 0

        position.iloc[i] = current_position

    return position

def calculate_pnl(
        basis: pd.Series,
        signals: pd.Series,
        nominal: float = 1_000_000,
        transaction_cost_bps: float = 2.0
) -> pd.DataFrame:
    """
    Calcule le P&L de la stratégie basis trading.

    Paramètres
    ----------
    basis : pd.Series
        Série temporelle du gross basis.
    signals : pd.Series
        Série des signaux de position (-1, 0, +1).
    nominal : float
        Nominal de la position en dollars (défaut : 1M).
    transaction_cost_bps : float
        Coût de transaction en points de base (défaut : 2bp).

    Retourne
    --------
    pd.DataFrame
        DataFrame avec basis, signal, pnl_daily, pnl_cumulative.
    """
    # Variation quotidienne du basis
    basis_change = basis.diff()

    #P&L brut : variation du basis x nominal x signal de la veille
    #On utilise le signal de la veille pour éviter le look-ahead bias
    pnl_brut = signals.shift(1) * basis_change * nominal / 100

    #Coûts de transaction : appliqué à chaque changement de position
    position_change = signals.diff().abs()
    transaction_costs = position_change * (transaction_cost_bps / 10000) * nominal

    #P&L net
    pnl_net = pnl_brut - transaction_costs

    #P&L cumulé
    pnl_cumulative = pnl_net.cumsum()

    return pd.DataFrame({
        "basis": basis,
        "signal": signals,
        "pnl_daily": pnl_net,
        "pnl_cumulative": pnl_cumulative
    })


