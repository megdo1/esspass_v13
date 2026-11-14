import pandas as pd
import datetime


def date_fin_trimestre(annee, trimestre):
    # trimestre: "T1", "T2", "T3", "T4"
    t_map = {"T1": (3, 31), "T2": (6, 30), "T3": (9, 30), "T4": (12, 31)}
    mois, jour = t_map[trimestre]
    return datetime.datetime(annee, mois, jour)


def trimestre_courant(dt=None):
    """Retourne (année, 'Tn') du dernier trimestre courant à une date donnée"""
    if dt is None:
        dt = datetime.datetime.now()
    mois = dt.month
    if mois <= 3:
        return dt.year, "T1"
    elif mois <= 6:
        return dt.year, "T2"
    elif mois <= 9:
        return dt.year, "T3"
    else:
        return dt.year, "T4"


def dernier_trimestre_termine(dt=None):
    """
    Retourne (année, trimestre) du dernier trimestre entièrement terminé par rapport à la date dt (ou aujourd'hui).
    Ex: le 08/08/2025 => (2025, "T2")
    """
    if dt is None:
        dt = datetime.datetime.now()
    annee = dt.year
    mois = dt.month
    if mois >= 10:
        return annee, "T3"
    elif mois >= 7:
        return annee, "T2"
    elif mois >= 4:
        return annee, "T1"
    else:
        return annee - 1, "T4"


