"""Tests de caractérisation de app/logic/logic_preco.py (comportement actuel figé)."""
import datetime

import pandas as pd
import pytest

from app.logic import logic_preco
from app.logic.logic_preco import (
    calcul_indicateurs_preco,
    date_fin_trimestre,
    dernier_trimestre_termine,
    trimestre_courant,
)

D = datetime.datetime


# ---------------------------------------------------------------- dates pures
@pytest.mark.parametrize("annee,trim,attendu", [
    (2025, "T1", D(2025, 3, 31)),
    (2025, "T2", D(2025, 6, 30)),
    (2025, "T3", D(2025, 9, 30)),
    (2025, "T4", D(2025, 12, 31)),
    (2024, "T1", D(2024, 3, 31)),  # année bissextile : sans effet sur le 31/03
])
def test_date_fin_trimestre(annee, trim, attendu):
    assert date_fin_trimestre(annee, trim) == attendu


def test_date_fin_trimestre_trimestre_inconnu():
    with pytest.raises(KeyError):
        date_fin_trimestre(2025, "T5")


@pytest.mark.parametrize("dt,attendu", [
    (D(2025, 1, 1), (2025, "T1")),
    (D(2025, 3, 31), (2025, "T1")),
    (D(2025, 4, 1), (2025, "T2")),
    (D(2025, 6, 30), (2025, "T2")),
    (D(2025, 7, 1), (2025, "T3")),
    (D(2025, 9, 30), (2025, "T3")),
    (D(2025, 10, 1), (2025, "T4")),
    (D(2025, 12, 31), (2025, "T4")),
])
def test_trimestre_courant_bornes(dt, attendu):
    assert trimestre_courant(dt) == attendu


@pytest.mark.parametrize("dt,attendu", [
    (D(2025, 1, 1), (2024, "T4")),   # passage d'année
    (D(2025, 3, 31), (2024, "T4")),
    (D(2025, 4, 1), (2025, "T1")),
    (D(2025, 6, 30), (2025, "T1")),
    (D(2025, 7, 1), (2025, "T2")),
    (D(2025, 8, 8), (2025, "T2")),   # exemple de la docstring
    (D(2025, 9, 30), (2025, "T2")),
    (D(2025, 10, 1), (2025, "T3")),
    (D(2025, 12, 31), (2025, "T3")),
])
def test_dernier_trimestre_termine_bornes(dt, attendu):
    assert dernier_trimestre_termine(dt) == attendu


def test_dates_acceptent_un_objet_date():
    # datetime.date possède .month/.year : comportement identique
    assert trimestre_courant(datetime.date(2026, 2, 1)) == (2026, "T1")
    assert dernier_trimestre_termine(datetime.date(2026, 2, 1)) == (2025, "T4")


# ------------------------------------------------- calcul_indicateurs_preco
COLS = ["Infrapôle", "Urgence", "Statut", "Statut échéance", "Echéance", "Enjeu sécurité",
        "Désignation ZP ouvrage"]
AUJ = "Aujourd'hui"


def _ligne(ip, urg, statut, ech, enjeu="Non", zp=None):
    return [ip, urg, statut, "", ech, enjeu, zp]


@pytest.fixture
def fige_termine(monkeypatch):
    """Dernier trimestre terminé figé à T3 2026 (jamais la vraie date du jour)."""
    monkeypatch.setattr(logic_preco, "dernier_trimestre_termine", lambda dt=None: (2026, "T3"))


@pytest.fixture
def df_nominal():
    lignes = [
        _ligne("A", "U0", "En cours", "01/01/2026", zp="ZP1"),
        _ligne("A", "U0", "Demande ADR", "15/06/2026", zp="ZP1"),
        _ligne("A", "U0", "Levée", "01/01/2026", zp="ZP1"),            # statut exclu
        _ligne("A", "U0", "En attente ADR", "01/03/2027", zp="ZP1"),   # non échue
        _ligne("A", "U1", "En attente de validation", "30/09/2026", "Oui", zp="ZP1"),
        _ligne("A", "U1", "En cours", "01/01/2026", "Non", zp="ZP2"),  # enjeu non : ignorée
        _ligne("A", "U1", "En cours", "31/12/2026", "Oui", zp="ZP2"),  # borne incluse
        _ligne("A", "U1", "En cours", "01/01/2027", "Oui", zp="ZP2"),  # non échue
        _ligne("B", "U0", "Annulée", "01/01/2026"),
        _ligne("B", "U1", "Mise en place", "01/01/2026", "Oui"),
    ]
    return pd.DataFrame(lignes, columns=COLS)


