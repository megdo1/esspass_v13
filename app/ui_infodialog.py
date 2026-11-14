from PyQt5.QtGui import QPixmap, QPalette, QBrush
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QStyle
from PyQt5.QtCore import Qt, QPropertyAnimation
from app.version import APP_VERSION


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # fond
        """self.setAutoFillBackground(True)
        palette = self.palette()
        bg = QPixmap("ressources/img/es_fond_3.png")
        palette.setBrush(QPalette.Window, QBrush(bg))
        self.setPalette(palette)"""

        self.setWindowTitle("À propos")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedWidth(400)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)

        # Logo/icône système
        logo_layout = QHBoxLayout()
        logo_label = QLabel()
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        logo_label.setPixmap(icon.pixmap(80, 80))
        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_label)
        # animation
        logo_label.setGraphicsEffect(None)
        logo_label.setWindowOpacity(0)
        self.logo_anim = QPropertyAnimation(logo_label, b"windowOpacity")
        self.logo_anim.setDuration(1200)  # ms
        self.logo_anim.setStartValue(0)
        self.logo_anim.setEndValue(1)
        self.logo_anim.start()

        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # Nom + version
        name_label = QLabel("<b style='font-size:20pt;'>ES-PASS</b>")
        name_label.setAlignment(Qt.AlignCenter)
        version_label = QLabel(f"<span style='font-size:13pt; color: #64748B;'>Version {APP_VERSION}</span>")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addSpacing(5)
        layout.addWidget(name_label)
        layout.addWidget(version_label)

        # Optionnel : description rapide
        desc = QLabel("ES-PASS : application de suivi des demandes d’assistance PIGC et données OA/OTH<br><br>"
                      "© 2025 – SNCF Réseau.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addSpacing(10)
        layout.addWidget(desc)

        # Fermer
        ok_btn = QPushButton("Fermer")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("padding: 7px 24px; font-weight: bold;")
        layout.addSpacing(8)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)
        self.setLayout(layout)