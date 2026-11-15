"""Tests de caractérisation de app/logic/logic_visite.py (indicateurs Visites cycliques).

Ils figent le comportement actuel ; valeurs attendues calculées à la main.
"""
import datetime

import pandas as pd
import pytest

from app.logic.logic_visite import (
    CATEGORIES_REFERENCE,
    INFRAPOLES_REFERENCE,
    calcul_indicateurs_visite,
)

ALP = "INFRAPOLE Alpes"
BRE = "INFRAPOLE Bretagne"
COLS = ["Infrapôle", "Catégorie", "Etat d'avancement", "Statut", "Date",
        "Année de programmation", "Date de réalisation", "Date validation",
        "Désignation ZP ouvrage"]


def _df(rows):
    return pd.DataFrame(rows, columns=COLS)


def _jeu():
    return _df([
        # Alpes / VA : 4 lignes, ZP majoritaire ZP1
        [ALP, "VA", "Réalisée", "PV validé", "10/01/2024", 2024, "15/02/2024", "20/02/2024", "ZP1"],
        [ALP, "VA", "Réalisée", "PV visé", "10/01/2024", 2024, "15/05/2024", "20/05/2024", "ZP1"],
        [ALP, "VA", "En cours", "En cours", "10/01/2024", 2024, None, None, "ZP2"],
        [ALP, "VA", "Réalisée", "PV validé", "10/01/2024", 2024, "01/03/2024", None, "ZP1"],
        # Alpes / VD : réalisée pile le 31/03 (borne T1 incluse)
        [ALP, "VD", "Réalisée", "CR visé", "05/06/2024", 2024, "31/03/2024", "31/03/2024", "ZPD"],
        # Annulée : exclue
        [ALP, "VP", "Annulée", "PV validé", "05/06/2024", 2024, "01/02/2024", "02/02/2024", "ZPX"],
        # Date 2023 / prog 2023 : hors année, exclue
        [ALP, "VP", "Réalisée", "PV validé", "05/06/2023", 2023, "01/02/2023", "02/02/2023", "ZPX"],
        # Date 2025 mais programmée 2024 : conservée (cond_B)
        [ALP, "VI", "En cours", "En cours", "15/01/2025", 2024, None, None, None],
        # Date 2024 mais programmée 2023 : exclue
        [ALP, "VP", "Réalisée", "PV validé", "05/06/2024", 2023, "01/02/2024", "02/02/2024", "ZPX"],
        # Bretagne / VA : programmée 2025, date 2024 : conservée (cond_A)
        [BRE, "VA", "Réalisée", "PV validé", "05/06/2024", 2025, "01/04/2024", "02/04/2024", "ZPB"],
    ])


def _ligne(res, infra, cat):
    sel = res[(res["Infrapôles"] == infra) & (res["Catégorie action"] == cat)]
    assert len(sel) == 1
    return sel.iloc[0]


def test_nominal_t1_pourcentages():
    res = calcul_indicateurs_visite(_jeu(), "T1", 2024)
    va = _ligne(res, ALP, "VA")
    # total 4 ; réalisées <= 31/03 : lignes 1 et 4 => 2 => 50.0 % ; PV validés : ligne 1 seule => 1/2
    assert va["Prévision 2024"] == "4"
    assert va["Réalisées à la fin du T1 2024"] == "2"
    assert va["Indicateur (Réalisation) en %"] == "50.0%"
    assert va["PV validés à la fin du T1 2024"] == "1"
    assert va["Indicateur (Validation) en %"] == "50.0%"
    assert va["ZP"] == "ZP1"


def test_nominal_t2_pourcentages():
    res = calcul_indicateurs_visite(_jeu(), "T2", 2024)
    va = _ligne(res, ALP, "VA")
    # réalisées <= 30/06 : 3/4 = 75.0 % ; PV validés : lignes 1 et 2 => 2/3 = 66.7 %
    assert va["Réalisées à la fin du T2 2024"] == "3"
    assert va["Indicateur (Réalisation) en %"] == "75.0%"
    assert va["PV validés à la fin du T2 2024"] == "2"
    assert va["Indicateur (Validation) en %"] == "66.7%"


def test_borne_trimestre_31_mars_incluse():
    res = calcul_indicateurs_visite(_jeu(), "T1", 2024)
    vd = _ligne(res, ALP, "VD")
    assert vd["Réalisées à la fin du T1 2024"] == "1"
    assert vd["Indicateur (Réalisation) en %"] == "100.0%"
    assert vd["Indicateur (Validation) en %"] == "100.0%"


