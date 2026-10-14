import pandas as pd
from pandas_datareader import data as web


def load_fred_data(start: str = "2016-01-01", end: str = "2024-01-01") -> pd.DataFrame:
    """
    Télécharge DGS10, SOFR et EFFR depuis FRED.
    Construit un taux de financement composite :
    - EFFR avant avril 2018 (le SOFR n'existait pas)
    - SOFR à partir d'avril 2018

    Paramètres
    ----------
    start : str
        Date de début au format YYYY-MM-DD.
    end : str
        Date de fin au format YYYY-MM-DD.

    Retourne
    --------
    pd.DataFrame
        Colonnes : yield_10y (%), sofr (%), effr (%), financing_rate (%)
        Index : DatetimeIndex (jours ouvrés)
    """
    treasury_10y = web.DataReader("DGS10", "fred", start, end)
    sofr = web.DataReader("SOFR", "fred", start, end)
    effr = web.DataReader("EFFR", "fred", start, end)

    df = pd.concat(
        [
            treasury_10y.rename(columns={"DGS10": "yield_10y"}),
            sofr.rename(columns={"SOFR": "sofr"}),
            effr.rename(columns={"EFFR": "effr"}),
        ],
        axis=1,
    )

    df = df.sort_index()
    df = df.dropna(how="all")
    df = df.ffill()

    # Série composite : SOFR quand disponible, EFFR sinon
    # Le SOFR a été publié pour la première fois le 3 avril 2018
    df["financing_rate"] = df["sofr"].fillna(df["effr"])

    return df

