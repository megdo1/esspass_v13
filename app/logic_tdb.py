import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime


def calcul_tdb_section_structure_activite(df, progress_callback=None):
    df = df.copy()
    for col in ["Date de réalisation", "Date limite retenue", "Date rédaction"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if "Date limite" in df.columns and "Date limite retenue" not in df.columns:
        df["Date limite retenue"] = pd.to_datetime(df["Date limite"], errors="coerce", dayfirst=True)
    today = pd.Timestamp(datetime.now().date())
    annee_deb = pd.Timestamp(datetime.now().year, 1, 1)

    results = []
    categorie_souscat = df[["Catégorie", "Sous-catégorie"]].drop_duplicates().reset_index(drop=True)
    total = len(categorie_souscat)
    current = 0

    for _, row in categorie_souscat.iterrows():
        cat = row["Catégorie"]
        souscat = row["Sous-catégorie"]
        df_cs = df[(df["Catégorie"] == cat) & (df["Sous-catégorie"] == souscat)]
        prefix = f"{cat}" if pd.isna(souscat) or souscat == "" or str(souscat).lower() == "nan" else f"{cat} - {souscat}"

        # Ligne 1 - à faire (dans les temps)
        mask_a_faire = df_cs["Etat d'avancement"].notna() & ~df_cs["Etat d'avancement"].isin(["Réalisée", "Annulée"])
        mask_limite = df_cs["Date limite retenue"].notna() & (df_cs["Date limite retenue"] >= today)
        n_a_faire_dans_les_temps = df_cs[mask_a_faire & mask_limite].shape[0]

        # Ligne 2 - à faire (hors délai)
        mask_limite_hors_delai = df_cs["Date limite retenue"].notna() & (df_cs["Date limite retenue"] < today)
        n_a_faire_hors_delai = df_cs[mask_a_faire & mask_limite_hors_delai].shape[0]

        # Ligne 3 - à faire (absence d'échéance)
        mask_limite_absente = df_cs["Date limite retenue"].isna()
        n_a_faire_sans_echeance = df_cs[mask_a_faire & mask_limite_absente].shape[0]

        # Ligne 4 - Réalisé (au cours de l'année)
        mask_rea = (df_cs["Etat d'avancement"] == "Réalisée")
        mask_rea_annee = df_cs["Date de réalisation"].notna() & (df_cs["Date de réalisation"] >= annee_deb)
        n_rea_annee = df_cs[mask_rea & mask_rea_annee].shape[0]

        # Ligne 5 - Soumis (au cours de l'année)
        mask_red_annee = df_cs["Date rédaction"].notna() & (df_cs["Date rédaction"] >= annee_deb)
        n_soumis_annee = df_cs[mask_rea & mask_red_annee].shape[0]

        lignes = [
            (f"{prefix} - à faire (dans les temps)", n_a_faire_dans_les_temps),
            (f"{prefix} - à faire (hors délai)", n_a_faire_hors_delai),
            (f"{prefix} - à faire (absence d'échéance)", n_a_faire_sans_echeance),
            (f"{prefix} - Réalisé (au cours de l'année)", n_rea_annee),
            (f"{prefix} - Soumis (au cours de l'année)", n_soumis_annee)
        ]
        for label, valeur in lignes:
            results.append({
                "Catégorie - Sous-catégorie": label,
                "Valeur": valeur
            })
        current += 1
        if progress_callback and (current % 10 == 0 or current == total):
            percent = int(current * 100 / total)
            progress_callback(percent)

    df_result = pd.DataFrame(results)
    ligne_labels = [
        "- à faire (dans les temps)",
        "- à faire (hors délai)",
        "- à faire (absence d'échéance)",
        "- Réalisé (au cours de l'année)",
        "- Soumis (au cours de l'année)"
    ]
    def tri_ligne(label):
        for i, suffix in enumerate(ligne_labels):
            if label.endswith(suffix):
                cat_souscat = label.replace(suffix, "").strip()
                return (cat_souscat, i)
        return (label, 999)
    df_result = df_result.sort_values(by="Catégorie - Sous-catégorie", key=lambda x: [tri_ligne(l) for l in x])
    if progress_callback: progress_callback(100)
    return df_result.reset_index(drop=True)


def calcul_tdb_section_structure(df, progress_callback=None):
    df = df.copy()
    for col in ["Date de réalisation", "Date limite", "Date rédaction"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    """
    if "Date limite" in df.columns and "Date limite" not in df.columns:
        df["Date limite"] = pd.to_datetime(df["Date limite"], errors="coerce", dayfirst=True)
    """
    min_date = df["Date de réalisation"].min()
    if pd.isnull(min_date):
        if progress_callback: progress_callback(100)
        return None
    start_month = pd.Timestamp(min_date.year, min_date.month, 1)
    end_month = pd.Timestamp(datetime.now().year, datetime.now().month, 1)
    months = pd.date_range(start=start_month, end=end_month, freq='MS')

    results = []
    categorie_souscat = df[["Catégorie", "Sous-catégorie"]].drop_duplicates().reset_index(drop=True)
    total = len(categorie_souscat) * len(months)
    current = 0

    for _, row in categorie_souscat.iterrows():
        cat = row["Catégorie"]
        souscat = row["Sous-catégorie"]
        df_cs = df[(df["Catégorie"] == cat) & (df["Sous-catégorie"] == souscat)]
        if pd.isna(souscat) or souscat == "" or str(souscat).lower() == "nan":
            prefix = f"{cat}"
        else:
            prefix = f"{cat} - {souscat}"
        for m in months:
            month_label = m.strftime('%m-%Y')
            month_start = m
            month_end = (m + relativedelta(months=1)) - pd.Timedelta(days=1)
            mask_a_faire = df_cs["Etat d'avancement"].notna() & ~df_cs["Etat d'avancement"].isin(["Réalisée", "Annulée"])
            mask_limite = df_cs["Date limite"].notna() & (df_cs["Date limite"] >= month_end)
            n_a_faire_dans_les_temps = df_cs[mask_a_faire & mask_limite].shape[0]
            mask_limite_dans_mois = df_cs["Date limite"].notna() & \
                                    (df_cs["Date limite"] >= month_start) & \
                                    (df_cs["Date limite"] <= month_end)
            n_a_faire_echeance_dans_mois = df_cs[mask_a_faire & mask_limite_dans_mois].shape[0]
            mask_limite_hors_delai = df_cs["Date limite"].notna() & (df_cs["Date limite"] < month_start)
            n_a_faire_hors_delai = df_cs[mask_a_faire & mask_limite_hors_delai].shape[0]
            mask_limite_absente = df_cs["Date limite"].isna()
            n_a_faire_sans_echeance = df_cs[mask_a_faire & mask_limite_absente].shape[0]
            mask_rea_mois = df_cs["Etat d'avancement"] == "Réalisée"
            mask_rea_date_mois = df_cs["Date de réalisation"].notna() & \
                                 (df_cs["Date de réalisation"].dt.month == m.month) & \
                                 (df_cs["Date de réalisation"].dt.year == m.year)
            mask_limite_rea = df_cs["Date limite"].notna()
            mask_rea_dans_les_temps = mask_rea_mois & mask_rea_date_mois & mask_limite_rea & \
                                      (df_cs["Date de réalisation"] <= df_cs["Date limite"])
            n_rea_dans_les_temps = df_cs[mask_rea_dans_les_temps].shape[0]
            mask_rea_hors_delai = mask_rea_mois & mask_rea_date_mois & mask_limite_rea & \
                                  (df_cs["Date de réalisation"] > df_cs["Date limite"])
            n_rea_hors_delai = df_cs[mask_rea_hors_delai].shape[0]
            mask_rea_sans_echeance = mask_rea_mois & mask_rea_date_mois & df_cs["Date limite"].isna()
            n_rea_sans_echeance = df_cs[mask_rea_sans_echeance].shape[0]
            mask_soumis = df_cs["Date rédaction"].notna() & \
                          (df_cs["Date rédaction"].dt.month == m.month) & \
                          (df_cs["Date rédaction"].dt.year == m.year)
            n_soumis_dans_mois = df_cs[mask_soumis].shape[0]
            lignes = [
                (f"{prefix} - à faire (dans les temps)", n_a_faire_dans_les_temps),
                (f"{prefix} - à faire (échéance dans le mois)", n_a_faire_echeance_dans_mois),
                (f"{prefix} - à faire (hors délai)", n_a_faire_hors_delai),
                (f"{prefix} - à faire (absence d'échéance)", n_a_faire_sans_echeance),
                (f"{prefix} - Réalisé dans le mois (dans les temps)", n_rea_dans_les_temps),
                (f"{prefix} - Réalisé dans le mois (hors délai)", n_rea_hors_delai),
                (f"{prefix} - Réalisé dans le mois (absence d'échéance)", n_rea_sans_echeance),
                (f"{prefix} - Soumis dans le mois", n_soumis_dans_mois),
            ]
            for idx, (label, valeur) in enumerate(lignes):
                # Pour "Cadrage SR" ou "Cadrage SP", ne garder que "Réalisé dans le mois", "Réalisé", "Soumis dans le
                # mois", "Soumis" (indices 2,3,4,5)
                if cat in ["Cadrage SR", "Cadrage SP"] and idx < 6:
                    continue
                results.append({
                    "Catégorie - Sous-catégorie": label,
                    "Mois": month_label,
                    "Valeur": valeur
                })
            """for label, valeur in lignes:
                results.append({
                    "Catégorie - Sous-catégorie": label,
                    "Mois": month_label,
                    "Valeur": valeur
                })"""
            current += 1
            if progress_callback and (current % 10 == 0 or current == total):
                percent = int(current * 100 / total)
                progress_callback(percent)

    df_result = pd.DataFrame(results)
    pivot = df_result.pivot(index="Catégorie - Sous-catégorie", columns="Mois", values="Valeur").fillna(0).astype(int)
    pivot = pivot.loc[:, (pivot != 0).any(axis=0)]
    ligne_labels = [
        "- à faire (dans les temps)",
        "- à faire (échéance dans le mois)",
        "- à faire (hors délai)",
        "- à faire (absence d'échéance)",
        "- Réalisé dans le mois (dans les temps)",
        "- Réalisé dans le mois (hors délai)",
        "- Réalisé dans le mois (absence d'échéance)",
        "- Soumis dans le mois"
    ]

    def tri_ligne(lab):
        for i, suffix in enumerate(ligne_labels):
            if lab.endswith(suffix):
                cat_souscat = lab.replace(suffix, "").strip()
                return cat_souscat, i
        return lab, 999

    pivot = pivot.sort_index(key=lambda idx: [tri_ligne(val) for val in idx])
    pivot = pivot.reset_index()
    mois_cols = [col for col in pivot.columns if col != "Catégorie - Sous-catégorie"]
    mois_cols_sorted = sorted(mois_cols, key=lambda x: (int(x.split("-")[1]), int(x.split("-")[0])))
    pivot = pivot[["Catégorie - Sous-catégorie"] + mois_cols_sorted]
    if progress_callback:
        progress_callback(100)
    return pivot
