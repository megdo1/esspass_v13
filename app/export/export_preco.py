import openpyxl
from openpyxl.styles import Font, Alignment
from copy import copy
import datetime


def export_preconisations(
    df, trimestre, year, chemin_export, modele_path,
    date_export=None, nom_fichier=None
):
    """
    Exporte le DataFrame indicateurs Préconisations dans le modèle Excel.

    Args:
        df (pd.DataFrame): Tableau indicateurs à exporter (incluant ZP).
        trimestre (str): "Aujourd'hui", "T1", "T2", "T3", "T4".
        year (int): Année en cours.
        chemin_export (str): Chemin cible pour le fichier exporté.
        modele_path (str): Chemin du modèle Excel à utiliser.
        date_export (str, optional): Date formatée pour le remplissage du modèle.
        nom_fichier (str, optional): Nom du fichier de sortie (non utilisé ici, voir main.py pour la logique du nom).
    """
    today_dt = datetime.datetime.now()
    today_str = date_export if date_export else today_dt.strftime("%d-%m-%Y")
    if not chemin_export:
        raise ValueError("Aucun chemin d'export fourni.")

    if trimestre == "Aujourd'hui":
        message_export = (
            "PRECONISATIONS DU DOMAINE OUVRAGES EN TERRE (MT00256)\n"
            f"état au {today_str} - source PIGC"
        )
    else:
        message_export = (
            "PRECONISATIONS DU DOMAINE OUVRAGES EN TERRE (MT00256)\n"
            f"état au {trimestre} {year} - source PIGC"
        )

    wb = openpyxl.load_workbook(modele_path)
    ws = wb.active

    # Ligne 2, cellule D2 : remplacer le message, centré
    ws["D2"].value = message_export
    ws["D2"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Export dès B6
    start_row = 6
    start_col = 2  # B
    nb_cols = len(df.columns)
    style_row_modele = [ws.cell(row=start_row, column=start_col + i) for i in range(nb_cols)]
    styles = []
    for cell in style_row_modele:
        style = {
            "font": cell.font,
            "fill": copy(cell.fill) if cell.fill else None,
            "border": copy(cell.border) if cell.border else None,
            "alignment": copy(cell.alignment) if cell.alignment else None
        }
        styles.append(style)

    for r_idx, row in enumerate(df.itertuples(index=False), 0):
        for c_idx, value in enumerate(row):
            cell = ws.cell(row=start_row + r_idx, column=start_col + c_idx, value=value)
            style = styles[c_idx]
            cell.font = Font(
                bold=False,
                color=style["font"].color if style["font"] else None
            )
            cell.fill = style["fill"]
            cell.border = style["border"]
            cell.alignment = style["alignment"]

    for i in range(nb_cols):
        ws.column_dimensions[openpyxl.utils.get_column_letter(start_col + i)].width = 22

    wb.save(chemin_export)
