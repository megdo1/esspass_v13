import pandas as pd
import datetime


INFRAPOLES_REFERENCE = [
    "INFRAPOLE Alpes",
    "INFRAPOLE Aquitaine",
    "INFRAPOLE Auvergne Nivernais",
    "INFRAPOLE Bourgogne Franche-Comté",
    "INFRAPOLE Bretagne",
    "INFRAPOLE Centre",
    "INFRAPOLE Champagne-Ardenne",
    "INFRAPOLE Est-Européen",
    "INFRAPOLE Haute-Picardie",
    "INFRAPOLE Indre Limousin",
    "INFRAPOLE Languedoc-Roussillon",
    "INFRAPOLE LGV Atlantique",
    "INFRAPOLE LGV Sud Est Européen",
    "INFRAPOLE Lorraine",
    "INFRAPOLE Midi-Pyrénées",
    "INFRAPOLE Nord Européen",
    "INFRAPOLE Nord-Pas-de-Calais",
    "INFRAPOLE Normandie",
    "INFRAPOLE PACA",
    "INFRAPOLE Paris Saint-Lazare",
    "INFRAPOLE Paris Sud Ouest",
    "INFRAPOLE Paris-Est",
    "INFRAPOLE Paris-Nord",
    "INFRAPOLE Paris-Sud-Est",
    "INFRAPOLE Pays-de-Loire",
    "INFRAPOLE Poitou-Charentes",
    "INFRAPOLE Rhénan",
    "INFRAPOLE Rhodanien",
]

CATEGORIES_REFERENCE = ["VA", "VD", "VI", "VP"]


