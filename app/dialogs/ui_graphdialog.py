from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import pandas as pd
import re


class GraphDialog(QDialog):
    def __init__(self, df, key):
        super().__init__()
        self.df = df
        self.key = key
        self.setWindowTitle("ES-PIGC : module de visualisation")
        self.resize(900, 700)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.options_layout = QHBoxLayout()
        self.layout.addLayout(self.options_layout)
        if key == ("ES-IND", "OT", "Préconisations"):
            self.add_preconisations_controls()
            self.plot_preconisations()
        elif key == ("ES-IND", "OT", "Visites cycliques"):
            self.add_visites_cycliques_controls()
            self.plot_visites_cycliques()

    def add_preconisations_controls(self):
        self.combo_scope = QComboBox()
        scopes = ["National (tous infrapôles)"] + sorted(self.df["Infrapôle"].unique())
        self.combo_scope.addItems(scopes)
        self.combo_urgence = QComboBox()
        urgences = ["U0", "U1", "Tous"]
        self.combo_urgence.addItems(urgences)
        self.options_layout.addWidget(QLabel("Graphe :"))
        self.options_layout.addWidget(self.combo_scope)
        # self.options_layout.addWidget(QLabel("Urgence :"))
        self.label_urgence = QLabel("Urgence:")
        self.options_layout.addWidget(self.label_urgence)
        self.options_layout.addWidget(self.combo_urgence)

        self.combo_scope.currentIndexChanged.connect(self.plot_preconisations)
        self.combo_urgence.currentIndexChanged.connect(self.plot_preconisations)

        self.label_mesure = QLabel("Mesure :")
        self.combo_mesure = QComboBox()
        self.combo_mesure.addItems(["Comparatif", "Toujours en cours", "Sortie après trimestre"])
        self.options_layout.addWidget(self.label_mesure)
        self.options_layout.addWidget(self.combo_mesure)
        self.combo_mesure.currentIndexChanged.connect(self.plot_preconisations)

    def plot_preconisations(self):
        self.figure.clear()
        scope = self.combo_scope.currentText()
        urgence = self.combo_urgence.currentText()
        dfg = self.df.copy()
        title = "Préconisations"

        def get_past_trim_cols(cols):
            cours = [c for c in cols if re.match(r"^Préconisé avant .+ toujours en cours$", c)]
            traite = [c for c in cols if re.match(r"^Préconisé avant .+ / traité ou annulé aprés .+$", c)]
            return cours[0] if cours else None, traite[0] if traite else None

        col_cours, col_traite = get_past_trim_cols(list(dfg.columns))
        is_past_trim = (col_cours is not None and col_traite is not None)

        # 3 - Masquer la combo urgence si trimestre dans le passé...
        if hasattr(self, "combo_urgence"):
            self.combo_urgence.setVisible(not is_past_trim)
        if hasattr(self, "label_urgence"):
            self.label_urgence.setVisible(not is_past_trim)
        if hasattr(self, "combo_mesure"):
            self.combo_mesure.setVisible(is_past_trim)
        if hasattr(self, "label_mesure"):
            self.label_mesure.setVisible(is_past_trim)

        if is_past_trim:
            if scope != "National (tous infrapôles)":
                dfg = dfg[dfg["Infrapôle"] == scope]
                title += f" – {scope}"

            labels = list(dfg["Infrapôle"])
            vals_cours = list(dfg[col_cours].values)
            vals_sortie_apres = list(dfg[col_traite].values)

            if not vals_cours:
                vals_cours = [0]
            if not vals_sortie_apres:
                vals_sortie_apres = [0]
            if not labels:
                labels = ["(Aucun)"]
            x = range(len(labels))

            width = 0.35
            mesure = self.combo_mesure.currentText() if hasattr(self, "combo_mesure") else "Comparatif"

            # Tri dynamique
            if mesure == "Comparatif":
                order = sorted(range(len(labels)), key=lambda i: (vals_cours[i] + vals_sortie_apres[i]), reverse=True)
            elif mesure == "Toujours en cours":
                order = sorted(range(len(labels)), key=lambda i: vals_cours[i], reverse=True)
            elif mesure == "Sortie après trimestre":
                order = sorted(range(len(labels)), key=lambda i: vals_sortie_apres[i], reverse=True)
            else:
                order = list(range(len(labels)))

            labels = [labels[i] for i in order]
            vals_cours = [vals_cours[i] for i in order]
            vals_sortie_apres = [vals_sortie_apres[i] for i in order]
            x = range(len(labels))

            self.figure.clear()

            # Cas double axe uniquement si >1 infrapôle
            if mesure == "Comparatif" and len(labels) > 1:
                ax1 = self.figure.add_subplot(111)
                ax2 = ax1.twinx()

                bars1 = ax1.bar([i - width / 2 for i in x], vals_cours, width=width, label="Toujours en cours",
                                color="#4682B4", alpha=0.85)
                bars2 = ax2.bar([i + width / 2 for i in x], vals_sortie_apres, width=width,
                                label="Sortie après trimestre", color="#FFA500", alpha=0.65)

                for i, bar in enumerate(bars1):
                    ax1.annotate(f"{vals_cours[i]}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                 xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9,
                                 color="#304860")
                for i, bar in enumerate(bars2):
                    ax2.annotate(f"{vals_sortie_apres[i]}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                 xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9,
                                 color="#C87100")

                ax1.set_ylabel("Toujours en cours", color="#4682B4")
                ax2.set_ylabel("Sortie après trimestre", color="#FFA500")
                ax1.tick_params(axis='y', labelcolor="#4682B4")
                ax2.tick_params(axis='y', labelcolor="#FFA500")
                ax1.grid(axis="y", linestyle="--", alpha=0.5)
                ax1.set_xticks(list(x))
                ax1.set_xticklabels(labels, rotation=15, ha="right")
                ax1.set_title(title)
                # Affiche une légende simple SANS fusionner les deux axes (évite le crash)
                ax1.legend([bars1, bars2], ["Toujours en cours", "Sortie après trimestre"], loc="upper right")
                ax1.set_ylim(bottom=0, top=max(vals_cours) * 1.1 if vals_cours else 1)
                ax2.set_ylim(bottom=0, top=max(vals_sortie_apres) * 1.1 if vals_sortie_apres else 1)

            else:
                # Mono-axe, même pour comparatif si un seul infrapôle
                ax1 = self.figure.add_subplot(111)
                if mesure == "Comparatif":
                    bars1 = ax1.bar([i - width / 2 for i in x], vals_cours, width=width, label="Toujours en cours",
                                    color="#4682B4")
                    bars2 = ax1.bar([i + width / 2 for i in x], vals_sortie_apres, width=width,
                                    label="Sortie après trimestre", color="#FFA500")
                    for i, bar in enumerate(bars1):
                        ax1.annotate(f"{vals_cours[i]}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
                    for i, bar in enumerate(bars2):
                        ax1.annotate(f"{vals_sortie_apres[i]}",
                                     xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
                    ax1.legend(loc="upper right")
                elif mesure == "Toujours en cours":
                    bars1 = ax1.bar(x, vals_cours, width=width, label="Toujours en cours", color="#4682B4")
                    for i, bar in enumerate(bars1):
                        ax1.annotate(f"{vals_cours[i]}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
                    ax1.legend(loc="upper right")
                elif mesure == "Sortie après trimestre":
                    bars2 = ax1.bar(x, vals_sortie_apres, width=width, label="Sortie après trimestre", color="#FFA500")
                    for i, bar in enumerate(bars2):
                        ax1.annotate(f"{vals_sortie_apres[i]}",
                                     xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
                    ax1.legend(loc="upper right")

                ax1.set_ylabel(mesure if mesure != "Comparatif" else "Nombre")
                ax1.set_xticks(list(x))
                ax1.set_xticklabels(labels, rotation=15, ha="right")
                ax1.set_title(title)
                ax1.grid(axis="y", linestyle="--", alpha=0.5)
                top = max(vals_cours + vals_sortie_apres) * 1.1 if (vals_cours + vals_sortie_apres) else 1.1
                ax1.set_ylim(bottom=0, top=top)

            self.canvas.draw()
            return

        # ************************************************************************************************************
        self.figure.clear()
        scope = self.combo_scope.currentText()
        urgence = self.combo_urgence.currentText()
        dfg = self.df.copy()
        title = "Préconisations"

        # --- PATCH sécurité : conversion des colonnes numériques ---
        num_cols = [
            "U0 Nombre total de préconisations", "U0 Préconisations échues",
            "U0 Analyse de risque - demandées ou en cours",
            "U1 Nombre total de préconisations", "U1 Préconisations échues",
            "U1 Analyse de risque - demandées ou en cours"
        ]

        for col in num_cols:
            if col in dfg.columns:
                dfg[col] = pd.to_numeric(dfg[col], errors="coerce").fillna(0)

        if scope != "National (tous infrapôles)":
            dfg = dfg[dfg["Infrapôle"] == scope]
            title += f" – {scope}"
        # Sélection urgence
        if urgence == "U0":
            labels = [
                "U0 Nombre total de préconisations", "U0 Préconisations échues", "U0 Analyse de risque - demandées ou en cours"
            ]
        elif urgence == "U1":
            labels = [
                "U1 Nombre total de préconisations", "U1 Préconisations échues", "U1 Analyse de risque - demandées ou en cours"
            ]
        else:  # Tous
            labels = [
                "U0 Nombre total de préconisations", "U1 Nombre total de préconisations",
                "U0 Préconisations échues", "U1 Préconisations échues"
            ]
        ax1 = self.figure.add_subplot(121)
        if urgence in ("U0", "U1"):
            vals = []
            for col in labels:
                vals.append(dfg[col].sum() if col in dfg else 0)
            col_simple = ["Total", "Echues", "Risque"]
            ax1.bar(col_simple, vals, color=["#8f6cce", "#ea8e2d", "#43A047"])
            ax1.set_title(f"{title} ({urgence})")
            total = vals[0]
            echues = vals[1]
            non_echues = max(0, total - echues)
            ax2 = self.figure.add_subplot(122)
            parts = [echues, non_echues]
            pie_labels = ["Echues", "Non échues"]
            if sum(parts) == 0:
                parts = [1]
                pie_labels = ["Pas de données"]
            ax2.pie(parts, labels=pie_labels, autopct="%.1f%%", startangle=90)
            ax2.set_title("Répartition préconisations")
        else:
            v0 = dfg["U0 Nombre total de préconisations"].sum() if "U0 Nombre total de préconisations" in dfg else 0
            v1 = dfg["U1 Nombre total de préconisations"].sum() if "U1 Nombre total de préconisations" in dfg else 0
            v2 = dfg["U0 Préconisations échues"].sum() if "U0 Préconisations échues" in dfg else 0
            v3 = dfg["U1 Préconisations échues"].sum() if "U1 Préconisations échues" in dfg else 0
            ax1.bar(["U0 Total", "U1 Total"], [v0, v1], color=["#8f6cce", "#53ce7c"])
            ax1.bar(["U0 Echues", "U1 Echues"], [v2, v3], color=["#ea8e2d", "#ea8e2d"])
            ax1.set_title(f"{title} (U0/U1)")
            ax2 = self.figure.add_subplot(122)
            total_all = v0 + v1
            echues_all = v2 + v3
            parts = [echues_all, max(0, total_all - echues_all)]
            pie_labels = ["Echues", "Non échues"]
            if sum(parts) == 0:
                parts = [1]
                pie_labels = ["Pas de données"]
            ax2.pie(parts, labels=pie_labels, autopct="%.1f%%", startangle=90)
            ax2.set_title("Répartition préconisations (global)")
        self.canvas.draw()

    def add_visites_cycliques_controls(self):
        self.combo_scope = QComboBox()
        scopes = ["National (tous infrapôles)"] + sorted(self.df["Infrapôles"].unique())
        self.combo_scope.addItems(scopes)
        self.combo_cat = QComboBox()
        # cats = ["Toutes les catégories"] + sorted(self.df["Catégorie action"].unique())
        cats_uniques = [c for c in self.df["Catégorie action"].unique() if pd.notna(c) and str(c).strip() != ""]
        cats = ["Toutes les catégories"] + sorted(cats_uniques)
        self.combo_cat.addItems(cats)
        self.options_layout.addWidget(QLabel("Infrapôle :"))
        self.options_layout.addWidget(self.combo_scope)
        self.options_layout.addWidget(QLabel("Catégorie :"))
        self.options_layout.addWidget(self.combo_cat)
        self.combo_scope.currentIndexChanged.connect(self.plot_visites_cycliques)
        self.combo_cat.currentIndexChanged.connect(self.plot_visites_cycliques)


    def plot_visites_cycliques(self):
        self.figure.clear()
        scope = self.combo_scope.currentText()
        cat = self.combo_cat.currentText()
        dfg = self.df.copy()

        # 1. Retirer les lignes "Données manquantes"
        if "Indicateur (Validation) en %" in dfg.columns:
            dfg = dfg[dfg["Indicateur (Validation) en %"].astype(str).str.lower() != "données manquantes"]

        # 2. Filtre sur l'infrapôle sélectionné
        if scope != "National (tous infrapôles)":
            dfg = dfg[dfg["Infrapôles"] == scope]
        # 3. Filtre sur la catégorie sélectionnée
        if cat != "Toutes les catégories":
            dfg = dfg[dfg["Catégorie action"] == cat]

        # 4. Si aucune donnée à afficher après tous les filtres, on affiche un message et on arrête
        if dfg.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Aucune donnée à afficher", ha='center', va='center', fontsize=14)
            ax.axis("off")
            self.canvas.draw()
            return

        # 5. Préparation des colonnes à tracer
        prevision_col = [c for c in dfg.columns if c.startswith("Prévision")][0]
        real_col = [c for c in dfg.columns if c.startswith("Réalisées")][0]
        pv_col = [c for c in dfg.columns if c.startswith("PV validés")][0]

        # 6. Conversion sûre en numériques
        dfg[prevision_col] = pd.to_numeric(dfg[prevision_col], errors="coerce").fillna(0)
        dfg[real_col] = pd.to_numeric(dfg[real_col], errors="coerce").fillna(0)
        dfg[pv_col] = pd.to_numeric(dfg[pv_col], errors="coerce").fillna(0)

        # 7. Agrégation en cohérence avec le scope et la catégorie
        if scope == "National (tous infrapôles)":
            if cat == "Toutes les catégories":
                # Une barre par catégorie (somme tous infrapôles)
                agg = (dfg.groupby("Catégorie action", as_index=False)
                       [[prevision_col, real_col, pv_col]].sum())
                labels = agg["Catégorie action"].tolist()
                prevision = agg[prevision_col].tolist()
                realisees = agg[real_col].tolist()
                pv = agg[pv_col].tolist()
                title = "Visites cycliques – National"
            else:
                # Une seule catégorie choisie → somme tous infrapôles
                agg = dfg[[prevision_col, real_col, pv_col]].sum(numeric_only=True)
                labels = [cat]
                prevision = [float(agg[prevision_col])]
                realisees = [float(agg[real_col])]
                pv = [float(agg[pv_col])]
                title = f"Visites cycliques – National – {cat}"
        else:
            # Infrapôle précis
            if cat == "Toutes les catégories":
                # Une barre par catégorie (sur l'infrapôle)
                agg = (dfg.groupby("Catégorie action", as_index=False)
                       [[prevision_col, real_col, pv_col]].sum())
                labels = agg["Catégorie action"].tolist()
                prevision = agg[prevision_col].tolist()
                realisees = agg[real_col].tolist()
                pv = agg[pv_col].tolist()
                title = f"Visites cycliques – {scope}"
            else:
                # Une seule catégorie sur l'infrapôle
                agg = dfg[[prevision_col, real_col, pv_col]].sum(numeric_only=True)
                labels = [cat]
                prevision = [float(agg[prevision_col])]
                realisees = [float(agg[real_col])]
                pv = [float(agg[pv_col])]
                title = f"Visites cycliques – {scope} – {cat}"

        # Sécurité affichage
        if not labels:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Aucune donnée à afficher", ha='center', va='center', fontsize=14)
            ax.axis("off")
            self.canvas.draw()
            return

        # 8. Tracé des barres (échelle commune et lisible)
        ax1 = self.figure.add_subplot(121)
        x = range(len(labels))
        width = 0.27

        bars_prev = ax1.bar([i - width for i in x], prevision, width=width, label="Prévision")
        bars_real = ax1.bar(x, realisees, width=width, label="Réalisées")
        bars_pv = ax1.bar([i + width for i in x], pv, width=width, label="PV validés")

        ax1.set_xticks(list(x))
        ax1.set_xticklabels(labels, rotation=20, ha="right")
        ax1.set_ylabel("Nombre")
        ax1.set_title(title)
        ax1.legend(loc="upper right")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)

        top = 1.15 * max([0] + prevision + realisees + pv)
        ax1.set_ylim(0, top)

        # 9. Camembert du taux de réalisation
        total_prev = sum(prevision)
        total_real = sum(realisees)
        ax2 = self.figure.add_subplot(122)
        if total_prev > 0:
            ax2.pie([total_real, max(0, total_prev - total_real)],
                    labels=["Réalisées", "Non réalisées"], autopct="%.1f%%", startangle=90)
            taux = (total_real / total_prev) * 100
            ax2.set_title(f"Taux de réalisation : {taux:.1f}%")
        else:
            ax2.text(0.5, 0.5, "Pas de données à représenter", ha='center', va='center', fontsize=14)
            ax2.axis("off")

        self.canvas.draw()
