"""Tests de caractérisation de app/logic/logic_indicateurs_oa.py (comportement actuel figé)."""
import warnings

import pandas as pd
import pytest

from app.logic.logic_indicateurs_oa import (
    analyse_surveillance_statuts,
    calcul_indicateurs_trimestriels,
    maintenance_nb_par_categorie_urgence,
    maintenance_utm_hors_delai,
)

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# ------------------------------------------------ analyse_surveillance_statuts
@pytest.fixture
def df_surv():
    return pd.DataFrame({
        "Programme": ["PGM 2026", "PGM 2026", "PGM 2026", "PGM 2026", "PGM 2025", "PGM 2026", "PGM 2026"],
        "Catégorie": ["VI", "VI", "VI", "VI exceptionnelle", "VI", "VD", "IDR"],
        "Statut": ["Réalisée", "Réalisée", "Planifiée", "Réalisée", "Réalisée", None, "Réalisée"],
        "Infrapôle": ["X", "X", "Y", "X", "X", "Y", "X"],
    })


def test_surv_nominal(df_surv):
    res = analyse_surveillance_statuts(df_surv, 2026)
    assert set(res) == {"VI", "VD", "IDE", "IDR"}
    vi = res["VI"]
    # VI 2026 (+ variante exceptionnelle) : 4 lignes, l'année 2025 est exclue
    assert list(vi["Statut"]) == ["Réalisée", "Planifiée"]
    assert list(vi["Nombre"]) == [3, 1]
    assert list(vi["Pourcentage"]) == [75.0, 25.0]
    # Statut vide -> "Inconnu"
    assert list(res["VD"]["Statut"]) == ["Inconnu"]
    assert list(res["VD"]["Pourcentage"]) == [100.0]
    # Catégorie sans ligne -> DataFrame vide aux bonnes colonnes
    assert res["IDE"].empty
    assert list(res["IDE"].columns) == ["Statut", "Nombre", "Pourcentage"]


def test_surv_filtre_infrapole(df_surv):
    res = analyse_surveillance_statuts(df_surv, 2026, infrapole="X")
    assert list(res["VI"]["Nombre"]) == [3]
    assert res["VD"].empty
    # "Tous" ne filtre pas
    res_tous = analyse_surveillance_statuts(df_surv, 2026, infrapole="Tous")
    assert int(res_tous["VI"]["Nombre"].sum()) == 4


def test_surv_pourcentages_arrondis():
    df = pd.DataFrame({"Programme": ["2026"] * 3, "Catégorie": ["IDE"] * 3,
                       "Statut": ["A", "B", "B"]})
    res = analyse_surveillance_statuts(df, 2026, categories=("IDE",))["IDE"]
    assert list(res["Statut"]) == ["B", "A"]
    assert list(res["Pourcentage"]) == [66.7, 33.3]  # 200/3 et 100/3 arrondis à 0,1


def test_surv_tri_ex_aequo_alphabetique():
    df = pd.DataFrame({"Programme": ["2026"] * 2, "Catégorie": ["VI"] * 2, "Statut": ["Z", "A"]})
    res = analyse_surveillance_statuts(df, 2026, categories=("VI",))["VI"]
    assert list(res["Statut"]) == ["A", "Z"]


def test_surv_colonnes_avec_espaces():
    df = pd.DataFrame({" Programme ": ["2026"], "Catégorie ": ["VI"], "Statut": ["OK"]})
    assert list(analyse_surveillance_statuts(df, 2026)["VI"]["Nombre"]) == [1]


def test_surv_vide_none_ou_colonne_manquante(df_surv):
    assert analyse_surveillance_statuts(None, 2026) == {}
    assert analyse_surveillance_statuts(pd.DataFrame(), 2026) == {}
    assert analyse_surveillance_statuts(df_surv.drop(columns=["Statut"]), 2026) == {}


def test_surv_annee_sans_ligne(df_surv):
    res = analyse_surveillance_statuts(df_surv, 1999)
    assert all(v.empty for v in res.values())


# ------------------------------------------------- maintenance_utm_hors_delai
@pytest.fixture
def df_utm():
    return pd.DataFrame({
        "Urgence": ["U0s", "U0s", "U0s", "U0s", "U0s", "U1s", " U0s "],
        "Hors délai": ["Oui", "OUI", "Oui", "oui", "Non", "Oui", "Oui"],
        "UTM": ["A", "A", "B", "", "A", "A", "A"],  # "" -> (Vide)
    })


