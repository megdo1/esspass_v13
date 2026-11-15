"""Tests de caractérisation de app/logic/logic_sar.py (indicateurs S.A.R).

ECART (bug réel) : dans le calcul « SR hors délai » (mask_sr), le code combine
deux Series avec l'opérateur Python `or` au lieu de `|`. Pandas lève alors
ValueError("The truth value of a Series is ambiguous") quelle que soit la taille
du DataFrame (0, 1 ou n lignes). Résultat : calcul_sar_indicateurs ne va JAMAIS
au bout pour un trimestre valide. Les tests « crash_actuel » figent ce
comportement avant correction ; ils sont devenus des tests de non-régression, et les
valeurs attendues ont été calculées à la main.
"""
import pandas as pd
import pytest

from app.logic.logic_sar import calcul_sar_indicateurs

COLS = ["Urgence", "Etat d'avancement", "Date limite", "Date limite étendue",
        "Date de réalisation", "Hors délai", "Saisie de l'analyse de risque",
        "Evènement / phénomène redouté", "Probabilité", "Mesure conservatoire différée",
        "Description mesure conservatoire", "Catégorie", "Programme"]


def _df(rows):
    return pd.DataFrame(rows, columns=COLS)


def _ligne(urg, etat, lim, ext=None, rea=None, hd="Non", risque="Non", evt=None, prob=None,
           mc="Non", desc=None, cat="Autre", prog="2024"):
    return [urg, etat, lim, ext, rea, hd, risque, evt, prob, mc, desc, cat, prog]


def _jeu():
    return _df([
        # A : U0s non traitée, limite T1, analyse de risque + mesure conservatoire saisies
        _ligne("U0s", "En cours", "15/02/2024", risque="Oui", evt="e", prob="p", mc="Oui", desc="d"),
        # B : U0s non traitée, limite T2, rien de saisi
        _ligne("U0s", "En cours", "10/05/2024"),
        # C : U0s déjà réalisée : hors ligne 1
        _ligne("U0s", "Réalisée", "01/01/2024", rea="02/01/2024"),
        # D : U0s limite après T2 : hors ligne 1 pour T1 et T2
        _ligne("U0s", "En cours", "01/07/2024"),
        # E : IDR programme "2024.0" réalisée le 20/02/2024
        _ligne("U1", "Réalisée", "01/02/2024", rea="20/02/2024", cat="IDR", prog="2024.0"),
        # F : IDR exceptionnelle programme 2024 en cours
        _ligne("U1", "En cours", "01/09/2024", cat="IDR exceptionnelle", prog=2024),
        # G : IDR d'un autre programme
        _ligne("U1", "Réalisée", "01/02/2023", rea="20/02/2023", cat="IDR", prog="2023"),
    ])


# --- Comportement actuel (figé) ---------------------------------------------

@pytest.mark.parametrize("df", [_jeu(), _df([]), _df([_ligne("U0s", "En cours", "15/02/2024")])])
def test_calcul_aboutit_sans_erreur(df):
    # Non-régression : `or` entre Series dans mask_sr levait ValueError (« truth value of a Series »)
    res = calcul_sar_indicateurs(df, 2024, "T2")
    assert len(res) == 16


def test_trimestre_inconnu_leve_valueerror():
    with pytest.raises(ValueError):
        calcul_sar_indicateurs(_jeu(), 2024, "T9")


def test_colonne_manquante_leve_keyerror():
    with pytest.raises(KeyError):
        calcul_sar_indicateurs(pd.DataFrame(), 2024, "T1")


def test_dataframe_entree_non_modifie():
    df = _jeu()
    avant = df.copy()
    calcul_sar_indicateurs(df, 2024, "T1")
    pd.testing.assert_frame_equal(df, avant)


# --- Valeurs attendues (calculées à la main) ----------------------------------------


def test_nominal_t2_u0s_et_idr():
    res = calcul_sar_indicateurs(_jeu(), 2024, "T2").set_index("Indicateur")
    assert list(res.columns) == ["T1", "T2"]
    lignes = res.reset_index()
    # T1 : seule A (limite 15/02 <= 31/03) ; T2 : A et B
    assert lignes.loc[0, ["T1", "T2"]].tolist() == ["1", "2"]          # U0s non traitées
    assert lignes.loc[1, ["T1", "T2"]].tolist() == ["1", "1"]          # avec analyse de risque
    assert lignes.loc[2, ["T1", "T2"]].tolist() == ["100.0 %", "50.0 %"]
    assert lignes.loc[3, ["T1", "T2"]].tolist() == ["1", "1"]          # avec mesure conservatoire
    assert lignes.loc[4, ["T1", "T2"]].tolist() == ["100.0 %", "50.0 %"]
    # IDR : E réalisée le 20/02 (programme "2024.0" normalisé) ; programme = E + F = 2
    assert lignes.loc[13, ["T1", "T2"]].tolist() == ["1", "1"]
    assert lignes.loc[14, ["T1", "T2"]].tolist() == ["2", "2"]
    assert lignes.loc[15, ["T1", "T2"]].tolist() == ["50.0 %", "50.0 %"]


def test_dataframe_vide_donne_zeros():
    res = calcul_sar_indicateurs(_df([]), 2024, "T1")
    assert len(res) == 16
    assert (res["T1"].isin(["0", "0.0 %"])).all()


def test_t5_donne_cinq_colonnes():
    res = calcul_sar_indicateurs(_jeu(), 2024, "T5")
    assert list(res.columns) == ["Indicateur", "T1", "T2", "T3", "T4", "T5"]


# --- SR hors délai (lignes 6 à 8) : régression de l'opérateur `or` -> `|` ------------

def _jeu_sr():
    return _df([
        # S1 : réalisée le 10/02, au-delà de la limite étendue (05/02) : dépassement > 3 j
        _ligne("U1", "Réalisée", "01/02/2024", ext="05/02/2024", rea="10/02/2024", hd="Oui", cat="SR"),
        # S2 : réalisée le 15/05 (T2), dans la limite étendue : dépassement <= 3 j
        _ligne("U1", "Réalisée", "10/05/2024", ext="20/05/2024", rea="15/05/2024", hd="Oui", cat="SR"),
        # S3 : en cours, hors délai : comptée à chaque trimestre, ni <= 3 j ni > 3 j (pas de réalisation)
        _ligne("U1", "En cours", "01/03/2024", ext="05/03/2024", hd="Oui", cat="SR"),
        # S4 : annulée : jamais comptée
        _ligne("U1", "Annulée", "01/03/2024", ext="05/03/2024", hd="Oui", cat="SR"),
        # S5 : réalisée mais pas hors délai : jamais comptée
        _ligne("U1", "Réalisée", "01/03/2024", ext="05/03/2024", rea="02/03/2024", hd="Non", cat="SR"),
        # S6 : réalisée avant le début de l'année : jamais comptée
        _ligne("U1", "Réalisée", "01/03/2023", ext="05/03/2023", rea="10/01/2023", hd="Oui", cat="SR"),
    ])


def test_sr_hors_delai_lignes_6_a_8():
    res = calcul_sar_indicateurs(_jeu_sr(), 2024, "T2")
    sr = res.iloc[10:13][["T1", "T2"]].values.tolist()   # SR_1 + 2 sous-lignes
    # ligne 6 : S1 + S3 en T1 ; S1 + S2 + S3 en T2
    # ligne 7 (<= 3 j) : aucune en T1 ; S2 en T2
    # ligne 8 (> 3 j)  : S1 en T1 et en T2
    assert sr == [["2", "3"], ["0", "1"], ["1", "1"]]