def test_preco_nominal_t4(df_nominal, fige_termine):
    res = calcul_indicateurs_preco(df_nominal, "T4", 2026)
    assert list(res.columns) == [
        "Infrapôle", "ZP",
        "U0 Nombre total de préconisations", "U0 Préconisations échues",
        "U0 Analyse de risque - demandées ou en cours",
        "U1 Nombre total de préconisations", "U1 Préconisations échues",
        "U1 Analyse de risque - demandées ou en cours"]
    a = res[res["Infrapôle"] == "A"].iloc[0]
    # U0 : total = 3 (hors Levée) ; échues = 2 ; risque (Demande ADR échue) = 1
    # U1 (enjeu Oui) : total = 3 ; échues = 2 (30/09 et 31/12) ; risque = 1
    assert [a.iloc[i] for i in range(2, 8)] == [3, 2, 1, 3, 2, 1]
    assert a["ZP"] == "ZP1"  # mode : ZP1 x5 contre ZP2 x3
    b = res[res["Infrapôle"] == "B"].iloc[0]
    assert [b.iloc[i] for i in range(2, 8)] == [0, 0, 0, 0, 0, 0]
    assert b["ZP"] == ""  # colonne ZP entièrement vide


def test_preco_t3_egal_dernier_termine_n_est_pas_passe(df_nominal, fige_termine):
    # T3 2026 == dernier trimestre terminé : comparaison stricte => mode normal
    res = calcul_indicateurs_preco(df_nominal, "T3", 2026)
    assert "U0 Nombre total de préconisations" in res.columns
    a = res[res["Infrapôle"] == "A"].iloc[0]
    # échéance <= 30/09/2026 : U0 -> lignes 1 et 2 ; U1 Oui -> ligne 5 (30/09 inclus)
    assert a["U0 Préconisations échues"] == 2
    assert a["U1 Préconisations échues"] == 1
    assert a["U1 Analyse de risque - demandées ou en cours"] == 1


def test_preco_zp_colonne_avec_retour_ligne(fige_termine):
    df = pd.DataFrame([_ligne("A", "U0", "En cours", "01/01/2026", zp="ZPX")],
                      columns=COLS[:-1] + ["Désignation ZP\nouvrage"])
    res = calcul_indicateurs_preco(df, "T4", 2026)
    assert res.iloc[0]["ZP"] == "ZPX"


def test_preco_sans_colonne_zp(fige_termine):
    df = pd.DataFrame([_ligne("A", "U0", "En cours", "01/01/2026")], columns=COLS)
    df = df.drop(columns=["Désignation ZP ouvrage"])
    res = calcul_indicateurs_preco(df, "T4", 2026)
    assert res.iloc[0]["ZP"] == ""
    assert res.iloc[0]["U0 Nombre total de préconisations"] == 1


def test_preco_aujourdhui():
    # Echéances très anciennes / très lointaines : indépendant de la date du jour
    lignes = [
        _ligne("A", "U0", "En cours", "01/01/2000"),            # échue
        _ligne("A", "U0", "Demande ADR", "01/01/2000"),         # échue + risque
        _ligne("A", "U0", "En cours", "01/01/2999"),            # non échue
        _ligne("A", "U1", "En attente ADR", "01/01/2000", "Oui"),
        _ligne("A", "U1", "En cours", "01/01/2999", "Oui"),
    ]
    df = pd.DataFrame(lignes, columns=COLS)
    a = calcul_indicateurs_preco(df, AUJ).iloc[0]
    assert [a.iloc[i] for i in range(2, 8)] == [3, 2, 1, 2, 1, 1]


def test_preco_trimestre_passe(fige_termine):
    cols = COLS + ["Date de la première préconisation", "Date de levée"]

    def ligne(statut, premiere, levee=None):
        return _ligne("A", "U0", statut, "01/01/2026") + [premiere, levee]

    df = pd.DataFrame([
        ligne("En cours", "01/02/2026"),                  # en cours à fin T1
        ligne("Levée", "15/03/2026", "10/05/2026"),       # statut exclu, sortie après T1
        ligne("En cours", "01/04/2026"),                  # préconisée après T1 : ignorée
        ligne("En cours", "31/03/2026", "01/04/2026"),    # borne incluse : en cours ET sortie après
        ligne("Levée", "01/01/2026", "20/03/2026"),       # sortie avant T1 : ignorée
    ], columns=cols)
    res = calcul_indicateurs_preco(df, "T1", 2026)
    assert list(res.columns) == [
        "Infrapôle", "ZP",
        "Préconisé avant T1-2026 toujours en cours",
        "Préconisé avant T1-2026 / traité ou annulé aprés T1-2026"]
    r = res.iloc[0]
    assert r.iloc[2] == 2  # lignes 1 et 4
    assert r.iloc[3] == 2  # lignes 2 et 4


@pytest.mark.parametrize("manquante", ["Infrapôle", "Urgence", "Statut", "Statut échéance",
                                       "Echéance", "Enjeu sécurité"])
def test_preco_colonne_critique_absente(manquante):
    df = pd.DataFrame([_ligne("A", "U0", "En cours", "01/01/2026")], columns=COLS)
    df = df.drop(columns=[manquante])
    with pytest.raises(ValueError, match=manquante):
        calcul_indicateurs_preco(df, "T4", 2026)


def test_preco_dataframe_vide(fige_termine):
    res = calcul_indicateurs_preco(pd.DataFrame(columns=COLS), "T4", 2026)
    assert res.empty
    assert len(res.columns) == 8
