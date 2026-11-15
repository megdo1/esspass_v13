import pandas as pd
import openpyxl
import re
from openpyxl.utils import get_column_letter
from shutil import copyfile

import logging
logger = logging.getLogger(__name__)



def export_oa_indicateurs(df_indicateurs: pd.DataFrame, trimestre: str, annee: int, infrapole: str,
                           chemin_export: str, chemin_modele: str) -> None:
    # 1. Copier le modèle
    copyfile(chemin_modele, chemin_export)
    wb = openpyxl.load_workbook(chemin_export)
    ws = wb.active

    # 2. Nettoyer l’infrapôle (retirer le mot "INFRAPOLE" insensible à la casse)
    infrapole_clean = re.sub(r'^(?i)infrap[oô]le[\s\u00A0]+', '', infrapole, flags=re.IGNORECASE).strip()

    logger.info(f"infrapôle {infrapole}, court: {infrapole_clean}")
    # 3. Préparer les variables à remplacer
    valeurs_vars = {
        "[année]": str(annee),
        "[année+1]": str(annee + 1),
        "[trimestre]": trimestre,
        "[infrapôle]": infrapole.strip(),
        "[infrapole_court]": infrapole_clean,
    }

    # 4. Remplacer les balises [xxx] dans toutes les cellules
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                for tag, val in valeurs_vars.items():
                    if tag in cell.value:
                        cell.value = cell.value.replace(tag, val)

    # 5. Trouver la colonne "titre indicateur" dans la ligne 5
    ligne_titre = 5
    col_titre_idx = None
    for cell in ws[ligne_titre]:
        if isinstance(cell.value, str) and cell.value.strip().lower() == "titre indicateur":
            col_titre_idx = cell.col_idx  # openpyxl indexe à partir de 1
            break

    if not col_titre_idx:
        raise ValueError("Colonne 'titre indicateur' non trouvée dans la ligne 5.")

    # 6. Construire dictionnaire {indicateur: [T1, T2, ...]}
    indic_dict = dict(zip(df_indicateurs["Indicateur"], df_indicateurs.iloc[:, 1:].values.tolist()))

    # 7. Écriture à partir de la colonne E (colonne 5), soit col_titre_idx + 1
    for row in ws.iter_rows(min_row=ligne_titre + 1):
        titre_cell = row[col_titre_idx - 1]  # attention : col_titre_idx est 1-based
        if titre_cell.value and titre_cell.value in indic_dict:
            valeurs = indic_dict[titre_cell.value]
            for i, val in enumerate(valeurs):
                col_dest = col_titre_idx + i + 1  # +1 pour commencer après la colonne "titre indicateur"
                col_letter = get_column_letter(col_dest)
                ws[f"{col_letter}{titre_cell.row}"] = val

    wb.save(chemin_export)