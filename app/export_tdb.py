import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from copy import copy
import datetime


def export_tdb(
    df, trimestre, year, chemin_export, modele_path,
    date_export=None, nom_fichier=None
):
    """
    Exporte le DataFrame TDB dans le modèle Excel.
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
        # Détection "Données manquantes"
        is_missing = (
            "ZP" in df.columns and
            str(getattr(row, "ZP")).strip().lower() == "données manquantes"
        )

        if is_missing:
            infra_val = getattr(row, "Infrapôles", "")
            row_excel = start_row + r_idx
            col_infra = start_col

            # Colonne Infrapôles
            cell_infra = ws.cell(row=row_excel, column=col_infra, value=str(infra_val))
            cell_infra.font = Font(bold=False)
            cell_infra.alignment = Alignment(horizontal="center", vertical="center")
            cell_infra.fill = jaune_clair

            # Fusion et style pour "Données manquantes"
            if len(df.columns) > 1:
                ws.merge_cells(
                    start_row=row_excel,
                    start_column=col_infra + 1,
                    end_row=row_excel,
                    end_column=col_infra + len(df.columns) - 1
                )
                cell = ws.cell(row=row_excel, column=col_infra + 1)
                cell.value = "Données manquantes"
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = jaune_clair
                for col_idx in range(col_infra + 2, col_infra + len(df.columns)):
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