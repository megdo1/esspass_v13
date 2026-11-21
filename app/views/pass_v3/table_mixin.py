"""Chargement, rafraîchissement et sélection des lignes du tableau des demandes."""

from PyQt5.QtWidgets import QWidget, QProgressDialog
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import app.logic.logic_extract_mails_unread as sync_outlook
from typing import List
from app.utils.decorators import busy_cursor, busy_cursor_no_args
from app.utils.ui_helpers import show_info, show_error
import logging

logger = logging.getLogger(__name__)


class TableMixin:
    """Chargement, rafraîchissement et sélection des lignes du tableau des demandes."""

    def auto_refresh_data(self):
        """Rafraîchit automatiquement les données"""
        self.collecte_info = self.data_manager.get_last_collecte()
        self.dashboard_stats = self.data_manager.get_dashboard_stats()
        self.update_display_info()
        nb_total= self.load_demandes_table()

        show_info(
            self,
            "Mise à jour terminée",
            f"Synchronisation réussie !\n\n"
            f"Total demandes : {nb_total}"
        )

    @busy_cursor
    def load_demandes_table(self, ids_tri=None):
        """Charge les demandes - AVEC SAUVEGARDE DES ÉTATS"""

        # Les tuiles de statistiques suivent toujours le tableau : sans cela, modifier ou affecter une
        # demande laissait « Demandes non affectées » périmé jusqu'au prochain démarrage.
        if getattr(self, 'kpi_value_labels', None):
            self.dashboard_stats = self.data_manager.get_dashboard_stats()
            self.update_dashboard()

        # ===== SAUVEGARDER L'ÉTAT AVANT RECHARGEMENT =====
        ids_coches = set()
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    id_item = self.table.verticalHeaderItem(row)
                    if id_item:
                        try:
                            id_demande = int(id_item.text())
                            ids_coches.add(id_demande)
                        except Exception:
                            logger.debug("Exception ignorée dans load_demandes_table", exc_info=True)
        # Récupérer l'état des filtres
        inclure_archivees = self.cb_archives.isChecked()
        inclure_annulees = self.cb_annulees.isChecked()
        inclure_realisees = self.cb_realisees.isChecked()

        # La limite se règle dans Configuration > Général (enregistrée en base, pas dans config.json)
        limitDemandes = self.data_manager.get_limite_demandes()
        self.limite_chargement = limitDemandes

        # Charger avec filtres
        erreurs_avant = self.data_manager.error_count
        demandes = self.data_manager.get_demandes(
            limit=limitDemandes,
            inclure_archivees=inclure_archivees,
            inclure_annulees=inclure_annulees,
            inclure_realisees=inclure_realisees
        )

        self.nb_demandes_chargees = len(demandes or [])

        if not demandes and self.data_manager.error_count > erreurs_avant:
            # Erreur d'accès base (et non « aucun résultat ») : on garde le tableau affiché tel quel
            show_error(self, "Chargement impossible",
                       "Les demandes n'ont pas pu être chargées (base inaccessible ?).\n\n"
                       f"{self.data_manager.last_error}\n\nLe tableau affiché n'est pas à jour.")
            return self.table.rowCount()

        if not demandes:
            logger.info("⚠️ Aucune demande trouvée avec ces filtres")
            self.table.setRowCount(0)
            self.update_info_label()
            return
        # ========== APPLIQUER LE TRI SI DEMANDÉ ==========
        if ids_tri:
            # Réorganiser les demandes selon l'ordre de ids_tri
            demandes_dict = {d.get('id_demande'): d for d in demandes}
            demandes_triees = []
            for iddem in ids_tri:
                if iddem in demandes_dict:
                    demandes_triees.append(demandes_dict[iddem])
            # Ajouter les demandes qui n'étaient pas dans ids_tri (nouvelles)
            ids_tri_set = set(ids_tri)
            for d in demandes:
                if d.get('id_demande') not in ids_tri_set:
                    demandes_triees.append(d)
            demandes = demandes_triees

        # ✅ RÉCUPÉRER LA CONFIG DES COLONNES DEPUIS LA BD
        colonnes_config = self.data_manager.get_colonnes_config(visible_only=True)

        # Extraire les libellés pour le header
        colonnes_labels = [col['libelle'] for col in colonnes_config]
        self.colonnes_tableau = colonnes_config   # lue par l'édition au double-clic

        self.table.setColumnCount(len(colonnes_labels))
        self.table.setHorizontalHeaderLabels(colonnes_labels)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setRowCount(len(demandes))

        vertical_headers = []

        def safe_truncate(value, max_len=50):
            if value is None:
                return ""
            return str(value)[:max_len]

        def get_alignement(align_str):
            """Convertit l'alignement string en Qt constant"""
            alignments = {
                'left': Qt.AlignLeft | Qt.AlignVCenter,
                'center': Qt.AlignCenter,
                'right': Qt.AlignRight | Qt.AlignVCenter
            }
            return alignments.get(align_str, Qt.AlignLeft | Qt.AlignVCenter)

        for row_idx, demande in enumerate(demandes):
            id_demande = demande.get('id_demande', row_idx + 1)
            vertical_headers.append(str(id_demande))

            # Parcourir les colonnes configurées
            for col_idx, col_config in enumerate(colonnes_config):
                type_col = col_config['type']
                champ = col_config['champ']
                tronquer = col_config['tronquer']
                alignement = get_alignement(col_config['alignement'])

                # Gérer les types spéciaux de colonnes
                if type_col == 'checkbox':
                    checkbox = QCheckBox()
                    checkbox.setStyleSheet("margin-left: 10px;")
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.setAlignment(Qt.AlignCenter)
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    self.table.setCellWidget(row_idx, col_idx, checkbox_widget)
                    checkbox.stateChanged.connect(self.update_selection_count)

                elif type_col == 'icone':
                    # Colonne pièces jointes
                    value = "📎" if demande.get(champ) else ""
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(alignement)
                    self.table.setItem(row_idx, col_idx, item)

                elif type_col == 'actions':
                    # Boutons d'actions
                    actions_widget = self.create_actions_widget(row_idx)
                    self.table.setCellWidget(row_idx, col_idx, actions_widget)

                elif type_col == 'priorite':
                    # Colonne priorité avec couleurs
                    value = safe_truncate(demande.get(champ, ''), tronquer)
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(alignement)

                    # Appliquer les couleurs
                    if value == "P1":
                        item.setBackground(QColor("#C53030"))
                        item.setForeground(QColor("white"))
                    elif value == "P2":
                        item.setBackground(QColor("#F6AD55"))
                    elif value == "P3":
                        item.setBackground(QColor("#FAF089"))
                    elif value == "P4":
                        item.setBackground(QColor("#2F855A"))
                        item.setForeground(QColor("white"))

                    self.table.setItem(row_idx, col_idx, item)

                elif type_col == 'etat':
                    # Colonne état avec couleurs
                    value = safe_truncate(demande.get(champ, ''), tronquer)
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(alignement)

                    if value == "Traitée":
                        item.setBackground(QColor("#E6F4EC"))
                    elif value == "À étudier":
                        item.setBackground(QColor("#FDF1E3"))
                    elif "En cours" in value:
                        item.setBackground(QColor("#E8EEF9"))

                    self.table.setItem(row_idx, col_idx, item)

                else:
                    # Colonnes texte standard
                    value = safe_truncate(demande.get(champ, ''), tronquer)
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(alignement)
                    self.table.setItem(row_idx, col_idx, item)

        # Appliquer les IDs comme labels du vertical header
        self.table.setVerticalHeaderLabels(vertical_headers)
        self.table.verticalHeader().setFixedWidth(45)

        # ✅ APPLIQUER LES LARGEURS DEPUIS LA CONFIG
        for col_idx, col_config in enumerate(colonnes_config):
            self.table.setColumnWidth(col_idx, col_config['largeur'])

        logger.info(f"✅ {len(demandes)} demandes chargées avec {len(colonnes_config)} colonnes")
        # Définir la hauteur des lignes pour que les boutons soient visibles
        self.table.verticalHeader().setDefaultSectionSize(42)

        self.update_info_label()
        self.update_corner_position()

        # ===== RESTAURER L'ÉTAT APRÈS RECHARGEMENT =====
        # RESTAURER les checkboxes
        if ids_coches:
            for row in range(self.table.rowCount()):
                id_item = self.table.verticalHeaderItem(row)
                if id_item:
                    try:
                        id_demande = int(id_item.text())
                        if id_demande in ids_coches:
                            checkbox_widget = self.table.cellWidget(row, 0)
                            if checkbox_widget:
                                checkbox = checkbox_widget.findChild(QCheckBox)
                                if checkbox:
                                    checkbox.blockSignals(True)
                                    checkbox.setChecked(True)
                                    checkbox.blockSignals(False)
                    except Exception:
                        logger.debug("Exception ignorée dans load_demandes_table", exc_info=True)

        # RESTAURER les filtres (AVEC VÉRIFICATION)
        if hasattr(self, 'mots_cles') and any(self.mots_cles.values()):
            self.filtrerDonnees()
            self.majHeaderIndicateurs()

        # Mettre à jour le compteur (AVEC VÉRIFICATION)
        if hasattr(self, 'update_selection_count'):
            self.update_selection_count()

        # Mettre à jour le compteur
        self.update_selection_count()

        return len(demandes)

    def get_selected_demandes(self) -> List[int]:
        """Récupère les IDs des demandes sélectionnées via checkbox"""
        selected_ids = []

        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    id_demande = int(self.table.verticalHeaderItem(row).text())
                    selected_ids.append(id_demande)

        return selected_ids

    def _find_row_by_id(self, id_demande):
        """Trouve la ligne du tableau correspondant à un ID de demande"""
        for row in range(self.table.rowCount()):
            if int(self.table.verticalHeaderItem(row).text()) == id_demande:
                return row
        return -1

    @busy_cursor_no_args
    def refresh_data(self):
        """Rafraîchit les données - VERSION OPTIMISÉE sans double lecture"""
        logger.info("Début de la mise à jour...")

        conf = self.data_manager.get_all_parametres()
        outlook_folder = conf.get("outlook_folder", "PIGC")
        pj_path = conf.get("pj_path", "./pieces_jointes/")

        try:
            from PyQt5.QtWidgets import QApplication
            import time

            # ✅ Créer une barre indéterminée au début
            progress = QProgressDialog(self)
            progress.setWindowTitle("Collecte depuis la LD")
            progress.setLabelText(
                f"Connexion à Outlook...\n"
                f"Lecture du dossier '{outlook_folder}'"
            )
            progress.setRange(0, 100)  # Temporaire, sera mis à jour
            progress.setValue(0)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)
            progress.setMinimumWidth(400)
            progress.show()
            QApplication.processEvents()

            # ✅ Callback qui reçoit le total dès le premier appel
            first_call = [True]  # Astuce pour modifier dans la closure

            def progress_callback(current, total, nouvelles_demandes):
                # Au premier appel, on connaît le total
                if first_call[0]:
                    progress.setRange(0, total)  # ✅ Définir le range maintenant
                    first_call[0] = False

                # Mettre à jour tous les 5 emails (performance)
                if current % 5 == 0 or current == total:
                    progress.setValue(current)
                    progress.setLabelText(
                        f"Traitement des emails...\n"
                        f"Email {current}/{total}\n\n"
                        f"Nouvelles demandes créées : {nouvelles_demandes}"
                    )
                    QApplication.processEvents()
                return True

            try:
                start_time = time.time()

                # ✅ Un seul appel - pas de double lecture !
                nb_emails_traites, nb_nouvelles = sync_outlook.sync_outlook_to_sqlite(
                    self.user_info,
                    outlook_folder,
                    pj_path,
                    self.collecte_info['date_time'],
                    progress_callback=progress_callback
                )

                elapsed_time = time.time() - start_time

                # Finaliser
                progress.setLabelText("Rechargement des données...")
                QApplication.processEvents()

                # Rafraîchir l'interface
                self.user_info = self.data_manager.get_current_user()
                self.collecte_info = self.data_manager.get_last_collecte()
                self.dashboard_stats = self.data_manager.get_dashboard_stats()
                self.update_display_info()
                nb_total = self.load_demandes_table()

                progress.close()

                # Message final
                show_info(
                    self,
                    "✅ Synchronisation terminée",
                    f"Collecte réussie !\n\n"
                    f"📧 Emails traités : {nb_emails_traites}\n"
                    f"🆕 Nouvelles demandes : {nb_nouvelles}\n"
                    f"📊 Total demandes : {nb_total}\n"
                    f"⏱️  Durée : {elapsed_time:.1f}s\n"
                    f"📁 Dossier : {outlook_folder}"
                )

            except Exception as e:
                progress.close()
                logger.exception("Erreur non gérée")
                show_error(
                    self,
                    "❌ Erreur de synchronisation",
                    f"Erreur :\n\n{str(e)}"
                )

        except Exception as e:
            logger.exception("Erreur non gérée")
            show_error(self, "❌ Erreur", f"Erreur :\n\n{str(e)}")
