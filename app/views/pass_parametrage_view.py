from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView
)
from PyQt5.QtCore import Qt
import json
import os
from app.data.data_manager import DataManager
from app.data.data_config import loadConfig

from app.data.data_config import CONFIG_FILE
from app.utils.auth import has_permission
from app.views.referentiels_tab import ReferentielsTab

class ParametrageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Tentative d'initialisation du DataManager
        try:
            self.data_manager = DataManager()  # Lèvera une exception si DB inaccessible
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur d'accès à la base de données",
                str(e)  # Le message est déjà explicite depuis DataManager
            )
            self.reject()
            return

        # Vérification des droits admin
        if self.data_manager and not self.data_manager.is_current_user_actif():
            QMessageBox.warning(
                self,
                "Accès refusé",
                "Vous compte n'existe pas ou son statut est inactif.\n\n"
                "Contactez votre administrateur système."
            )
            self.reject()
            return
        self.setWindowTitle("Paramétrage application")
        self.setMinimumSize(700, 500)
        self.changes_made = False
        self.init_ui()
        self.load_config()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Créer le système d'onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #F4F6FA;
                border: 1px solid #CBD5E1;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: #E2E8F0;
            }
        """)
        
        # Onglet 1 : Paramètres généraux
        tab_general = self.create_general_tab()
        self.tabs.addTab(tab_general, "⚙️ Général")
        
        # Onglet 2 : Colonnes du tableau
        if self.data_manager:
            tab_colonnes = self.create_colonnes_tab()
            self.tabs.addTab(tab_colonnes, "📊 Colonnes")

        # Onglet 3 : Référentiels (listes de valeurs) - réservé au droit "Gérer les listes de valeurs"
        self.tab_referentiels = None
        if self.data_manager:
            role = (self.data_manager.get_current_user() or {}).get('role')
            if has_permission(role, 'gerer_listes'):
                self.tab_referentiels = ReferentielsTab(self.data_manager)
                self.tabs.addTab(self.tab_referentiels, "🗂️ Référentiels")
                self.tabs.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.tabs)
        
        # Boutons en bas
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("💾 Enregistrer")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("padding: 8px 20px; border-radius: 8px;")
        self.btn_save.clicked.connect(self.save_all_config)
        btn_layout.addWidget(self.btn_save)
        
        btn_cancel = QPushButton("Annuler")
        self.btn_cancel = btn_cancel
        btn_cancel.setStyleSheet("padding: 8px 20px; border-radius: 8px;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        main_layout.addLayout(btn_layout)

    def on_tab_changed(self, index):
        """L'onglet Référentiels enregistre immédiatement : on masque Enregistrer/Annuler pendant son affichage."""
        visible = self.tabs.widget(index) is not self.tab_referentiels
        self.btn_save.setVisible(visible)
        self.btn_cancel.setVisible(visible)

    def create_general_tab(self):
        """Crée l'onglet des paramètres généraux"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(18)

        # SQLite path
        row_sqlite = QHBoxLayout()
        label_sqlite = QLabel("Emplacement stockage de la base :")
        label_sqlite.setMinimumWidth(220)
        row_sqlite.addWidget(label_sqlite)
        self.txt_sqlite = QLineEdit()
        self.txt_sqlite.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.txt_sqlite.textChanged.connect(self.on_change)
        row_sqlite.addWidget(self.txt_sqlite)
        btn_sqlite = QPushButton("Parcourir…")
        btn_sqlite.setFixedHeight(32)
        btn_sqlite.clicked.connect(self.browse_sqlite)
        row_sqlite.addWidget(btn_sqlite)
        layout.addLayout(row_sqlite)

        # PJ path
        row_pj = QHBoxLayout()
        label_pj = QLabel("Dossier des pièces jointes :")
        label_pj.setMinimumWidth(220)
        row_pj.addWidget(label_pj)
        self.txt_pj = QLineEdit()
        self.txt_pj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.txt_pj.textChanged.connect(self.on_change)
        row_pj.addWidget(self.txt_pj)
        btn_pj = QPushButton("Parcourir…")
        btn_pj.setFixedHeight(32)
        btn_pj.clicked.connect(self.browse_pj)
        row_pj.addWidget(btn_pj)
        layout.addLayout(row_pj)

        # Outlook folder
        row_outlook = QHBoxLayout()
        label_outlook = QLabel("Nom du dossier Outlook :")
        label_outlook.setMinimumWidth(220)
        row_outlook.addWidget(label_outlook)
        self.txt_outlook_folder = QLineEdit()
        self.txt_outlook_folder.setPlaceholderText("Ex: PIGC")
        self.txt_outlook_folder.textChanged.connect(self.on_change)
        row_outlook.addWidget(self.txt_outlook_folder)
        layout.addLayout(row_outlook)

        # Profondeur mails
        collect_layout = QHBoxLayout()
        label_collect = QLabel("Profondeur collecte mails (en jours) :")
        label_collect.setMinimumWidth(220)
        collect_layout.addWidget(label_collect)
        self.spin_profondeur = QSpinBox()
        self.spin_profondeur.setRange(1, 365)
        self.spin_profondeur.setSuffix(" jours")
        self.spin_profondeur.setValue(30)
        self.spin_profondeur.setFixedWidth(120)
        self.spin_profondeur.valueChanged.connect(self.on_change)
        collect_layout.addWidget(self.spin_profondeur)
        collect_layout.addStretch()
        layout.addLayout(collect_layout)

        # Limite demandes
        limite_layout = QHBoxLayout()
        label_limite = QLabel("Limite récupération demandes (0 = illimité) :")
        label_limite.setMinimumWidth(220)
        limite_layout.addWidget(label_limite)
        self.spin_limite = QSpinBox()
        self.spin_limite.setRange(0, 100000)
        self.spin_limite.setSuffix(" demandes")
        self.spin_limite.setValue(0)
        self.spin_limite.setFixedWidth(120)
        self.spin_limite.valueChanged.connect(self.on_change)
        limite_layout.addWidget(self.spin_limite)
        limite_layout.addStretch()
        layout.addLayout(limite_layout)

        layout.addStretch()
        return tab

    def create_colonnes_tab(self):
        """Crée l'onglet de gestion des colonnes"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Titre et instructions
        title = QLabel("Gestion de la visibilité des colonnes")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1F4E9C;")
        layout.addWidget(title)

        info = QLabel("Cochez/décochez les colonnes à afficher dans le tableau des demandes.")
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        # Table des colonnes
        self.table_colonnes = QTableWidget()
        self.table_colonnes.setColumnCount(4)
        self.table_colonnes.setHorizontalHeaderLabels(['Visible', 'Colonne', 'Largeur', 'Ordre'])
        self.table_colonnes.horizontalHeader().setStretchLastSection(False)
        self.table_colonnes.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_colonnes.setColumnWidth(0, 80)
        self.table_colonnes.setColumnWidth(2, 100)
        self.table_colonnes.setColumnWidth(3, 80)
        self.table_colonnes.verticalHeader().setVisible(False)
        self.table_colonnes.setAlternatingRowColors(True)
        self.table_colonnes.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)

        # ✅ AJOUT : Détecter les modifications dans les cellules
        self.table_colonnes.itemChanged.connect(self.on_table_item_changed)

        # Charger les colonnes depuis la BD
        self.load_colonnes_config()

        layout.addWidget(self.table_colonnes)

        # Boutons d'action rapide
        btn_layout = QHBoxLayout()

        btn_all = QPushButton("✓ Tout sélectionner")
        btn_all.clicked.connect(self.select_all_colonnes)
        btn_layout.addWidget(btn_all)

        btn_none = QPushButton("✗ Tout désélectionner")
        btn_none.clicked.connect(self.deselect_all_colonnes)
        btn_layout.addWidget(btn_none)

        btn_reset = QPushButton("🔄 Réinitialiser")
        btn_reset.clicked.connect(self.reset_colonnes)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return tab

    def load_colonnes_config(self):
        """Charge les colonnes depuis la BD et remplit le tableau"""
        if not self.data_manager:
            QMessageBox.warning(
                self,
                "Base de données inaccessible",
                "Impossible de charger la configuration des colonnes.\n"
                "Veuillez vérifier l'accès à la base de données."
            )
            return

        colonnes = self.data_manager.get_colonnes_config(visible_only=False)
        self.table_colonnes.setRowCount(len(colonnes))

        # ✅ Bloquer temporairement les signaux pour éviter de déclencher on_change pendant le chargement
        self.table_colonnes.blockSignals(True)

        for row_idx, col in enumerate(colonnes):
            # Checkbox visible
            checkbox = QCheckBox()
            checkbox.setChecked(col['visible'] == 1)
            checkbox.stateChanged.connect(self.on_change)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table_colonnes.setCellWidget(row_idx, 0, checkbox_widget)

            # Nom colonne
            item_nom = QTableWidgetItem(col['libelle'])
            item_nom.setFlags(item_nom.flags() & ~Qt.ItemIsEditable)
            item_nom.setData(Qt.UserRole, col['nom'])  # Stocker le nom technique
            self.table_colonnes.setItem(row_idx, 1, item_nom)

            # Largeur
            item_largeur = QTableWidgetItem(str(col['largeur']))
            item_largeur.setTextAlignment(Qt.AlignCenter)
            self.table_colonnes.setItem(row_idx, 2, item_largeur)

            # Ordre
            item_ordre = QTableWidgetItem(str(col['ordre']))
            item_ordre.setTextAlignment(Qt.AlignCenter)
            self.table_colonnes.setItem(row_idx, 3, item_ordre)

        # ✅ Réactiver les signaux après le chargement
        self.table_colonnes.blockSignals(False)

    def on_table_item_changed(self, item):
        """✅ NOUVELLE MÉTHODE : Détecte les modifications dans les cellules du tableau"""
        # Ne pas déclencher pendant le chargement initial
        if self.table_colonnes.signalsBlocked():
            return

        # Marquer comme modifié
        self.on_change()

    def on_change(self):
        """Active le bouton Enregistrer quand des modifications sont détectées"""
        if not self.changes_made:
            self.changes_made = True
            self.btn_save.setEnabled(True)
            self.btn_save.setStyleSheet("""
                background: #2F855A;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 8px;
            """)

    def save_all_config(self):
        """Sauvegarde toute la configuration (général + colonnes)"""
        # 1. Sauvegarder UNIQUEMENT le chemin BD dans config.json
        db_path = self.txt_sqlite.text().strip().replace('\\', '/')
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'sqlite_path': db_path}, f, indent=2)
        print(f"Chemin BD sauvegardé : {db_path}")

        # 2. Sauvegarder les autres paramètres dans la BD
        if self.data_manager:
            parametres = {
                'pj_path': self.txt_pj.text().strip(),
                'outlook_folder': self.txt_outlook_folder.text().strip() or 'PIGC',
                'outlook_folder': self.txt_outlook_folder.text().strip() or 'PIGC',
                'mail_days': str(self.spin_profondeur.value()),
                'demande_limit': str(self.spin_limite.value()),
            }
            success = self.data_manager.update_parametres_bulk(parametres)
            if not success:
                QMessageBox.warning(self, "Erreur", "Erreur lors de la sauvegarde des paramètres.")
                return

        # 3. Sauvegarder config colonnes
        colonnes_saved = True
        if self.data_manager:
            colonnes_saved = self.save_colonnes_config()

        if colonnes_saved:
            # ✅ Réinitialiser l'état après sauvegarde
            self.changes_made = False
            self.btn_save.setEnabled(False)
            self.btn_save.setStyleSheet("padding: 8px 20px; border-radius: 8px;")

            QMessageBox.information(
                self,
                "Paramètres enregistrés",
                "Les paramètres ont bien été enregistrés !"
            )

    def select_all_colonnes(self):
        """Sélectionne toutes les colonnes"""
        for row in range(self.table_colonnes.rowCount()):
            checkbox_widget = self.table_colonnes.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)

    def deselect_all_colonnes(self):
        """Désélectionne toutes les colonnes"""
        for row in range(self.table_colonnes.rowCount()):
            checkbox_widget = self.table_colonnes.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

    def reset_colonnes(self):
        """Réinitialise les colonnes aux valeurs par défaut"""
        reply = QMessageBox.question(
            self,
            "Réinitialiser",
            "Voulez-vous vraiment réinitialiser toutes les colonnes aux valeurs par défaut ?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes and self.data_manager:
            success = self.data_manager.reset_colonnes_default()
            if success:
                self.load_colonnes_config()
                self.on_change()
                QMessageBox.information(self, "Réinitialisation", "Les colonnes ont été réinitialisées.")

    def save_colonnes_config(self):
        """Sauvegarde la configuration des colonnes via le data_manager"""
        if not self.data_manager:
            print("⚠️ Data manager non disponible")
            return False
        
        # Préparer les données pour l'update en bulk
        colonnes_data = []
        
        for row in range(self.table_colonnes.rowCount()):
            # Récupérer le checkbox de visibilité
            checkbox_widget = self.table_colonnes.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            visible = 1 if checkbox.isChecked() else 0
            
            # Récupérer les autres données
            nom_colonne = self.table_colonnes.item(row, 1).data(Qt.UserRole)
            largeur = int(self.table_colonnes.item(row, 2).text())
            ordre = int(self.table_colonnes.item(row, 3).text())
            
            colonnes_data.append({
                'nom': nom_colonne,
                'visible': visible,
                'largeur': largeur,
                'ordre': ordre
            })
        
        # Appeler la fonction centralisée du data_manager
        success = self.data_manager.update_colonnes_bulk(colonnes_data)
        
        if not success:
            QMessageBox.warning(
                self,
                "Erreur",
                "Une erreur est survenue lors de la sauvegarde des colonnes."
            )
        
        return success



    def browse_sqlite(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir base SQLite", "",
            "Fichiers SQLite (*.db *.sqlite);;Tous les fichiers (*)"
        )
        if path:
            self.txt_sqlite.setText(path)

    def browse_pj(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir dossier PJ")
        if path:
            self.txt_pj.setText(path)

    def load_config(self):
        """Charge la configuration depuis la BD et config.json"""
        # 1. Charger le chemin BD depuis config.json
        conf = loadConfig()
        self.txt_sqlite.setText(conf.get("sqlite_path", "./app/data/demandes.db"))

        
        # 2. Charger les autres paramètres depuis la BD
        if self.data_manager:
            params = self.data_manager.get_all_parametres()
            self.txt_pj.setText(params.get("pj_path", "./pieces_jointes"))
            self.txt_outlook_folder.setText(params.get("outlook_folder", "PIGC"))
            self.spin_profondeur.setValue(params.get("mail_days", 30))
            self.spin_limite.setValue(params.get("demande_limit", 1000))




    
    