def test_utm_nominal(df_utm):
    res = maintenance_utm_hors_delai(df_utm, 2026, "U0s")
    d = res.set_index("UTM")
    # U0s + Hors délai oui : A x3 (dont " U0s " nettoyé), B x1, (Vide) x1 => total 5
    assert d.loc["A", "Nombre"] == 3
    assert d.loc["B", "Nombre"] == 1
    assert d.loc["(Vide)", "Nombre"] == 1
    assert d.loc["A", "Pourcentage"] == 60.0
    assert d.loc["B", "Pourcentage"] == 20.0
    assert d.loc["(Vide)", "Pourcentage"] == 20.0
    assert res.iloc[0]["UTM"] == "A"  # tri décroissant


def test_utm_none_selon_version_pandas():
    # ECART: le code vise a regrouper None/NaN sous "(Vide)" via astype(str) -> "None"/"nan".
    # Avec pandas >= 3, astype(str) conserve NaN : la ligne est alors perdue par le groupby.
    # Le test accepte les deux comportements (dependant de la version de pandas).
    df = pd.DataFrame({"Urgence": ["U0s", "U0s"], "Hors délai": ["Oui", "Oui"], "UTM": ["A", None]})
    res = maintenance_utm_hors_delai(df, 2026, "U0s")
    assert int(res["Nombre"].sum()) in (1, 2)
    assert res.set_index("UTM").loc["A", "Nombre"] == 1


def test_utm_autre_urgence(df_utm):
    res = maintenance_utm_hors_delai(df_utm, 2026, "U1s")
    assert list(res["UTM"]) == ["A"] and list(res["Pourcentage"]) == [100.0]


def test_utm_cas_vides(df_utm):
    cols = ["UTM", "Nombre", "Pourcentage"]
    for r in (maintenance_utm_hors_delai(None, 2026, "U0s"),
              maintenance_utm_hors_delai(pd.DataFrame(), 2026, "U0s"),
              maintenance_utm_hors_delai(df_utm.drop(columns=["UTM"]), 2026, "U0s"),
              maintenance_utm_hors_delai(df_utm, 2026, "U9s")):  # aucune ligne ne correspond
        assert r.empty and list(r.columns) == cols


# --------------------------------------- maintenance_nb_par_categorie_urgence
def test_nb_cat_urgence_nominal():
    df = pd.DataFrame({
        "Catégorie": ["IDR", "IDR", "IDR", "VI", "VI", "IDE", "IDE", "SR", "VD"],
        "Urgence": ["U0s", "u0", "U1a", "U1s", "u1S", "U2s", "", "U0x", None],
    })
    res = maintenance_nb_par_categorie_urgence(df, 2026)
    assert list(res.columns) == ["Catégorie", "U0s", "U1s", "Total"]
    # IDE (U2s, vide), SR (U0x non reconnu) et VD (None -> "nan") sont écartées
    assert list(res["Catégorie"]) == ["IDR", "VI"]
    assert list(res["U0s"]) == [2, 0]
    assert list(res["U1s"]) == [1, 2]
    assert list(res["Total"]) == [3, 2]


def test_nb_cat_urgence_variantes_u0_u1():
    df = pd.DataFrame({"Catégorie": ["C"] * 6, "Urgence": ["U0", "U0s", "U0e", "U0a", "U1", "U10"]})
    r = maintenance_nb_par_categorie_urgence(df, 2026).iloc[0]
    assert (r["U0s"], r["U1s"], r["Total"]) == (4, 1, 5)  # U10 ne correspond à rien


def test_nb_cat_urgence_cas_vides():
    cols = ["Catégorie", "U0s", "U1s", "Total"]
    assert list(maintenance_nb_par_categorie_urgence(None, 2026).columns) == cols
    assert maintenance_nb_par_categorie_urgence(pd.DataFrame(), 2026).empty
    assert maintenance_nb_par_categorie_urgence(pd.DataFrame({"Catégorie": ["A"]}), 2026).empty
    tout_vide = pd.DataFrame({"Catégorie": ["A"], "Urgence": [""]})
    assert maintenance_nb_par_categorie_urgence(tout_vide, 2026).empty


# --------------------------------------------- calcul_indicateurs_trimestriels
COLS = ["Programme", "Catégorie", "Famille Ouvrage", "Etat d'avancement", "Date de fin",
        "Date validation", "Date visa", "Date limite", "Hors délai", "Urgence",
        "Date de l'incident ou de sa détection", "Classement incident"]


