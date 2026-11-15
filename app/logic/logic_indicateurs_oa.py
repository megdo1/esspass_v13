import pandas as pd
import re

def analyse_surveillance_statuts(df: pd.DataFrame, annee: int, categories=("VI", "VD", "IDE", "IDR"), infrapole: str = None):
    """
    Retourne un dict {categorie: DataFrame[Statut, Nombre, Pourcentage]}
    - Filtre Programme contenant l'année
    - Filtre Catégorie avec variantes 'exceptionnelle'
    - Optionnellement filtre Infrapôle (si passé)
    - Agrège par colonne 'Statut'
    """
    if df is None or df.empty:
        return {}

    cols = [c.strip() for c in df.columns]
    df = df.copy()
    df.columns = cols

    required = {"Programme", "Catégorie", "Statut"}
    if not required.issubset(set(df.columns)):
        return {}

    # Filtre année sur 'Programme'
    df = df[df["Programme"].astype(str).str.contains(str(annee), na=False)]

    # Filtre infrapôle si demandé
    if infrapole and "Infrapôle" in df.columns and infrapole not in ("Tous", "Infrapôle"):
        df = df[df["Infrapôle"].astype(str).str.strip() == str(infrapole).strip()]

    # Map catégories -> liste de valeurs acceptées (avec "exceptionnelle")
    def variants(cat):
        return [cat, f"{cat} exceptionnelle"]

    out = {}
    for cat in categories:
        df_cat = df[df["Catégorie"].isin(variants(cat))]
        if df_cat.empty:
            out[cat] = pd.DataFrame(columns=["Statut", "Nombre", "Pourcentage"])
            continue

        vc = df_cat["Statut"].fillna("Inconnu").astype(str).str.strip().value_counts(dropna=False)
        total = int(vc.sum())
        res = pd.DataFrame({
            "Statut": vc.index.tolist(),
            "Nombre": vc.values.tolist(),
        })
        res["Pourcentage"] = res["Nombre"].apply(lambda n: round(100.0 * n / total, 1) if total else 0.0)
        # Tri pour une lecture stable (du plus fréquent au moins fréquent)
        res = res.sort_values(by=["Nombre", "Statut"], ascending=[False, True]).reset_index(drop=True)
        out[cat] = res

    return out


