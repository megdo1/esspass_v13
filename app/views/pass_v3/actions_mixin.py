"""Actions sur les demandes : gestion, duplication, traitement, archivage, annulation."""

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt
from app.utils.decorators import busy_cursor, busy_cursor_no_args
from app.utils.ui_helpers import ask_question, show_info, show_warning, show_error, clear_all_cursors
from app.views.pass_v3.demande_dialogs import EditDemandeDialog, CreateDemandeDialog, DuplicateDemandeDialog
from app.views.pass_v3.mail_dialog import MailDetailsDialog
from app.views.pass_v3.traitement_dialogs import TraiterDemandeDialog, TraiterMasseDialog, GererMasseDialog
from app.views.pass_v3.rapports import RapportsDialog

import logging
logger = logging.getLogger(__name__)



class ActionsMixin:
    """Actions sur les demandes : gestion, duplication, traitement, archivage, annulation."""

    def generer_rapports(self):
        """Ouvre le dialogue de génération de rapports"""
        dialog = RapportsDialog(self.data_manager, self)
        dialog.exec_()

    @busy_cursor
    def gerer_demande(self, row):
        """Ouvre le dialogue de gestion en mode non-modal (permet plusieurs fenêtres)"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())

            # ✅ Vérifier si cette demande est déjà ouverte
            if id_demande in self.open_dialogs :
                # Si déjà ouverte, la remettre au premier plan
                existing_dialog = self.open_dialogs[id_demande]
                existing_dialog.activateWindow()
                existing_dialog.raise_()
                show_info(
                    self,
                    "Demande déjà ouverte",
                    f"La demande #{id_demande} est déjà ouverte dans une autre fenêtre."
                )
                return

            # ✅ Créer le dialogue en mode non-modal
            dialog = EditDemandeDialog(id_demande, self.data_manager, self)

            # ✅ Personnaliser le titre avec l'ID
            dialog.setWindowTitle(f"Gérer la demande #{id_demande}")

            # ✅ Stocker la référence
            self.open_dialogs[id_demande] = dialog

            # ✅ Connecter le signal de fermeture pour nettoyer
            dialog.finished.connect(lambda result: self.on_dialog_closed(id_demande, result))

            # ✅ Afficher en non-modal (permet d'en ouvrir plusieurs)
            dialog.show()

        except Exception as e:
            show_error(self, "Erreur", f"Impossible d'ouvrir la demande : {e}")

    def on_dialog_closed(self, id_demande, result):
        """
        ✅ NOUVELLE MÉTHODE : Appelée quand un dialogue est fermé
        """
        # Retirer du dictionnaire
        if id_demande in self.open_dialogs:
            del self.open_dialogs[id_demande]

        # Recharger le tableau si la demande a été sauvegardée
        if result == QDialog.Accepted:
            logger.info(f"Demande #{id_demande} modifiée")
            self.load_demandes_table()

    @busy_cursor
    def dupliquer_demande(self, row):
        """Ouvre le dialogue de duplication pour une demande"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())
            dialog = DuplicateDemandeDialog(id_demande, self.data_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                logger.info(f"✅ Demande #{id_demande} dupliquée")
                # Recharger les données
                self.collecte_info = self.data_manager.get_last_collecte()
                self.dashboard_stats = self.data_manager.get_dashboard_stats()
                self.load_demandes_table()
        except Exception as e:
            show_error(self, "Erreur", f"Impossible de dupliquer la demande :\n{e}")

    @busy_cursor
    def voir_plus_demande(self, row):
        """Affiche les détails en mode non-modal"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())

            # ✅ Pour les détails, on peut autoriser plusieurs instances
            # (lecture seule, pas de conflit)
            demande_data = self.data_manager.get_demande_by_id(id_demande)

            if demande_data:
                dlg = MailDetailsDialog(demande_data, self.data_manager, self)
                dlg.setWindowTitle(f"Détails de la demande #{id_demande}")

                # ✅ Afficher en non-modal (lecture seule)
                dlg.show()
            else:
                show_warning(self, "Erreur", "Demande introuvable")

        except Exception as e:
            show_error(self, "Erreur", f"Impossible d'afficher les détails : {e}")

    @busy_cursor
    def traiter_demande(self, row):
        """Ouvre le dialogue de traitement pour une demande"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())
            dialog = TraiterDemandeDialog(id_demande, self.data_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                logger.info(f"✅ Traitement de la demande #{id_demande} sauvegardé")
                self.load_demandes_table()
        except Exception as e:
            show_error(self, "Erreur", f"Impossible d'ouvrir le dialogue de traitement :\n{e}")

    def nouvelle_demande(self):
        """Ouvre le dialogue de création de demande"""
        try:
            dialog = CreateDemandeDialog(self.data_manager, self)

            if dialog.exec_() == QDialog.Accepted:
                logger.info("✅ Nouvelle demande créée")
                # Recharger les données
                self.collecte_info = self.data_manager.get_last_collecte()
                self.dashboard_stats = self.data_manager.get_dashboard_stats()
                # Mettre à jour l'affichage du dashboard
                self.update_dashboard()
                # Recharger le tableau
                self.load_demandes_table()

        except Exception as e:
            logger.error(f"❌ Erreur ouverture dialogue création : {e}")
            show_error(self, "Erreur", f"Impossible d'ouvrir le dialogue de création :\n{e}")

    @busy_cursor_no_args
    def annuler_masse(self):
        """Annule les demandes sélectionnées (état = Annulée)"""
        selected_ids = self.get_selected_demandes()

        if not selected_ids:
            show_warning(
                self,
                "Aucune sélection",
                "Veuillez sélectionner au moins une demande à annuler."
            )
            return

        # Créer QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirmer l'annulation")
        msg_box.setText(f"Voulez-vous vraiment annuler les {len(selected_ids)} demandes ?")
        msg_box.setTextFormat(Qt.PlainText)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # RÉCUPÉRER et modifier les boutons
        yes_button = msg_box.button(QMessageBox.Yes)
        no_button = msg_box.button(QMessageBox.No)
        yes_button.setText("Oui")
        no_button.setText("Non")

        clear_all_cursors()
        reply = msg_box.exec_()
        if reply == QMessageBox.No:
            return

        id_etat_annulee = self.data_manager.get_etat_id_by_libelle("Annulée")

        if not id_etat_annulee:
            show_error(
                self,
                "Erreur",
                "État 'Annulée' introuvable dans la base de données."
            )
            return

        succes, echec = self.data_manager.update_etat_multiple(selected_ids, id_etat_annulee)

        if echec == 0:
            show_info(
                self,
                "Succès",
                f"✅ {succes} demande(s) annulée(s) avec succès !"
            )
        else:
            show_warning(
                self,
                "Annulation partielle",
                f"✅ {succes} demande(s) annulée(s)\n❌ {echec} échec(s)"
            )

        self.load_demandes_table()

    @busy_cursor_no_args
    def archiver_masse(self):
        """Archive les demandes sélectionnées (état = Archivée)"""
        selected_ids = self.get_selected_demandes()

        if not selected_ids:
            show_warning(
                self,
                "Aucune sélection",
                "Veuillez sélectionner au moins une demande à archiver."
            )
            return

        # Créer QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirmer l'archivage")
        msg_box.setText(f"Voulez-vous vraiment archiver les {len(selected_ids)} demandes ?")
        msg_box.setTextFormat(Qt.PlainText)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # RÉCUPÉRER et modifier les boutons
        yes_button = msg_box.button(QMessageBox.Yes)
        no_button = msg_box.button(QMessageBox.No)
        yes_button.setText("Oui")
        no_button.setText("Non")

        clear_all_cursors()
        reply = msg_box.exec_()

        if reply == QMessageBox.No:
            return

        id_etat_archivee = self.data_manager.get_etat_id_by_libelle("Archivée")

        if not id_etat_archivee:
            show_error(
                self,
                "Erreur",
                "État 'Archivée' introuvable dans la base de données."
            )
            return

        succes, echec = self.data_manager.update_etat_multiple(selected_ids, id_etat_archivee)

        if echec == 0:
            show_info(
                self,
                "Succès",
                f"✅ {succes} demande(s) archivée(s) avec succès !"
            )
        else:
            show_warning(
                self,
                "Archivage partiel",
                f"✅ {succes} demande(s) archivée(s)\n❌ {echec} échec(s)"
            )

        self.load_demandes_table()

    @busy_cursor
    def annuler_demande_row(self, row):
        """Annule une demande depuis une ligne du tableau"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())

            reply = ask_question(
                self,
                "Confirmer l'annulation",
                f"Voulez-vous vraiment annuler la demande #{id_demande} ?\n\n"
                "Cette action changera son état en 'Annulée'.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                return

            id_etat_annulee = self.data_manager.get_etat_id_by_libelle("Annulée")
            if not id_etat_annulee:
                show_error(self, "Erreur", "État 'Annulée' introuvable.")
                return

            # Mettre à jour l'état
            if self.data_manager.update_etat_multiple([id_demande], id_etat_annulee):
                show_info(self, "Succès", f"✅ Demande #{id_demande} annulée avec succès !")
                self.load_demandes_table()
            else:
                show_error(self, "Erreur", "❌ Erreur lors de l'annulation de la demande")
        except Exception as e:
            show_error(self, "Erreur", f"Erreur: {e}")

    @busy_cursor
    def archiver_demande_row(self, row):
        """Archive une demande depuis une ligne du tableau"""
        try:
            id_demande = int(self.table.verticalHeaderItem(row).text())


            # Créer d'abord l'objet QMessageBox
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Confirmer l'archivage")
            msg_box.setText(f"Voulez-vous vraiment archiver la demande {id_demande} ?")
            msg_box.setTextFormat(Qt.PlainText)  # Évite le format HTML
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            # PERSONNALISER les boutons en français
            msg_box.setButtonText(QMessageBox.Yes, "Oui")
            msg_box.setButtonText(QMessageBox.No, "Non")

            # Afficher et récupérer la réponse
            clear_all_cursors()
            reply = msg_box.exec_()

            if reply == QMessageBox.No:
                return

            id_etat_archivee = self.data_manager.get_etat_id_by_libelle("Archivée")
            if not id_etat_archivee:
                show_error(self, "Erreur", "État 'Archivée' introuvable.")
                return

            # Mettre à jour l'état
            if self.data_manager.update_etat_multiple([id_demande], id_etat_archivee):
                show_info(self, "Succès", f"✅ Demande #{id_demande} archivée avec succès !")
                self.load_demandes_table()
            else:
                show_error(self, "Erreur", "❌ Erreur lors de l'archivage de la demande")
        except Exception as e:
            show_error(self, "Erreur", f"Erreur: {e}")

    @busy_cursor_no_args
    def traiter_masse(self):
        """Traite plusieurs demandes en masse"""
        selected_ids = self.get_selected_demandes()

        if not selected_ids:
            show_warning(
                self,
                "Aucune sélection",
                "Veuillez sélectionner au moins une demande à traiter."
            )
            return

        if len(selected_ids) == 1:
            row = self._find_row_by_id(selected_ids[0])
            if row >= 0:
                self.traiter_demande(row)
            return

        clear_all_cursors()
        dialog = TraiterMasseDialog(selected_ids, self.data_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info(f"{len(selected_ids)} demandes traitées en masse")
            self.load_demandes_table()

    @busy_cursor_no_args
    def gerer_masse(self):
        """Gère plusieurs demandes en masse"""
        selected_ids = self.get_selected_demandes()

        if not selected_ids:
            show_warning(
                self,
                "Aucune sélection",
                "Veuillez sélectionner au moins une demande à gérer."
            )
            return

        if len(selected_ids) == 1:
            row = self._find_row_by_id(selected_ids[0])
            if row >= 0:
                self.gerer_demande(row)
            return
        clear_all_cursors()
        dialog = GererMasseDialog(selected_ids, self.data_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info(f"{len(selected_ids)} demandes gérées en masse")
            # Recharger les données
            self.collecte_info = self.data_manager.get_last_collecte()
            self.dashboard_stats = self.data_manager.get_dashboard_stats()
            # Mettre à jour l'affichage du dashboard
            self.update_dashboard()
            self.load_demandes_table()
