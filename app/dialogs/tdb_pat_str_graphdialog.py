# tdb_patstr_graphdialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem, QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class PatStrGraphDialog(QDialog):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowTitle("Évolution des indicateurs Section Structures")
        self.resize(1200, 700)
        self.setMinimumWidth(900)
        self.layout = QVBoxLayout(self)

        # Zone de filtres (catégorie / sous-catégorie)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Catégorie :"))
        self.combo_cat = QComboBox()
        self.combo_cat.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_layout.addWidget(self.combo_cat)

        filter_layout.addWidget(QLabel("Sous-catégorie :"))
        self.combo_souscat = QComboBox()
        self.combo_souscat.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_layout.addWidget(self.combo_souscat)

        filter_layout.addWidget(QLabel("Indicateurs :"))
        self.list_indicateurs = QListWidget()
        self.list_indicateurs.setSelectionMode(QListWidget.MultiSelection)
        self.list_indicateurs.setMaximumWidth(320)
        filter_layout.addWidget(self.list_indicateurs)

        self.btn_plot = QPushButton("Tracer")
        filter_layout.addWidget(self.btn_plot)
        filter_layout.addStretch()
        self.layout.addLayout(filter_layout)

        # Zone du graphique
        self.figure, self.ax = plt.subplots(figsize=(12, 5))
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.populate_categories()
        self.combo_cat.currentTextChanged.connect(self.populate_souscategories)
        self.combo_souscat.currentTextChanged.connect(self.populate_indicateurs)
        self.btn_plot.clicked.connect(self.plot_selected)
        self.populate_souscategories()  # pour la catégorie sélectionnée par défaut

    def populate_categories(self):
        # Extrait toutes les catégories uniques
        lignes = self.df["Catégorie - Sous-catégorie"].unique()
        cats = sorted(set(l.split("-")[0].strip() for l in lignes))
        self.combo_cat.clear()
        self.combo_cat.addItems(cats)

    def populate_souscategories(self):
        cat = self.combo_cat.currentText()
        lignes = self.df["Catégorie - Sous-catégorie"].unique()
        souscats = []
        for l in lignes:
            if l.startswith(cat):
                part = l[len(cat):].strip()
                if part.startswith("-"):
                    part = part[1:].strip()
                if part and ":" in part:
                    souscat = part.split(":", 1)[0].strip()
                    souscats.append(souscat)
                else:
                    souscats.append("")  # Catégorie seule
        souscats = sorted(set(souscats))
        self.combo_souscat.clear()
        self.combo_souscat.addItem("")  # Option "tout"
        for sc in souscats:
            if sc:
                self.combo_souscat.addItem(sc)
        self.populate_indicateurs()

    def populate_indicateurs(self):
        cat = self.combo_cat.currentText()
        souscat = self.combo_souscat.currentText()
        if souscat:
            prefix = f"{cat} - {souscat}"
        else:
            prefix = cat
        lignes = [l for l in self.df["Catégorie - Sous-catégorie"].unique() if l.startswith(prefix)]
        self.list_indicateurs.clear()
        for l in lignes:
            indic = l.split(":")[-1].strip()
            item = QListWidgetItem(indic)
            item.setData(32, l)  # Qt.UserRole = 32
            item.setSelected(True)
            self.list_indicateurs.addItem(item)

    def plot_selected(self):
        cat = self.combo_cat.currentText()
        souscat = self.combo_souscat.currentText()
        if souscat:
            prefix = f"{cat} - {souscat}"
        else:
            prefix = cat
        # Mois
        months = [col for col in self.df.columns if col != "Catégorie - Sous-catégorie"]
        # Lignes à afficher
        lignes_sel = [self.list_indicateurs.item(i).data(32)
                      for i in range(self.list_indicateurs.count())
                      if self.list_indicateurs.item(i).isSelected()]
        if not lignes_sel:
            return
        self.ax.clear()
        for l in lignes_sel:
            serie = self.df.loc[self.df["Catégorie - Sous-catégorie"] == l, months]
            if not serie.empty:
                values = serie.iloc[0].values
                self.ax.plot(months, values, marker='o', label=l.split(":")[-1].strip())
        self.ax.set_title(f"Évolution des indicateurs : {prefix}")
        self.ax.set_xlabel("Mois")
        self.ax.set_ylabel("Nombre")
        self.ax.set_xticks(months)
        self.ax.set_xticklabels(months, rotation=45)
        self.ax.legend(loc="best")
        self.figure.tight_layout()
        self.canvas.draw()
