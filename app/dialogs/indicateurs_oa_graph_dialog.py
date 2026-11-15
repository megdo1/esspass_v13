from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTabWidget, QWidget, QStyle,
    QHBoxLayout, QComboBox, QFileDialog, QGridLayout, QToolButton, QShortcut
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import re
from collections import defaultdict
from app.dialogs.analyse_surveillance.charts_mixin import ChartsMixin
import logging

logger = logging.getLogger(__name__)


class IndicateursOAGraphDialog(QDialog):
    def __init__(self, df, programme=None, parent=None):
        super().__init__(parent)
        self.df = df
        self.programme = programme
        self.setWindowTitle("ES - Visualisation des indicateurs OA")
        self.resize(1100, 750)

        self.layout = QVBoxLayout(self)

        self.control_layout = QHBoxLayout()
        self.combo_trimestre = QComboBox()
        self.combo_trimestre.addItem("Tous")
        # self.trimestres = list(self.df.columns[1:])
        from datetime import datetime
        self.trimestres = [datetime.now().strftime("%d/%m/%Y") if t == "Aujourd'hui" else t for t in
                           self.df.columns[1:]]

        for t in self.trimestres:
            self.combo_trimestre.addItem(t)
        self.combo_trimestre.setCurrentText(self.trimestres[-1])

        RACINES_VALIDES = ["IDR", "IDTU", "IDE", "VD", "VI", "SR", "U0s", "ESR"]
        self.combo_racine = QComboBox()
        self.racines_solides = []
        for ind in self.df["Indicateur"]:
            if not isinstance(ind, str):
                continue
            # match = re.match(r"^(\d{4})_([A-Z0-9]+)", ind)
            match = re.match(r"^(\d{4})_([A-Za-z0-9]+)", ind)
            if match:
                annee, code = match.groups()
                if code in RACINES_VALIDES:
                    racine = f"{annee}_{code}"
                    if racine not in self.racines_solides:
                        self.racines_solides.append(racine)

        self.combo_racine.addItem("Tous")
        for r in sorted(self.racines_solides):
            self.combo_racine.addItem(r)

        # Ajoute dynamiquement les racines absolues présentes dans le df
        for ind in self.df["Indicateur"]:
            if isinstance(ind, str) and (re.match(r"^\d{4}_U0s$", ind) or re.match(r"^\d{4}_ESR$", ind)):
                if ind not in self.racines_solides:
                    self.racines_solides.append(ind)
                    logger.debug("racines_solides : %s", self.racines_solides)

        self.btn_export = QPushButton("Exporter l'image")
        self.btn_export.clicked.connect(self.export_image)

        self.control_layout.addWidget(QLabel("Trimestre :"))
        self.control_layout.addWidget(self.combo_trimestre)
        self.control_layout.addWidget(QLabel("Indicateur :"))
        self.control_layout.addWidget(self.combo_racine)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.btn_export)
        self.layout.addLayout(self.control_layout)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self._connected = True
        self.combo_trimestre.currentTextChanged.connect(self.refresh)
        self.combo_racine.currentTextChanged.connect(self.refresh)

        # à supprimer self.current_fig = None

        self.close_btn = QPushButton("Fermer")
        self.close_btn.clicked.connect(self.close)
        self.layout.addWidget(self.close_btn)

        self.combo_trimestre.setCurrentIndex(self.combo_trimestre.count() - 1)
        self.combo_racine.setCurrentIndex(0)

        # self.refresh()
        # QTimer.singleShot(0, self.refresh)
        self.plot_all_indicateurs()

    def refresh(self):
        if not self.isVisible():
            return
        # Sauvegarde l'onglet courant (par défaut 0 si aucun)
        current_index = self.tabs.currentIndex()
        self.tabs.clear()
        self.plot_all_indicateurs()
        # Restaure l'onglet courant (sauf si le nombre d'onglets a changé)
        if self.tabs.count() > current_index and current_index >= 0:
            self.tabs.setCurrentIndex(current_index)

    def plot_all_indicateurs(self):
        df = self.df.copy()
        if "Indicateur" not in df.columns:
            self.tabs.addTab(QLabel("Aucune colonne 'Indicateur' trouvée."), "Erreur")
            return

        trimestre_choisi = self.combo_trimestre.currentText()
        racine_choisie = self.combo_racine.currentText()

        df_pct = df[df.apply(lambda row: any(isinstance(val, str) and "%" in val for val in row.values), axis=1)]
        df_abs = df[~df.index.isin(df_pct.index)]

        # --- Construction des groupes par racine solide ---
        groupes = defaultdict(list)
        racines_reellement_presentes = set()
        for _, row in df_pct.iterrows():
            cle = row["Indicateur"]
            # Racine solide : 2025_VI à partir de 2025_VI1, 2025_VI2, etc.
            match = re.match(r"^(\d{4}_[A-Z]+)", cle)
            if not match:
                continue
            racine = match.group(1)
            racines_reellement_presentes.add(racine)
            if racine_choisie != "Tous" and racine != racine_choisie:
                continue

            valeurs = []
            colonnes = []
            for col in self.trimestres:
                if trimestre_choisi != "Tous" and col != trimestre_choisi:
                    continue
                val = row[col]
                if isinstance(val, str) and "%" in val:
                    try:
                        valeurs.append(float(val.replace("%", "").replace(",", ".")))
                        colonnes.append(col)
                    except Exception:
                        logger.debug("Exception ignorée dans plot_all_indicateurs", exc_info=True)
            if valeurs:
                groupes[racine].append((cle, valeurs, colonnes))

        # --- Indicateurs absolus spéciaux ---
        groupes_abs = {}
        for _, row in df_abs.iterrows():
            cle = row["Indicateur"]
            if racine_choisie != "Tous" and racine_choisie != cle:
                continue
            if isinstance(cle, str) and (re.match(r"^\d{4}_U0s$", cle) or re.match(r"^\d{4}_ESR$", cle)):
                valeurs = []
                colonnes = []
                for col in self.trimestres:
                    if trimestre_choisi != "Tous" and col != trimestre_choisi:
                        continue
                    val = row[col]
                    try:
                        valeurs.append(float(str(val).replace(",", ".")))
                        colonnes.append(col)
                    except Exception:
                        logger.debug("Exception ignorée dans plot_all_indicateurs", exc_info=True)
                if valeurs:
                    groupes_abs[cle] = (valeurs, colonnes)

        # --- Affichage des onglets par racine solide ---
        for racine in sorted(groupes):
            self.create_group_tab(racine, {racine: groupes[racine]})

        # Toujours créer un onglet pour chaque indicateur absolu (U0s, ESR par année), peu importe le filtre
        # for racine, (valeurs, colonnes) in groupes_abs.items():
          #  if racine_choisie == "Tous" or racine_choisie == racine:
           #     self.create_abs_tab(racine, valeurs, colonnes)

        # --- Onglet "Tous" ---
        if racine_choisie == "Tous":
            if groupes:
                self.create_all_together_tab(groupes)
            if groupes_abs:
                for racine, (valeurs, colonnes) in groupes_abs.items():
                    self.create_abs_tab(racine, valeurs, colonnes)
        else:
            for racine, (valeurs, colonnes) in groupes_abs.items():
                if racine_choisie == racine:
                    self.create_abs_tab(racine, valeurs, colonnes)

    def create_group_tab(self, titre, groupes):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        all_labels = []
        noms_series = []
        for racine, lignes in groupes.items():
            for nom, valeurs, colonnes in lignes:
                if not all_labels:
                    all_labels = colonnes
                noms_series.append(nom)

        x = range(len(all_labels))
        width = 0.8 / len(noms_series) if noms_series else 0.4

        for i, (racine, lignes) in enumerate(groupes.items()):
            for j, (nom, valeurs, _) in enumerate(lignes):
                positions = [p + j * width for p in x]
                bar_container = ax.bar(positions, valeurs, width=width, label=nom)
                for rect in bar_container:
                    height = rect.get_height()
                    ax.text(rect.get_x() + rect.get_width()/2, height, f"{height:.1f}%", ha='center', va='bottom',
                            fontsize=8)

        ax.set_xticks([p + width * (len(noms_series) - 1) / 2 for p in x])
        ax.set_xticklabels(all_labels)
        ax.set_ylabel("% Atteint")
        ax.axhline(100, color='gray', linestyle='--')
        ax.legend()
        ax.set_title(f"Indicateurs - {titre}")
        fig.tight_layout()
        layout.addWidget(canvas)
        self.tabs.addTab(tab, titre)
        # à supprimer ? self.current_fig = fig

    def create_abs_tab(self, titre, valeurs, colonnes):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(8, 4))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        bar_container = ax.bar(range(len(valeurs)), valeurs, tick_label=colonnes, color='orange')
        for rect in bar_container:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2, height, f"{height:.0f}", ha='center', va='bottom', fontsize=9)

        ax.set_title(f"{titre} – Valeurs absolues")
        ax.set_ylabel("Nombre")
        ax.set_xlabel("Trimestre")
        fig.tight_layout()
        layout.addWidget(canvas)
        self.tabs.addTab(tab, titre)
        # à supprimer self.current_fig = fig

    def create_all_together_tab(self, groupes):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(12, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        all_racines = sorted(groupes.keys())
        sous_indics = []
        # Collecte TOUS les suffixes y compris l'absence de suffixe
        for racine in all_racines:
            for (cle, _, _) in groupes[racine]:
                suffixe = cle.replace(racine, "")
                if suffixe not in sous_indics:
                    sous_indics.append(suffixe)

        trimestres = self.trimestres
        trimestre_choisi = self.combo_trimestre.currentText()

        if trimestre_choisi == "Tous":
            # Affichage pour tous les trimestres
            n_trimestres = len(trimestres)
            n_racines = len(all_racines)
            n_sous = len(sous_indics)
            total_width = 0.8
            bar_width = total_width / (n_racines * n_sous)
            x = list(range(n_trimestres))
            colors = plt.cm.get_cmap("tab10")

            legende_labels = []
            for idx_r, racine in enumerate(all_racines):
                for idx_s, suffixe in enumerate(sous_indics):
                    label = f"{racine}{suffixe}".strip()
                    valeurs_barre = []
                    has_data = False
                    for t_idx, trimestre in enumerate(trimestres):
                        valeur = 0.0
                        for (cle, valeurs, colonnes) in groupes[racine]:
                            if cle == label:
                                if trimestre in colonnes:
                                    val_idx = colonnes.index(trimestre)
                                    valeur = valeurs[val_idx]
                                    has_data = has_data or valeur != 0
                                break
                        valeurs_barre.append(valeur)
                    # Ajoute la série SEULEMENT si elle a des données réelles
                    if has_data:
                        positions = [i + idx_r * n_sous * bar_width + idx_s * bar_width for i in x]
                        color = colors((idx_r * n_sous + idx_s) % 10)
                        bars = ax.bar(positions, valeurs_barre, width=bar_width,
                                      label=label, color=color)
                        # Etiquettes : nom de l’indicateur et valeur
                        for pos, val in zip(positions, valeurs_barre):
                            if val != 0:
                                code_court = label.split('_', 1)[-1]
                                ax.text(pos, val, f"{code_court}\n{val:.1f}%", ha='center', va='bottom', fontsize=8)
                                # ax.text(pos, val, f"{label}\n{val:.1f}%", ha='center', va='bottom', fontsize=8,
                                  #      rotation=0)
                        legende_labels.append(label)

            ax.set_xticks([i + total_width / 2 - bar_width / 2 for i in x])
            ax.set_xticklabels(trimestres)
            ax.set_ylabel("% Atteint")
            ax.axhline(100, color='gray', linestyle='--')
            ax.set_title(f"Comparatif – Tous les indicateurs - {self.programme}")
            ax.legend(fontsize=8)
        else:
            # Cas standard : on affiche un groupe par racine, une barre par suffixe (comme avant)
            n_racines = len(all_racines)
            n_sous = len(sous_indics)
            bar_width = 0.8 / (n_sous if n_sous else 1)
            x = list(range(n_racines))
            colors = plt.cm.get_cmap("tab10")
            for idx_s, suffixe in enumerate(sous_indics):
                valeurs_barre = []
                for racine in all_racines:
                    valeur = 0.0
                    for (cle, valeurs, colonnes) in groupes[racine]:
                        if cle == racine + suffixe:
                            valeur = valeurs[0] if valeurs else 0  # Un seul trimestre, on prend le 1er/unique
                            break
                    valeurs_barre.append(valeur)
                positions = [i + idx_s * bar_width for i in x]
                color = colors(idx_s % 10)
                ax.bar(positions, valeurs_barre, width=bar_width, label=f"Indicateur {suffixe}", color=color)
                for pos, val in zip(positions, valeurs_barre):
                    ax.text(pos, val, f"{val:.1f}%", ha='center', va='bottom', fontsize=8)

            ax.set_xticks([i + bar_width * (n_sous - 1) / 2 for i in x])
            ax.set_xticklabels(all_racines)
            ax.set_ylabel("% Atteint")
            ax.axhline(100, color='gray', linestyle='--')
            ax.set_title(f"Tous les indicateurs - {self.programme}")
            ax.legend(fontsize=8)

        fig.tight_layout()
        layout.addWidget(canvas)
        self.tabs.addTab(tab, "Tous")
        # à supprimer self.current_fig = fig


    def export_image(self):
        current_widget = self.tabs.currentWidget()
        if not current_widget:
            return

        # Cherche un canvas Matplotlib dans le widget courant
        canvas = current_widget.findChild(FigureCanvas)
        if not canvas:
            return

        fig = canvas.figure
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'image", "graphique.png",
            "Images (*.png *.jpg *.jpeg);;PDF (*.pdf)", options=options
        )
        if file_path:
            fig.savefig(file_path)

    def closeEvent(self, event):
        if self._connected:
            try:
                self.combo_trimestre.currentTextChanged.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                logger.debug("Exception ignorée dans closeEvent", exc_info=True)
            try:
                self.combo_racine.currentTextChanged.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                logger.debug("Exception ignorée dans closeEvent", exc_info=True)
            self._connected = False

        self.combo_trimestre = None
        self.combo_racine = None
        # à supprimer self.current_fig = None

        super().closeEvent(event)