def calcul_indicateurs_visite(df, trimestre, year=None):
    """
    Calcule les indicateurs pour la vue ES-IND -> OT -> Visites cycliques.

    Args:
        df (pd.DataFrame): Le DataFrame issu du fichier Excel chargé.
        trimestre (str): Un des labels "Aujourd'hui", "T1", "T2", "T3", "T4".
        year (int): L'année en cours (par défaut, année système).

    Returns:
        pd.DataFrame: DataFrame des indicateurs prêts à l'affichage/export.
    Raises:
        ValueError: Si colonne(s) critique(s) manquante(s)
    """

    if year is None:
        year = datetime.datetime.now().year
    """
    # Filtre 1 : "Année de programmation"
    if "Année de programmation" in df.columns:
        prog_col = pd.to_numeric(df["Année de programmation"], errors="coerce")
        df = df[prog_col.fillna(0).astype(int) >= year]
    # Si absente, on ne filtre pas mais on continue (le contrôle UI affiche l'avertissement).
    """
    # Filtre 2 : éliminer les actions "Annulée"
    if "Etat d'avancement" in df.columns:
        df = df[df["Etat d'avancement"] != "Annulée"]
    # Si absente, on ne filtre pas mais on continue (le contrôle UI affiche l'avertissement). ?????????????
    """
    # Filtre 3 : éliminer les actions avec année(Date) différent de l'année choisie
    if "Date" in df.columns and year is not None:
        try:
            dates = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
            df = df[dates.dt.year == year]
        except Exception:
            pass
    """
    if "Date" in df.columns and "Année de programmation" in df.columns and year is not None:
        dates = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        prog_col = pd.to_numeric(df["Année de programmation"], errors="coerce").astype("Int64")
        end_of_year = pd.Timestamp(year=year, month=12, day=31)
        cond_A = (dates.dt.year == year) & (prog_col >= year)
        cond_B = (prog_col == year) & (dates > end_of_year)
        df = df[cond_A | cond_B]
    else:
        pass


    # 2. Recherche colonne ZP (désignation ZP ouvrage)
    col_zp = None
    for col in df.columns:
        col_norm = col.lower().strip().replace('\n', ' ').replace('\r', ' ')
        if col_norm == "désignation zp ouvrage" or col_norm == "designation zp ouvrage":
            col_zp = col
            break

    # 3. Colonnes critiques
    required_cols = ["Infrapôle", "Catégorie", "Etat d'avancement", "Statut"]
    for rc in required_cols:
        if rc not in df.columns:
            raise ValueError(f"Colonne '{rc}' absente du fichier chargé.")

    # 4. Recherche colonne date de réalisation/validation
    col_date_rea = None
    for c in df.columns:
        if "date de réalis" in c.lower():
            col_date_rea = c
            break
    if not col_date_rea:
        raise ValueError("Colonne 'Date de réalisation' absente du fichier chargé.")

    col_date_val = None
    for c in df.columns:
        if "date valid" in c.lower():
            col_date_val = c
            break
    if not col_date_val:
        raise ValueError("Colonne 'Date validation' absente du fichier chargé.")

    # 5. Trimestre/limite de date
    today_dt = datetime.datetime.now()
    today_str = today_dt.strftime("%d/%m/%Y")

    if trimestre == "Aujourd'hui":
        limite = today_dt
        real_date_label = today_str
        pv_label = today_str
    else:
        """
        fin_trimestre = {"T1": "31/03", "T2": "30/06", "T3": "30/09", "T4": "31/12"}[trimestre]
        date_limite_str = f"{fin_trimestre}/{year}"
        limite = datetime.datetime.strptime(date_limite_str, "%d/%m/%Y")
        real_date_label = f"la fin du {trimestre} {year}"
        pv_label = f"la fin du {trimestre} {year}""
        """
        fin_trimestre_dict = {
            "T1": f"31/03/{year}",
            "T2": f"30/06/{year}",
            "T3": f"30/09/{year}",
            "T4": f"31/12/{year}",
            "T5": f"31/03/{year + 1}"
        }
        date_limite_str = fin_trimestre_dict[trimestre]
        limite = datetime.datetime.strptime(date_limite_str, "%d/%m/%Y")
        real_date_label = f"la fin du {trimestre} {year if trimestre != 'T5' else year + 1}"
        pv_label = f"la fin du {trimestre} {year if trimestre != 'T5' else year + 1}"

    statut_valide = {
        "PV pré-visé", "PV validé", "PV validé et PAC en cours", "PV validé et PAC réalisé", "PV visé", "PV visé OA",
        "CR Validé / En attente avis RMOAOT", "CR Validé / En attente avis COT", "CR Validé / Avis COT réalisé",
        "CR Validé / Avis RMOAOT réalisé", "CR validé", "CR pré-visé", "CR visé"
    }

    # 6. Calcul groupé
    result = []
    grouped = df.groupby(["Infrapôle", "Catégorie"])

    for (infrapole, categorie), group in grouped:
        total = len(group)
        group = group.copy()
        group[col_date_rea] = pd.to_datetime(group[col_date_rea], errors='coerce', dayfirst=True)
        group[col_date_val] = pd.to_datetime(group[col_date_val], errors='coerce', dayfirst=True)
        realisees = group[group[col_date_rea].notna() & (group[col_date_rea] <= limite)]
        nb_real = len(realisees)
        indic_rea = (nb_real / total * 100) if total > 0 else 0
        pv_valides = realisees[
            realisees["Statut"].isin(statut_valide) &
            (realisees[col_date_val].notna()) &
            (realisees[col_date_val] <= limite)
        ]

        pv_count = len(pv_valides)
        indic_val = (pv_count / nb_real * 100) if nb_real > 0 else 0

        # Colonne ZP (sécurisée)
        zp_val = ""
        if col_zp and col_zp in group.columns:
            zp_col = group[col_zp].dropna()
            if not zp_col.empty:
                try:
                    zp_val = str(zp_col.mode().iat[0]) if not zp_col.mode().empty else ""
                except Exception:
                    zp_val = ""
        else:
            zp_val = ""

        result.append([
            infrapole,
            zp_val,
            categorie,
            total,
            nb_real,
            f"{indic_rea:.1f}%",
            "",  # Commentaires (champ éditable)
            pv_count,
            f"{indic_val:.1f}%"
        ])

    col_real_label = f"Réalisées à {real_date_label}"
    col_pv_label = f"PV validés à {pv_label}"
    indicator_df = pd.DataFrame(result, columns=[
        "Infrapôles", "ZP", "Catégorie action",
        f"Prévision {year}", col_real_label, "Indicateur (Réalisation) en %",
        "Commentaires", col_pv_label, "Indicateur (Validation) en %"
    ])

    # Ajout des infrapôles absents avec mention "Données manquantes"
    infrapoles_present = set(indicator_df["Infrapôles"].unique())

    """for infrapole_ref in INFRAPOLES_REFERENCE:
        if infrapole_ref not in infrapoles_present:
            \"""
            missing_row = {
                "Infrapôles": infrapole_ref,
                "ZP": "Données manquantes",
                "Catégorie action": "",
                f"Prévision {year}": "",
                col_real_label: "",
                "Indicateur (Réalisation) en %": "",
                "Commentaires": "",
                col_pv_label: "",
                "Indicateur (Validation) en %": "Données manquantes"
            }
            indicator_df = pd.concat([indicator_df, pd.DataFrame([missing_row])], ignore_index=True)
            \"""
            # Construction sécurisée de la ligne vide
            missing_row = {col: "" for col in indicator_df.columns}
            missing_row["Infrapôles"] = infrapole_ref
            missing_row["ZP"] = "Données manquantes"
            missing_row["Indicateur (Validation) en %"] = "Données manquantes"
            indicator_df = pd.concat([indicator_df, pd.DataFrame([missing_row])], ignore_index=True)"""

    for infrapole_ref in INFRAPOLES_REFERENCE:
        for cat_ref in CATEGORIES_REFERENCE:
            masque = (
                    (indicator_df["Infrapôles"] == infrapole_ref)
                    & (indicator_df["Catégorie action"] == cat_ref)
            )
            if not masque.any():
                zp_vals = indicator_df.loc[
                    indicator_df["Infrapôles"] == infrapole_ref, "ZP"
                ]
                if not zp_vals.empty and not zp_vals.isin(["", "Données manquantes"]).all():
                    zp_val = zp_vals[zp_vals != "Données manquantes"].mode()
                    zp_val = zp_val.iat[0] if not zp_val.empty else ""
                else:
                    zp_val = ""
                missing_row = {col: "" for col in indicator_df.columns}
                missing_row["Infrapôles"] = infrapole_ref
                missing_row["Catégorie action"] = cat_ref
                missing_row["ZP"] = zp_val
                missing_row["Indicateur (Validation) en %"] = "Données manquantes"
                indicator_df = pd.concat([indicator_df, pd.DataFrame([missing_row])], ignore_index=True)

    # Remettre l'ordre des infrapôles selon la référence
    indicator_df["Infrapôles"] = pd.Categorical(
        indicator_df["Infrapôles"], categories=INFRAPOLES_REFERENCE, ordered=True
    )
    indicator_df["Catégorie action"] = pd.Categorical(
        indicator_df["Catégorie action"], categories=CATEGORIES_REFERENCE, ordered=True
    )
    # indicator_df = indicator_df.sort_values("Infrapôles").reset_index(drop=True)
    indicator_df = indicator_df.sort_values(["Infrapôles", "Catégorie action"]).reset_index(drop=True)

    """
    print("DEBUG: Colonnes indicator_df:", indicator_df.columns)
    print("DEBUG: Shape indicator_df:", indicator_df.shape)
    print("DEBUG: Types:", indicator_df.dtypes)
    print("DEBUG: Valeurs uniques Infrapôles:", indicator_df["Infrapôles"].unique())
    """

    # Nettoyage du DataFrame pour robustesse UI/affichage
    indicator_df = indicator_df.astype(str).fillna("")
    indicator_df = indicator_df.reset_index(drop=True)
    return indicator_df
