"""Export Excel de la liste des demandes."""

from PyQt5.QtWidgets import QMessageBox
from app.utils.decorators import busy_cursor_no_args
from app.utils.ui_helpers import show_info, show_warning, show_error, clear_all_cursors

import logging
logger = logging.getLogger(__name__)



class ExportMixin:
    """Export Excel de la liste des demandes."""

    @busy_cursor_no_args
    def exporter_demandes(self):
        """Exporte les demandes sélectionnées vers un fichier Excel"""
        from PyQt5.QtWidgets import QFileDialog
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from datetime import datetime

        selected_ids = self.get_selected_demandes()

        if not selected_ids:
            show_warning(
                self,
                "Aucune sélection",
                "Veuillez sélectionner au moins une demande à exporter."
            )
            return

        # Nom de fichier par défaut avec timestamp unique
        default_filename = f"export_demandes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        clear_all_cursors()
        # Ouvrir le dialogue de sauvegarde pour choisir le nom et l'emplacement
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les demandes",
            default_filename,
            "Fichiers Excel (*.xlsx);;Tous les fichiers (*)"
        )

        if not filepath:
            return  # L'utilisateur a annulé

        try:
            # Récupérer les données complètes des demandes sélectionnées
            # 1) récupérer toutes les demandes d’un coup
            demandes_data = self.data_manager.get_demandes_by_ids(selected_ids)

            if not demandes_data:
                show_warning(self, "Erreur", "Aucune donnée à exporter.")
                return

            # Créer le classeur Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Demandes"

            # En-têtes de colonnes
            headers = [
                "ID", "Libellé", "Sujet", "Résumé", "Demandeur",
                "Date réception", "Canal", "Domaine", "Responsable",
                "Catégorie", "Sous-catégorie", "Nature",
                "Impact", "Urgence", "Priorité calculée",
                "État", "Date traitement", "Solution", "Commentaire","Date_création","Date_dernier_maj"
            ]

            # Style pour les en-têtes
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Écrire les en-têtes
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = border

            # Écrire les données
            for row_idx, demande in enumerate(demandes_data, start=2):
                data_row = [
                    demande.get('id_demande', ''),
                    demande.get('libelle', ''),
                    demande.get('sujet', ''),
                    demande.get('resume', ''),
                    demande.get('demandeur', ''),
                    demande.get('date_reception', ''),
                    demande.get('libelle_canal', ''),
                    demande.get('libelle_domaine', ''),
                    demande.get('nom_responsable', ''),
                    demande.get('libelle_categorie', ''),
                    demande.get('libelle_sous_categorie', ''),
                    demande.get('libelle_nature', ''),
                    demande.get('libelle_impact', ''),
                    demande.get('libelle_urgence', ''),
                    demande.get('priorite_calculee', ''),
                    demande.get('libelle_etat', ''),
                    demande.get('date_traitement', ''),
                    demande.get('solution_suite_a_donner', ''),
                    demande.get('commentaire', ''),
                    demande.get('created_at', ''),
                    demande.get('updated_at', '')
                ]

                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

                    # Coloration selon l'état (colonne 15)
                    if col_idx == 16:
                        if value == "Traitée":
                            cell.fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
                        elif value == "À étudier":
                            cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
                        elif "En cours" in str(value):
                            cell.fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
                        elif value == "Annulée":
                            cell.fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")

            # Ajuster la largeur des colonnes
            column_widths = {
                'A': 8, 'B': 35, 'C': 35, 'D': 50, 'E': 25,
                'F': 18, 'G': 15, 'H': 20, 'I': 25, 'J': 20,
                'K': 25, 'L': 15, 'M': 12, 'N': 12, 'O': 12,
                'P': 15, 'Q': 18, 'R': 40, 'S': 40,'T': 25,'U': 25
            }

            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width

            # Figer la première ligne
            ws.freeze_panes = "A2"

            # Ajouter une feuille récapitulative
            ws_recap = wb.create_sheet("Récapitulatif")
            ws_recap.cell(1, 1, "Récapitulatif de l'export").font = Font(bold=True, size=14)
            ws_recap.cell(3, 1, "Date d'export :").font = Font(bold=True)
            ws_recap.cell(3, 2, datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
            ws_recap.cell(4, 1, "Nombre de demandes :").font = Font(bold=True)
            ws_recap.cell(4, 2, len(demandes_data))

            # Compter les demandes par état
            etats = {}
            for demande in demandes_data:
                etat = demande.get('libelle_etat', 'Non défini')
                etats[etat] = etats.get(etat, 0) + 1

            ws_recap.cell(6, 1, "Répartition par état :").font = Font(bold=True)
            row_idx = 7
            for etat, count in etats.items():
                ws_recap.cell(row_idx, 1, etat)
                ws_recap.cell(row_idx, 2, count)
                row_idx += 1

            # Sauvegarder le fichier
            wb.save(filepath)

            show_info(
                self,
                "Export réussi",
                f"✅ {len(demandes_data)} demandes exportées avec succès !\n\n"
                f"Fichier : {filepath}"
            )

            # Proposer d'ouvrir le fichier - AVEC BOUTONS PERSONNALISÉS
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Question)
            msgbox.setWindowTitle("Ouvrir le fichier")
            msgbox.setText("Voulez-vous ouvrir le fichier Excel maintenant ?")
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            # Personnaliser les textes des boutons
            yes_button = msgbox.button(QMessageBox.Yes)
            no_button = msgbox.button(QMessageBox.No)
            yes_button.setText("Oui")
            no_button.setText("Non")

            reply = msgbox.exec_()

            if reply == QMessageBox.Yes:
                import os
                import platform
                import subprocess

                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', filepath])
                else:  # Linux
                    subprocess.call(['xdg-open', filepath])

        except Exception as e:
            show_error(
                self,
                "Erreur d'export",
                f"❌ Erreur lors de l'export :\n{str(e)}"
            )