def test_bretagne_realisee_apres_fin_t1():
    t1 = _ligne(calcul_indicateurs_visite(_jeu(), "T1", 2024), BRE, "VA")
    assert t1["Prévision 2024"] == "1"
    assert t1["Indicateur (Réalisation) en %"] == "0.0%"
    # nb_real = 0 => indicateur de validation 0.0 %
    assert t1["Indicateur (Validation) en %"] == "0.0%"
    t2 = _ligne(calcul_indicateurs_visite(_jeu(), "T2", 2024), BRE, "VA")
    assert t2["Indicateur (Réalisation) en %"] == "100.0%"
    assert t2["Indicateur (Validation) en %"] == "100.0%"


def test_filtre_annee_date_et_programmation():
    res = calcul_indicateurs_visite(_jeu(), "T1", 2024)
    vi = _ligne(res, ALP, "VI")  # Date 2025 mais programmée 2024 : conservée
    assert vi["Prévision 2024"] == "1"
    vp = _ligne(res, ALP, "VP")  # annulée, 2023 et prog 2023 : toutes exclues
    assert vp["Indicateur (Validation) en %"] == "Données manquantes"
    assert vp["Prévision 2024"] == ""


def test_grille_complete_et_donnees_manquantes():
    res = calcul_indicateurs_visite(_jeu(), "T1", 2024)
    assert len(res) == len(INFRAPOLES_REFERENCE) * len(CATEGORIES_REFERENCE)
    assert list(res.columns)[:3] == ["Infrapôles", "ZP", "Catégorie action"]
    assert res["Infrapôles"].iloc[0] == INFRAPOLES_REFERENCE[0]
    assert res["Catégorie action"].iloc[:4].tolist() == CATEGORIES_REFERENCE
    nord = _ligne(res, "INFRAPOLE Rhodanien", "VA")
    assert nord["Indicateur (Validation) en %"] == "Données manquantes"
    assert nord["Prévision 2024"] == ""


def test_dataframe_vide_avec_colonnes():
    res = calcul_indicateurs_visite(_df([]), "T1", 2024)
    assert len(res) == 112
    assert (res["Indicateur (Validation) en %"] == "Données manquantes").all()


def test_t5_fin_mars_annee_suivante():
    res = calcul_indicateurs_visite(_jeu(), "T5", 2024)
    assert "Réalisées à la fin du T5 2025" in res.columns
    va = _ligne(res, ALP, "VA")
    # limite 31/03/2025 : 3 réalisées sur 4
    assert va["Indicateur (Réalisation) en %"] == "75.0%"


def test_aujourdhui_libelle_et_valeurs():
    res = calcul_indicateurs_visite(_jeu(), "Aujourd'hui", 2024)
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    assert f"Réalisées à {today}" in res.columns
    assert _ligne(res, ALP, "VA")["Indicateur (Réalisation) en %"] == "75.0%"


def test_trimestre_inconnu_leve_keyerror():
    with pytest.raises(KeyError):
        calcul_indicateurs_visite(_jeu(), "T9", 2024)


@pytest.mark.parametrize("col", ["Infrapôle", "Catégorie", "Etat d'avancement", "Statut"])
def test_colonne_critique_absente(col):
    with pytest.raises(ValueError):
        calcul_indicateurs_visite(_jeu().drop(columns=[col]), "T1", 2024)


@pytest.mark.parametrize("col", ["Date de réalisation", "Date validation"])
def test_colonne_date_absente(col):
    with pytest.raises(ValueError):
        calcul_indicateurs_visite(_jeu().drop(columns=[col]), "T1", 2024)


def test_sans_colonnes_date_ni_programmation_pas_de_filtre_annee():
    df = _jeu().drop(columns=["Date", "Année de programmation"])
    res = calcul_indicateurs_visite(df, "T1", 2024)
    # plus de filtre année : VP contient la ligne 2023 (Annulée exclue, ligne prog 2023 conservée => 2 lignes)
    vp = _ligne(res, ALP, "VP")
    assert vp["Prévision 2024"] == "2"


def test_annee_par_defaut_annee_systeme():
    res = calcul_indicateurs_visite(_df([]), "T1")
    an = datetime.datetime.now().year
    assert f"Prévision {an}" in res.columns
    assert f"Réalisées à la fin du T1 {an}" in res.columns