def maintenance_utm_hors_delai(df: pd.DataFrame, annee: int, urgence_code: str) -> pd.DataFrame:
    """
    Donut 'OA - PRECOS Ux S Hors délai par UTM'
    ⚠️ Ne filtre plus par année : utilise toutes les lignes du fichier/sauvegarde déjà masquées en amont.
    Filtre: Urgence == urgence_code (ex: 'U0s' ou 'U1s') et 'Hors délai' == 'Oui'
    Retour: DataFrame[UTM, Nombre, Pourcentage]
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["UTM", "Nombre", "Pourcentage"])

    work = df.copy()
    work.columns = work.columns.str.strip()
    needed = {"Urgence", "Hors délai", "UTM"}
    if not needed.issubset(work.columns):
        return pd.DataFrame(columns=["UTM", "Nombre", "Pourcentage"])

    work["Urgence"] = work["Urgence"].astype(str).str.strip()
    work["Hors délai"] = work["Hors délai"].astype(str).str.strip().str.lower()
    work["UTM"] = (
        work["UTM"].astype(str).str.strip()
        .replace({"": "(Vide)", "nan": "(Vide)", "None": "(Vide)"})
    )

    sub = work[(work["Urgence"] == urgence_code) & (work["Hors délai"] == "oui")]
    grp = sub.groupby("UTM").size().reset_index(name="Nombre")
    if grp.empty:
        return pd.DataFrame(columns=["UTM", "Nombre", "Pourcentage"])

    grp = grp.sort_values("Nombre", ascending=False).reset_index(drop=True)
    total = int(grp["Nombre"].sum())
    grp["Pourcentage"] = grp["Nombre"].apply(lambda n: round(100.0 * n / total, 1) if total else 0.0)
    return grp


def maintenance_nb_par_categorie_urgence(df: pd.DataFrame, annee: int) -> pd.DataFrame:
    """
    'OA - Nombre d'Urgence par Catégorie et Urgence'
    ⚠️ Ne filtre plus par année : utilise toutes les lignes du fichier/sauvegarde déjà masquées en amont.
    - U0 = variantes U0x où x ∈ {s, e, a, ""}  (insensible à la casse)
    - U1 = variantes U1x où x ∈ {s, e, a, ""}  (insensible à la casse)
    - Ignore les urgences vides
    Retour: DataFrame[Catégorie, U0s, U1s, Total] trié desc. (colonnes conservées pour compatibilité graphique)
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Catégorie", "U0s", "U1s", "Total"])

    work = df.copy()
    work.columns = work.columns.str.strip()
    needed = {"Catégorie", "Urgence"}
    if not needed.issubset(work.columns):
        return pd.DataFrame(columns=["Catégorie", "U0s", "U1s", "Total"])

    work["Catégorie"] = work["Catégorie"].astype(str).str.strip()
    urg = work["Urgence"].astype(str).str.strip()

    # Exclure vides
    mask_non_vide = urg.ne("").fillna(False)
    work = work[mask_non_vide]
    if work.empty:
        return pd.DataFrame(columns=["Catégorie", "U0s", "U1s", "Total"])

    # Regex variantes (insensible à la casse)
    pat_u0 = re.compile(r"^U0([sea])?$", flags=re.IGNORECASE)
    pat_u1 = re.compile(r"^U1([sea])?$", flags=re.IGNORECASE)

    # Masques U0/U1
    urg_lc = work["Urgence"].astype(str).str.strip()
    m_u0 = urg_lc.str.match(pat_u0)
    m_u1 = urg_lc.str.match(pat_u1)

    # Comptage par catégorie
    g = work.groupby("Catégorie", dropna=False)
    df_out = g.apply(lambda gdf: pd.Series({
        "U0s": int(m_u0.loc[gdf.index].sum()),
        "U1s": int(m_u1.loc[gdf.index].sum()),
    })).reset_index()

    # Total et nettoyage catégories sans urgence
    df_out["Total"] = df_out["U0s"] + df_out["U1s"]
    df_out = df_out[(df_out["U0s"] > 0) | (df_out["U1s"] > 0)]

    df_out = df_out.sort_values("Total", ascending=False).reset_index(drop=True)
    return df_out[["Catégorie", "U0s", "U1s", "Total"]]