def _l(**kw):
    ligne = {c: None for c in COLS}
    ligne["Programme"] = "PGM 2026"
    ligne.update(kw)
    return ligne


@pytest.fixture
def df_trim():
    R = "Réalisée"
    lignes = [
        # IDR hors tunnel (famille "Pont")
        _l(**{"Catégorie": "IDR", "Famille Ouvrage": "Pont", "Etat d'avancement": R,
              "Date de fin": "15/02/2026", "Date validation": "20/03/2026"}),
        _l(**{"Catégorie": "IDR exceptionnelle", "Famille Ouvrage": "Pont", "Etat d'avancement": R,
              "Date de fin": "10/05/2026", "Date validation": "01/06/2026"}),
        _l(**{"Catégorie": "IDR", "Famille Ouvrage": "Pont", "Etat d'avancement": "Planifiée"}),
        _l(**{"Catégorie": "IDR", "Famille Ouvrage": "Pont", "Etat d'avancement": R,  # autre année
              "Programme": "PGM 2025", "Date de fin": "10/01/2026"}),
        # Tunnel (IDI inclus)
        _l(**{"Catégorie": "IDI", "Famille Ouvrage": "Tunnel", "Etat d'avancement": R,
              "Date de fin": "01/04/2026", "Date validation": "02/04/2026"}),
        _l(**{"Catégorie": "IDR", "Famille Ouvrage": "Tunnel", "Etat d'avancement": "Planifiée"}),
        # IDE : date de fin == borne T2 (incluse)
        _l(**{"Catégorie": "IDE", "Etat d'avancement": R, "Date de fin": "30/06/2026",
              "Date validation": "30/06/2026"}),
        # VI
        _l(**{"Catégorie": "VI", "Etat d'avancement": R, "Date de fin": "01/03/2026",
              "Date visa": "05/05/2026"}),
        # SR (la logique SR n'est pas filtrée par année)
        _l(**{"Catégorie": "SR", "Etat d'avancement": R, "Date limite": "15/02/2026", "Hors délai": "Oui"}),
        _l(**{"Catégorie": "SR", "Etat d'avancement": R, "Date limite": "20/05/2026", "Hors délai": "Non"}),
        _l(**{"Catégorie": "SR", "Etat d'avancement": "En cours", "Date limite": "31/03/2026"}),
        _l(**{"Catégorie": "SR", "Etat d'avancement": "En cours", "Date limite": "10/02/2026"}),
        # U0s non traitées hors délai
        _l(**{"Catégorie": "Autre", "Urgence": "U0s", "Etat d'avancement": "En cours", "Date limite": "15/03/2026"}),
        _l(**{"Catégorie": "Autre", "Urgence": "U0s", "Etat d'avancement": "En cours", "Date limite": "31/03/2026"}),
        _l(**{"Catégorie": "Autre", "Urgence": "U0s", "Etat d'avancement": R, "Date limite": "01/01/2026"}),
        # Incidents ESR
        _l(**{"Catégorie": "Incident", "Date de l'incident ou de sa détection": "15/01/2026",
              "Classement incident": "ES (évènement sécurité)"}),
        _l(**{"Catégorie": "Incident", "Date de l'incident ou de sa détection": "31/12/2025",
              "Classement incident": "ES (évènement sécurité)"}),
        _l(**{"Catégorie": "Incident", "Date de l'incident ou de sa détection": "20/02/2026",
              "Classement incident": "Autre"}),
        _l(**{"Catégorie": "Incident", "Date de l'incident ou de sa détection": "01/01/2026",
              "Classement incident": "ES (évènement sécurité)"}),
    ]
    return pd.DataFrame(lignes, columns=COLS)


def _val(res, cle, trim):
    return res.set_index("Indicateur").loc[cle, trim]


def test_trim_structure_et_callback(df_trim):
    appels = []
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T2", appels.append)
    assert list(res.columns) == ["Indicateur", "T1", "T2"]
    assert appels[0] == 5 and appels[-1] == 100
    assert appels == sorted(appels)
    assert res.iloc[0]["Indicateur"] == "2026_IDR_IP"
    assert len(res) == 30  # 5 familles x 5 indicateurs + SR_P, SR_HD, SR + U0s + ESR


