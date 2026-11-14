from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QRadioButton, QButtonGroup
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class PatStrActiviteGraphDialog(QDialog):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowTitle("Analyse graphique - Activité")
        self.resize(900, 580)
        layout = QVBoxLayout(self)

        # ---- Filtrage par couple ----
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Couple Catégorie - Sous-catégorie :"))
        self.combo_couple = QComboBox()
        filter_layout.addWidget(self.combo_couple)

        # ---- Type de graphique ----
        self.radio_group = QButtonGroup(self)
        self.radio_bar = QRadioButton("Barres verticales")
        self.radio_pie = QRadioButton("Camembert")
        self.radio_bar.setChecked(True)
        self.radio_group.addButton(self.radio_bar)
        self.radio_group.addButton(self.radio_pie)
        filter_layout.addWidget(self.radio_bar)
        filter_layout.addWidget(self.radio_pie)

        # self.btn_plot = QPushButton("Tracer")
        # filter_layout.addWidget(self.btn_plot)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # ---- Zone graphique ----
        self.figure, self.ax = plt.subplots(figsize=(9, 4.5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # ---- Setup ----
        self.populate_couples()
        self.combo_couple.currentTextChanged.connect(self.plot_selected)
        # self.btn_plot.clicked.connect(self.plot_selected)
        self.radio_bar.toggled.connect(self.plot_selected)
        self.radio_pie.toggled.connect(self.plot_selected)


    def populate_couples(self):
        couples = set()
        for l in self.df["Catégorie - Sous-catégorie"]:
            parts = l.split("-")
            couple = "-".join([p.strip() for p in parts[:-1]]).strip()
            couples.add(couple)
        couples = sorted(couples)
        self.combo_couple.blockSignals(True)
        self.combo_couple.clear()
        self.combo_couple.addItem("Toutes")  # Option supplémentaire en début
        self.combo_couple.addItems(couples)
        self.combo_couple.blockSignals(False)
        self.combo_couple.setCurrentIndex(0)
        self.plot_selected()


    def plot_selected(self):
        couple = self.combo_couple.currentText()

        def get_couple(l):
            parts = l.split("-")
            return "-".join([p.strip() for p in parts[:-1]]).strip()

        if couple == "Toutes":
            df_couple = self.df.copy()
        else:
            mask = self.df["Catégorie - Sous-catégorie"].apply(lambda l: get_couple(l) == couple)
            df_couple = self.df[mask]
        if df_couple.empty:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            self.ax.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
            self.canvas.draw()
            return
        # Génère les étiquettes : couple + indicateur
        indic_labels = []
        indic_values = []
        for l, v in zip(df_couple["Catégorie - Sous-catégorie"], df_couple["Valeur"]):
            cpl = get_couple(l)
            indic = l.split("-")[-1].strip()
            if couple == "Toutes":
                label = f"{cpl} | {indic}"
            else:
                label = indic
            indic_labels.append(label)
            try:
                indic_values.append(float(v))
            except Exception:
                indic_values.append(0)
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        color_map = plt.cm.tab20.colors
        colors = color_map * ((len(indic_labels) // len(color_map)) + 1)
        if self.radio_bar.isChecked():
            bars = self.ax.bar(indic_labels, indic_values, color=colors[:len(indic_labels)])
            self.ax.set_ylabel("Nombre")
            self.ax.set_xlabel("Couple | Indicateur" if couple == "Toutes" else "Indicateur")
            self.ax.set_title("Activité : Toutes les catégories" if couple == "Toutes" else f"Activité : {couple}")
            self.ax.set_ylim(0, max(indic_values + [1]) * 1.2)
            for idx, v in enumerate(indic_values):
                self.ax.text(idx, v + max(indic_values) * 0.02, str(int(v)), ha='center', va='bottom', fontsize=9)
            # Légende survol facultative, sinon toutes les barres sont labellisées
            if len(bars) <= 12:
                self.ax.legend(bars, indic_labels, loc='upper right', bbox_to_anchor=(1.20, 1))
            else:
                self.ax.legend().set_visible(False)
        else:
            if sum(indic_values) == 0:
                self.ax.text(0.5, 0.5, "Aucune donnée à afficher", ha='center', va='center')
            else:
                wedges, texts, autotexts = self.ax.pie(
                    indic_values, labels=indic_labels, autopct="%1.0f%%",
                    startangle=90, colors=colors[:len(indic_labels)]
                )
                self.ax.legend(wedges, indic_labels, loc='upper right', bbox_to_anchor=(1.20, 1))
            self.ax.set_title(
                "Répartition des indicateurs : Toutes les catégories" if couple == "Toutes" else f"Répartition des indicateurs : {couple}")
        self.figure.tight_layout()
        self.canvas.draw()