def calcul_indicateurs_preco(df, trimestre, year=None):
    """
    Calcule les indicateurs pour la vue ES-IND -> OT -> Préconisations.

    Args:
        df (pd.DataFrame): DataFrame issu du fichier Excel chargé.
        trimestre (str): Un des labels "Aujourd'hui", "T1", "T2", "T3", "T4".
        year (int): L'année en cours (défaut : année système).

    Returns:
        pd.DataFrame: DataFrame indicateurs (prêt à afficher ou exporter).

    Raises:
        ValueError: Si colonne(s) critique(s) absente(s).
    """
    if year is None:
        year = datetime.datetime.now().year

    # Recherche colonne ZP
    col_zp = None
    for col in df.columns:
        col_norm = col.lower().strip().replace('\n', ' ').replace('\r', ' ')
        if col_norm == "désignation zp ouvrage" or col_norm == "designation zp ouvrage":
            col_zp = col
            break

    # Vérification colonnes critiques
    required_cols = ["Infrapôle", "Urgence", "Statut", "Statut échéance", "Echéance", "Enjeu sécurité"]

    for rc in required_cols:
        if rc not in df.columns:
            raise ValueError(f"Colonne '{rc}' absente du fichier chargé.")

    # -- Nouvelle logique trimestre dans le passé ou non
    is_aujourdhui = (trimestre == "Aujourd'hui")

    if not is_aujourdhui:
        # Récupère l'année et le trimestre sélectionné
        annee_select = int(year)
        trimestre_select = trimestre
        date_fin_selected = date_fin_trimestre(annee_select, trimestre_select)

        # Calcule le dernier trimestre par rapport à aujourd'hui
        # annee_cur, trimestre_cur = trimestre_courant()
        # date_fin_trimestre_courant = date_fin_trimestre(annee_cur, trimestre_cur)

        # Détermine la date de fin du dernier trimestre complètement terminé
        annee_termine, trimestre_termine = dernier_trimestre_termine()
        date_fin_trimestre_termine = date_fin_trimestre(annee_termine, trimestre_termine)

        # Le trimestre sélectionné est-il dans le passé ?
        # On est "dans le passé" si la date de fin du trimestre choisi < date de fin du dernier trimestre terminé
        trimestre_dans_le_passe = (date_fin_selected < date_fin_trimestre_termine)
    else:
        trimestre_dans_le_passe = False
        date_fin_selected = datetime.datetime.now()

    # Calcul groupé
    grouped = df.groupby("Infrapôle")
    result = []

    for infrapole, data in grouped:
        # Colonne ZP (sécurisée)
        # print(f"DEBUG(Préconisations): calcul_indicateurs_preco - 1: {col_zp}", flush=True)
        if col_zp and not data[col_zp].isnull().all():
            try:
                zp_val = data[col_zp].mode().iat[0] if not data[col_zp].mode().empty else ""
                # print(f"DEBUG(Préconisations): calcul_indicateurs_preco - 2: {zp_val}", flush=True)
            except Exception:
                zp_val = ""
        else:
            zp_val = ""

        if not is_aujourdhui and trimestre_dans_le_passe:
            # Filtrer sur les préconisations <= date de fin du trimestre choisi
            data = data.copy()
            data["Date première préco_dt"] = pd.to_datetime(data["Date de la première préconisation"], errors='coerce',
                                                            dayfirst=True)
            mask_avant_trimestre = data["Date première préco_dt"].le(date_fin_selected)

            # 1. Préconisé avant {trimestre}-{année} toujours en cours
            # Statut non dans la liste
            statuts_exclus = ["Amortie", "Annulée", "Mise en place", "Levée"]
            mask_encours = ~data["Statut"].isin(statuts_exclus)
            indic_encours = data[mask_avant_trimestre & mask_encours].groupby("Infrapôle").size().get(infrapole, 0)

            # 2. Sortie après trimestre
            # Colonnes de dates à vérifier
            cols_dates_sortie = [
                "Date de réalisation des travaux",
                "Date annulation",
                "Date de mise en place",
                "Date de levée"
            ]
            mask_sortie_apres = pd.Series(False, index=data.index)
            for col in cols_dates_sortie:
                if col in data.columns:
                    date_col = pd.to_datetime(data[col], errors='coerce', dayfirst=True)
                    mask_sortie_apres = mask_sortie_apres | (mask_avant_trimestre & date_col.gt(date_fin_selected))
            indic_sortie_apres = data[mask_sortie_apres].groupby("Infrapôle").size().get(infrapole, 0)

            # Tu peux stocker ces deux valeurs dans le result[] à la place/ajout des indicateurs
            result.append([
                infrapole,
                zp_val,
                indic_encours,  # Préconisé avant {trimestre} toujours en cours
                indic_sortie_apres  # Préconisé avant {trimestre} mais sortie après
            ])
        else:
            # Gestion du trimestre/date limite
            # print(f"DEBUG(Préconisations): calcul_indicateurs_preco - 3: {trimestre}-{year}", flush=True)
            if trimestre != "Aujourd'hui":
                t_map = {"T1": (3, 31), "T2": (6, 30), "T3": (9, 30), "T4": (12, 31)}
                mois, jour = t_map[trimestre]
                date_limite = datetime.datetime(year, mois, jour)
                data = data.copy()
                data["Echéance_dt"] = pd.to_datetime(data["Echéance"], errors='coerce', dayfirst=True)
                condition_echeance = data["Echéance_dt"].le(date_limite)
            else:
                # date_limite = datetime.datetime.now().date()
                # date_limite = pd.to_datetime(datetime.datetime.now().date())
                date_limite = pd.Timestamp('today').normalize()
                data["Echéance_dt"] = pd.to_datetime(data["Echéance"], errors='coerce', dayfirst=True)
                condition_echeance = data["Echéance_dt"].le(date_limite)
                # condition_echeance = (data["Statut échéance"] == "En retard")

            statuts_exclus = ["Amortie", "Annulée", "Mise en place", "Levée"]
            mask_encours = ~data["Statut"].isin(statuts_exclus)

            # Indicateurs U0
            u0_total = len(data[(data["Urgence"] == "U0") & mask_encours])
            u0_echues = len(data[(data["Urgence"] == "U0") & condition_echeance & mask_encours])
            u0_risque = len(data[(data["Urgence"] == "U0")
                                 & condition_echeance & mask_encours
                                 & data["Statut"].isin(["Demande ADR", "En attente ADR", "En attente de validation"])])

            # Indicateurs U1
            u1_total = len(data[(data["Urgence"] == "U1") & (data["Enjeu sécurité"] == "Oui") & mask_encours])
            mask_u1_echues = ((data["Urgence"] == "U1") & (data["Enjeu sécurité"] == "Oui") & condition_echeance
                              & mask_encours)
            mask_u1_risque = (mask_u1_echues
                              & data["Statut"].isin(["Demande ADR", "En attente ADR", "En attente de validation"]))

            u1_echues = len(data[mask_u1_echues])
            u1_risque = len(data[mask_u1_risque])
            # print(f"{infrapole}:{u1_total}-{u1_echues}-{u1_risque}", flush=True)

            result.append([
                infrapole,
                zp_val,
                u0_total,
                u0_echues,
                u0_risque,
                u1_total,
                u1_echues,
                u1_risque
            ])

    # -- Construction du DataFrame résultat selon le mode --
    if not is_aujourdhui and trimestre_dans_le_passe:
        indicator_df = pd.DataFrame(result, columns=[
            "Infrapôle", "ZP",
            f"Préconisé avant {trimestre}-{year} toujours en cours",
            f"Préconisé avant {trimestre}-{year} / traité ou annulé aprés {trimestre}-{year}"
        ])
    else:
        indicator_df = pd.DataFrame(result, columns=[
            "Infrapôle", "ZP",
            "U0 Nombre total de préconisations", "U0 Préconisations échues",
            "U0 Analyse de risque - demandées ou en cours",
            "U1 Nombre total de préconisations", "U1 Préconisations échues",
            "U1 Analyse de risque - demandées ou en cours"
        ])
    """indicator_df = pd.DataFrame(result, columns=[
        "Infrapôle", "ZP",
        "U0 Nombre total de préconisations", "U0 Préconisations échues",
        "U0 Analyse de risque - demandées ou en cours",
        "U1 Nombre total de préconisations", "U1 Préconisations échues",
        "U1 Analyse de risque - demandées ou en cours"
    ])"""
    return indicator_df
