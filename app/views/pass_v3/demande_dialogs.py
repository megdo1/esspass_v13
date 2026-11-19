"""Dialogues de création, modification et duplication d'une demande."""

from PyQt5.QtWidgets import QWidget, QGroupBox, QTextEdit, QComboBox, QFormLayout
from PyQt5.QtWidgets import QLineEdit, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QDialog, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from datetime import datetime
from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDate
from app.data.errors import ConflitModificationError
from app.utils.decorators import busy_cursor_no_args
from app.utils.ui_helpers import show_info, show_warning, show_error
from app.views.pass_v3.widgets import NoScrollComboBox, ensure_combo_has_value


            # Fermer ce dialogue aussi
            # self.accept()


class EditDemandeDialog(QDialog):
    """Dialogue d'édition - UTILISE UNIQUEMENT DataManager"""

    def __init__(self, id_demande, data_manager, parent=None):
        super().__init__(parent)
        self.parent = parent  #
        # ✅ Configurer les flags de fenêtre pour permettre réduire/maximiser
        self.setWindowFlags(
            Qt.Window |  # Fenêtre indépendante
            Qt.WindowMinimizeButtonHint |  # Bouton réduire
            Qt.WindowMaximizeButtonHint |  # Bouton maximiser
            Qt.WindowCloseButtonHint  # Bouton fermer
        )

        # ✅ Empêcher la modalité (permet de réduire indépendamment)
        self.setWindowModality(Qt.NonModal)

        self.id_demande = id_demande
        self.data_manager = data_manager
        self.demande_data = {}
        self.setWindowTitle(f"Gérer la demande #{id_demande}")
        self.setMinimumSize(900, 700)
        self.load_demande()
        self.init_ui()

    @busy_cursor_no_args
    def load_demande(self):
        self.demande_data = self.data_manager.get_demande_by_id(self.id_demande)
        if not self.demande_data:
            show_error(self, "Erreur", "Demande introuvable")
            self.reject()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        title = QLabel(f"🔧 Traiter la demande #{self.id_demande}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        self.create_info_zone(scroll_layout)
        self.create_classification_zone(scroll_layout)
        self.create_priorisation_zone(scroll_layout)
        self.create_traitement_zone(scroll_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px; font-size: 12px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        btn_save = QPushButton("💾 Sauvegarder")
        btn_save.setStyleSheet("""
            QPushButton {background: #2F855A; color: white; font-weight: bold; padding: 10px 20px; font-size: 12px;}
            QPushButton:hover {background: #276749;}
        """)
        btn_save.clicked.connect(self.save_demande)
        buttons_layout.addWidget(btn_save)
        main_layout.addLayout(buttons_layout)

    def create_info_zone(self, parent_layout):
        # ✅ Vérifier si la demande est créée manuellement (ESPASS)
        conversation_id = self.demande_data.get("conversation_id", "")
        is_manual_demand = conversation_id.startswith("ESPASS")

        group = QGroupBox("📋 Informations générales")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }")
        layout = QFormLayout()
        self.txt_id = QLineEdit(str(self.demande_data.get('id_demande', '')))
        self.txt_id.setReadOnly(True)
        self.txt_id.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("ID :", self.txt_id)
        self.txt_libelle = QLineEdit(str(self.demande_data.get('libelle', '')))
        if is_manual_demand:
            self.txt_libelle.setReadOnly(False)
            self.txt_libelle.setStyleSheet("background-color: white;")
        else:
            self.txt_libelle.setReadOnly(True)
            self.txt_libelle.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Libellé :", self.txt_libelle)
        self.txt_sujet = QLineEdit(str(self.demande_data.get('sujet', '')))
        if is_manual_demand:
            self.txt_sujet.setReadOnly(False)
            self.txt_sujet.setStyleSheet("background-color: white;")
        else:
            self.txt_sujet.setReadOnly(True)
            self.txt_sujet.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Sujet :", self.txt_sujet)
        self.txt_demandeur = QLineEdit(str(self.demande_data.get('demandeur', '')))
        if is_manual_demand:
            self.txt_demandeur.setReadOnly(False)
            self.txt_demandeur.setStyleSheet("background-color: white;")
        else:
            self.txt_demandeur.setReadOnly(True)
            self.txt_demandeur.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Demandeur :", self.txt_demandeur)
        self.txt_date_reception = QLineEdit(str(self.demande_data.get('date_reception', '')))
        self.txt_date_reception.setReadOnly(True)
        self.txt_date_reception.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Date réception :", self.txt_date_reception)
        self.txt_resume = QTextEdit(str(self.demande_data.get('resume', '') if self.demande_data.get('resume') else ''))
        self.txt_resume.setMaximumHeight(80)
        layout.addRow("Résumé :", self.txt_resume)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_classification_zone(self, parent_layout):
        group = QGroupBox("🏷️ Classification")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #B45309; }")
        layout = QFormLayout()
        self.combo_canal = self.create_combo('canaux', 'id_canal')
        layout.addRow("Canal :", self.combo_canal)
        self.combo_domaine = self.create_combo('domaines', 'id_domaine')
        layout.addRow("Domaine :", self.combo_domaine)
        self.combo_responsable = NoScrollComboBox()
        self.combo_responsable.addItem("", None)
        users = self.data_manager.get_responsables()
        for user in users:
            self.combo_responsable.addItem(user['nom_complet'], user['id'])
        self.set_combo_value(self.combo_responsable, self.demande_data.get('id_responsable'))
        layout.addRow("Responsable :", self.combo_responsable)
        self.combo_categorie = self.create_combo('categories', 'id_categorie')
        self.combo_categorie.currentTextChanged.connect(self.on_categorie_changed)
        layout.addRow("Catégorie :", self.combo_categorie)
        self.combo_sous_categorie = NoScrollComboBox()
        self.combo_sous_categorie.addItem("", None)
        layout.addRow("Sous-catégorie :", self.combo_sous_categorie)
        self.update_sous_categories()
        self.combo_nature = self.create_combo('natures', 'id_nature')
        layout.addRow("Nature :", self.combo_nature)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_priorisation_zone(self, parent_layout):
        group = QGroupBox("⚡ Priorisation")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #C53030; }")
        layout = QFormLayout()
        self.combo_impact = self.create_combo('impacts', 'id_impact')
        layout.addRow("Impact :", self.combo_impact)
        self.combo_urgence = self.create_combo('urgences', 'id_urgence')
        layout.addRow("Urgence :", self.combo_urgence)
        #self.txt_priorite = QLineEdit(str(self.demande_data.get('priorite_calculee', '')))
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_traitement_zone(self, parent_layout):
        group = QGroupBox("✅ Zone Traitement")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }
        """)

        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(15)

        self.combo_etat = self.create_combo('etats', 'id_etat')
        self.combo_etat.currentTextChanged.connect(self.on_etat_changed)
        self.combo_etat.setMinimumWidth(220)
        layout.addRow("État :", self.combo_etat)

        self.label_date_traitement = QLabel("Date de traitement")

        self.date_traitement = QDateEdit()
        self.date_traitement.setCalendarPopup(True)  # ← Active le calendrier
        self.date_traitement.setDisplayFormat("yyyy-MM-dd")
        self.date_traitement.setDate(QDate.currentDate())
        self.date_traitement.setMinimumWidth(220)
        self.date_traitement.setStyleSheet("""
                QDateEdit {
                    background-color: #E6F4EC;
                    font-weight: bold;
                    padding: 8px;
                    border: 1px solid #2F855A;
                    border-radius: 3px;
                }
            """)

        layout.addRow(self.label_date_traitement, self.date_traitement)

        self.txt_solution = QTextEdit(
            str(self.demande_data.get('solution_suite_a_donner', '')) if self.demande_data.get(
                'solution_suite_a_donner') else ''
        )
        self.txt_solution.setMinimumHeight(100)
        self.txt_solution.setStyleSheet("background-color: white; border: 1px solid #ddd; padding: 8px;")
        layout.addRow("Solution :", self.txt_solution)

        self.txt_commentaire = QTextEdit(
            str(self.demande_data.get('commentaire', '')) if self.demande_data.get('commentaire') else ''
        )
        self.txt_commentaire.setMinimumHeight(85)
        self.txt_commentaire.setStyleSheet("background-color: white; border: 1px solid #ddd; padding: 8px;")
        layout.addRow("Commentaire :", self.txt_commentaire)

        group.setLayout(layout)
        parent_layout.addWidget(group)

        self.on_etat_changed()

    def on_etat_changed(self):
        """Affiche ou masque la date de traitement selon l'état"""
        etat_text = self.combo_etat.currentText()

        # Afficher uniquement pour "Traitée" ou "Fermée"
        if etat_text in ["Traitée", "Fermée"]:
            # Afficher la date actuelle
            #self.txt_date_traitement.setText(str(self.demande_data.get('date_traitement')
            #    or datetime.now().strftime("%Y-%m-%d")))
            self.label_date_traitement.setVisible(True)
            self.date_traitement.setVisible(True)
        else:
            # Masquer la date de traitement
            self.label_date_traitement.setVisible(False)
            self.date_traitement.setVisible(False)


    def create_combo(self, table_name, field_name):
        """Crée un combo et filtre selon les droits utilisateur"""
        combo = NoScrollComboBox()
        combo.addItem("", None)

        valeurs = self.data_manager.get_liste_valeurs(table_name)

        # ✅ Récupérer le rôle de l'utilisateur
        user_role = self.parent.user_info.get('role') if self.parent else None

        for valeur in valeurs:
            id_val = self.data_manager.id_mapping[table_name].get(valeur)

            # ✅ FILTRER l'état "Archivé" pour les non-administrateurs
            if table_name == 'etats' and valeur == "Archivée":
                # N'ajouter "Archivé" que pour les Administrateurs
                if user_role == "Administrateur":
                    combo.addItem(valeur, id_val)
                # Sinon, on skip (ne pas l'ajouter)
            else:
                # Tous les autres états/valeurs sont ajoutés normalement
                combo.addItem(valeur, id_val)

        # Pré-sélectionner la valeur actuelle
        self.set_combo_value(combo, self.demande_data.get(field_name))
        if table_name != 'etats':
            ensure_combo_has_value(combo, self.demande_data.get(field_name),
                                   self.data_manager.get_reference_label(table_name, self.demande_data.get(field_name)))

        return combo

    def on_categorie_changed(self):
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("", None)
        categorie_text = self.combo_categorie.currentText()
        if categorie_text in self.data_manager.sous_categories_by_categorie:
            sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
            for libelle_sc in sous_cats:
                id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                self.combo_sous_categorie.addItem(libelle_sc, id_sc)

    def update_sous_categories(self):
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("", None)
        categorie_text = self.demande_data.get('libelle_categorie', '')
        if categorie_text in self.data_manager.sous_categories_by_categorie:
            sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
            for libelle_sc in sous_cats:
                id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                self.combo_sous_categorie.addItem(libelle_sc, id_sc)
        self.set_combo_value(self.combo_sous_categorie, self.demande_data.get('id_sous_categorie'))
        ensure_combo_has_value(self.combo_sous_categorie, self.demande_data.get('id_sous_categorie'),
                               self.data_manager.get_reference_label('sous_categories', self.demande_data.get('id_sous_categorie')))

    def set_combo_value(self, combo, value_id):
        if value_id:
            index = combo.findData(value_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def save_demande(self):
        """Sauvegarde les modifications"""
        etat_text = self.combo_etat.currentText()

        data = {
            'resume': self.txt_resume.toPlainText(),
            'id_canal': self.combo_canal.currentData(),
            'id_domaine': self.combo_domaine.currentData(),
            'id_responsable': self.combo_responsable.currentData(),
            'id_categorie': self.combo_categorie.currentData(),
            'id_sous_categorie': self.combo_sous_categorie.currentData(),
            'id_nature': self.combo_nature.currentData(),
            'id_impact': self.combo_impact.currentData(),
            'id_urgence': self.combo_urgence.currentData(),
            'id_etat': self.combo_etat.currentData(),
            'solution_suite_a_donner': self.txt_solution.toPlainText(),
            'commentaire': self.txt_commentaire.toPlainText(),
            'libelle': self.txt_libelle.text().strip(),
            'sujet': self.txt_sujet.text().strip(),
            'demandeur': self.txt_demandeur.text().strip()
        }

        # Validation de la date de traitement
        date_traitement_text = self.date_traitement.date().toString("yyyy-MM-dd")
        if date_traitement_text:
            if self.combo_etat.currentText() in ('Traitée', 'Fermée'):
                try:
                    # Parser la date (format BD : YYYY-MM-DD HH:MM:SS)
                    dt_traitement = datetime.strptime(date_traitement_text, '%Y-%m-%d')
                    dt_maintenant = datetime.now()

                    # ❌ BLOQUER si la date est dans le futur
                    if dt_traitement > dt_maintenant:
                        show_warning(
                            self,
                            "⚠️ Date invalide",
                            f"La date de traitement ne peut pas être dans le futur !\n\n"
                            f"Date saisie : {dt_traitement.strftime('%Y-%m-%d')}\n"
                            f"Date actuelle : {dt_maintenant.strftime('%Y-%m-%d')}\n\n"
                            f"Veuillez corriger la date."
                        )
                        self.date_traitement.setFocus()
                        return

                    data['date_traitement'] = date_traitement_text
                except ValueError:
                    show_warning(
                        self,
                        "Format de date invalide",
                        "Le format de la date de traitement doit être : AAAA-MM-JJ\n"
                        "Exemple : 2025-01-01"
                    )
                    return
            elif self.combo_etat.currentText() in ('En cours de traitement','À étudier'):
                data['date_traitement'] = ''


        try:
            sauvegarde_ok = self.data_manager.update_demande(
                self.id_demande, data,
                expected_updated_at=(self.demande_data or {}).get('updated_at'))
        except ConflitModificationError as e:
            show_warning(self, "Conflit de modification",
                         f"{e}\n\nVos changements n'ont PAS été enregistrés.\n"
                         "Fermez cette fenêtre, rouvrez la demande puis refaites votre modification.")
            return

        if sauvegarde_ok:
            show_info(self, "Succès", "✅ Demande sauvegardée avec succès !")
            self.accept()
        else:
            show_error(self, "Erreur", "❌ Sauvegarde impossible : " + (self.data_manager.last_error or "erreur lors de la sauvegarde"))


class CreateDemandeDialog(QDialog):
    """Dialogue de création - Champs auto-générés: ID, Date, Utilisateur"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("➕ Créer une nouvelle demande")
        self.setMinimumSize(900, 700)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        title = QLabel("➕ Créer une nouvelle demande")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        self.create_info_zone(scroll_layout)
        self.create_classification_zone(scroll_layout)
        self.create_priorisation_zone(scroll_layout)
        self.create_traitement_zone(scroll_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px; font-size: 12px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        btn_save = QPushButton("💾 Créer la demande")
        btn_save.setStyleSheet(
            "QPushButton {background: #2F855A; color: white; font-weight: bold; padding: 10px 20px; font-size: 12px;} QPushButton:hover {background: #276749;}")
        btn_save.clicked.connect(self.create_demande)
        buttons_layout.addWidget(btn_save)
        main_layout.addLayout(buttons_layout)

    def create_info_zone(self, parent_layout):
        group = QGroupBox("📋 Informations de base")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }")
        layout = QFormLayout()
        self.txt_id = QLineEdit("Auto-généré")
        self.txt_id.setReadOnly(True)
        self.txt_id.setStyleSheet("background-color: #E6F4EC; font-weight: bold;")
        layout.addRow("ID :", self.txt_id)
        self.txt_date_reception = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.txt_date_reception.setReadOnly(True)
        self.txt_date_reception.setStyleSheet("background-color: #E6F4EC;")
        layout.addRow("Date réception :", self.txt_date_reception)
        user_info = self.data_manager.get_current_user()
        self.txt_createur = QLineEdit(f"{user_info['prenom']} {user_info['nom']}")
        self.txt_createur.setReadOnly(True)
        self.txt_createur.setStyleSheet("background-color: #E6F4EC;")
        layout.addRow("Créé par :", self.txt_createur)
        self.txt_libelle = QLineEdit()
        self.txt_libelle.setPlaceholderText("Titre court de la demande (obligatoire)")
        layout.addRow("Libellé * :", self.txt_libelle)
        self.txt_sujet = QLineEdit()
        self.txt_sujet.setPlaceholderText("Sujet principal (obligatoire)")
        layout.addRow("Sujet * :", self.txt_sujet)
        self.txt_demandeur = QLineEdit()
        self.txt_demandeur.setPlaceholderText("Email du demandeur (obligatoire)")
        layout.addRow("Demandeur * :", self.txt_demandeur)
        self.txt_resume = QTextEdit()
        self.txt_resume.setPlaceholderText("Description détaillée de la demande...")
        self.txt_resume.setMaximumHeight(100)
        layout.addRow("Résumé :", self.txt_resume)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_classification_zone(self, parent_layout):
        group = QGroupBox("🏷️ Classification")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #B45309; }")
        layout = QFormLayout()
        self.combo_canal = self.create_combo('canaux')
        layout.addRow("Canal :", self.combo_canal)

        # Présélectionner CRP si présent dans la liste
        index = self.combo_canal.findText("CRP")
        if index >= 0:
            self.combo_canal.setCurrentIndex(index)

        self.combo_domaine = self.create_combo('domaines')
        layout.addRow("Domaine :", self.combo_domaine)
        self.combo_responsable = NoScrollComboBox()
        self.combo_responsable.addItem("", None)
        users = self.data_manager.get_responsables()
        for user in users:
            self.combo_responsable.addItem(user['nom_complet'], user['id'])
        layout.addRow("Responsable :", self.combo_responsable)
        self.combo_categorie = self.create_combo('categories')
        self.combo_categorie.currentTextChanged.connect(self.on_categorie_changed)
        layout.addRow("Catégorie :", self.combo_categorie)
        self.combo_sous_categorie = NoScrollComboBox()
        self.combo_sous_categorie.addItem("", None)
        layout.addRow("Sous-catégorie :", self.combo_sous_categorie)
        self.combo_nature = self.create_combo('natures')
        layout.addRow("Nature :", self.combo_nature)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_priorisation_zone(self, parent_layout):
        group = QGroupBox("⚡ Priorisation")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #C53030; }")
        layout = QFormLayout()
        self.combo_impact = self.create_combo('impacts')
        layout.addRow("Impact :", self.combo_impact)
        self.combo_urgence = self.create_combo('urgences')
        layout.addRow("Urgence :", self.combo_urgence)
        info_label = QLabel("💡 La priorité sera calculée automatiquement selon Impact × Urgence")
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addRow("", info_label)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_traitement_zone(self, parent_layout):
        group = QGroupBox("⚙️ Informations complémentaires")
        group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }")
        layout = QFormLayout()
        self.combo_etat = self.create_combo('etats')
        index = self.combo_etat.findText("À étudier")
        if index >= 0:
            self.combo_etat.setCurrentIndex(index)
        self.combo_etat.currentTextChanged.connect(self.on_etat_changed)
        layout.addRow("État :", self.combo_etat)

        # Date de traitement : saisissable dès la création si le ticket est déjà traité
        self.label_date_traitement = QLabel("Date de traitement :")
        self.date_traitement = QDateEdit()
        self.date_traitement.setCalendarPopup(True)
        self.date_traitement.setDisplayFormat("yyyy-MM-dd")
        self.date_traitement.setDate(QDate.currentDate())
        self.date_traitement.setMaximumDate(QDate.currentDate())
        layout.addRow(self.label_date_traitement, self.date_traitement)

        self.txt_solution = QTextEdit()
        self.txt_solution.setPlaceholderText("Solution ou suite à donner...")
        self.txt_solution.setMaximumHeight(80)
        layout.addRow("Solution :", self.txt_solution)
        self.txt_commentaire = QTextEdit()
        self.txt_commentaire.setPlaceholderText("Commentaires additionnels...")
        self.txt_commentaire.setMaximumHeight(60)
        layout.addRow("Commentaire :", self.txt_commentaire)
        group.setLayout(layout)
        parent_layout.addWidget(group)
        self.on_etat_changed()

    def on_etat_changed(self):
        """Affiche la date de traitement uniquement pour les états 'Traitée' ou 'Fermée'"""
        visible = self.combo_etat.currentText() in ("Traitée", "Fermée")
        self.label_date_traitement.setVisible(visible)
        self.date_traitement.setVisible(visible)

    def create_combo(self, table_name):
        combo = NoScrollComboBox()
        combo.addItem("", None)
        valeurs = self.data_manager.get_liste_valeurs(table_name)
        for valeur in valeurs:
            id_val = self.data_manager.id_mapping[table_name].get(valeur)
            combo.addItem(valeur, id_val)
        return combo

    def on_categorie_changed(self):
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("", None)
        categorie_text = self.combo_categorie.currentText()
        if categorie_text in self.data_manager.sous_categories_by_categorie:
            sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
            for libelle_sc in sous_cats:
                id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                self.combo_sous_categorie.addItem(libelle_sc, id_sc)

    def create_demande(self):
        if not self.txt_libelle.text().strip():
            show_warning(self, "Champ obligatoire", "Le libellé est obligatoire !")
            self.txt_libelle.setFocus()
            return
        if not self.txt_sujet.text().strip():
            show_warning(self, "Champ obligatoire", "Le sujet est obligatoire !")
            self.txt_sujet.setFocus()
            return
        if not self.txt_demandeur.text().strip():
            show_warning(self, "Champ obligatoire", "Le demandeur est obligatoire !")
            self.txt_demandeur.setFocus()
            return
        data = {
            'libelle': self.txt_libelle.text().strip(),
            'sujet': self.txt_sujet.text().strip(),
            'resume': self.txt_resume.toPlainText().strip(),
            'demandeur': self.txt_demandeur.text().strip(),
            'date_reception': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'id_canal': self.combo_canal.currentData(),
            'id_domaine': self.combo_domaine.currentData(),
            'id_responsable': self.combo_responsable.currentData(),
            'id_categorie': self.combo_categorie.currentData(),
            'id_sous_categorie': self.combo_sous_categorie.currentData(),
            'id_nature': self.combo_nature.currentData(),
            'id_impact': self.combo_impact.currentData(),
            'id_urgence': self.combo_urgence.currentData(),
            'id_etat': self.combo_etat.currentData(),
            'solution_suite_a_donner': self.txt_solution.toPlainText().strip(),
            'commentaire': self.txt_commentaire.toPlainText().strip()
        }
        if self.combo_etat.currentText() in ("Traitée", "Fermée"):
            date_traitement = self.date_traitement.date()
            if date_traitement > QDate.currentDate():
                show_warning(
                    self,
                    "⚠️ Date invalide",
                    "La date de traitement ne peut pas être dans le futur !\n\n"
                    f"Date saisie : {date_traitement.toString('yyyy-MM-dd')}\n"
                    f"Date actuelle : {QDate.currentDate().toString('yyyy-MM-dd')}\n\n"
                    "Veuillez corriger la date."
                )
                self.date_traitement.setFocus()
                return
            data['date_traitement'] = date_traitement.toString("yyyy-MM-dd")
        id_demande = self.data_manager.create_demande(data)
        if id_demande:
            show_info(self, "Succès",
                                    f"✅ Demande créée avec succès !\n\nID : {id_demande}\nLibellé : {data['libelle']}")
            self.accept()
        else:
            show_error(self, "Erreur", "❌ Création impossible : " + (self.data_manager.last_error or "erreur lors de la création"))


class DuplicateDemandeDialog(QDialog):
    """Dialogue de duplication - Pré-remplit tous les champs sauf ID et conversation_id"""

    def __init__(self, id_demande, data_manager, parent=None):
        super().__init__(parent)
        self.id_demande_source = id_demande
        self.data_manager = data_manager
        self.demande_data = {}
        self.setWindowTitle(f"📋 Dupliquer la demande #{id_demande}")
        self.setMinimumSize(900, 700)
        self.load_demande_source()
        self.init_ui()

    @busy_cursor_no_args
    def load_demande_source(self):
        """Charge les données de la demande à dupliquer"""
        self.demande_data = self.data_manager.get_demande_by_id(self.id_demande_source)
        if not self.demande_data:
            show_error(self, "Erreur", "Demande source introuvable")
            self.reject()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Titre
        title = QLabel(f"📋 Dupliquer la demande #{self.id_demande_source}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Info label
        info_label = QLabel(
            "💡 Les champs sont pré-remplis avec les données de la demande source. Vous pouvez les modifier avant de créer.")
        info_label.setStyleSheet(
            "color: #B45309; font-style: italic; padding: 10px; background: #FDF1E3; border-radius: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.create_info_zone(scroll_layout)
        self.create_classification_zone(scroll_layout)
        self.create_priorisation_zone(scroll_layout)
        self.create_traitement_zone(scroll_layout)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px; font-size: 12px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_save = QPushButton("📋 Créer la copie")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #4C51BF;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #434190;
            }
        """)
        btn_save.clicked.connect(self.create_duplicate)
        buttons_layout.addWidget(btn_save)

        main_layout.addLayout(buttons_layout)

    def create_info_zone(self, parent_layout):
        """Zone informations - Champs modifiables"""
        group = QGroupBox("📋 Informations de base")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }
        """)

        layout = QFormLayout()

        # ID - auto-généré
        self.txt_id = QLineEdit("Nouvel ID (auto-généré)")
        self.txt_id.setReadOnly(True)
        self.txt_id.setStyleSheet("background-color: #E6F4EC; font-weight: bold;")
        layout.addRow("ID :", self.txt_id)

        # Date - date actuelle
        self.txt_date_reception = QLineEdit(datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.txt_date_reception.setReadOnly(True)
        self.txt_date_reception.setStyleSheet("background-color: #E6F4EC;")
        layout.addRow("Date réception :", self.txt_date_reception)

        # Créateur - utilisateur actuel
        user_info = self.data_manager.get_current_user()
        self.txt_createur = QLineEdit(f"{user_info['prenom']} {user_info['nom']}")
        self.txt_createur.setReadOnly(True)
        self.txt_createur.setStyleSheet("background-color: #E6F4EC;")
        layout.addRow("Créé par :", self.txt_createur)

        # Libellé - pré-rempli avec "Copie de..."
        libelle_original = str(self.demande_data.get('libelle', ''))
        self.txt_libelle = QLineEdit(f"Copie de {libelle_original}")
        self.txt_libelle.setPlaceholderText("Titre court de la demande (obligatoire)")
        layout.addRow("Libellé * :", self.txt_libelle)

        # Sujet - pré-rempli
        self.txt_sujet = QLineEdit(str(self.demande_data.get('sujet', '')))
        self.txt_sujet.setPlaceholderText("Sujet principal (obligatoire)")
        layout.addRow("Sujet * :", self.txt_sujet)

        # Demandeur - pré-rempli
        self.txt_demandeur = QLineEdit(str(self.demande_data.get('demandeur', '')))
        self.txt_demandeur.setPlaceholderText("Email du demandeur (obligatoire)")
        layout.addRow("Demandeur * :", self.txt_demandeur)

        # Résumé - pré-rempli
        resume = str(self.demande_data.get('resume', '') if self.demande_data.get('resume') else '')
        self.txt_resume = QTextEdit(resume)
        self.txt_resume.setPlaceholderText("Description détaillée de la demande...")
        self.txt_resume.setMaximumHeight(100)
        layout.addRow("Résumé :", self.txt_resume)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_classification_zone(self, parent_layout):
        """Zone classification - Pré-remplie"""
        group = QGroupBox("🏷️ Classification")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #B45309; }
        """)

        layout = QFormLayout()

        # Canal
        self.combo_canal = self.create_combo('canaux', 'id_canal')
        layout.addRow("Canal :", self.combo_canal)

        # Domaine
        self.combo_domaine = self.create_combo('domaines', 'id_domaine')
        layout.addRow("Domaine :", self.combo_domaine)

        # Responsable
        self.combo_responsable = QComboBox()
        self.combo_responsable.addItem("", None)
        users = self.data_manager.get_responsables()
        for user in users:
            self.combo_responsable.addItem(user['nom_complet'], user['id'])
        self.set_combo_value(self.combo_responsable, self.demande_data.get('id_responsable'))
        layout.addRow("Responsable :", self.combo_responsable)

        # Catégorie
        self.combo_categorie = self.create_combo('categories', 'id_categorie')
        self.combo_categorie.currentTextChanged.connect(self.on_categorie_changed)
        layout.addRow("Catégorie :", self.combo_categorie)

        # Sous-catégorie
        self.combo_sous_categorie = QComboBox()
        self.combo_sous_categorie.addItem("", None)
        layout.addRow("Sous-catégorie :", self.combo_sous_categorie)
        self.update_sous_categories()

        # Nature
        self.combo_nature = self.create_combo('natures', 'id_nature')
        layout.addRow("Nature :", self.combo_nature)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_priorisation_zone(self, parent_layout):
        """Zone priorisation - Pré-remplie"""
        group = QGroupBox("⚡ Priorisation")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #C53030; }
        """)

        layout = QFormLayout()

        # Impact
        self.combo_impact = self.create_combo('impacts', 'id_impact')
        layout.addRow("Impact :", self.combo_impact)

        # Urgence
        self.combo_urgence = self.create_combo('urgences', 'id_urgence')
        layout.addRow("Urgence :", self.combo_urgence)

        # Info priorité
        info_label = QLabel("💡 La priorité sera recalculée automatiquement")
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addRow("", info_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_traitement_zone(self, parent_layout):
        """Zone traitement - Pré-remplie"""
        group = QGroupBox("⚙️ Informations complémentaires")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }
        """)

        layout = QFormLayout()

        # État - par défaut "À étudier"
        self.combo_etat = self.create_combo('etats', None)
        index = self.combo_etat.findText("À étudier")
        if index >= 0:
            self.combo_etat.setCurrentIndex(index)
        layout.addRow("État :", self.combo_etat)

        # Solution - pré-remplie
        solution = str(self.demande_data.get('solution_suite_a_donner', '') if self.demande_data.get(
            'solution_suite_a_donner') else '')
        self.txt_solution = QTextEdit(solution)
        self.txt_solution.setPlaceholderText("Solution ou suite à donner...")
        self.txt_solution.setMaximumHeight(80)
        layout.addRow("Solution :", self.txt_solution)

        # Commentaire - pré-rempli avec indication de duplication
        commentaire_original = str(
            self.demande_data.get('commentaire', '') if self.demande_data.get('commentaire') else '')
        commentaire = f"[Dupliqué de la demande #{self.id_demande_source}]\n{commentaire_original}"
        self.txt_commentaire = QTextEdit(commentaire)
        self.txt_commentaire.setPlaceholderText("Commentaires additionnels...")
        self.txt_commentaire.setMaximumHeight(60)
        layout.addRow("Commentaire :", self.txt_commentaire)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_combo(self, table_name, field_name):
        """Crée un combo et pré-sélectionne la valeur"""
        combo = QComboBox()
        combo.addItem("", None)
        valeurs = self.data_manager.get_liste_valeurs(table_name)
        for valeur in valeurs:
            id_val = self.data_manager.id_mapping[table_name].get(valeur)
            combo.addItem(valeur, id_val)

        # Pré-sélectionner la valeur si field_name fourni
        if field_name:
            self.set_combo_value(combo, self.demande_data.get(field_name))
            if table_name != 'etats':
                ensure_combo_has_value(combo, self.demande_data.get(field_name),
                                       self.data_manager.get_reference_label(table_name, self.demande_data.get(field_name)))

        return combo

    def set_combo_value(self, combo, value_id):
        if value_id:
            index = combo.findData(value_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def on_categorie_changed(self):
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("", None)
        categorie_text = self.combo_categorie.currentText()
        if categorie_text in self.data_manager.sous_categories_by_categorie:
            sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
            for libelle_sc in sous_cats:
                id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                self.combo_sous_categorie.addItem(libelle_sc, id_sc)

    def update_sous_categories(self):
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("", None)
        categorie_text = self.demande_data.get('libelle_categorie', '')
        if categorie_text in self.data_manager.sous_categories_by_categorie:
            sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
            for libelle_sc in sous_cats:
                id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                self.combo_sous_categorie.addItem(libelle_sc, id_sc)
        self.set_combo_value(self.combo_sous_categorie, self.demande_data.get('id_sous_categorie'))
        ensure_combo_has_value(self.combo_sous_categorie, self.demande_data.get('id_sous_categorie'),
                               self.data_manager.get_reference_label('sous_categories', self.demande_data.get('id_sous_categorie')))

    @busy_cursor_no_args
    def create_duplicate(self):
        """Crée la demande dupliquée"""
        # Validation des champs obligatoires
        if not self.txt_libelle.text().strip():
            show_warning(self, "Champ obligatoire", "Le libellé est obligatoire !")
            self.txt_libelle.setFocus()
            return

        if not self.txt_sujet.text().strip():
            show_warning(self, "Champ obligatoire", "Le sujet est obligatoire !")
            self.txt_sujet.setFocus()
            return

        if not self.txt_demandeur.text().strip():
            show_warning(self, "Champ obligatoire", "Le demandeur est obligatoire !")
            self.txt_demandeur.setFocus()
            return

        # Préparer les données (sans id_demande ni conversation_id)
        data = {
            'libelle': self.txt_libelle.text().strip(),
            'sujet': self.txt_sujet.text().strip(),
            'resume': self.txt_resume.toPlainText().strip(),
            'demandeur': self.txt_demandeur.text().strip(),
            'date_reception': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'id_canal': self.combo_canal.currentData(),
            'id_domaine': self.combo_domaine.currentData(),
            'id_responsable': self.combo_responsable.currentData(),
            'id_categorie': self.combo_categorie.currentData(),
            'id_sous_categorie': self.combo_sous_categorie.currentData(),
            'id_nature': self.combo_nature.currentData(),
            'id_impact': self.combo_impact.currentData(),
            'id_urgence': self.combo_urgence.currentData(),
            'id_etat': self.combo_etat.currentData(),
            'solution_suite_a_donner': self.txt_solution.toPlainText().strip(),
            'commentaire': self.txt_commentaire.toPlainText().strip()
        }

        # Créer la demande (génèrera un nouvel ID et conversation_id)
        id_demande = self.data_manager.create_demande(data)

        if id_demande:
            show_info(
                self,
                "Succès",
                f"✅ Demande dupliquée avec succès !\n\n"
                f"Nouvel ID : {id_demande}\n"
                f"Source : Demande #{self.id_demande_source}\n"
                f"Libellé : {data['libelle']}"
            )
            self.accept()
        else:
            show_error(self, "Erreur", "❌ Duplication impossible : " + (self.data_manager.last_error or "erreur lors de la duplication"))
