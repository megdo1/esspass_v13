import pandas as pd
import openpyxl


def extract_data_after_second_empty_row(excel_path):
    """
    Extrait la zone de données d’un fichier Excel selon la règle métier :
    - Première ligne : nom de la source (à ignorer)
    - Première ligne vide (à ignorer)
    - Critères variables (à ignorer)
    - Deuxième ligne vide (marqueur)
    - Puis tableau de données à analyser (ligne d'en-tête)

    Args:
        excel_path (str): Chemin vers le fichier Excel à analyser.

    Returns:
        tuple: (df_data, idx_en_tete)
            df_data (pd.DataFrame): DataFrame des données à analyser (avec l'en-tête)
            idx_en_tete (int): Index (ligne, base 0) de la ligne d'en-tête détectée
        None, None si la structure n'est pas conforme.
    """
    xl = pd.ExcelFile(excel_path)
    sheet = xl.sheet_names[0]
    df_full = xl.parse(sheet, header=None)
    empty_count = 0
    start_data_idx = None
    for idx, row in df_full.iterrows():
        if row.isnull().all() or all(str(x).strip() == "" for x in row):
            empty_count += 1
        if empty_count == 2:
            start_data_idx = idx + 1
            break
    if start_data_idx is None:
        return None, None  # Structure non conforme
    df_data = xl.parse(sheet, header=start_data_idx)
    return df_data, start_data_idx


def check_required_columns(df, required_cols):
    """
    Vérifie la présence des colonnes requises dans le DataFrame.

    Args:
        df (pd.DataFrame): DataFrame à contrôler.
        required_cols (list): Liste des colonnes attendues.

    Returns:
        list: Liste des colonnes absentes (sinon liste vide).
    """
    missing = [col for col in required_cols if col not in df.columns]
    return missing


def extract_data_pigc_file_granular(excel_path, progress_callback=None):
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active
    total_rows = ws.max_row
    if progress_callback: progress_callback(2)
    rows = []
    empty_count = 0
    start_data_idx = None
    idx_en_tete = None
    reading_data = False
    header_found = False
    header = None
    data = []

    for idx, row in enumerate(ws.iter_rows(values_only=True), start=0):
        if all((cell is None or str(cell).strip() == "") for cell in row):
            empty_count += 1
            continue
        if empty_count < 2:
            continue
        if not header_found:
            # Première ligne NON vide après 2e ligne vide = header
            header = [str(cell).strip() if cell is not None else "" for cell in row]
            idx_en_tete = idx
            header_found = True
            continue
        # Après l’en-tête, lignes de données
        data.append(row)
        if progress_callback and total_rows > 0:
            percent = int(idx * 60 / total_rows)
            progress_callback(percent)
    if not header_found or not data:
        if progress_callback: progress_callback(100)
        return None, None
    # On construit le DataFrame
    chunk_size = 100
    df_chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        df_chunk = pd.DataFrame(chunk, columns=header)
        df_chunks.append(df_chunk)
        if progress_callback:
            percent = 60 + int(i * 40 / max(1, len(data)))
            progress_callback(min(percent, 99))

    # Harmonise les colonnes et ne garde que les chunks vraiment utiles
    df_chunks_clean = []
    for df in df_chunks:
        if df.empty:
            continue
        # Exclut tout chunk où toutes les colonnes sont None/NA
        col_ok = [col for col in df.columns if col is not None and col != ""]
        if not col_ok:
            continue
        # Vérifie que la DataFrame a au moins UNE valeur non-NA sur une colonne réelle
        if df[col_ok].notna().values.any():
            df_chunks_clean.append(df.reindex(columns=header))

    if df_chunks_clean:
        # Nettoyage des colonnes all-NA dans chaque chunk
        for i, df in enumerate(df_chunks_clean):
            df_chunks_clean[i] = df.loc[:, ~df.isna().all()]

        df_data = pd.concat(df_chunks_clean, ignore_index=True)
        # Facultatif : nouvelle passe sur le résultat final
        df_data = df_data.loc[:, ~df_data.isna().all()]
    else:
        df_data = pd.DataFrame(columns=[col for col in header if col and col != "None"])

    df_data.columns = [str(col).strip() if col is not None else "" for col in df_data.columns]
    if progress_callback:
        progress_callback(100)
    return df_data, idx_en_tete
