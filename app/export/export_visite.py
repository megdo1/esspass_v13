import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from copy import copy
import datetime

import logging
logger = logging.getLogger(__name__)



def export_visites_cycliques(
    df, trimestre, year, chemin_export, modele_path,
    date_export=None, nom_fichier=None
):
    """
    Exporte le DataFrame indicateurs Visites cycliques dans le modèle Excel.
    """
    today_dt = datetime.datetime.now()
    today_str = date_export if date_export else today_dt.strftime("%d-%m-%Y")
    if not chemin_export:
        raise ValueError("Aucun chemin d'export fourni.")

    wb = openpyxl.load_workbook(modele_path)
    ws = wb.active

    # Remplacement des champs entre crochets
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                cell.value = cell.value.replace("[Date export]", today_str)
                if trimestre == "Aujourd'hui":
                    cell.value = cell.value.replace("[Trimestre export]", today_str)
                else:
                    cell.value = cell.value.replace("[Trimestre export]", f"{trimestre} {year}")

    # Emplacement du tableau (à adapter selon modèle)
    start_row = 2
    start_col = 2

    # Vérification du modèle
    header_row_modele = [ws.cell(row=start_row, column=col) for col in range(start_col, start_col + len(df.columns))]
    if len(header_row_modele) != len(df.columns):
        raise ValueError(
            f"Le modèle à la ligne {start_row} ne comporte pas {len(df.columns)} colonnes comme attendu ({len(header_row_modele)} vs {len(df.columns)})"
        )

    # Copier le style du modèle
    header_styles = []
    for cell in header_row_modele:
        style = {
            "font": cell.font,
            "fill": copy(cell.fill) if cell.fill else None,
            "border": copy(cell.border) if cell.border else None,
            "alignment": copy(cell.alignment) if cell.alignment else None
        }
        header_styles.append(style)

    # Écraser la ligne d’en-tête modèle avec style et police grasse
    for c_idx, col_name in enumerate(df.columns):
        cell = ws.cell(row=start_row, column=start_col + c_idx, value=col_name)
        cell.font = Font(
            bold=True,
            color=header_row_modele[c_idx].font.color if header_row_modele[c_idx].font else None
        )
        cell.fill = header_styles[c_idx]["fill"]
        cell.border = header_styles[c_idx]["border"]
        cell.alignment = header_styles[c_idx]["alignment"]

    # Jaune clair
    jaune_clair = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")

    # Insérer les lignes du DataFrame (avec style du modèle, police non-gras)
    for r_idx, row in enumerate(df.itertuples(index=False), 1):
        if r_idx == 1:
            logger.debug("Attributs du premier row : %s", row._fields)

        # Pour trouver l'attribut correspondant à "Indicateur (Validation) en %"
        if r_idx == 1:
            col_missing = "Indicateur (Validation) en %"
            idx_missing = list(df.columns).index(col_missing)
            attr_missing = row._fields[idx_missing]
            logger.debug(f"DEBUG: colonne '{col_missing}' -> attribut '{attr_missing}'")
        # Ensuite, dans chaque ligne :
        is_missing = str(getattr(row, attr_missing, "")).strip().lower() == "données manquantes"

        if is_missing:
            row_excel = start_row + r_idx
            # Index des colonnes à afficher normalement (Infrapôles, ZP, Catégorie action)
            col_debut = start_col
            col_zp = start_col + 1
            col_cat = start_col + 2
            # Les noms de colonnes peuvent varier, mais ici on suppose toujours ce mapping (adapter si besoin)

            # Récupération des valeurs
            """infra_val = getattr(row, "Infrapôles", "")
            zp_val = getattr(row, "ZP", "")
            cat_val = getattr(row, "Catégorie_action", "") if hasattr(row, "Catégorie_action") else getattr(row,
                                                                                                            "Catégorie action",
                                                                                                            "")"""
            # --- Récupération dynamique des attributs ---
            colnames = list(df.columns)
            # Infrapôles
            idx_infra = colnames.index("Infrapôles")
            attr_infra = row._fields[idx_infra]
            infra_val = getattr(row, attr_infra, "")
            # ZP
            idx_zp = colnames.index("ZP")
            attr_zp = row._fields[idx_zp]
            zp_val = getattr(row, attr_zp, "")
            # Catégorie action
            idx_cat = colnames.index("Catégorie action")
            attr_cat = row._fields[idx_cat]
            cat_val = getattr(row, attr_cat, "")

            # Ecrire les 3 premières colonnes normalement
            cell_infra = ws.cell(row=row_excel, column=col_debut, value=str(infra_val))
            cell_infra.font = Font(bold=False)
            cell_infra.alignment = Alignment(horizontal="center", vertical="center")
            cell_infra.fill = jaune_clair

            cell_zp = ws.cell(row=row_excel, column=col_zp, value=str(zp_val))
            cell_zp.font = Font(bold=False)
            cell_zp.alignment = Alignment(horizontal="center", vertical="center")
            cell_zp.fill = jaune_clair

            cell_cat = ws.cell(row=row_excel, column=col_cat, value=str(cat_val))
            cell_cat.font = Font(bold=False)
            cell_cat.alignment = Alignment(horizontal="center", vertical="center")
            cell_cat.fill = jaune_clair

            # Fusionner le reste de la ligne
            col_fusion_start = start_col + 3
            col_fusion_end = start_col + len(df.columns) - 1
            ws.merge_cells(
                start_row=row_excel,
                start_column=col_fusion_start,
                end_row=row_excel,
                end_column=col_fusion_end
            )
            cell_fusion = ws.cell(row=row_excel, column=col_fusion_start)
            cell_fusion.value = "Données manquantes"
            cell_fusion.font = Font(bold=True)
            cell_fusion.alignment = Alignment(horizontal="center", vertical="center")
            cell_fusion.fill = jaune_clair

            # Appliquer le fond jaune sur toutes les cellules fusionnées restantes
            for col_idx in range(col_fusion_start + 1, col_fusion_end + 1):
                ws.cell(row=row_excel, column=col_idx).fill = jaune_clair
        else:
            for c_idx, value in enumerate(row):
                safe_val = str(value) if value is not None else ""
                cell = ws.cell(row=start_row + r_idx, column=start_col + c_idx, value=safe_val)
                style = header_styles[c_idx]
                cell.font = Font(
                    bold=False,
                    color=style["font"].color if style["font"] else None
                )
                cell.fill = style["fill"]
                cell.border = style["border"]
                cell.alignment = style["alignment"]

    # Largeur colonnes
    for i in range(len(df.columns)):
        ws.column_dimensions[openpyxl.utils.get_column_letter(start_col + i)].width = 22

    wb.save(chemin_export)