class AnalyseSurveillanceDialog(ChartsMixin, QDialog):
    """
    Affiche 4 camemberts (2 x 2) pour les catégories VI, VD, IDE, IDR.
    Chaque secteur = un 'Statut' avec étiquette 'nombre (xx%)' et une légende à droite.
    """
    def __init__(self, data_dict, programme=None, parent=None,
                 u0_utm_df=None, u1_utm_df=None, cat_urg_df=None):
        super().__init__(parent)
        logger.debug("DEBUG: - AnalyseSurveillanceDialog - 1")
        self.data = data_dict          # dict: {cat: DataFrame[Statut, Nombre, Pourcentage]}
        self.programme = programme
        self.u0_utm_df = u0_utm_df  # DF[UTM, Nombre, Pourcentage]
        self.u1_utm_df = u1_utm_df
        self.cat_urg_df = cat_urg_df  # DF[Catégorie, U0s, U1s, Total]
        self.setWindowTitle(f"Analyse surveillance – {programme}")
        self.resize(1100, 750)

        main = QVBoxLayout(self)

        # Bouton Réduire (minimiser)
        self.btn_minimize = QToolButton(self)
        self.btn_minimize.setToolTip("Réduire")
        self.btn_minimize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.btn_minimize.setAutoRaise(True)
        self.btn_minimize.clicked.connect(self.showMinimized)

        # --- Bandeau haut avec bouton plein écran (style Windows, en haut à droite)
        header = QHBoxLayout()
        header.addStretch()
        self.btn_fullscreen = QToolButton(self)
        self.btn_fullscreen.setToolTip("Plein écran (F11)")
        self.btn_fullscreen.setText("⛶")  # symbole Maximize
        self.btn_fullscreen.setAutoRaise(True)  # rendu discret comme un bouton de barre de titre
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        # header.addWidget(self.btn_fullscreen, 0, Qt.AlignRight)
        # On ajoute d'abord Réduire puis Plein écran dans le header
        header.addWidget(self.btn_minimize, 0, Qt.AlignRight)
        header.addWidget(self.btn_fullscreen, 0, Qt.AlignRight)
        main.addLayout(header)

        # Raccourci clavier F11
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)

        # Titre discret
        titre = QLabel(f"Répartition par 'Statut' – Programme {programme}")
        titre.setStyleSheet("font-weight: bold; font-size: 14px;")
        main.addWidget(titre)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        main.addLayout(grid)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs)

        ordre = ["VI", "VD", "IDE", "IDR"]  # ordre d’affichage demandé

        # affichage des 4 camemberts ==> ok
        """positions = [(0,0), (0,1), (1,0), (1,1)]
        for cat, (r, c) in zip(ordre, positions):
            w = self._build_pie_widget(cat, self.data.get(cat))
            grid.addWidget(w, r, c)"""

        # 1 onglet par catégorie (camembert unique)
        for cat in ordre:
            tab = QWidget()
            v = QVBoxLayout(tab)
            v.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"{cat} 2")
            # Correction des zone vide autour des labels
            # lbl.setStyleSheet("font-weight: bold;")
            #v.addWidget(lbl)

            df_cat = self.data.get(cat)
            fig = Figure(figsize=(5.8, 4.0))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            if df_cat is not None and not df_cat.empty:
                labels_statut = df_cat["Statut"].tolist()
                sizes = [int(x) for x in df_cat["Nombre"].tolist()]
                pcts = df_cat["Pourcentage"].tolist()
                self._draw_pie(ax, labels_statut, sizes, pcts, titre=cat)
            else:
                ax.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
                ax.axis("off")

            # Titre DANS la figure (plus d’espace “vide” de QLabel)
            ax.set_title(f"{cat} 2", loc="left", fontsize=11, pad=6)

            # Légende à droite + compaction des marges
            # ancienne valeur: fig.tight_layout()
            fig.tight_layout(rect=[0.02, 0.02, 0.88, 0.98])

            v.addWidget(canvas)
            self.tabs.addTab(tab, cat)

        # 5e onglet : Ensemble (les 4 camemberts en 2×2) — marges compactes, titre dans la figure
        tab_all = QWidget()
        grid = QGridLayout(tab_all)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for (cat, (r, c)) in zip(ordre, positions):
            cont = QWidget()
            v = QVBoxLayout(cont)
            v.setContentsMargins(0, 0, 0, 0)

            df_cat = self.data.get(cat)
            fig = Figure(figsize=(5.4, 3.8))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            if df_cat is not None and not df_cat.empty:
                labels_statut = df_cat["Statut"].tolist()
                sizes = [int(x) for x in df_cat["Nombre"].tolist()]
                pcts = df_cat["Pourcentage"].tolist()
                self._draw_pie(ax, labels_statut, sizes, pcts, titre=cat)
            else:
                ax.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
                ax.axis("off")

            # Titre DANS la figure (plus d’espace vide)
            ax.set_title(f"{cat} 2", loc="left", fontsize=11, pad=6)

            # Légende à droite + marges serrées (réserve ~12% à droite pour la légende)
            fig.tight_layout(rect=[0.02, 0.02, 0.88, 0.98])

            v.addWidget(canvas)
            grid.addWidget(cont, r, c)

        self.tabs.addTab(tab_all, "Ensemble")

        #Maintenance
        # U0s par UTM
        logger.debug("DEBUG: - U0s par UTM")
        tab_u0 = self._tab_donut_utm_df("OA - PRECOS U0 S Hors délai par UTM", self.u0_utm_df)
        self.tabs.addTab(tab_u0, "U0s par UTM")

        # U1s par UTM
        logger.debug("DEBUG: - U1s par UTM")
        tab_u1 = self._tab_donut_utm_df("OA - PRECOS U1 S Hors délai par UTM", self.u1_utm_df)
        self.tabs.addTab(tab_u1, "U1s par UTM")

        # Catégorie × Urgence
        logger.debug("DEBUG: - Catégorie × Urgence")
        tab_cat = self._tab_bar_hstack_cat_urgences_df("OA - Nombre d'Urgence par Catégorie et Urgence",
                                                       self.cat_urg_df)
        self.tabs.addTab(tab_cat, "Catégorie × Urgence")

        # Maintenance (regroupement)
        tab_maint = QWidget()
        grid = QGridLayout(tab_maint)
        grid.setContentsMargins(0, 0, 0, 0);
        grid.setHorizontalSpacing(12);
        grid.setVerticalSpacing(12)
        grid.addWidget(
            self._tab_donut_utm_df("OA - PRECOS U0 S Hors délai par UTM", self.u0_utm_df, return_container=True), 0, 0)
        grid.addWidget(
            self._tab_donut_utm_df("OA - PRECOS U1 S Hors délai par UTM", self.u1_utm_df, return_container=True), 0, 1)
        grid.addWidget(
            self._tab_bar_hstack_cat_urgences_df("OA - Nombre d'Urgence par Catégorie et Urgence", self.cat_urg_df,
                                                 return_container=True), 1, 0, 1, 2)
        self.tabs.addTab(tab_maint, "Maintenance")

        # Bas de fenêtre
        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_export = QPushButton("Exporter l'image")
        self.btn_export.clicked.connect(self.export_image)
        self.btn_close = QPushButton("Fermer")
        self.btn_close.clicked.connect(self.close)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_close)
        main.addLayout(actions)


    def toggle_fullscreen(self):
        # Bascule plein écran / taille normale et change l’icône
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶")  # revenir à l’icône Maximize
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("🗗")  # icône Restore/Windowed


    def export_image(self):
        # Exporte l’onglet complet (grille) tel qu’affiché (capture de la fenêtre)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'image", f"Analyse_surveillance_{self.programme}.png",
            "Images (*.png *.jpg *.jpeg);;PDF (*.pdf)", options=options
        )
        if not file_path:
            return
        # On sauvegarde la fenêtre Qt en image (rendu rapide et fidèle à la grille 2x2)
        # Fallback : si grab() indisponible, on pourrait sauvegarder fig par fig.
        pix = self.grab()
        pix.save(file_path)