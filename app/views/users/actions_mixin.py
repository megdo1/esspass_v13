"""Chargement, filtrage et actions sur les utilisateurs (rôle, activation, suppression, création)."""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QComboBox, QLineEdit, QCheckBox, QGroupBox, QFormLayout, QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from app.styles import style
from app.views.users.tabs_mixin import (
    COL_EMAIL, COL_ID, COL_NOM, COL_PRENOM, COL_RESPONSABLE, COL_ROLE, COL_STATUT, INFOBULLE_TABLE_ABSENTE,
    TEXTE_CASE_RESPONSABLE,
)
from app.views.users.widgets import (
    ARDOISE, DANGER, PASTILLE_ROLE, ROLE_PASTILLE, SARCELLE, SUCCES, couleurs_pastille,
)


class ActionsMixin:
    """Chargement, filtrage et actions sur les utilisateurs (rôle, activation, suppression, création)."""

    def load_utilisateurs(self):
        """Charge la liste des utilisateurs depuis la base de données et met à jour les tuiles de synthèse."""
        utilisateurs = self.data_manager.get_all_users_with_roles()
        if not utilisateurs and self.data_manager.last_error:
            return                                   # erreur d'accès : on garde l'affichage actuel

        t = self.tableau_utilisateurs
        t.setRowCount(len(utilisateurs))
        for row, user in enumerate(utilisateurs):
            role = user['libelle_role']
            actif = bool(user['actif'])
            est_responsable = user.get('est_responsable')

            item_id = QTableWidgetItem(str(user['id_utilisateur']))
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setForeground(QColor("#94A3B8"))
            t.setItem(row, COL_ID, item_id)
            t.setItem(row, COL_NOM, QTableWidgetItem(user['nom'] or ""))
            t.setItem(row, COL_PRENOM, QTableWidgetItem(user['prenom'] or ""))
            t.setItem(row, COL_EMAIL, QTableWidgetItem(user['email'] or ""))

            # Rôle, statut et responsable : pastilles colorées (dessinées par PastilleDelegate)
            item_role = QTableWidgetItem(role or "Non défini")
            item_role.setTextAlignment(Qt.AlignCenter)
            item_role.setData(ROLE_PASTILLE, couleurs_pastille(PASTILLE_ROLE.get(role, ARDOISE)))
            t.setItem(row, COL_ROLE, item_role)

            item_statut = QTableWidgetItem("Actif" if actif else "Inactif")
            item_statut.setTextAlignment(Qt.AlignCenter)
            item_statut.setData(ROLE_PASTILLE, couleurs_pastille(SUCCES if actif else DANGER))
            item_statut.setData(Qt.UserRole, actif)        # état réel, relu par la boîte de modification
            t.setItem(row, COL_STATUT, item_statut)

            if est_responsable is None:                    # table utilisateur_responsable absente
                item_resp = QTableWidgetItem("n/a")
                item_resp.setToolTip(INFOBULLE_TABLE_ABSENTE)
                item_resp.setForeground(QColor("#94A3B8"))
            elif est_responsable:
                item_resp = QTableWidgetItem("Oui")
                item_resp.setData(ROLE_PASTILLE, couleurs_pastille(SARCELLE))
            else:
                item_resp = QTableWidgetItem("—")
                item_resp.setForeground(QColor("#94A3B8"))
            item_resp.setTextAlignment(Qt.AlignCenter)
            item_resp.setData(Qt.UserRole, None if est_responsable is None else bool(est_responsable))
            t.setItem(row, COL_RESPONSABLE, item_resp)

        self._maj_synthese(utilisateurs)
        self.filtrer_utilisateurs()
        self._maj_boutons_actions()

    def _maj_synthese(self, utilisateurs):
        """Met à jour les quatre tuiles : total, actifs, administrateurs actifs, responsables ES-PASS actifs."""
        tuiles = getattr(self, 'tuiles_utilisateurs', None)
        if not tuiles:
            return
        actifs = [u for u in utilisateurs if u['actif']]
        tuiles["total"].setText(str(len(utilisateurs)))
        tuiles["actifs"].setText(str(len(actifs)))
        tuiles["admins"].setText(str(sum(1 for u in actifs if u['libelle_role'] == "Administrateur")))
        if any(u.get('est_responsable') is not None for u in utilisateurs):
            tuiles["responsables"].setText(str(sum(1 for u in actifs if u.get('est_responsable'))))
        else:
            tuiles["responsables"].setText("n/a")              # script 001 non appliqué

    def filtrer_utilisateurs(self, *_):
        """Filtre la liste : texte (nom, prénom, e-mail) et filtres rôle / statut / responsable ES-PASS."""
        t = self.tableau_utilisateurs
        texte = self.search_input.text().strip().lower()
        role = self.combo_filtre_role.currentData()
        statut = self.combo_filtre_statut.currentData()
        responsable = self.combo_filtre_responsable.currentData()

        visibles = 0
        for row in range(t.rowCount()):
            nom = t.item(row, COL_NOM).text().lower()
            prenom = t.item(row, COL_PRENOM).text().lower()
            email = t.item(row, COL_EMAIL).text().lower()
            visible = (not texte or texte in nom or texte in prenom or texte in email
                       or texte in f"{prenom} {nom}" or texte in f"{nom} {prenom}")
            if visible and role is not None:
                visible = t.item(row, COL_ROLE).text() == role
            if visible and statut is not None:
                visible = bool(t.item(row, COL_STATUT).data(Qt.UserRole)) == statut
            if visible and responsable is not None:
                visible = bool(t.item(row, COL_RESPONSABLE).data(Qt.UserRole)) == responsable
            t.setRowHidden(row, not visible)
            visibles += visible

        if t.currentRow() >= 0 and t.isRowHidden(t.currentRow()):
            t.clearSelection()
            t.setCurrentCell(-1, -1)
        self.lbl_compteur_utilisateurs.setText(f"{visibles} utilisateur(s) affiché(s) sur {t.rowCount()}")

    def _maj_boutons_actions(self):
        """Active les boutons selon la ligne sélectionnée (Activer / Désactiver selon le statut)."""
        t = self.tableau_utilisateurs
        ligne = t.currentRow() if t.selectedItems() else -1
        selection = ligne >= 0
        actif = selection and bool(t.item(ligne, COL_STATUT).data(Qt.UserRole))
        self.btn_modifier.setEnabled(selection)
        self.btn_supprimer.setEnabled(selection)
        self.btn_activer.setEnabled(selection and not actif)
        self.btn_desactiver.setEnabled(selection and actif)

    def _nom_complet_ligne(self, ligne) -> str:
        t = self.tableau_utilisateurs
        return f"{t.item(ligne, COL_NOM).text()} {t.item(ligne, COL_PRENOM).text()}".strip()

    def modifier_role_utilisateur(self):
        """Modifie le rôle de l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self._nom_complet_ligne(selected_row)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifier le rôle de {nom_prenom}")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"Sélectionner le nouveau rôle pour {nom_prenom}:"))

        combo_role = QComboBox()
        combo_role.addItem("🔵 Consultant", "consultant")
        combo_role.addItem("🟢 Membre MCO", "membre_mco")
        combo_role.addItem("🔴 Administrateur", "administrateur")
        combo_role.setMinimumHeight(35)

        model = combo_role.model()
        model.item(0).setForeground(QColor(style.COLOR_CONSULTANT))
        model.item(0).setFont(style.FONT_BOLD_11)
        model.item(1).setForeground(QColor(style.COLOR_MCO))
        model.item(1).setFont(style.FONT_BOLD_11)
        model.item(2).setForeground(QColor(style.COLOR_ADMIN))
        model.item(2).setFont(style.FONT_BOLD_11)

        layout.addWidget(combo_role)

        btn_layout = QHBoxLayout()
        btn_valider = QPushButton("✅ Valider")
        btn_annuler = QPushButton("❌ Annuler")
        btn_valider.clicked.connect(dialog.accept)
        btn_annuler.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_valider)
        btn_layout.addWidget(btn_annuler)
        layout.addLayout(btn_layout)

        if dialog.exec_() == QDialog.Accepted:
            new_role = combo_role.currentData()
            id_role = self.data_manager.get_role_id_by_libelle(new_role)

            if id_role:
                self.data_manager.update_user_role(id_user,id_role)

                QMessageBox.information(self, "✅ Succès", f"Rôle de {nom_prenom} modifié avec succès.")
                self.load_utilisateurs()
            else:
                QMessageBox.critical(self, "❌ Erreur", "Impossible de trouver le rôle.")

    def modifier_utilisateur(self):
        """Modifie tous les attributs de l'utilisateur sélectionné"""
        selectedrow = self.tableau_utilisateurs.currentRow()
        if selectedrow < 0:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        iduser = int(self.tableau_utilisateurs.item(selectedrow, 0).text())
        nom = self.tableau_utilisateurs.item(selectedrow, 1).text()
        prenom = self.tableau_utilisateurs.item(selectedrow, 2).text()
        email = self.tableau_utilisateurs.item(selectedrow, 3).text()
        role_actuel = self.tableau_utilisateurs.item(selectedrow, COL_ROLE).text()

        # Créer le dialogue de modification
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifier l'utilisateur {nom} {prenom}")
        dialog.setMinimumSize(520, 460)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        titre_dialogue = QLabel("Modifier l'utilisateur")
        titre_dialogue.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F2A52;")
        layout.addWidget(titre_dialogue)
        sous_titre = QLabel(f"{nom} {prenom} — {email}")
        sous_titre.setStyleSheet("color: #64748B;")
        layout.addWidget(sous_titre)

        # Groupe Informations utilisateur
        formgroup = QGroupBox("Informations de l'utilisateur")
        formlayout = QFormLayout()

        # Champ Nom
        inputnom = QLineEdit(nom)
        inputnom.setMinimumHeight(35)
        formlayout.addRow("Nom :", inputnom)

        # Champ Prénom
        inputprenom = QLineEdit(prenom)
        inputprenom.setMinimumHeight(35)
        formlayout.addRow("Prénom :", inputprenom)

        # Champ Email
        inputemail = QLineEdit(email)
        inputemail.setMinimumHeight(35)
        formlayout.addRow("Email :", inputemail)

        # ComboBox Rôle
        comborole = QComboBox()
        comborole.addItem("Consultant", "consultant")
        comborole.addItem("Membre MCO", "membre_mco")
        comborole.addItem("Administrateur", "administrateur")
        comborole.setMinimumHeight(35)

        # Appliquer les couleurs
        model = comborole.model()
        model.item(0).setForeground(QColor(style.COLOR_CONSULTANT))
        model.item(0).setFont(style.FONT_BOLD_11)
        model.item(1).setForeground(QColor(style.COLOR_MCO))
        model.item(1).setFont(style.FONT_BOLD_11)
        model.item(2).setForeground(QColor(style.COLOR_ADMIN))
        model.item(2).setFont(style.FONT_BOLD_11)

        # Sélectionner le rôle actuel
        if role_actuel == "Consultant":
            comborole.setCurrentIndex(0)
        elif role_actuel == "Membre MCO":
            comborole.setCurrentIndex(1)
        elif role_actuel == "Administrateur":
            comborole.setCurrentIndex(2)

        formlayout.addRow("Rôle :", comborole)

        # Checkbox Actif
        checkactif = QCheckBox("Utilisateur actif")
        checkactif.setStyleSheet(style.CHECKBOX_STYLE)
        # L'état vient des données de la cellule : le texte affiché (« ✅ Actif ») ne vaut jamais « Actif »,
        # ce qui décochait la case et désactivait l'utilisateur à chaque modification.
        checkactif.setChecked(bool(self.tableau_utilisateurs.item(selectedrow, 5).data(Qt.UserRole)))
        formlayout.addRow("Statut :", checkactif)

        # Case Responsable ES-PASS (grisée si la table utilisateur_responsable n'existe pas)
        responsable_actuel = self.tableau_utilisateurs.item(selectedrow, 6).data(Qt.UserRole)
        checkresp = QCheckBox(TEXTE_CASE_RESPONSABLE)
        checkresp.setStyleSheet(style.CHECKBOX_STYLE)
        if responsable_actuel is None:
            checkresp.setEnabled(False)
            checkresp.setToolTip(INFOBULLE_TABLE_ABSENTE)
        else:
            checkresp.setChecked(bool(responsable_actuel))
        formlayout.addRow("Responsable :", checkresp)

        formgroup.setLayout(formlayout)
        layout.addWidget(formgroup)

        # Boutons de validation
        btnlayout = QHBoxLayout()
        btnvalider = QPushButton("Valider")
        btnannuler = QPushButton("Annuler")

        btnvalider.clicked.connect(dialog.accept)
        btnannuler.clicked.connect(dialog.reject)
        btnvalider.setStyleSheet(style.BUTTON_PRIMAIRE_STYLE)

        btnlayout.addStretch()
        btnlayout.addWidget(btnannuler)
        btnlayout.addWidget(btnvalider)
        layout.addLayout(btnlayout)

        # Afficher le dialogue
        if dialog.exec_() == QDialog.Accepted:
            # Récupérer les valeurs
            nouveau_nom = inputnom.text().strip()
            nouveau_prenom = inputprenom.text().strip()
            nouveau_email = inputemail.text().strip()
            nouveau_role = comborole.currentData()
            nouveau_actif = checkactif.isChecked()

            # Validation
            if not nouveau_nom or not nouveau_prenom or not nouveau_email:
                QMessageBox.warning(self, "Champs obligatoires", "Tous les champs sont obligatoires.")
                return

            if "@" not in nouveau_email:
                QMessageBox.warning(self, "Email invalide", "Veuillez entrer un email valide.")
                return

            # Vérifier si l'email existe déjà (sauf si c'est le même)
            if nouveau_email != email:
                existing = self.data_manager.check_user_exists_by_email(nouveau_email)
                if existing:
                    QMessageBox.warning(self, "Email existe déjà",
                                        f"Un autre utilisateur avec l'email {nouveau_email} existe déjà.")
                    return

            # Récupérer l'ID du rôle
            idrole = self.data_manager.get_role_id_by_libelle(nouveau_role)
            if not idrole:
                QMessageBox.critical(self, "Erreur", f"Le rôle {nouveau_role} n'existe pas.")
                return

            # Mettre à jour l'utilisateur
            success = self.data_manager.update_user(
                idutilisateur=iduser,
                nom=nouveau_nom,
                prenom=nouveau_prenom,
                email=nouveau_email,
                idrole=idrole,
                actif=nouveau_actif
            )

            if success:
                message = f"L'utilisateur {nouveau_nom} {nouveau_prenom} a été modifié avec succès."
                message += self._appliquer_statut_responsable(iduser, responsable_actuel, checkresp.isChecked())
                QMessageBox.information(self, "Succès", message)
                self.load_utilisateurs()
            else:
                QMessageBox.critical(self, "Erreur", "Erreur lors de la modification de l'utilisateur.")

    def _appliquer_statut_responsable(self, id_user, etat_actuel, souhaite) -> str:
        """Enregistre « Responsable ES-PASS » s'il a changé ; retourne un complément pour le message de succès."""
        if etat_actuel is None or bool(etat_actuel) == bool(souhaite):
            return ""
        if not self.data_manager.definir_responsable(id_user, souhaite):
            QMessageBox.warning(self, "Responsable ES-PASS non modifié",
                                "Les informations sont enregistrées, mais le statut « Responsable ES-PASS » "
                                f"n'a pas pu être modifié :\n{self.data_manager.last_error}")
            return ""
        if souhaite:
            return "\n\n✅ Désormais responsable ES-PASS : proposé dans les listes « Responsable »."
        nb = self.data_manager.get_nb_demandes_affectees(id_user)
        return ("\n\nN'est plus responsable ES-PASS : il n'est plus proposé dans les listes."
                + (f"\nLes {nb} demande(s) qui lui sont déjà affectées le restent." if nb else ""))

    def activer_utilisateur(self):
        """Active l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self._nom_complet_ligne(selected_row)

        self.data_manager.activate_user(id_user)

        QMessageBox.information(self, "✅ Succès", f"{nom_prenom} a été activé.")
        self.load_utilisateurs()

    def desactiver_utilisateur(self):
        """Désactive l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self._nom_complet_ligne(selected_row)


        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setWindowTitle("Désactiver un utilisateur")
        msgbox.setText(f"Êtes-vous sûr de vouloir désactiver {nom_prenom}?")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # Personnaliser les textes des boutons
        yes_button = msgbox.button(QMessageBox.Yes)
        no_button = msgbox.button(QMessageBox.No)
        yes_button.setText("Oui")
        no_button.setText("Non")

        reply = msgbox.exec_()

        if reply == QMessageBox.Yes:
            self.data_manager.deactivate_user(id_user)

            QMessageBox.information(self, "✅ Succès", f"{nom_prenom} a été désactivé.")
            self.load_utilisateurs()

    def supprimer_utilisateur(self):
        """Supprime l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self._nom_complet_ligne(selected_row)


        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setWindowTitle("Supprimer un utilisateur")
        msgbox.setText(f"Êtes-vous VRAIMENT sûr de vouloir supprimer {nom_prenom}?\n")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # Personnaliser les textes des boutons
        yes_button = msgbox.button(QMessageBox.Yes)
        no_button = msgbox.button(QMessageBox.No)
        yes_button.setText("Oui")
        no_button.setText("Non")

        reply = msgbox.exec_()

        if reply == QMessageBox.Yes:
            self.data_manager.delete_user(id_user)

            QMessageBox.information(self, "✅ Succès", f"{nom_prenom} a été supprimé.")
            self.load_utilisateurs()

    def creer_utilisateur(self):
        """Crée un nouvel utilisateur"""
        nom = self.input_nom.text().strip()
        prenom =self.input_prenom.text().strip()
        email = self.input_email.text().strip()
        role = self.combo_role_new.currentData()
        actif = self.check_actif.isChecked()

        if not nom or not email or not prenom:
            QMessageBox.warning(self, "⚠️ Champs obligatoires", "Veuillez remplir tous les champs.")
            return

        if '@' not in email:
            QMessageBox.warning(self, "⚠️ Email invalide", "Veuillez entrer un email valide.")
            return

        # Vérifier si l'email existe déjà
        existing = self.data_manager.check_user_exists_by_email(email)

        if existing:
            QMessageBox.warning(self, "Email existe déjà", f"Un utilisateur avec l'email {email} existe déjà")
            return

        id_role = self.data_manager.get_role_id_by_libelle(role)

        if not id_role:
            QMessageBox.critical(self, "❌ Erreur", f"Le rôle '{role}' n'existe pas dans la base de données.")
            return


        if self.data_manager.create_user_with_role(nom, prenom, email, id_role, actif):
            complement = ""
            if self.check_responsable.isChecked() and self.check_responsable.isEnabled():
                id_cree = self.data_manager.get_id_utilisateur_par_email(email)
                if id_cree and self.data_manager.definir_responsable(id_cree, True):
                    complement = "\nResponsable ES-PASS : oui"
                else:
                    QMessageBox.warning(self, "Responsable ES-PASS non enregistré",
                                        "L'utilisateur est créé, mais le statut « Responsable ES-PASS » n'a pas pu "
                                        f"être enregistré :\n{self.data_manager.last_error}")
            QMessageBox.information(
                self, "Succès",
                f"✅ Utilisateur {nom} {prenom} créé avec succès\nRôle : {role}{complement}"
            )
            self.reinitialiser_form()
            self.load_utilisateurs()
        else:
            QMessageBox.critical(self, "Erreur", "❌ Erreur lors de la création de l'utilisateur")

    def reinitialiser_form(self):
        """Réinitialise le formulaire de création d'utilisateur"""
        self.input_nom.clear()
        self.input_prenom.clear()
        self.input_email.clear()
        self.combo_role_new.setCurrentIndex(0)
        self.check_actif.setChecked(True)
        self.check_responsable.setChecked(False)
