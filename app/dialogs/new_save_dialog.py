import os
import json
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QComboBox, QDateEdit, QTextEdit, QFileDialog, QMessageBox, QFormLayout
from PyQt5.QtCore import Qt, QDate
import datetime


class DialogNouvelleSauvegarde(QDialog):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ES-PIGC : Nouvelle sauvegarde")
        self.resize(500, 300)

        form_layout = QFormLayout(self)
        form_layout.setVerticalSpacing(2)
        form_layout.setContentsMargins(6, 6, 6, 6)

        self.edit_nom = QLineEdit()
        self.edit_nom.setFixedHeight(22)
        form_layout.addRow(QLabel("Nom de la sauvegarde :"), self.edit_nom)

        self.edit_fichier = QLineEdit()
        self.edit_fichier.setReadOnly(True)
        self.edit_fichier.setFixedHeight(22)
        form_layout.addRow(QLabel("Fichier :"), self.edit_fichier)

        btn_select = QPushButton("Sélectionner le fichier")
        btn_select.setFixedHeight(22)
        btn_select.clicked.connect(self.choisir_fichier)
        form_layout.addRow(QLabel(""), btn_select)

        self.combo_categorie = QComboBox()
        self.combo_categorie.addItems(["Patrimoine", "Surveillance", "Maintenance", "Besoin", "Référentiel", "Autre"])
        self.combo_categorie.setFixedHeight(22)
        form_layout.addRow(QLabel("Catégorie :"), self.combo_categorie)

        self.date_valeur = QDateEdit(QDate.currentDate())
        self.date_valeur.setCalendarPopup(True)
        self.date_valeur.setDisplayFormat("dd/MM/yyyy")
        self.date_valeur.setFixedHeight(22)
        form_layout.addRow(QLabel("Date de valeur :"), self.date_valeur)

        label_comment = QLabel("Commentaire :")
        label_comment.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.edit_comment = QTextEdit()
        self.edit_comment.setFixedHeight(60)
        self.edit_comment.setMaximumHeight(60)
        self.edit_comment.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.edit_comment.setPlaceholderText("Saisissez un commentaire sur la sauvegarde")
        form_layout.addRow(label_comment, self.edit_comment)

        self.btn_save = QPushButton("Enregistrer la sauvegarde")
        self.btn_save.setFixedHeight(24)
        self.btn_save.clicked.connect(self.enregistrer)
        form_layout.addRow(QLabel(""), self.btn_save)

        # Uniformisation QLineEdit

        height = 32
        font = self.edit_nom.font()
        font.setPointSize(11)

        for champ in [self.edit_nom, self.edit_fichier]:
            champ.setFixedHeight(height)
            champ.setFont(font)
            champ.setStyleSheet("""
                        QLineEdit {
                            border: 1px solid #aaa;
                            border-radius: 6px;
                            padding: 4px 12px 4px 8px;
                            font-size: 13px;
                            background: white;
                        }
                        QLineEdit:focus {
                            border: 1.5px solid #1F4E9C;
                        }
                    """)

        # Uniformisation QComboBox
        self.combo_categorie.setFixedHeight(height)
        self.combo_categorie.setFont(font)
        self.combo_categorie.setStyleSheet("""
                    QComboBox {
                        border: 1px solid #aaa;
                        border-radius: 6px;
                        padding: 4px 12px 4px 8px;
                        font-size: 13px;
                        background: white;
                    }
                    QComboBox:focus {
                        border: 1.5px solid #1F4E9C;
                    }
                """)

        # Uniformisation QDateEdit
        self.date_valeur.setFixedHeight(height)
        self.date_valeur.setFont(font)
        self.date_valeur.setStyleSheet("""
                    QDateEdit {
                        border: 1px solid #aaa;
                        border-radius: 6px;
                        padding: 4px 12px 4px 8px;
                        font-size: 13px;
                        background: white;
                    }
                    QDateEdit:focus {
                        border: 1.5px solid #1F4E9C;
                    }
                """)

        # Uniformisation QTextEdit (commentaire)
        self.edit_comment.setFont(font)
        self.edit_comment.setStyleSheet("""
                    QTextEdit {
                        border: 1px solid #aaa;
                        border-radius: 6px;
                        font-size: 13px;
                        background: white;
                        padding: 4px 8px;
                    }
                    QTextEdit:focus {
                        border: 1.5px solid #1F4E9C;
                    }
                """)

        # Uniformisation boutons
        for btn in [self.btn_save, btn_select]:
            btn.setFixedHeight(height)
            btn.setFont(font)
            btn.setStyleSheet("""
                        QPushButton {
                            border: 1px solid #1F4E9C;
                            border-radius: 6px;
                            background: #F8FAFC;
                            font-size: 13px;
                            padding: 4px 18px;
                        }
                        QPushButton:focus {
                            border: 2px solid #1F4E9C;
                        }
                    """)

        self.setLayout(form_layout)

    def choisir_fichier(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier sauvegarde", "", "Excel Files (*.xlsx *.xls);;All Files (*)")
        if file_path:
            self.edit_fichier.setText(file_path)
            self.file_path = file_path

    def enregistrer(self):
        nom = self.edit_nom.text().strip()
        cat = self.combo_categorie.currentText()
        date_valeur = self.date_valeur.date().toString("dd/MM/yyyy")
        commentaire = self.edit_comment.toPlainText().strip()
        fichier = self.file_path
        effectue_le = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if not nom or not fichier:
            QMessageBox.warning(self, "Champ manquant", "Veuillez saisir un nom et sélectionner un fichier.")
            return

        # Créer le dossier sauvegardes si nécessaire
        dir_saves = os.path.join(os.getcwd(), "sauvegardes")
        os.makedirs(dir_saves, exist_ok=True)
        nom_fichier_base = os.path.basename(fichier)
        file_dest = os.path.join(dir_saves, f"{nom}_{nom_fichier_base}")
        try:
            import shutil
            shutil.copy(fichier, file_dest)
        except Exception as e:
            QMessageBox.critical(self, "Erreur copie", f"Erreur lors de la copie du fichier : {e}")
            return

        # Sauvegarder les métadonnées
        metadata_path = os.path.join(dir_saves, "metadata.json")
        metadata = []
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                try:
                    metadata = json.load(f)
                except Exception:
                    metadata = []

        record = {
            "nom_sauvegarde": nom,
            "fichier": file_dest,
            "nom_fichier": nom_fichier_base,
            "effectue_le": effectue_le,
            "categorie": cat,
            "date_valeur": date_valeur,
            "commentaire": commentaire,
        }
        metadata.append(record)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        QMessageBox.information(self, "Succès", "Sauvegarde enregistrée !")
        self.accept()  # Ferme la fenêtre