def calcul_indicateurs_trimestriels(df: pd.DataFrame, annee: int, trimestre_max: str,
                                    progress_callback=None) -> pd.DataFrame:
    """
    Calcule les indicateurs trimestriels pour l'année et le trimestre choisis.
    :param df: DataFrame source
    :param annee: année choisie (int)
    :param trimestre_max: exemple: "T1", "T2", ..., "T4"
    :param progress_callback
    :return: DataFrame avec les lignes d'indicateurs et colonnes par trimestre
    """
    # Sécurité : conversion en str pour éviter les erreurs
    # df = df.copy()
    # Nettoyage des noms de colonnes : suppression des sauts de ligne et espaces superflus
    # df.columns = df.columns.str.replace(r"[\n\r]+", " ", regex=True).str.strip()
    # df = df[df["Programme"].astype(str).str.contains(str(annee), na=False)]

    df_complet = df.copy()
    df_complet.columns = df_complet.columns.str.replace(r"[\n\r]+", " ", regex=True).str.strip()
    df_annee = df_complet[df_complet["Programme"].astype(str).str.contains(str(annee), na=False)]

    # Initialisation de la structure de sortie
    # trimestres = [f"T{i}" for i in range(1, int(trimestre_max[1]) + 1)]
    # --- Bloc modifié pour gérer "Aujourd'hui" ---
    from datetime import datetime

    now = datetime.now()
    bornes_trimestres = [
        ("T1", datetime(annee, 3, 31)),
        ("T2", datetime(annee, 6, 30)),
        ("T3", datetime(annee, 9, 30)),
        ("T4", datetime(annee, 12, 31)),
        ("T5", datetime(annee + 1, 3, 31)),
    ]
    trimestres = []
    # print(f"calcul_indicateurs_trimestriels - trimestre reçu: {trimestre_max}", flush=True)
    if trimestre_max == "Aujourd'hui":
        for nom_trim, fin_trim in bornes_trimestres:
            if now >= fin_trim:
                trimestres.append(nom_trim)
        trimestres.append("Aujourd'hui")
    else:
        # trimestres = [f"T{i}" for i in range(1, int(trimestre_max[1]) + 1)]
        max_trim = int(trimestre_max[1])
        trimestres = [f"T{i}" for i in range(1, max_trim + 1)]

    resultats = {}

    if progress_callback:
        progress_callback(5)

    def filtre_lignes_old(cats, famille=None, etat=None, date_col=None, date_max=None):
        cond = df["Catégorie"].isin(cats)
        if famille is not None:
            if famille == "Tunnel":
                cond &= df["Famille Ouvrage"] == "Tunnel"
            elif famille == "hors Tunnel":
                cond &= df["Famille Ouvrage"] != "Tunnel"
        if etat:
            cond &= df["Etat d'avancement"] == etat
        if date_col and date_max:
            dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
            cond &= (dates <= date_max)
        return df[cond]

    def filtre_lignes(cats, famille=None, etat=None, date_col=None, date_max=None, source_df=df_annee):
        cond = source_df["Catégorie"].isin(cats)
        if famille is not None:
            if famille == "Tunnel":
                cond &= source_df["Famille Ouvrage"] == "Tunnel"
            elif famille == "hors Tunnel":
                cond &= source_df["Famille Ouvrage"] != "Tunnel"
        if etat:
            cond &= source_df["Etat d'avancement"] == etat
        if date_col and date_max:
            dates = pd.to_datetime(source_df[date_col], errors="coerce", dayfirst=True)
            cond &= (dates <= date_max)
        return source_df[cond]

    def count_rows(df_filtre):
        return int(len(df_filtre))

    def pct(part, total):
        return f"{round(100 * part / total, 1)}%" if total else "0.0%"

    def date_fin_trim(annee, trimestre):
        return {
            "T1": datetime(annee, 3, 31),
            "T2": datetime(annee, 6, 30),
            "T3": datetime(annee, 9, 30),
            "T4": datetime(annee, 12, 31),
            "T5": datetime(annee+1, 3, 31)
        }[trimestre]

    i = 0
    for trimestre in trimestres:
        i += 1
        # fin_trim = date_fin_trim(annee, trimestre)
        if trimestre == "Aujourd'hui":
            fin_trim = now
        else:
            fin_trim = date_fin_trim(annee, trimestre)
        # IDR hors tunnel
        idr_prevu = filtre_lignes(["IDR", "IDR exceptionnelle"], "hors Tunnel")
        idr_real = filtre_lignes(["IDR", "IDR exceptionnelle"], "hors Tunnel", "Réalisée",
                                 "Date de fin", fin_trim)
        """
        if idr_real.empty:
            idr_real = filtre_lignes(["IDR", "IDR exceptionnelle"], "hors Tunnel", "Réalisée", "Date de réalisation",
                                     fin_trim)"""
        idr_valid = filtre_lignes(["IDR", "IDR exceptionnelle"], "hors Tunnel", "Réalisée", "Date validation", fin_trim)

        # IDR Tunnel
        idtu_prevu = filtre_lignes(["IDR", "IDR exceptionnelle", "IDI"], "Tunnel")
        idtu_real = filtre_lignes(["IDR", "IDR exceptionnelle", "IDI"], "Tunnel", "Réalisée", "Date de fin", fin_trim)
        """if idtu_real.empty:
            idtu_real = filtre_lignes(["IDR", "IDR exceptionnelle", "IDI"], "Tunnel", "Réalisée", "Date de réalisation",
                                      fin_trim)"""
        idtu_valid = filtre_lignes(["IDR", "IDR exceptionnelle", "IDI"], "Tunnel", "Réalisée", "Date validation",
                                   fin_trim)

        # IDE
        ide_prevu = filtre_lignes(["IDE", "IDE exceptionnelle"])
        ide_real = filtre_lignes(["IDE", "IDE exceptionnelle"], None, "Réalisée", "Date de fin", fin_trim)
        """if ide_real.empty:
            ide_real = filtre_lignes(["IDE", "IDE exceptionnelle"], None, "Réalisée", "Date de réalisation", fin_trim)"""
        ide_valid = filtre_lignes(["IDE", "IDE exceptionnelle"], None, "Réalisée", "Date validation", fin_trim)

        # VD
        vd_prevu = filtre_lignes(["VD", "VD exceptionnelle"])
        vd_real = filtre_lignes(["VD", "VD exceptionnelle"], None, "Réalisée", "Date de fin", fin_trim)
        """if vd_real.empty:
            vd_real = filtre_lignes(["VD", "VD exceptionnelle"], None, "Réalisée", "Date de réalisation", fin_trim)"""
        vd_valid = filtre_lignes(["VD", "VD exceptionnelle"], None, "Réalisée", "Date validation", fin_trim)

        # VI
        vi_prevu = filtre_lignes(["VI", "VI exceptionnelle"])
        vi_real = filtre_lignes(["VI", "VI exceptionnelle"], None, "Réalisée", "Date de fin", fin_trim)
        """if vi_real.empty:
            vi_real = filtre_lignes(["VI", "VI exceptionnelle"], None, "Réalisée", "Date de réalisation", fin_trim)"""
        vi_visa = filtre_lignes(["VI", "VI exceptionnelle"], None, "Réalisée", "Date visa", fin_trim)

        resultats.setdefault(f"{annee}_IDR_IP", []).append(str(count_rows(idr_prevu)))
        resultats.setdefault(f"{annee}_IDR_VR", []).append(str(count_rows(idr_real)))
        resultats.setdefault(f"{annee}_IDR1", []).append(pct(count_rows(idr_real), count_rows(idr_prevu)))
        resultats.setdefault(f"{annee}_IDR_RV", []).append(str(count_rows(idr_valid)))
        resultats.setdefault(f"{annee}_IDR2", []).append(pct(count_rows(idr_valid), count_rows(idr_real)))

        resultats.setdefault(f"{annee}_IDTU_IP", []).append(str(count_rows(idtu_prevu)))
        resultats.setdefault(f"{annee}_IDTU_VR", []).append(str(count_rows(idtu_real)))
        resultats.setdefault(f"{annee}_IDTU1", []).append(pct(count_rows(idtu_real), count_rows(idtu_prevu)))
        resultats.setdefault(f"{annee}_IDTU_RV", []).append(str(count_rows(idtu_valid)))
        resultats.setdefault(f"{annee}_IDTU2", []).append(pct(count_rows(idtu_valid), count_rows(idtu_real)))

        resultats.setdefault(f"{annee}_IDE_IP", []).append(str(count_rows(ide_prevu)))
        resultats.setdefault(f"{annee}_IDE_VR", []).append(str(count_rows(ide_real)))
        resultats.setdefault(f"{annee}_IDE1", []).append(pct(count_rows(ide_real), count_rows(ide_prevu)))
        resultats.setdefault(f"{annee}_IDE_RV", []).append(str(count_rows(ide_valid)))
        resultats.setdefault(f"{annee}_IDE2", []).append(pct(count_rows(ide_valid), count_rows(ide_real)))

        resultats.setdefault(f"{annee}_VD_IP", []).append(str(count_rows(vd_prevu)))
        resultats.setdefault(f"{annee}_VD_VR", []).append(str(count_rows(vd_real)))
        resultats.setdefault(f"{annee}_VD1", []).append(pct(count_rows(vd_real), count_rows(vd_prevu)))
        resultats.setdefault(f"{annee}_VD_RV", []).append(str(count_rows(vd_valid)))
        resultats.setdefault(f"{annee}_VD2", []).append(pct(count_rows(vd_valid), count_rows(vd_real)))

        resultats.setdefault(f"{annee}_VI_IP", []).append(str(count_rows(vi_prevu)))
        resultats.setdefault(f"{annee}_VI_VR", []).append(str(count_rows(vi_real)))
        resultats.setdefault(f"{annee}_VI1", []).append(pct(count_rows(vi_real), count_rows(vi_prevu)))
        resultats.setdefault(f"{annee}_VI_RV", []).append(str(count_rows(vi_visa)))
        resultats.setdefault(f"{annee}_VI2", []).append(pct(count_rows(vi_visa), count_rows(vi_real)))

        # SR prévues (ligne 26)
        df_sr_prevu = df_complet[(df_complet["Catégorie"] == "SR")]
        df_sr_prevu = df_sr_prevu[pd.to_datetime(df_sr_prevu["Date limite"], errors="coerce", dayfirst=True) <= fin_trim]
        sr_prevu_count = count_rows(df_sr_prevu)
        resultats.setdefault(f"{annee}_SR_P", []).append(str(sr_prevu_count))

        # SR hors délai (ligne 27)
        df_sr = df_complet[(df_complet["Catégorie"] == "SR")].copy()
        df_sr["Date limite"] = pd.to_datetime(df_sr["Date limite"], errors="coerce", dayfirst=True)
        df_sr_hd = df_sr[
            (df_sr["Date limite"] <= fin_trim) & (
                ((df_sr["Etat d'avancement"] == "Réalisée") & (df_sr["Hors délai"].astype(str).str.lower() == "oui")) |
                ((df_sr["Etat d'avancement"] != "Réalisée") & (df_sr["Date limite"] < fin_trim))
            )
        ]
        sr_hd_count = count_rows(df_sr_hd)
        resultats.setdefault(f"{annee}_SR_HD", []).append(str(sr_hd_count))

        # % SR hors délai (ligne 28)
        resultats.setdefault(f"{annee}_SR", []).append(pct(sr_hd_count, sr_prevu_count))

        # U0s non traitées et hors délai (ligne 29)
        df_u0s = df_complet[
            (df_complet["Urgence"] == "U0s") &
            (pd.to_datetime(df_complet["Date limite"], errors="coerce", dayfirst=True) < fin_trim) &
            (df_complet["Etat d'avancement"] != "Réalisée")
        ]
        resultats.setdefault(f"{annee}_U0s", []).append(str(count_rows(df_u0s)))

        # ESR depuis le 1er janvier (ligne 30)
        debut_annee = datetime(annee, 1, 1)
        df_esr = df_complet[
            (df_complet["Catégorie"] == "Incident") &
            (pd.to_datetime(df_complet["Date de l'incident ou de sa détection"], errors="coerce", dayfirst=True) >= debut_annee) &
            (df_complet["Classement incident"] == "ES (évènement sécurité)")
        ]
        resultats.setdefault(f"{annee}_ESR", []).append(str(count_rows(df_esr)))

        if progress_callback:
            progress_callback(5 + int(25 * i / len(trimestres)))

    df_result = pd.DataFrame.from_dict(resultats, orient="index", columns=trimestres).reset_index()
    # df_result.columns = ["Indicateur"] + trimestres
    trimestres_affiches = [datetime.now().strftime("%d/%m/%Y") if t == "Aujourd'hui" else t for t in trimestres]
    df_result.columns = ["Indicateur"] + trimestres_affiches

    if progress_callback:
        progress_callback(100)
    return df_result
