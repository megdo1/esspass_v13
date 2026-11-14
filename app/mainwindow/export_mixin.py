"""Export Excel des résultats par vue."""

from PyQt5.QtWidgets import QFileDialog, QMessageBox
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from copy import copy
import datetime
from app.ressources import MODEL_PRECO_PATH, MODEL_VISITES_PATH


class ExportMixin:
    """Export Excel des résultats par vue."""

    def export_result_for_view(self, key):
        df = self.indicators_by_view.get(key)
        if df is None:
            return
        # --- Export Visites cycliques ---
        if key == ("ES-IND", "OT", "Visites cycliques"):
            widget = self.zone3_widgets[key]
            df = self.sync_commentaires_from_table(widget.table, df, commentaire_col="Commentaires")
            # modele_path = "export_model\\Model_Export_ES-IND_OT_Visites-Cycliques_v1.xlsx"
            modele_path = MODEL_VISITES_PATH
            today_dt = datetime.datetime.now()
            today_str = today_dt.strftime("%d-%m-%Y")
            trimestre_labels = ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"]
            trimestre_index = next(
                (i for i, btn in enumerate(self.zone3_widgets[key].trimestre_radios) if btn.isChecked()), 0)
            selected_trimestre = trimestre_labels[trimestre_index]

            # year = today_dt.year

            # --- Utilisation de l'année choisie dans la combo si activée ---
            try:
                combo_annee = self.zone3_widgets[key].combo_annee
                if combo_annee.isEnabled():
                    year = combo_annee.currentText()
                else:
                    year = str(today_dt.year)
            except Exception:
                year = str(today_dt.year)

            if selected_trimestre == "Aujourd'hui":
                nom_fichier = f"Visites-cycliques_indicateur-OT_{today_str}.xlsx"
            else:
                nom_fichier = f"Visites-cycliques_indicateur-OT_{selected_trimestre}_{year}.xlsx"

            file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
            if not file_name:
                return

            try:
                wb = openpyxl.load_workbook(modele_path)
                ws = wb.active

                # Remplacement des champs entre crochets
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            cell.value = cell.value.replace("[Date export]", today_str)
                            if selected_trimestre == "Aujourd'hui":
                                cell.value = cell.value.replace("[Trimestre export]", today_str)
                            else:
                                cell.value = cell.value.replace("[Trimestre export]",
                                                                f"{selected_trimestre} {year}")

                start_row = 2
                start_col = 2

                # Vérification sécurité : la ligne modèle a-t-elle le bon nombre de colonnes ?
                header_row_modele = [ws.cell(row=start_row, column=col) for col in
                                     range(start_col, start_col + len(df.columns))]
                if len(header_row_modele) != len(df.columns):
                    QMessageBox.critical(self, "Export impossible",
                                         f"Incohérence : le modèle à la ligne {start_row} ne comporte pas {len(df.columns)} colonnes comme attendu ({len(header_row_modele)} vs {len(df.columns)}).\n"
                                         "Merci de vérifier le modèle ou d’adapter le code à la structure exacte.")
                    return

                # Copier le style du modèle
                header_styles = []
                for cell in header_row_modele:
                    style = {
                        "font": cell.font,
                        "fill": cell.fill,
                        "border": cell.border,
                        "alignment": cell.alignment
                    }
                    header_styles.append(style)

                # Écraser la ligne d’en-tête modèle avec style et police grasse
                for c_idx, col_name in enumerate(df.columns):
                    cell = ws.cell(row=start_row, column=start_col + c_idx, value=col_name)
                    cell.font = Font(
                        bold=True,
                        color=header_row_modele[c_idx].font.color if header_row_modele[c_idx].font else None
                    )
                    cell.fill = copy(header_row_modele[c_idx].fill) if header_row_modele[c_idx].fill else None
                    cell.border = copy(header_row_modele[c_idx].border) if header_row_modele[c_idx].border else None
                    cell.alignment = copy(header_row_modele[c_idx].alignment) if header_row_modele[
                        c_idx].alignment else None

                # Jaune clair (tu peux adapter la teinte : FFFF99 ou FFFFC2)
                jaune_clair = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")

                # Insérer les lignes du DataFrame (avec style du modèle, police non-gras)
                for r_idx, row in enumerate(df.itertuples(index=False), 1):
                    """
                    # Trouve dynamiquement le bon champ
                    if r_idx == 1:
                        print("Champs disponibles dans row :", row._fields)
                    indic_val_col = None
                    for f in row._fields:
                        if "validation" in f.lower() and "indicateur" in f.lower():
                            indic_val_col = f
                            break
                    if indic_val_col is None:
                        raise Exception(
                            "Impossible de trouver le champ 'Indicateur (Validation) en %' dans : " + str(row._fields))

                    is_missing = str(getattr(row, indic_val_col)).strip().lower() == "données manquantes"
                    is_missing = (
                            "Indicateur (Validation) en %" in df.columns and
                            str(getattr(row, "Indicateur_Validation_en___")).strip().lower() == "données manquantes"
                    )
                    """
                    is_missing = (
                            "ZP" in df.columns and
                            str(getattr(row, "ZP")).strip().lower() == "données manquantes"
                    )

                    if is_missing:
                        # Ecrire l'infrapôle dans la 1ère colonne
                        # ws.cell(row=start_row + r_idx, column=start_col, value=getattr(row, "Infrapôles"))
                        infra_val = getattr(row, "Infrapôles", "")
                        ws.cell(row=start_row + r_idx, column=start_col, value=str(infra_val))

                        row_excel = start_row + r_idx
                        col_infra = start_col

                        # 1. Écrire et styler la colonne Infrapôles (centré + fond jaune)
                        cell_infra = ws.cell(row=row_excel, column=col_infra, value=str(infra_val))
                        cell_infra.font = Font(bold=False)
                        cell_infra.alignment = Alignment(horizontal="center", vertical="center")
                        cell_infra.fill = jaune_clair

                        # 2. Fusionner et styliser les autres colonnes (fond jaune + centré + gras)
                        """
                        if len(df.columns) > 1:
                            ws.merge_cells(
                                start_row=start_row + r_idx,
                                start_column=start_col + 1,
                                end_row=start_row + r_idx,
                                end_column=start_col + len(df.columns) - 1
                            )
                            cell = ws.cell(row=start_row + r_idx, column=start_col + 1)
                            cell.value = "Données manquantes"
                            cell.font = Font(bold=True)
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        """
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

                            # (Facultatif, pour être sûr, applique aussi le fond jaune aux cellules fusionnées)
                            for col_idx in range(col_infra + 2, col_infra + len(df.columns)):
                                ws.cell(row=row_excel, column=col_idx).fill = jaune_clair
                    else:
                        for c_idx, value in enumerate(row):
                            safe_val = str(value) if value is not None else ""
                            cell = ws.cell(row=start_row + r_idx, column=start_col + c_idx, value=safe_val)
                            # cell = ws.cell(row=start_row + r_idx, column=start_col + c_idx, value=value)
                            cell.font = Font(
                                bold=False,
                                color=header_row_modele[c_idx].font.color if header_row_modele[c_idx].font else None
                            )
                            cell.fill = copy(header_row_modele[c_idx].fill) if header_row_modele[c_idx].fill else None
                            cell.border = copy(header_row_modele[c_idx].border) if header_row_modele[
                                c_idx].border else None
                            cell.alignment = copy(header_row_modele[c_idx].alignment) if header_row_modele[
                                c_idx].alignment else None

                # Largeur colonnes
                for i, col in enumerate(df.columns, start=1):
                    ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 22

                wb.save(file_name)
            except Exception as e:
                QMessageBox.critical(self, "Erreur export", f"Erreur lors de la génération du fichier :\n{e}")
                return

        # --- Export PRECONISATIONS ---
        if key == ("ES-IND", "OT", "Préconisations"):
            # modele_path = "export_model\\Model_Export_ES-IND_OT_Préconisations_v1.xlsx"
            modele_path = MODEL_PRECO_PATH
            today_dt = datetime.datetime.now()
            today_str = today_dt.strftime("%d-%m-%Y")
            trimestre_labels = ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"]
            trimestre_index = next(
                (i for i, btn in enumerate(self.zone3_widgets[key].trimestre_radios) if btn.isChecked()), 0)
            selected_trimestre = trimestre_labels[trimestre_index]
            year = today_dt.year
            if selected_trimestre == "Aujourd'hui":
                nom_fichier = f"Preconisations_indicateur-OT_{today_str}.xlsx"
                message_export = (
                    "PRECONISATIONS DU DOMAINE OUVRAGES EN TERRE (MT00256)\n"
                    f"état au {today_str} - source PIGC"
                )
            else:
                nom_fichier = f"Preconisations_indicateur-OT_{selected_trimestre}_{year}.xlsx"
                message_export = (
                    "PRECONISATIONS DU DOMAINE OUVRAGES EN TERRE (MT00256)\n"
                    f"état au {selected_trimestre} {year} - source PIGC"
                )

            file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
            if not file_name:
                return

            try:
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

                wb.save(file_name)
            except Exception as e:
                QMessageBox.critical(self, "Erreur export", f"Erreur lors de la génération du fichier :\n{e}")
            return
