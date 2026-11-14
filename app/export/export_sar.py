from openpyxl import load_workbook


def export_sar_indicateurs(df_indicateurs, trimestre, annee, file_name, model_path):
    wb = load_workbook(model_path)
    ws = wb.active

    # 1. Construire le dictionnaire des remplacements globaux
    replacements = {
        "[Année]": str(annee),
        "[année]": str(annee),
        "[Trimestre]": trimestre,
        "[trimestre]": trimestre,
        "[année +1]": str(annee + 1),
        "[Année +1]": str(annee + 1),
    }

    # 2. Remplacer les balises dans toutes les cellules
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                for key, val in replacements.items():
                    if key in cell.value:
                        cell.value = cell.value.replace(key, val)

    # 3. Insérer les données indicateurs dans les zones fixes
    def insert_values(df, row_start, lignes_idx):
        for i, idx in enumerate(lignes_idx):
            if idx < len(df):
                row = row_start + i
                for j, col in enumerate(df.columns[1:]):  # on saute "Indicateur"
                    val = df.iloc[idx, j + 1]
                    col_letter = chr(ord("C") + j)  # C, D, E, ...
                    ws[f"{col_letter}{row}"] = val

    insert_values(df_indicateurs, row_start=6, lignes_idx=range(0, 5))     # C6+
    insert_values(df_indicateurs, row_start=12, lignes_idx=range(5, 10))   # C12+
    insert_values(df_indicateurs, row_start=18, lignes_idx=range(10, 13))  # C18+
    insert_values(df_indicateurs, row_start=22, lignes_idx=range(13, 16))  # C22+

    wb.save(file_name)
