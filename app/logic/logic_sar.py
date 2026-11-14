import pandas as pd
from datetime import datetime

TRIMESTRE_FIN = {
    "T1": (3, 31),
    "T2": (6, 30),
    "T3": (9, 30),
    "T4": (12, 31),
}


def calcul_sar_indicateurs(df, annee, trimestre_choisi, progress_callback=None):
    # Nettoyage et parsing
    # print("DEBUG: S.A.R - calcul_sar_indicateurs() - 0", flush=True)
    df = df.copy()
    for col in ["Date limite", "Date limite étendue", "Date de réalisation"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if "Programme" in df.columns:
        df["Programme"] = df["Programme"].astype(str)

    # --- GESTION TRIMESTRES AVEC T5 ET AUJOURD'HUI ---
    trimestres_de_base = ["T1", "T2", "T3", "T4", "T5"]

    def get_fin_trim(annee, trimestre):
        if trimestre == "T1":
            return datetime(int(annee), 3, 31)
        elif trimestre == "T2":
            return datetime(int(annee), 6, 30)
        elif trimestre == "T3":
            return datetime(int(annee), 9, 30)
        elif trimestre == "T4":
            return datetime(int(annee), 12, 31)
        elif trimestre == "T5":
            return datetime(int(annee) + 1, 3, 31)
        elif trimestre == "Aujourd'hui":
            return datetime.now()
        else:
            raise ValueError(f"Trimestre non géré : {trimestre}")

    if trimestre_choisi == "Aujourd'hui":
        trimestres_courus = []
        today = datetime.now()
        for t in trimestres_de_base:
            if get_fin_trim(annee, t) <= today:
                trimestres_courus.append(t)
        trimestres_courus.append("Aujourd'hui")
    elif trimestre_choisi == "T5":
        trimestres_courus = trimestres_de_base
    else:
        trimestres = ["T1", "T2", "T3", "T4"]
        idx_tri = trimestres.index(trimestre_choisi) + 1
        trimestres_courus = trimestres[:idx_tri]
        # idx_tri = ["T1", "T2", "T3", "T4"].index(trimestre_choisi) + 1
        # trimestres_courus = ["T1", "T2", "T3", "T4"][:idx_tri]

    # trimestres = ["T1", "T2", "T3", "T4"]
    # idx_tri = trimestres.index(trimestre_choisi) + 1
    # trimestres_courus = trimestres[:idx_tri]

    # data = {}

    # Calcul des dates de fin de trimestre pour l'année sélectionnée
    #dates_fin_trim = {
     #   t: datetime(int(annee), *TRIMESTRE_FIN[t]) for t in trimestres
    #}
    dates_fin_trim = {t: get_fin_trim(annee, t) for t in trimestres_courus}

    if progress_callback:
        progress_callback(5)
    # ************************************** FIN de la GESTION TRIMESTRES **************************************
    # --- Lignes 1bis à 5bis ---
    l1 = []
    l2 = []
    l3 = []
    l4 = []
    l5 = []
    for i, t in enumerate(trimestres_courus):
        fin_trim = dates_fin_trim[t]
        # Ligne 1
        mask_u0 = ((df["Urgence"] == "U0s") &
                   (df["Etat d'avancement"] != "Réalisée") &
                   (df["Date limite"] <= fin_trim)
        )
        n_u0 = df[mask_u0].shape[0]
        l1.append(n_u0)

        # Ligne 2 : Avec analyse de risque saisie (nombre)
        mask_risque = (
            mask_u0 &
            (df["Saisie de l'analyse de risque"] == "Oui") &
            (df["Evènement / phénomène redouté"].notna()) &
            (df["Probabilité"].notna())
        )
        n_risque = df[mask_risque].shape[0]
        l2.append(n_risque)

        # Ligne 3 : Avec analyse de risque saisie (%)
        l3.append((n_risque / n_u0 * 100) if n_u0 else 0)

        # Ligne 4 : Avec mesure conservatoire saisie (nombre)
        mask_mc = (
            mask_u0 &
            (df["Mesure conservatoire différée"] == "Oui") &
            (df["Description mesure conservatoire"].notna())
        )
        n_mc = df[mask_mc].shape[0]
        l4.append(n_mc)
        # Ligne 5 : Avec mesure conservatoire saisie (%)
        l5.append((n_mc / n_u0 * 100) if n_u0 else 0)
        if progress_callback:
            progress_callback(5 + int(25 * (i+1)/len(trimestres_courus)))
    # --- Lignes 1 à 5 ---
    l1_bis = []
    l2_bis = []
    l3_bis = []
    l4_bis = []
    l5_bis = []
    for i, t in enumerate(trimestres_courus):
        # debut_trim = datetime(int(annee), (i) * 3 + 1, 1)
        if t == "T5":
            debut_trim = datetime(int(annee) + 1, 1, 1)
        else:
            debut_trim = datetime(int(annee), (i) * 3 + 1, 1)
        fin_trim = dates_fin_trim[t]

        # Ligne 1 bis
        mask_u0_t_hd= ((df["Urgence"] == "U0s") &
                   (df["Etat d'avancement"] == "Réalisée") &
                   (df["Hors délai"] == "Oui") &
                   (df["Date de réalisation"] <= fin_trim) &
                   (df["Date de réalisation"] >= debut_trim)
        )
        n_u0_t_hd = df[mask_u0_t_hd].shape[0]
        l1_bis.append(n_u0_t_hd)

        # Ligne 2 bis : Avec analyse de risque saisie (nombre)
        mask_risque_t_hd = (
                mask_u0_t_hd &
                (df["Saisie de l'analyse de risque"] == "Oui") &
                (df["Evènement / phénomène redouté"].notna()) &
                (df["Probabilité"].notna())
        )
        n_risque_t_hd = df[mask_risque_t_hd].shape[0]
        l2_bis.append(n_risque_t_hd)

        # Ligne 3 bis: Avec analyse de risque saisie (%)
        l3_bis.append((n_risque_t_hd / n_u0_t_hd * 100) if n_u0_t_hd else 0)

        # Ligne 4 bis: Avec mesure conservatoire saisie (nombre)
        mask_mc_t_hd = (
                mask_u0_t_hd &
                (df["Mesure conservatoire différée"] == "Oui") &
                (df["Description mesure conservatoire"].notna())
        )
        n_mc_t_hd = df[mask_mc_t_hd].shape[0]
        l4_bis.append(n_mc_t_hd)
        # Ligne 5 : Avec mesure conservatoire saisie (%)
        l5_bis.append((n_mc_t_hd / n_u0_t_hd * 100) if n_u0_t_hd else 0)
        if progress_callback:
            progress_callback(5 + int(25 * (i + 1) / len(trimestres_courus)))

    # --- Lignes 6 à 8 ---
    l6 = []
    l7 = []
    l8 = []
    for i, t in enumerate(trimestres_courus):
        # debut_trim = datetime(int(annee), (i)*3+1, 1)
        if t == "T5":
            debut_trim = datetime(int(annee) + 1, 1, 1)
        else:
            debut_trim = datetime(int(annee), i * 3 + 1, 1)

        fin_trim = dates_fin_trim[t]
        # Ligne 6 : SR hors délai yc tolérance
        debut_annee = datetime(int(annee), 1, 1)

        mask_sr_all = (
                (df["Catégorie"] == "SR")
                & (df["Date limite"] <= fin_trim) 
                & (df["Date limite"] >= datetime(int(annee), 1, 1))
        )

        mask_sr = (
                (df["Catégorie"] == "SR")
                & (df["Hors délai"] == "Oui")
                & (
                    ((df["Etat d'avancement"] == "Réalisée")
                        & (df["Date de réalisation"] >= debut_annee)
                        & (df["Date de réalisation"] <= fin_trim))
                    or
                    ((df["Etat d'avancement"] != "Réalisée")
                     & (df["Etat d'avancement"] != "Annulée"))
                  )
        )
        n_sr = df[mask_sr].shape[0]
        l6.append(n_sr)
        # Ligne 7 : dont dépassement <= 3j
        mask_3j = mask_sr & (df["Date de réalisation"] <= df["Date limite étendue"])
        n_3j = df[mask_3j].shape[0]
        l7.append(n_3j)
        # Ligne 8 : dont dépassement > 3j
        mask_sup3j = mask_sr & (df["Date de réalisation"] > df["Date limite étendue"])
        n_sup3j = df[mask_sup3j].shape[0]
        l8.append(n_sup3j)
        if progress_callback:
            progress_callback(30 + int(30 * (i+1)/len(trimestres_courus)))
    # --- Lignes 9 à 11 ---
    # IDR1 (cumulé)
    # print(f"DEBUG: S.A.R - IDR1 (cumulé) - programme de {annee}", flush=True)
    toto = (
        df["Catégorie"].str.contains("IDR", na=False) &
        (df["Programme"] == str(annee)) &
        (df["Etat d'avancement"] == "Réalisée")
    )
    l9 = []
    l10 = []
    l11 = []

    # Harmonisation ultra-stricte : "2024", "2024.0" → "2024"

    def normalize_annee(val):
        if pd.isna(val):
            return ""
        try:
            # Si déjà un int ou float, récupère la partie entière
            return str(int(float(val)))
        except Exception:
            # Si string qui ressemble à un float, convertit
            val_str = str(val).strip()
            if val_str.endswith(".0"):
                return val_str[:-2]
            return val_str

    df["Programme"] = df["Programme"].apply(normalize_annee)
    annee_str = str(int(annee))

    for i, t in enumerate(trimestres_courus):
        fin_trim = dates_fin_trim[t]
        # Ligne 9
        # print("DEBUG valeurs uniques Programme :", sorted(df["Programme"].unique()))
        #print("DEBUG annee_str :", annee_str)

        mask_idr1 = (
                (df["Catégorie"].isin(["IDR", "IDR exceptionnelle"])) &
                (df["Programme"].astype(str) == annee_str) &
                (df["Etat d'avancement"] == "Réalisée") &
                (df["Date de réalisation"] <= fin_trim)
        )
        n_idr1 = df[mask_idr1].shape[0]
        l9.append(n_idr1)
        # Ligne 10
        mask_prog = (
                (df["Catégorie"].isin(["IDR", "IDR exceptionnelle"])) &
                (df["Programme"].astype(str) == annee_str)
        )
        n_prog = df[mask_prog].shape[0]
        l10.append(n_prog)
        # Ligne 11
        l11.append((n_idr1 / n_prog * 100) if n_prog else 0)
        if progress_callback:
            progress_callback(60 + int(35 * (i + 1) / len(trimestres_courus)))

    # Organisation du DataFrame final
    lignes = [
        ("U0s hors délai (non traitées)", l1),
        ("    Avec analyse de risque saisie (nombre)", l2),
        ("    Avec analyse de risque saisie (%)", l3),
        ("    Avec mesure conservatoire saisie (nombre)", l4),
        ("    Avec mesure conservatoire saisie (%)", l5),
        ("U0s hors délai (traitées)", l1_bis),
        ("    Avec analyse de risque saisie (nombre)", l2_bis),
        ("    Avec analyse de risque saisie (%)", l3_bis),
        ("    Avec mesure conservatoire saisie (nombre)", l4_bis),
        ("    Avec mesure conservatoire saisie (%)", l5_bis),
        ("SR_1 (SR hors délai yc tolérance)", l6),
        ("    dont dépassement <= 3 jours", l7),
        ("    dont dépassement > 3 jours", l8),
        ("IDR1 (cumulé)", l9),
        ("    Programme IDR sur l'année", l10),
        ("    % (cumulé)", l11),
    ]
    df_out = pd.DataFrame({ "Indicateur": [x[0] for x in lignes] })
    for i, t in enumerate(trimestres_courus):
        df_out[f"{t}"] = [x[1][i] for x in lignes]

    for col in df_out.columns:
        if col != "Indicateur":
            df_out[col] = df_out[col].astype("object")

    pourcent_lignes = [i for i, val in enumerate(df_out["Indicateur"]) if "%" in val]

    for col in df_out.columns:
        if col == "Indicateur":
            continue
        for i, v in enumerate(df_out[col]):
            if i in pourcent_lignes:
                try:
                    val = float(v)
                    df_out.at[i, col] = f"{val:.1f} %"
                except Exception:
                    df_out.at[i, col] = ""
            else:
                try:
                    val = float(v)
                    df_out.at[i, col] = f"{int(round(val))}"
                except Exception:
                    df_out.at[i, col] = ""

    if progress_callback: progress_callback(100)

    return df_out

