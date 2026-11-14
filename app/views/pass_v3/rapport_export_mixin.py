"""Exports Excel et PDF des rapports."""

from PyQt5.QtWidgets import QMessageBox
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QFileDialog
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import warnings
import os
from app.utils.decorators import busy_cursor_no_args
from app.utils.mpl_cache import ensure_mpl_cache_dir
from app.utils.ui_helpers import show_info, show_error
import logging

logger = logging.getLogger(__name__)


class RapportExportMixin:
    """Exports Excel et PDF des rapports."""

    @busy_cursor_no_args
    def export_to_excel(self):
        """Exporte les rapports en Excel"""
        from PyQt5.QtWidgets import QFileDialog
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        default_filename = f"rapport_PASS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en Excel",
            default_filename,
            "Fichiers Excel (*.xlsx)"
        )

        if not filepath:
            return

        try:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            # Page de garde
            ws_cover = wb.create_sheet("📊 Rapport PASS")
            ws_cover.cell(2, 2, "RAPPORT STATISTIQUE PASS").font = Font(bold=True, size=16, color="607D8B")
            ws_cover.cell(3, 2, f"Période : {self.date_debut} au {self.date_fin}").font = Font(size=12)
            ws_cover.cell(4, 2, f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}").font = Font(size=10)

            # Exporter chaque rapport sélectionné
            if self.rapports_selectionnes.get('categorie'):
                self._export_categorie_to_excel(wb)

            if self.rapports_selectionnes.get('domaine'):
                self._export_domaine_to_excel(wb)

            if self.rapports_selectionnes.get('nature'):
                self._export_nature_to_excel(wb)

            if self.rapports_selectionnes.get('metriques'):
                self._export_metriques_to_excel(wb)

            if self.rapports_selectionnes.get('evolution'):
                self._export_evolution_to_excel(wb)

            wb.save(filepath)

            show_info(
                self,
                "Export réussi",
                f"✅ Le rapport a été exporté avec succès !\n\nFichier : {filepath}"
            )

            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Question)
            msgbox.setWindowTitle("Ouvrir le fichier")
            msgbox.setText("Voulez-vous ouvrir le rapport ?")
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            # Personnaliser les textes des boutons
            yes_button = msgbox.button(QMessageBox.Yes)
            no_button = msgbox.button(QMessageBox.No)
            yes_button.setText("Oui")
            no_button.setText("Non")

            reply = msgbox.exec_()


            if reply == QMessageBox.Yes:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(filepath)
                    else:  # macOS/Linux
                        import subprocess
                        subprocess.call(['xdg-open', filepath])
                except Exception as e:
                    show_error(
                        self,
                        "Erreur",
                        f"Impossible d'ouvrir le fichier :\n{str(e)}"
                    )


        except Exception as e:
            show_error(self, "Erreur", f"Erreur lors de l'export :\n{str(e)}")

    def _export_categorie_to_excel(self, wb):
        """Exporte les données catégories vers Excel"""
        from openpyxl.styles import Font, PatternFill

        ws = wb.create_sheet("📂 Par catégorie")

        query = """
            SELECT 
                COALESCE(cat.libelle_categorie , 'Non défini') as categorie,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY cat.libelle_categorie
            ORDER BY nombre DESC
        """

        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        # En-têtes
        ws.cell(1, 1, "Catégorie").font = Font(bold=True, size=12)
        ws.cell(1, 1).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")
        ws.cell(1, 2, "Nombre").font = Font(bold=True, size=12)
        ws.cell(1, 2).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")

        # Données
        if results:
            for idx, (categorie, nombre) in enumerate(results, start=2):
                ws.cell(idx, 1, categorie)
                ws.cell(idx, 2, nombre)

        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15

    def _export_domaine_to_excel(self, wb):
        """Exporte les données domaines vers Excel"""
        from openpyxl.styles import Font, PatternFill

        ws = wb.create_sheet("🏢 Par domaine")

        query = """
            SELECT 
                COALESCE(dom.libelle_domaine, 'Non défini') as domaine,
                COUNT(*) as total,
                SUM(CASE WHEN et.libelle_etat = 'Traitée' THEN 1 ELSE 0 END) as traitées,
                SUM(CASE WHEN et.libelle_etat LIKE '%En cours%' THEN 1 ELSE 0 END) as en_cours,
                SUM(CASE WHEN et.libelle_etat = 'À étudier' THEN 1 ELSE 0 END) as a_etudier
            FROM demandes d
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY dom.libelle_domaine
            ORDER BY total DESC
        """

        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        # En-têtes
        headers = ["Domaine", "Total", "Réalisées", "En cours", "À étudier"]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(1, col_idx, header)
            cell.font = Font(bold=True, size=12)
            cell.fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")

        # Données
        if results:
            for idx, (domaine, total, realisees, en_cours, a_etudier) in enumerate(results, start=2):
                ws.cell(idx, 1, domaine)
                ws.cell(idx, 2, total)
                ws.cell(idx, 3, realisees)
                ws.cell(idx, 4, en_cours)
                ws.cell(idx, 5, a_etudier)

        for col in ['A', 'B', 'C', 'D', 'E']:
            ws.column_dimensions[col].width = 20

    def _export_nature_to_excel(self, wb):
        """Exporte les données natures vers Excel"""
        from openpyxl.styles import Font, PatternFill

        ws = wb.create_sheet("🔍 Par nature")

        query = """
            SELECT 
                COALESCE(n.libelle_nature, 'Non défini') as nature,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY n.libelle_nature
            ORDER BY nombre DESC
        """

        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        # En-têtes
        ws.cell(1, 1, "Nature").font = Font(bold=True, size=12)
        ws.cell(1, 1).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")
        ws.cell(1, 2, "Nombre").font = Font(bold=True, size=12)
        ws.cell(1, 2).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")

        # Données
        if results:
            for idx, (nature, nombre) in enumerate(results, start=2):
                ws.cell(idx, 1, nature)
                ws.cell(idx, 2, nombre)

        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15

    def _export_evolution_to_excel(self, wb):
        """Exporte les données évolutions vers Excel"""
        from openpyxl.styles import Font, PatternFill

        ws = wb.create_sheet("📈 Évolutions")

        query = """
            SELECT 
                COALESCE(et.libelle_etat, 'Non défini') as etat,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            WHERE date(d.date_reception) BETWEEN ? AND ?
              AND n.libelle_nature LIKE '%volution%'
            GROUP BY et.libelle_etat
            ORDER BY nombre DESC
        """

        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        # En-têtes
        ws.cell(1, 1, "État").font = Font(bold=True, size=12)
        ws.cell(1, 1).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")
        ws.cell(1, 2, "Nombre").font = Font(bold=True, size=12)
        ws.cell(1, 2).fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")

        # Données
        if results:
            for idx, (etat, nombre) in enumerate(results, start=2):
                ws.cell(idx, 1, etat)
                ws.cell(idx, 2, nombre)

        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15

    def _export_metriques_to_excel(self, wb):
        """Exporte les métriques vers Excel"""
        from openpyxl.styles import Font, PatternFill

        ws = wb.create_sheet("⏱️ Métriques")

        # Statistiques globales (même calcul que l'écran : voir get_metriques_periode)
        metriques = self.data_manager.get_metriques_periode(self.date_debut, self.date_fin)

        ws.cell(1, 1, "STATISTIQUES GLOBALES").font = Font(bold=True, size=14)
        if metriques:
            total, nb_realisees = metriques['total'], metriques['realisees']
            delai_moy = metriques['delai_moyen']
            ws.cell(3, 1, "Total demandes :").font = Font(bold=True)
            ws.cell(3, 2, total)
            ws.cell(4, 1, "Demandes réalisées :").font = Font(bold=True)
            ws.cell(4, 2, nb_realisees)
            ws.cell(5, 1, "Demandes en cours :").font = Font(bold=True)
            ws.cell(5, 2, metriques['en_cours'])
            ws.cell(6, 1, "Taux de réalisation :").font = Font(bold=True)
            ws.cell(6, 2, f"{(nb_realisees / total * 100):.1f}%" if total > 0 else "0%")
            ws.cell(7, 1, "Délai moyen (jours) :").font = Font(bold=True)
            ws.cell(7, 2, f"{delai_moy:.1f}" if delai_moy else "N/A")
            ws.cell(8, 1, "Hors calcul (annulées, archivées, hors assistance, non applicables) :")
            ws.cell(8, 2, metriques['hors_calcul'])

        # Délais par domaine
        query_domaine = """
            SELECT 
                COALESCE(dom.libelle_domaine, 'Non défini') as domaine,
                COUNT(*) as nombre,
                ROUND(AVG(julianday(d.date_traitement) - julianday(d.date_reception))) as delai_moyen
            FROM demandes d
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            WHERE date(d.date_reception) BETWEEN ? AND ?
              AND d.date_traitement IS NOT NULL
              AND (et.libelle_etat LIKE 'Trait%' OR et.libelle_etat LIKE 'Ferm%')
            GROUP BY dom.libelle_domaine
            ORDER BY delai_moyen DESC
        """

        results = self.data_manager.execute_query(query_domaine, (self.date_debut, self.date_fin))

        ws.cell(10, 1, "DÉLAIS PAR DOMAINE").font = Font(bold=True, size=12)

        # En-têtes
        headers = ["Domaine", "Nombre traité", "Délai moyen (jours)"]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(12, col_idx, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")

        # Données
        if results:
            for idx, (domaine, nombre, delai) in enumerate(results, start=13):
                ws.cell(idx, 1, domaine)
                ws.cell(idx, 2, nombre)
                ws.cell(idx, 3, f"{delai:.1f}" if delai else "N/A")

        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 25

    def export_to_pdf(self):
        ensure_mpl_cache_dir()
        """Exporte les graphiques en PDF avec une page de couverture"""

        # Supprimer les warnings pour les glyphes manquants
        warnings.filterwarnings('ignore', category=UserWarning, message='.*Glyph.*missing.*')

        default_filename = f"rapport_PASS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en PDF",
            default_filename,
            "Fichiers PDF (*.pdf)"
        )

        if not filepath:
            return

        try:
            # Formater les dates une seule fois
            datedebutformat = datetime.strptime(self.date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')
            datefinformat = datetime.strptime(self.date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
            period_text = f"Période : {datedebutformat} au {datefinformat}"

            with PdfPages(filepath) as pdf:
                # ========== PAGE DE COUVERTURE (INCHANGÉE) ==========
                cover_fig = Figure(figsize=(8.5, 11))
                cover_ax = cover_fig.add_subplot(111)
                cover_ax.axis('off')
                cover_ax.set_xlim(0, 1)
                cover_ax.set_ylim(0, 1)

                # Titre principal (SANS EMOJI)
                cover_ax.text(
                    0.5, 0.88,
                    "RAPPORTS ET STATISTIQUES",
                    ha='center', va='top',
                    fontsize=22, fontweight='bold',
                    color='#607D8B'
                )

                # Sous-titre
                cover_ax.text(
                    0.5, 0.82,
                    "PASS - Gestion des Demandes d'Assistance",
                    ha='center', va='top',
                    fontsize=13, color='#666666'
                )

                # Ligne de séparation
                cover_ax.plot(
                    [0.2, 0.8], [0.77, 0.77],
                    color='#2196F3', linewidth=2
                )

                # PÉRIODE EN GRAND
                cover_ax.text(
                    0.5, 0.70,
                    "PÉRIODE",
                    ha='center', va='top',
                    fontsize=12, fontweight='bold',
                    color='#333333'
                )

                cover_ax.text(
                    0.5, 0.64,
                    period_text,
                    ha='center', va='top',
                    fontsize=18, fontweight='bold',
                    color='#2196F3',
                    bbox=dict(boxstyle='round,pad=0.8', facecolor='#E3F2FD', alpha=0.8, edgecolor='#2196F3')
                )

                # Informations de génération
                generation_date = datetime.now().strftime('%d/%m/%Y à %H:%M')

                cover_ax.text(
                    0.5, 0.50,
                    "INFORMATIONS",
                    ha='center', va='top',
                    fontsize=12, fontweight='bold',
                    color='#333333'
                )

                # Récupérer l'utilisateur
                try:
                    user_name = f"{self.parent().parent().user_info['prenom']} {self.parent().parent().user_info['nom']}"
                except Exception:
                    user_name = "Utilisateur"

                cover_ax.text(
                    0.5, 0.45,
                    f"Généré le : {generation_date}",
                    ha='center', va='top',
                    fontsize=11, color='#666666'
                )

                cover_ax.text(
                    0.5, 0.41,
                    f"Utilisateur : {user_name}",
                    ha='center', va='top',
                    fontsize=11, color='#666666'
                )

                # RAPPORTS INCLUS
                cover_ax.text(
                    0.5, 0.32,
                    "RAPPORTS INCLUS",
                    ha='center', va='top',
                    fontsize=12, fontweight='bold',
                    color='#333333'
                )

                rapports_list = []
                if self.rapports_selectionnes.get('categorie'):
                    rapports_list.append("• Situation par catégorie")
                if self.rapports_selectionnes.get('domaine'):
                    rapports_list.append("• Situation par domaine")
                if self.rapports_selectionnes.get('nature'):
                    rapports_list.append("• Répartition par nature")
                if self.rapports_selectionnes.get('evolution'):
                    rapports_list.append("• Situation des évolutions")
                if self.rapports_selectionnes.get('metriques'):
                    rapports_list.append("• Métriques et délais")
                if self.rapports_selectionnes.get('copil'):
                    rapports_list.append("• Copil Métriques")

                y_pos = 0.27
                for rapport in rapports_list:
                    cover_ax.text(
                        0.5, y_pos,
                        rapport,
                        ha='center', va='top',
                        fontsize=11, color='#2196F3'
                    )
                    y_pos -= 0.04

                # Pied de page
                cover_ax.text(
                    0.5, 0.05,
                    "Rapport confidentiel - Aucune reproduction sans autorisation",
                    ha='center', va='bottom',
                    fontsize=8, color='#999999', style='italic'
                )

                # Sauvegarder la page de couverture
                pdf.savefig(cover_fig, bbox_inches='tight')
                plt.close(cover_fig)

                # ========== PAGES DES GRAPHIQUES AVEC DATE CENTRÉE ==========
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    canvas = tab.findChild(FigureCanvas)

                    if canvas:
                        fig = canvas.figure

                        # Sauvegarder les paramètres actuels
                        original_top = fig.subplotpars.top

                        # Détection du type de graphique
                        num_axes = len(fig.axes)

                        if num_axes > 1:
                            # Graphiques complexes
                            top_margin = 0.88
                            title_y = 0.98
                        else:
                            # Graphiques simples
                            top_margin = 0.87
                            title_y = 0.97

                        # Ajouter un suptitle avec la période (CENTRÉ AU-DESSUS DU TITRE)
                        fig.suptitle(
                            period_text,
                            fontsize=8,
                            color='#999999',
                            weight='normal',
                            y=title_y,
                            ha='center'
                        )

                        # Ajuster les marges
                        fig.subplots_adjust(top=top_margin)

                        # Sauvegarder dans le PDF
                        pdf.savefig(fig, bbox_inches='tight')

                        # Restaurer l'état original
                        if hasattr(fig, '_suptitle') and fig._suptitle:
                            fig._suptitle.remove()
                        fig.subplots_adjust(top=original_top)

                show_info(
                    self,
                    "Export réussi",
                    f"Le rapport PDF a été généré avec succès !\n\n{filepath}"
                )



                msgbox = QMessageBox(self)
                msgbox.setIcon(QMessageBox.Question)
                msgbox.setWindowTitle("Ouvrir le fichier")
                msgbox.setText("Voulez-vous ouvrir le rapport ?")
                msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

                # Personnaliser les textes des boutons
                yes_button = msgbox.button(QMessageBox.Yes)
                no_button = msgbox.button(QMessageBox.No)
                yes_button.setText("Oui")
                no_button.setText("Non")

                reply = msgbox.exec_()

                if reply == QMessageBox.Yes:
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(filepath)
                        else:  # macOS/Linux
                            import subprocess
                            subprocess.call(['xdg-open', filepath])
                    except Exception as e:
                        show_error(
                            self,
                            "Erreur",
                            f"Impossible d'ouvrir le fichier :\n{str(e)}"
                        )

        except Exception as e:
            show_error(
                self,
                "Erreur",
                f"Erreur lors de l'export PDF :\n{str(e)}"
            )
