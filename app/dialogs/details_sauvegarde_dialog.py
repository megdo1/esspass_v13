from PyQt5.QtWidgets import QLabel, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt


class DetailsSauvegardeDialog(QDialog):
    def __init__(self, md, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ES-PIGC : Détails de la sauvegarde")
        self.setWindowModality(Qt.NonModal)  # Fenêtre non bloquante
        self.resize(500, 220)
        layout = QVBoxLayout(self)
        txt = (
            f"<b>Nom :</b> {md['nom_sauvegarde']}<br>"
            f"<b>Effectuée le :</b> {md['effectue_le']}<br>"
            f"<b>Fichier :</b> {md['nom_fichier']}<br>"
            f"<b>Catégorie :</b> {md['categorie']}<br>"
            f"<b>Date de valeur :</b> {md['date_valeur']}<br>"
            f"<b>Commentaire :</b> {md['commentaire']}"
        )
        lbl = QLabel(txt)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)
        # Optionnel : bouton fermer
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton("Fermer")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

