"""Dialogues de traitement unitaire et en masse des demandes."""

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
from app.views.pass_v3.widgets import NoScrollComboBox


class TraiterDemandeDialog(QDialog):
    """Dialogue de traitement - Permet uniquement de modifier la zone traitement"""

    def __init__(self, id_demande, data_manager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.id_demande = id_demande
        self.data_manager = data_manager
        self.demande_data = {}
        self.setWindowTitle(f"Traiter la demande #{id_demande}")
        self.setMinimumSize(700, 600)
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

        # Titre
        title = QLabel(f"🔧 Traiter la demande #{self.id_demande}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Zone d'information en lecture seule
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.create_info_zone_readonly(scroll_layout)
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

        btn_save = QPushButton("💾 Sauvegarder le traitement")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #2F855A;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #276749;
            }
        """)
        btn_save.clicked.connect(self.save_traitement)
        buttons_layout.addWidget(btn_save)

        main_layout.addLayout(buttons_layout)

    def create_info_zone_readonly(self, parent_layout):
        """Zone d'information en lecture seule"""
        conversation_id = self.demande_data.get("conversation_id", "")
        is_manual_demand = conversation_id.startswith("ESPASS")

        group = QGroupBox("📋 Informations de la demande")
        group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }
        """)

        layout = QFormLayout()

        # Tous les champs en lecture seule
        self.txt_id = QLineEdit(str(self.demande_data.get("id_demande", "")))
        self.txt_id.setReadOnly(True)
        self.txt_id.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("ID :", self.txt_id)

        self.txt_libelle = QLineEdit(str(self.demande_data.get("libelle", "")))
        if is_manual_demand:
            self.txt_libelle.setReadOnly(False)
            self.txt_libelle.setStyleSheet("background-color: white;")
        else:
            self.txt_libelle.setReadOnly(True)
            self.txt_libelle.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Libellé :", self.txt_libelle)

        self.txt_sujet = QLineEdit(str(self.demande_data.get("sujet", "")))
        if is_manual_demand:
            self.txt_sujet.setReadOnly(False)
            self.txt_sujet.setStyleSheet("background-color: white;")
        else:
            self.txt_sujet.setReadOnly(True)
            self.txt_sujet.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Sujet :", self.txt_sujet)

        self.txt_demandeur = QLineEdit(str(self.demande_data.get("demandeur", "")))
        if is_manual_demand:
            self.txt_demandeur.setReadOnly(False)
            self.txt_demandeur.setStyleSheet("background-color: white;")
        else:
            self.txt_demandeur.setReadOnly(True)
            self.txt_demandeur.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Demandeur :", self.txt_demandeur)

        self.txt_date_reception = QLineEdit(str(self.demande_data.get("date_reception", "")))
        self.txt_date_reception.setReadOnly(True)
        self.txt_date_reception.setStyleSheet("background-color: #F1F5F9;")
        layout.addRow("Date réception :", self.txt_date_reception)

        self.txt_resume = QTextEdit(str(self.demande_data.get("resume", "") if self.demande_data.get("resume") else ""))
        if is_manual_demand:
            self.txt_demandeur.setReadOnly(False)
            self.txt_demandeur.setStyleSheet("background-color: white;")
        else:
            self.txt_demandeur.setReadOnly(True)
            self.txt_demandeur.setStyleSheet("background-color: #F1F5F9;")
        self.txt_resume.setMaximumHeight(80)
        layout.addRow("Résumé :", self.txt_resume)

        # Afficher la classification actuelle
        self.txt_etat_actuel = QLineEdit(str(self.demande_data.get("libelle_etat", "")))
        self.txt_etat_actuel.setReadOnly(True)
        self.txt_etat_actuel.setStyleSheet("background-color: #FDF1E3; font-weight: bold;")
        layout.addRow("État actuel :", self.txt_etat_actuel)

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



        self.label_date_traitement = QLabel("📅 Date de traitement :")
        self.date_traitement = QDateEdit()
        self.date_traitement.setCalendarPopup(True)  # ← Active le calendrier
        self.date_traitement.setDisplayFormat("yyyy-MM-dd")  # Format d'affichage
        self.date_traitement.setDate(QDate.currentDate())  # Date du jour par défaut
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
        self.txt_solution.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        layout.addRow("Solution :", self.txt_solution)

        self.txt_commentaire = QTextEdit(
            str(self.demande_data.get('commentaire', '')) if self.demande_data.get('commentaire') else ''
        )
        self.txt_commentaire.setMinimumHeight(85)
        self.txt_commentaire.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        layout.addRow("Commentaire :", self.txt_commentaire)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_combo(self, table_name, field_name):
        combo = QComboBox()
        combo.addItem("", None)
        valeurs = self.data_manager.get_liste_valeurs(table_name)
        for valeur in valeurs:
            id_val = self.data_manager.id_mapping[table_name].get(valeur)
            combo.addItem(valeur, id_val)
        self.set_combo_value(combo, self.demande_data.get(field_name))
        return combo

    def set_combo_value(self, combo, value_id):
        if value_id:
            index = combo.findData(value_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    @busy_cursor_no_args
    def save_traitement(self):
        """Sauvegarde uniquement les données de traitement"""
        date_traitement_text = self.date_traitement.date().toString("yyyy-MM-dd")
        if date_traitement_text:
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

            except ValueError:
                show_warning(
                    self,
                    "Format de date invalide",
                    "Le format de la date de traitement doit être : AAAA-MM-JJ\n"
                    "Exemple : 2025-01-01"
                )
                return

        # Préparer les données à mettre à jour
        data = {
            "id_etat": self.data_manager.get_etat_id_by_libelle("Traitée"),
            "solution_suite_a_donner": self.txt_solution.toPlainText(),
            "commentaire": self.txt_commentaire.toPlainText(),
            "id_responsable": self.parent.user_info['id'],
            "date_traitement": date_traitement_text,
            "libelle" : self.txt_libelle.text().strip(),
            'sujet': self.txt_sujet.text().strip(),
            'resume': self.txt_resume.toPlainText().strip(),
            'demandeur': self.txt_demandeur.text().strip()
        }


        # Mettre à jour uniquement les champs de traitement
        try:
            sauvegarde_ok = self.data_manager.update_demande(
                self.id_demande, data,
                expected_updated_at=(self.demande_data or {}).get('updated_at'))
        except ConflitModificationError as e:
            show_warning(self, "Conflit de modification",
                         f"{e}\n\nVos changements n'ont PAS été enregistrés.\n"
                         "Fermez cette fenêtre, rouvrez la demande puis refaites votre traitement.")
            return

        if sauvegarde_ok:
            show_info(self, "Succès", "✅ Traitement sauvegardé avec succès !")
            self.accept()
        else:
            show_error(self, "Erreur", "❌ Sauvegarde du traitement impossible : " + (self.data_manager.last_error or "erreur lors de la sauvegarde"))


class TraiterMasseDialog(QDialog):
    """Dialogue pour traiter plusieurs demandes en masse"""

    def __init__(self, liste_ids, datamanager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.liste_ids = liste_ids
        self.data_manager = datamanager
        self.setWindowTitle(f"Traiter {len(liste_ids)} demandes en masse")
        self.setMinimumSize(650, 500)
        self.initui()

    def initui(self):
        main_layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(f"⚙️ Traitement en masse de {len(self.liste_ids)} demandes")
        info_label.setStyleSheet("color: #1F4E9C; font-weight: bold; padding: 10px; font-size: 13px;")
        main_layout.addWidget(info_label)

        # ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)

        # Zone traitement
        group_trait = QGroupBox("🛠️ Zone Traitement")
        group_trait.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }
        """)
        self.layout_trait = QFormLayout()
        self.layout_trait.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layout_trait.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout_trait.setHorizontalSpacing(20)
        self.layout_trait.setVerticalSpacing(15)

        self.label_date_traitement = QLabel("Date de traitement")

        # ✅ Créer un QDateEdit avec calendrier popup
        self.date_traitement = QDateEdit()
        self.date_traitement.setCalendarPopup(True)  # ← Active le calendrier
        self.date_traitement.setDisplayFormat("yyyy-MM-dd")  # Format d'affichage
        self.date_traitement.setDate(QDate.currentDate())  # Date du jour par défaut
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

        self.layout_trait.addRow(self.label_date_traitement, self.date_traitement)

        # Solution
        self.txt_solution = QTextEdit()
        self.txt_solution.setPlaceholderText("Solution commune (optionnel)")
        self.txt_solution.setMinimumHeight(100)
        self.txt_solution.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        self.layout_trait.addRow("Solution :", self.txt_solution)

        # Commentaire
        self.txt_commentaire = QTextEdit()
        self.txt_commentaire.setPlaceholderText("Commentaire commun (optionnel)")
        self.txt_commentaire.setMinimumHeight(85)
        self.txt_commentaire.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        self.layout_trait.addRow("Commentaire :", self.txt_commentaire)

        group_trait.setLayout(self.layout_trait)
        form_layout.addWidget(group_trait)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_save = QPushButton("✅ Appliquer à toutes les demandes")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #2F855A;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #276749;
            }
        """)
        btn_save.clicked.connect(self.apply_changes)
        buttons_layout.addWidget(btn_save)

        main_layout.addLayout(buttons_layout)

    @busy_cursor_no_args
    def apply_changes(self):
        """Applique les modifications à toutes les demandes EN UNE SEULE REQUÊTE"""
        # Récupérer l'ID de l'état "Traité"
        id_etat = self.data_manager.get_etat_id_by_libelle('Traitée')
        solution = self.txt_solution.toPlainText().strip()
        commentaire = self.txt_commentaire.toPlainText().strip()

        # Préparer les données avec snake_case
        data = {
            'id_responsable': self.parent.user_info['id']
        }

        if id_etat:
            data['id_etat'] = id_etat

        # ✅ CHANGEMENT : Récupérer la date depuis QDateEdit
        date_traitement = self.date_traitement.date().toString("yyyy-MM-dd")
        if date_traitement:
            try:
                # Parser la date (format BD : YYYY-MM-DD HH:MM:SS)
                dt_traitement = datetime.strptime(date_traitement, '%Y-%m-%d')
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

                data['date_traitement'] = date_traitement

            except ValueError:
                show_warning(
                    self,
                    "Format de date invalide",
                    "Le format de la date de traitement doit être : AAAA-MM-JJ\n"
                    "Exemple : 2025-01-01"
                )
                return

        if solution:
            data['solution_suite_a_donner'] = solution

        if commentaire:
            data['commentaire'] = commentaire

        # ✅ OPTIMISATION : Un seul UPDATE pour toutes les demandes
        succes, echec = self.data_manager.update_demandes_bulk(self.liste_ids, data)

        if echec == 0:
            show_info(
                self,
                "Succès",
                f"✅ {succes} demandes traitées avec succès en une seule opération !"
            )
            self.accept()
        else:
            show_warning(
                self,
                "Traitement partiel",
                f"✅ {succes} demandes traitées\n❌ {echec} échecs"
            )
            self.accept()


class GererMasseDialog(QDialog):
    """Dialogue pour gérer plusieurs demandes en masse (modification complète)"""

    def __init__(self, liste_ids, data_manager, parent=None):
        super().__init__(parent)
        self.liste_ids = liste_ids
        self.data_manager = data_manager
        self.parent = parent  # ✅ Pour accéder au userinfo

        self.setWindowTitle(f"Gérer {len(liste_ids)} demandes en masse")
        self.setMinimumSize(800, 700)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(f"Modification en masse de {len(self.liste_ids)} demandes")
        info_label.setStyleSheet("color: #B45309; font-weight: bold; padding: 10px; font-size: 13px;")
        main_layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)

        # ZONE CLASSIFICATION
        group_classif = QGroupBox("📋 Zone Classification")
        group_classif.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #B45309; }")
        layout_classif = QFormLayout()

        self.combo_canal = self._create_combo_optional('canaux')
        layout_classif.addRow("Canal :", self.combo_canal)

        self.combo_domaine = self._create_combo_optional('domaines')
        layout_classif.addRow("Domaine :", self.combo_domaine)

        self.combo_responsable = NoScrollComboBox()
        self.combo_responsable.addItem("(Choisir une valeur)", None)
        users = self.data_manager.get_responsables()
        for user in users:
            self.combo_responsable.addItem(user['nom_complet'], user['id'])
        layout_classif.addRow("Responsable :", self.combo_responsable)

        self.combo_categorie = self._create_combo_optional('categories')
        self.combo_categorie.currentTextChanged.connect(self.on_categorie_changed)
        layout_classif.addRow("Catégorie :", self.combo_categorie)

        self.combo_sous_categorie = NoScrollComboBox()
        self.combo_sous_categorie.addItem("(Choisir une valeur)", None)
        layout_classif.addRow("Sous-catégorie :", self.combo_sous_categorie)

        self.combo_nature = self._create_combo_optional('natures')
        layout_classif.addRow("Nature :", self.combo_nature)

        group_classif.setLayout(layout_classif)
        form_layout.addWidget(group_classif)

        # ZONE PRIORISATION
        group_prio = QGroupBox("⚠️ Zone Priorisation")
        group_prio.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #C53030; }")
        layout_prio = QFormLayout()

        self.combo_impact = self._create_combo_optional('impacts')
        layout_prio.addRow("Impact :", self.combo_impact)

        self.combo_urgence = self._create_combo_optional('urgences')
        layout_prio.addRow("Urgence :", self.combo_urgence)

        group_prio.setLayout(layout_prio)
        form_layout.addWidget(group_prio)

        # Zone traitement harmonisée visuellement 
        group_trait = QGroupBox("✅ Zone Traitement")
        group_trait.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }
        """)
        self.layout_trait = QFormLayout()
        self.layout_trait.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layout_trait.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout_trait.setHorizontalSpacing(20)
        self.layout_trait.setVerticalSpacing(15)

        self.combo_etat = self._create_combo_optional('etats')
        self.combo_etat.currentTextChanged.connect(self.on_etat_changed)
        self.combo_etat.setMinimumWidth(220)
        self.layout_trait.addRow("État :", self.combo_etat)

        self.label_date_traitement = QLabel("📅 Date de traitement :")
        self.date_traitement = QDateEdit()
        self.date_traitement.setCalendarPopup(True)  # ← Active le calendrier
        self.date_traitement.setDisplayFormat("yyyy-MM-dd")  # Format d'affichage
        self.date_traitement.setDate(QDate.currentDate())  # Date du jour par défaut
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
        self.layout_trait.addRow(self.label_date_traitement, self.date_traitement)

        self.txt_solution = QTextEdit()
        self.txt_solution.setPlaceholderText("Solution commune (optionnel)")
        self.txt_solution.setMinimumHeight(100)
        self.txt_solution.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        self.layout_trait.addRow("Solution :", self.txt_solution)

        self.txt_commentaire = QTextEdit()
        self.txt_commentaire.setPlaceholderText("Commentaire commun (optionnel)")
        self.txt_commentaire.setMinimumHeight(85)
        self.txt_commentaire.setStyleSheet("background: white; border: 1px solid #ddd; padding: 8px;")
        self.layout_trait.addRow("Commentaire :", self.txt_commentaire)

        group_trait.setLayout(self.layout_trait)
        form_layout.addWidget(group_trait)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Appliquer les modifications")
        btn_save.setStyleSheet("background: #2F855A; color: white; font-weight: bold; padding: 10px 20px;")
        btn_save.clicked.connect(self.apply_changes)
        buttons_layout.addWidget(btn_save)

        main_layout.addLayout(buttons_layout)

        self.on_etat_changed()

    def on_etat_changed(self):
        """Affiche ou masque la date de traitement selon l'état"""
        etat_text = self.combo_etat.currentText()

        # Afficher uniquement pour "Traitée" ou "Fermée"
        if etat_text in ["Traitée", "Fermée"]:
            # Afficher la date actuelle
            self.label_date_traitement.setVisible(True)
            self.date_traitement.setVisible(True)
        else:
            # Masquer la date de traitement
            self.label_date_traitement.setVisible(False)
            self.date_traitement.setVisible(False)

    def _create_combo_optional(self, table_name):
        """Crée un combo avec option 'Ne pas modifier'"""
        combo = NoScrollComboBox()
        combo.addItem("Choisir une valeur…", None)
        valeurs = self.data_manager.get_liste_valeurs(table_name)
        for valeur in valeurs:
            id_val = self.data_manager.id_mapping[table_name].get(valeur)
            # ✅ FILTRER l'état "Archivé" pour les non-administrateurs
            if table_name == 'etats' and valeur == "Archivée":
                # Vérifier le rôle de l'utilisateur
                user_role = self.parent.user_info.get('role') if self.parent else None

                # N'ajouter "Archivé" que pour les Administrateurs
                if user_role == "Administrateur":
                    combo.addItem(valeur, id_val)
                # Sinon, on ne l'ajoute pas (skip)
            else:
                # Tous les autres états/valeurs sont ajoutés normalement
                combo.addItem(valeur, id_val)
        return combo

    def on_categorie_changed(self):
        """Mise à jour des sous-catégories"""
        self.combo_sous_categorie.clear()
        self.combo_sous_categorie.addItem("Choisir une valeur…", None)

        categorie_text = self.combo_categorie.currentText()
        if categorie_text and categorie_text != "Choisir une valeur…":
            if categorie_text in self.data_manager.sous_categories_by_categorie:
                sous_cats = self.data_manager.sous_categories_by_categorie[categorie_text]
                for libelle_sc in sous_cats:
                    id_sc = self.data_manager.sous_categories_ids_by_categorie.get(categorie_text, {}).get(libelle_sc)
                    self.combo_sous_categorie.addItem(libelle_sc, id_sc)

    @busy_cursor_no_args
    def apply_changes(self):
        """Applique les modifications à toutes les demandes EN UNE SEULE REQUÊTE"""
        data = {}

        # État
        if self.combo_etat.currentData():
            data['id_etat'] = self.combo_etat.currentData()

        # Canal
        if self.combo_canal.currentData():
            data['id_canal'] = self.combo_canal.currentData()

        # Domaine
        if self.combo_domaine.currentData():
            data['id_domaine'] = self.combo_domaine.currentData()

        # Responsable
        if self.combo_responsable.currentData():
            data['id_responsable'] = self.combo_responsable.currentData()

        # Catégorie
        if self.combo_categorie.currentData():
            data['id_categorie'] = self.combo_categorie.currentData()

        # Sous-catégorie
        if self.combo_sous_categorie.currentData():
            data['id_souscategorie'] = self.combo_sous_categorie.currentData()

        # Nature
        if self.combo_nature.currentData():
            data['id_nature'] = self.combo_nature.currentData()

        # Impact
        if self.combo_impact.currentData():
            data['id_impact'] = self.combo_impact.currentData()

        # Urgence
        if self.combo_urgence.currentData():
            data['id_urgence'] = self.combo_urgence.currentData()

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


        # Solution
        solution = self.txt_solution.toPlainText().strip()
        if solution:
            data['solution_suite_a_donner'] = solution

        # Commentaire
        commentaire = self.txt_commentaire.toPlainText().strip()
        if commentaire:
            data['commentaire'] = commentaire

        if not data:
            show_warning(
                self,
                "Aucune modification",
                "Veuillez sélectionner au moins un champ à modifier."
            )
            return

        # ✅ OPTIMISATION : Un seul UPDATE pour toutes les demandes
        succes, echec = self.data_manager.update_demandes_bulk(self.liste_ids, data)

        if echec == 0:
            show_info(
                self,
                "Succès",
                f"✅ {succes} demandes modifiées avec succès en une seule opération !"
            )
            self.accept()
        else:
            show_warning(
                self,
                "Modification partielle",
                f"✅ {succes} demandes OK\n❌ {echec} échecs"
            )
            self.accept()
