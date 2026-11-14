"""Chargement, filtrage et actions sur les utilisateurs (rôle, activation, suppression, création)."""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QComboBox, QLineEdit, QCheckBox, QGroupBox, QFormLayout, QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from app.styles import style


class ActionsMixin:
    """Chargement, filtrage et actions sur les utilisateurs (rôle, activation, suppression, création)."""

    def load_utilisateurs(self):
        """Charge la liste des utilisateurs depuis la base de données"""

        utilisateurs = self.data_manager.get_all_users_with_roles()

        if utilisateurs:
            self.tableau_utilisateurs.setRowCount(len(utilisateurs))

            for row, user in enumerate(utilisateurs):
                id_user = user['id_utilisateur']
                nom = user['nom']
                prenom = user['prenom']
                email = user['email']
                role = user['libelle_role']
                actif = user['actif']

                # Colonne ID
                item_id = QTableWidgetItem(str(id_user))
                self.tableau_utilisateurs.setItem(row, 0, item_id)

                # Colonne Nom 
                item_nom = QTableWidgetItem(f"{nom}")
                self.tableau_utilisateurs.setItem(row, 1, item_nom)
                
                # Colonne prenom
                item_preonom = QTableWidgetItem(f"{prenom}")
                self.tableau_utilisateurs.setItem(row, 2, item_preonom)

                # Colonne Email
                item_email = QTableWidgetItem(email)
                self.tableau_utilisateurs.setItem(row, 3, item_email)

                # Colonne Rôle Actuel avec couleurs
                item_role = QTableWidgetItem(role or "Non défini")
                item_role.setFont(style.FONT_BOLD_11)

                if role == "Consultant":
                    item_role.setBackground(QColor(style.COLOR_ROLE_CONSULTANT_BG))
                    item_role.setForeground(QColor(style.COLOR_ROLE_CONSULTANT_TEXT))
                elif role == "Membre MCO":
                    item_role.setBackground(QColor(style.COLOR_ROLE_MCO_BG))
                    item_role.setForeground(QColor(style.COLOR_ROLE_MCO_TEXT))
                elif role == "Administrateur":
                    item_role.setBackground(QColor(style.COLOR_ROLE_ADMIN_BG))
                    item_role.setForeground(QColor(style.COLOR_ROLE_ADMIN_TEXT))

                self.tableau_utilisateurs.setItem(row, 4, item_role)

                # Colonne Statut avec couleurs
                statut_text = "✅ Actif" if actif else "❌ Inactif"
                item_statut = QTableWidgetItem(statut_text)
                item_statut.setTextAlignment(Qt.AlignCenter)
                item_statut.setFont(style.FONT_BOLD_11)

                if actif:
                    item_statut.setBackground(QColor(style.COLOR_STATUT_ACTIF_BG))
                    item_statut.setForeground(QColor(style.COLOR_STATUT_ACTIF_TEXT))
                else:
                    item_statut.setBackground(QColor(style.COLOR_STATUT_INACTIF_BG))
                    item_statut.setForeground(QColor(style.COLOR_STATUT_INACTIF_TEXT))

                self.tableau_utilisateurs.setItem(row, 5, item_statut)

    def filtrer_utilisateurs(self):
        """Filtre les utilisateurs en fonction de la recherche"""
        filtre = self.search_input.text().lower()

        for row in range(self.tableau_utilisateurs.rowCount()):
            nom = self.tableau_utilisateurs.item(row, 1).text().lower()
            email = self.tableau_utilisateurs.item(row, 2).text().lower()

            visible = filtre in nom or filtre in email
            self.tableau_utilisateurs.setRowHidden(row, not visible)

    def modifier_role_utilisateur(self):
        """Modifie le rôle de l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self.tableau_utilisateurs.item(selected_row, 1).text()

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
        role_actuel = self.tableau_utilisateurs.item(selectedrow, 4).text()

        # Créer le dialogue de modification
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifier l'utilisateur {nom} {prenom}")
        dialog.setMinimumSize(450, 400)

        layout = QVBoxLayout(dialog)

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
        statut_actuel = self.tableau_utilisateurs.item(selectedrow, 5).text()
        checkactif.setChecked(statut_actuel == "Actif")
        formlayout.addRow("Statut :", checkactif)

        formgroup.setLayout(formlayout)
        layout.addWidget(formgroup)

        # Boutons de validation
        btnlayout = QHBoxLayout()
        btnvalider = QPushButton("Valider")
        btnannuler = QPushButton("Annuler")

        btnvalider.clicked.connect(dialog.accept)
        btnannuler.clicked.connect(dialog.reject)

        btnlayout.addWidget(btnvalider)
        btnlayout.addWidget(btnannuler)
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
                QMessageBox.information(self, "Succès",
                                        f"L'utilisateur {nouveau_nom} {nouveau_prenom} a été modifié avec succès.")
                self.load_utilisateurs()
            else:
                QMessageBox.critical(self, "Erreur", "Erreur lors de la modification de l'utilisateur.")

    def activer_utilisateur(self):
        """Active l'utilisateur sélectionné"""
        selected_row = self.tableau_utilisateurs.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "⚠️ Avertissement", "Veuillez sélectionner un utilisateur.")
            return

        id_user = int(self.tableau_utilisateurs.item(selected_row, 0).text())
        nom_prenom = self.tableau_utilisateurs.item(selected_row, 1).text()

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
        nom_prenom = self.tableau_utilisateurs.item(selected_row, 1).text()


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
        nom_prenom = self.tableau_utilisateurs.item(selected_row, 1).text()


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
            QMessageBox.information(
                self, "Succès",
                f"✅ Utilisateur {nom} {prenom} créé avec succès\nRôle : {role}"
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
