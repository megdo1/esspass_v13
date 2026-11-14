"""Barre latérale, menus de navigation et zones d'affichage (zones 1, 2 et 3)."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem, QStackedLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt


class NavigationMixin:
    """Barre latérale, menus de navigation et zones d'affichage (zones 1, 2 et 3)."""

    def toggle_sidebar(self):
        """Masque ou affiche le menu latéral"""
        if self.zone1.isVisible():
            # Masquer le menu
            self.zone1.hide()

            # ✅ Créer et afficher le bouton flottant
            if not hasattr(self, 'floating_btn'):
                self.floating_btn = QPushButton("☰", self.centralWidget())
                self.floating_btn.setObjectName("FloatingToggleBtn")
                self.floating_btn.setFixedSize(30, 30)
                self.floating_btn.setToolTip("Afficher le menu")
                self.floating_btn.clicked.connect(self.toggle_sidebar)
                self.floating_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1F4E9C;
                        color: white;
                        border: none;
                        border-radius: 25px;
                        font-size: 18px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #1A4286;
                    }
                    QPushButton:pressed {
                        background-color: #0F2A52;
                    }
                """)

            self.floating_btn.move(10, 10)
            self.floating_btn.show()
            self.floating_btn.raise_()

        else:
            # Afficher le menu
            self.zone1.show()

            # ✅ Masquer le bouton flottant
            if hasattr(self, 'floating_btn'):
                self.floating_btn.hide()

    def create_zone1_drilldown(self):
        frame = QFrame()
        frame.setFixedWidth(250)

        self.zone1_stack = QStackedLayout()

        # Container principal avec layout vertical
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(12, 18, 12, 18)

        # Commencer par afficher le niveau racine
        self.build_nav_level(self.menu_structure)

        top_layout.addLayout(self.zone1_stack)

        # ✅ NOUVEAU : Boutons en bas (Masquer et Fermer côte à côte)
        bottom_buttons_layout = QHBoxLayout()

        # Bouton Masquer
        btn_hide = QPushButton("Masquer")
        btn_hide.setObjectName("NavHideBtn")
        btn_hide.setToolTip("Masquer le menu latéral")
        btn_hide.clicked.connect(self.toggle_sidebar)

        # Bouton Fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("NavCloseBtn")
        close_btn.clicked.connect(self.close)

        bottom_buttons_layout.addWidget(btn_hide)
        bottom_buttons_layout.addWidget(close_btn)

        top_layout.addSpacing(5)
        top_layout.addLayout(bottom_buttons_layout)

        frame.setLayout(top_layout)

        return frame

    def build_nav_level(self, structure, breadcrumbs=None):
        if breadcrumbs is None:
            breadcrumbs = []
        widget = QWidget()
        vbox = QVBoxLayout()
        # Affiche bouton retour s'il y a une profondeur
        if len(breadcrumbs) > 0:
            back_btn = QPushButton("← Retour")
            back_btn.setObjectName("DrillBackBtn")
            def go_back():
                self.zone1_stack.setCurrentIndex(self.zone1_stack.currentIndex() - 1)
                # Optionnel : supprime le niveau pour libérer mémoire
            back_btn.clicked.connect(go_back)
            vbox.addWidget(back_btn)
        for title, subs in structure.items():
            btn = QPushButton(title)
            btn.setObjectName("DrillMenuBtn")
            btn.setMinimumHeight(38)
            
            # AJOUT : Désactiver les boutons ES-IND, ES-TDB et ES-RAP
            if title in ["ES-IND", "ES-TDB", "ES-RAP"]:
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #94A3B8;
                        border: none;
                    }
                """)
                
            vbox.addWidget(btn)
            # Si sous-menu est une list/dict non vide, drilldown sur clic :
            if isinstance(subs, dict) and subs:
                btn.clicked.connect(lambda checked, s=subs, bc=breadcrumbs + [title]: self.open_nav_level(s, bc))
            elif isinstance(subs, list) and subs:
                # Feuille : afficher la liste comme nouveaux boutons
                btn.clicked.connect(lambda checked, sublist=subs, main=title: self.show_leaf_level(main, sublist, breadcrumbs))
            else:
                btn.clicked.connect(lambda checked, main=title, crumbs=breadcrumbs: self.menu_drill_selected(crumbs, main))
        vbox.addStretch()
        widget.setLayout(vbox)
        self.zone1_stack.addWidget(widget)
        self.zone1_stack.setCurrentWidget(widget)

    def open_nav_level(self, subs, breadcrumbs):
        self.build_nav_level(subs, breadcrumbs)
        self.zone1_stack.setCurrentIndex(self.zone1_stack.count() - 1)

    def show_leaf_level(self, main, sublist, breadcrumbs):
        widget = QWidget()
        vbox = QVBoxLayout()
        if breadcrumbs:
            back_btn = QPushButton("← Retour")
            back_btn.setObjectName("DrillBackBtn")
            back_btn.clicked.connect(lambda: self.zone1_stack.setCurrentIndex(self.zone1_stack.currentIndex()-1))
            vbox.addWidget(back_btn)
        for sub in sublist:
            if sub == "👥 Utilisateurs" and main == "LD Assistance PIGC":
                if self.is_admin is None:
                    self.is_admin = self.dm.is_current_user_admin()
                if not self.is_admin:
                    continue  # Skip le bouton Utilisateurs
            btn = QPushButton(sub)
            btn.setObjectName("DrillMenuBtn")
            btn.setMinimumHeight(35)
            btn.clicked.connect(lambda checked, main=main, sub=sub, crumbs=breadcrumbs: self.menu_drill_selected(crumbs + [main], sub))
            vbox.addWidget(btn)
        vbox.addStretch()
        widget.setLayout(vbox)
        self.zone1_stack.addWidget(widget)
        self.zone1_stack.setCurrentWidget(widget)

    def menu_drill_selected(self, breadcrumbs, selection):
        key = tuple(breadcrumbs) + (selection,)
        self.current_key = key
        # Cas particulier : Configuration doit être recréé à chaque fois
        if key in [("PASS", "LD Assistance PIGC", "⚙️ Configuration"),('PASS', 'LD Assistance PIGC', '👥 Utilisateurs'),
                   ('PASS', 'LD Assistance PIGC', '📋 Demandes')]:
            # Ne pas stocker dans self.zone3_widgets, créer une nouvelle instance à chaque fois
            widget = self.build_zone3_widget_for_view(key)

            # Supprimer l'ancien widget de Configuration s'il existe
            if key in self.zone3_widgets:
                old_widget = self.zone3_widgets[key]
                self.zone3_layout.removeWidget(old_widget)
                old_widget.deleteLater()
                del self.zone3_widgets[key]

            # Ajouter le nouveau widget
            self.zone3_widgets[key] = widget
            self.zone3_layout.addWidget(widget)
            self.zone3_layout.setCurrentWidget(self.zone3_widgets[key])

        else:
            if key not in self.zone3_widgets:
                widget = self.build_zone3_widget_for_view(key)
                self.zone3_widgets[key] = widget
                self.zone3_layout.addWidget(widget)

            self.zone3_layout.setCurrentWidget(self.zone3_widgets[key])

    def update_zone3_style(self):
        if self.current_M1_sub == "OA":
            color = "#EEF0FD"
        elif self.current_M1_sub == "OT":
            color = "#E9F6EF"
        else:
            color = "#F4F6FA"
        self.zone3_frame.setStyleSheet(f"background: {color}; border-radius: 12px;")

    def create_zone1(self):
        frame = QFrame()
        frame.setFixedWidth(250)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)
        
        self.zone1_lists = {}
        # Utilisation de sections rétractables mais style très doux
        for title, subs in self.menu_structure.items():
            # Titre clickable, professionel et sobre
            title_label = QLabel(title)
            title_label.setObjectName("NavSectionTitle")
            title_label.setCursor(Qt.PointingHandCursor)
            layout.addWidget(title_label)
            
            if subs:
                list_widget = QListWidget()
                list_widget.setObjectName("NavSubList")
                list_widget.setVisible(False)
                for sub in subs:
                    item = QListWidgetItem(sub)
                    list_widget.addItem(item)
                list_widget.itemClicked.connect(lambda item, t=title: self.menu1_selected(t, item.text()))
                layout.addWidget(list_widget)
                self.zone1_lists[title] = list_widget
                
                # Toggle d'ouverture/fermeture
                def make_toggle(lw):
                    return lambda e: lw.setVisible(not lw.isVisible())
                title_label.mousePressEvent = make_toggle(list_widget)
            else:
                def make_select_callback(t):
                    return lambda e: self.menu1_selected(t, None)
                title_label.mousePressEvent = make_select_callback(title)
        layout.addStretch()

        # Bouton fermer sobre
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("NavCloseBtn")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        frame.setLayout(layout)
        return frame

    def create_zone2(self):
        frame = QFrame()
        frame.setFixedWidth(250)
        layout = QVBoxLayout()
        self.menu2_list = QListWidget()
        self.menu2_list.itemClicked.connect(self.menu2_selected)
        #layout.addWidget(QLabel("")) # Menu Secondaire
        layout.addWidget(self.menu2_list)
        frame.setLayout(layout)
        return frame

    def create_zone3(self):
        self.zone3_frame = QFrame()
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.gray)
        self.zone3_frame.setGraphicsEffect(shadow)
        self.zone3_layout = QStackedLayout()
        self.zone3_frame.setLayout(self.zone3_layout)
        self.zone3_empty = QWidget()
        self.zone3_layout.addWidget(self.zone3_empty)
        return self.zone3_frame

    def menu1_selected(self, title, sub):
        self.current_M1_title = title
        self.current_M1_sub = sub
        self.menu2_list.clear()
        for option in self.menu2_options.get((title, sub), []):
            self.menu2_list.addItem(option)
        self.zone3_layout.setCurrentWidget(self.zone3_empty)
        self.update_zone3_style()

    def menu2_selected(self, item):
        self.current_key = (self.current_M1_title, self.current_M1_sub, item.text())
        self.show_zone3_for_current_view()
        self.restore_state()
        self.update_zone3_style()

    def show_zone3_for_current_view(self):
        key = self.current_key
        if key not in self.zone3_widgets:
            widget = self.build_zone3_widget_for_view(key)
            self.zone3_widgets[key] = widget
            self.zone3_layout.addWidget(widget)
        self.zone3_layout.setCurrentWidget(self.zone3_widgets[key])