def test_trim_idr_hors_tunnel(df_trim):
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T2", lambda p: None)
    # Prévues : 3 (la ligne PGM 2025 est exclue)
    assert [_val(res, "2026_IDR_IP", t) for t in ("T1", "T2")] == ["3", "3"]
    assert [_val(res, "2026_IDR_VR", t) for t in ("T1", "T2")] == ["1", "2"]
    assert [_val(res, "2026_IDR1", t) for t in ("T1", "T2")] == ["33.3%", "66.7%"]
    assert [_val(res, "2026_IDR_RV", t) for t in ("T1", "T2")] == ["1", "2"]
    assert [_val(res, "2026_IDR2", t) for t in ("T1", "T2")] == ["100.0%", "100.0%"]


def test_trim_tunnel(df_trim):
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T2", lambda p: None)
    assert [_val(res, "2026_IDTU_IP", t) for t in ("T1", "T2")] == ["2", "2"]
    assert [_val(res, "2026_IDTU_VR", t) for t in ("T1", "T2")] == ["0", "1"]
    assert [_val(res, "2026_IDTU1", t) for t in ("T1", "T2")] == ["0.0%", "50.0%"]
    assert [_val(res, "2026_IDTU2", t) for t in ("T1", "T2")] == ["0.0%", "100.0%"]


def test_trim_ide_vd_vi(df_trim):
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T2", lambda p: None)
    # IDE : date de fin 30/06 = borne T2 incluse, absente de T1
    assert [_val(res, "2026_IDE_VR", t) for t in ("T1", "T2")] == ["0", "1"]
    assert [_val(res, "2026_IDE2", t) for t in ("T1", "T2")] == ["0.0%", "100.0%"]
    # VD : aucune ligne -> division par zéro protégée
    assert [_val(res, "2026_VD_IP", t) for t in ("T1", "T2")] == ["0", "0"]
    assert [_val(res, "2026_VD1", t) for t in ("T1", "T2")] == ["0.0%", "0.0%"]
    # VI : réalisée dès T1, visa seulement en T2
    assert [_val(res, "2026_VI_VR", t) for t in ("T1", "T2")] == ["1", "1"]
    assert [_val(res, "2026_VI_RV", t) for t in ("T1", "T2")] == ["0", "1"]
    assert [_val(res, "2026_VI2", t) for t in ("T1", "T2")] == ["0.0%", "100.0%"]


def test_trim_sr_u0s_esr(df_trim):
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T2", lambda p: None)
    # SR prévues : limite <= fin de trimestre -> T1 : 3 ; T2 : 4
    assert [_val(res, "2026_SR_P", t) for t in ("T1", "T2")] == ["3", "4"]
    # Hors délai : T1 = {réalisée "Oui", non réalisée 10/02} ; la limite 31/03 == fin T1 n'est pas
    # encore hors délai (comparaison stricte) ; T2 = 3 (la limite 31/03 l'est devenue)
    assert [_val(res, "2026_SR_HD", t) for t in ("T1", "T2")] == ["2", "3"]
    assert [_val(res, "2026_SR", t) for t in ("T1", "T2")] == ["66.7%", "75.0%"]
    # U0s non réalisées avec limite strictement avant la borne
    assert [_val(res, "2026_U0s", t) for t in ("T1", "T2")] == ["1", "2"]
    # ESR depuis le 1er janvier (inclus), indépendant du trimestre
    assert [_val(res, "2026_ESR", t) for t in ("T1", "T2")] == ["2", "2"]


def test_trim_quatre_trimestres_et_retours_ligne_colonnes(df_trim):
    df = df_trim.rename(columns={"Date validation": "Date\nvalidation"})
    res = calcul_indicateurs_trimestriels(df, 2026, "T4", lambda p: None)
    assert list(res.columns) == ["Indicateur", "T1", "T2", "T3", "T4"]
    assert _val(res, "2026_IDR_RV", "T4") == "2"


def test_trim_dataframe_vide_avec_colonnes():
    res = calcul_indicateurs_trimestriels(pd.DataFrame(columns=COLS), 2026, "T1", lambda p: None)
    vals = res[["T1"]].iloc[:, 0].tolist()
    assert set(vals) <= {"0", "0.0%"}


def test_trim_colonne_programme_absente():
    with pytest.raises(KeyError):
        calcul_indicateurs_trimestriels(pd.DataFrame({"Catégorie": []}), 2026, "T1", lambda p: None)


def test_trim_callback_none_par_defaut(df_trim):
    # Non-régression : progress_callback=None (défaut) levait TypeError ('NoneType' is not callable)
    res = calcul_indicateurs_trimestriels(df_trim, 2026, "T1")
    assert "Indicateur" in res.columns
