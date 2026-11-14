"""Onglets de rapports (COPIL, catégories, domaines, natures, évolution, métriques)."""

from PyQt5.QtWidgets import QWidget, QGroupBox, QComboBox
from PyQt5.QtWidgets import QCheckBox, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QLabel
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from datetime import datetime


class RapportTabsMixin:
    """Onglets de rapports (COPIL, catégories, domaines, natures, évolution, métriques)."""

    def create_rapport_copil_tab(self):
        """Onglet COPIL avec sélecteur checkboxes années/trimestres"""
        tab = QWidget()
        mainlayout = QVBoxLayout(tab)

        # ── Sélecteur avec checkboxes ─────────────────────────────────────────
        selectorgroup = QGroupBox("Sélection de la période COPIL")
        selectorgroup.setMaximumHeight(160)
        selectorgroup.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #475569;
                        border-radius: 4px; margin-top: 4px; padding: 6px 8px; }
            QGroupBox::title { color: #475569; font-size: 11px; }
        """)
        selectorlayout = QHBoxLayout()
        selectorlayout.setContentsMargins(10, 4, 10, 8)
        selectorlayout.setSpacing(20)

        # -- Années (checkboxes) --
        yearcol = QVBoxLayout()
        yearcol.setSpacing(2)
        lbl_year = QLabel("Années :")
        lbl_year.setStyleSheet("font-size: 11px; font-weight: bold; color: #1F4E9C;")
        yearcol.addWidget(lbl_year)

        year_scroll = QScrollArea()
        year_scroll.setWidgetResizable(True)
        year_scroll.setFixedSize(100, 95)
        year_scroll.setStyleSheet("border: 1px solid #ddd; background: white;")
        year_content = QWidget()
        year_content_layout = QVBoxLayout(year_content)
        year_content_layout.setSpacing(1)
        year_content_layout.setContentsMargins(4, 2, 4, 2)

        self.copil_year_checkboxes = []
        current_year = datetime.now().year
        for year in range(current_year - 5, current_year + 1):
            cb = QCheckBox(str(year))
            cb.setStyleSheet("font-size: 11px;")
            cb.setChecked(year == current_year)
            cb.stateChanged.connect(self._copil_update_trimestres)
            year_content_layout.addWidget(cb)
            self.copil_year_checkboxes.append((year, cb))

        year_content_layout.addStretch()
        year_scroll.setWidget(year_content)
        yearcol.addWidget(year_scroll)

        yearbtnlayout = QHBoxLayout()
        yearbtnlayout.setSpacing(4)
        btn_all_y = QPushButton("Tout")
        btn_none_y = QPushButton("Aucun")
        for b in [btn_all_y, btn_none_y]:
            b.setFixedHeight(20)
            b.setStyleSheet("padding: 0px 6px; font-size: 10px;")
            yearbtnlayout.addWidget(b)
        btn_all_y.clicked.connect(lambda: [cb.setChecked(True) for _, cb in self.copil_year_checkboxes])
        btn_none_y.clicked.connect(lambda: [cb.setChecked(False) for _, cb in self.copil_year_checkboxes])
        yearcol.addLayout(yearbtnlayout)
        selectorlayout.addLayout(yearcol)

        # -- Trimestres (checkboxes) --
        trimcol = QVBoxLayout()
        trimcol.setSpacing(2)
        lbl_trim = QLabel("Trimestres :")
        lbl_trim.setStyleSheet("font-size: 11px; font-weight: bold; color: #2F855A;")
        trimcol.addWidget(lbl_trim)

        trim_scroll = QScrollArea()
        trim_scroll.setWidgetResizable(True)
        trim_scroll.setFixedHeight(95)
        trim_scroll.setMinimumWidth(320)
        trim_scroll.setStyleSheet("border: 1px solid #ddd; background: white;")
        self.copil_trim_content = QWidget()
        self.copil_trim_layout = QVBoxLayout(self.copil_trim_content)
        self.copil_trim_layout.setSpacing(1)
        self.copil_trim_layout.setContentsMargins(4, 2, 4, 2)
        trim_scroll.setWidget(self.copil_trim_content)
        self.copil_trim_checkboxes = []
        trimcol.addWidget(trim_scroll)

        trimbtnlayout = QHBoxLayout()
        trimbtnlayout.setSpacing(4)
        btn_all_t = QPushButton("Tout")
        btn_none_t = QPushButton("Aucun")
        for b in [btn_all_t, btn_none_t]:
            b.setFixedHeight(20)
            b.setStyleSheet("padding: 0px 6px; font-size: 10px;")
            trimbtnlayout.addWidget(b)
        btn_all_t.clicked.connect(lambda: [cb.setChecked(True) for _, cb in self.copil_trim_checkboxes])
        btn_none_t.clicked.connect(lambda: [cb.setChecked(False) for _, cb in self.copil_trim_checkboxes])
        trimbtnlayout.addStretch()
        trimcol.addLayout(trimbtnlayout)
        selectorlayout.addLayout(trimcol)

        # -- Bouton Actualiser --
        selectorlayout.addStretch()
        btnrefresh = QPushButton("🔄 Actualiser")
        btnrefresh.setStyleSheet("""
            background: #475569; color: white; font-weight: bold;
            padding: 10px 20px; font-size: 13px; border-radius: 5px;
        """)
        btnrefresh.setFixedHeight(40)
        btnrefresh.setMinimumWidth(140)
        btnrefresh.clicked.connect(lambda: self._copil_refresh_charts(chartarea))
        selectorlayout.addWidget(btnrefresh, alignment=Qt.AlignVCenter)

        selectorgroup.setMaximumHeight(170)
        selectorgroup.setLayout(selectorlayout)

        mainlayout.addWidget(selectorgroup)

        # ── Zone graphiques (scroll) ──────────────────────────────────────────
        chartarea = QScrollArea()
        chartarea.setWidgetResizable(True)
        mainlayout.addWidget(chartarea)

        self.tabs.addTab(tab, "📊 COPIL")

        self._copil_update_trimestres()
        self._copil_refresh_charts(chartarea)

    def _copil_update_trimestres(self):
        """Met à jour les checkboxes trimestres selon les années cochées"""
        # Sauvegarder les trimestres déjà cochés (ex: Q1, Q2...)
        selected_keys = {
            data['q'] for data, cb in self.copil_trim_checkboxes if cb.isChecked()
        }

        # Vider le layout
        while self.copil_trim_layout.count():
            child = self.copil_trim_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.copil_trim_checkboxes = []

        selected_years = sorted([
            year for year, cb in self.copil_year_checkboxes if cb.isChecked()
        ])

        trim_names = [
            (1, "Jan-Fév-Mar"), (2, "Avr-Mai-Juin"),
            (3, "Juil-Août-Sept"), (4, "Oct-Nov-Déc"),
        ]
        for year in selected_years:
            for q, months in trim_names:
                label = f"T{q} {year}  ({months})"
                cb = QCheckBox(label)
                cb.setStyleSheet("font-size: 11px;")
                cb.setChecked(q in selected_keys)
                self.copil_trim_layout.addWidget(cb)
                self.copil_trim_checkboxes.append(({"label": label, "q": q, "year": year}, cb))

        self.copil_trim_layout.addStretch()

    def create_rapport_sous_categorie_tab(self):
        """Crée l'onglet rapport par sous-catégorie avec filtre par catégorie"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        # Zone de filtre
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrer par catégorie :"))

        self.combo_filter_categorie = QComboBox()
        self.combo_filter_categorie.addItem("Toutes les catégories", None)

        # Récupérer les catégories disponibles
        query_categories = """
			SELECT DISTINCT COALESCE(cat.libelle_categorie, 'Non défini')
			FROM demandes d
			LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
			WHERE date(d.date_reception) BETWEEN ? AND ?
			ORDER BY cat.libelle_categorie
		"""

        categories = self.data_manager.execute_query(query_categories, (self.date_debut, self.date_fin))
        if categories:
            for (categorie,) in categories:
                self.combo_filter_categorie.addItem(categorie, categorie)

        # ✅ IMPORTANT : Utiliser currentIndexChanged au lieu de currentTextChanged
        self.combo_filter_categorie.currentIndexChanged.connect(lambda: self.update_sous_categorie_graph())

        filter_layout.addWidget(self.combo_filter_categorie)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # Zone pour le graphique
        self.sous_categorie_layout = QVBoxLayout()
        main_layout.addLayout(self.sous_categorie_layout)

        # Générer le graphique initial
        self.update_sous_categorie_graph()

        self.tabs.addTab(tab, "📊 Par sous-catégorie")

    def update_sous_categorie_graph(self):
        """Met à jour le graphique des sous-catégories selon le filtre"""
        # Vider le layout
        while self.sous_categorie_layout.count():
            item = self.sous_categorie_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        categorie_filter = self.combo_filter_categorie.currentData()

        # Construire la requête selon le filtre
        if categorie_filter and categorie_filter != 'Toutes les catégories':
            query = """
                SELECT COALESCE(sc.libelle_sous_categorie, 'Non défini') as sous_categorie, COUNT(*) as nombre
                FROM demandes d
                LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
                LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
                WHERE date(d.date_reception) BETWEEN ? AND ?
                AND cat.libelle_categorie = ?
                GROUP BY sc.libelle_sous_categorie
                ORDER BY nombre DESC
            """
            results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin, categorie_filter))
        else:
            query = """
                SELECT COALESCE(sc.libelle_sous_categorie, 'Non défini') as sous_categorie, COUNT(*) as nombre
                FROM demandes d
                LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
                WHERE date(d.date_reception) BETWEEN ? AND ?
                GROUP BY sc.libelle_sous_categorie
                ORDER BY nombre DESC
            """
            results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        if results:
            n = len(results)
            fig_height = max(7, n * 0.4)  # Hauteur dynamique selon le nombre d'items
            fig = Figure(figsize=(16, fig_height))

            sous_categories = [row[0] for row in results]
            nombres = [row[1] for row in results]
            colors = plt.cm.Set3(range(len(sous_categories)))

            ax1 = fig.add_subplot(1, 2, 1)

            if n <= 8:
                # Camembert avec toutes les catégories
                vals = nombres
                labs = sous_categories
                wedges, texts, autotexts = ax1.pie(
                    vals, autopct='%1.1f%%', startangle=90,
                    colors=colors, pctdistance=0.8
                )
            else:
                # Top 10 + "Autres" si trop de catégories
                sorted_data = sorted(zip(nombres, sous_categories), reverse=True)
                top10 = sorted_data[:10]
                autres_total = sum(nb for nb, _ in sorted_data[10:])
                vals = [nb for nb, _ in top10] + ([autres_total] if autres_total else [])
                labs = [s for _, s in top10] + (['Autres'] if autres_total else [])
                wedges, texts, autotexts = ax1.pie(
                    vals, autopct='%1.1f%%', startangle=90,
                    colors=plt.cm.Set3(range(len(vals))), pctdistance=0.8
                )


            # Supprimer les labels inline pour éviter les chevauchements
            for text in texts:
                text.set_text('')

            # Légende externe — vals et labs sont toujours définis ici
            ax1.legend(
                wedges,
                [f"{s} ({nb})" for nb, s in zip(vals, labs)],
                loc='upper left',
                bbox_to_anchor=(-0.3, 1.0),
                fontsize=6,
                framealpha=0.8
            )
            ax1.set_title('Répartition par sous-catégorie', fontsize=13, fontweight='bold')

            # Barres horizontales avec taille adaptée
            ax2 = fig.add_subplot(1, 2, 2)
            ax2.barh(sous_categories, nombres, color=colors)
            ax2.set_xlabel('Nombre de demandes', fontsize=11)
            ax2.set_title('Volume par sous-catégorie', fontsize=13, fontweight='bold')
            ax2.invert_yaxis()
            for i, nombre in enumerate(nombres):
                ax2.text(nombre + 0.1, i, f' {nombre}', va='center', fontsize=8, fontweight='bold')
            ax2.tick_params(axis='y', labelsize=8)

            fig.tight_layout(pad=2.0)
            canvas = FigureCanvas(fig)
            self.sous_categorie_layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Aucune donnée pour cette sélection")
            no_data_label.setStyleSheet("font-size: 14px; color: #999; padding: 50px;")
            no_data_label.setAlignment(Qt.AlignCenter)
            self.sous_categorie_layout.addWidget(no_data_label)

    def create_rapport_categorie_tab(self):
        """Crée l'onglet rapport par catégorie"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        query = """
            SELECT COALESCE(cat.libelle_categorie, 'Non défini') as categorie, COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY cat.libelle_categorie
            ORDER BY nombre DESC
        """
        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        if results:
            n = len(results)
            fig = Figure(figsize=(16, 7))

            categories = [row[0] for row in results]
            nombres = [row[1] for row in results]
            colors = plt.cm.Set3(range(len(categories)))

            ax1 = fig.add_subplot(1, 2, 1)

            if n <= 5:
                # Peu de catégories : afficher toutes
                vals = nombres
                labs = categories
                wedges, texts, autotexts = ax1.pie(
                    vals, autopct='%1.1f%%', startangle=90,
                    colors=colors, pctdistance=0.8
                )
            else:
                # Garder uniquement les catégories top 10 avec >= 3% + regrouper le reste en "Autres"
                total_global = sum(nombres)
                sorted_data = sorted(zip(nombres, categories), reverse=True)

                top10 = [(nb, s) for nb, s in sorted_data[:10] if nb / total_global * 100 >= 3]
                autres_total = sum(nb for nb, s in sorted_data if (nb, s) not in top10)

                vals = [nb for nb, _ in top10] + ([autres_total] if autres_total else [])
                labs = [s for _, s in top10] + (['Autres'] if autres_total else [])

                wedges, texts, autotexts = ax1.pie(
                    vals, autopct='%1.1f%%', startangle=90,
                    colors=plt.cm.Set3(range(len(vals))), pctdistance=0.8
                )

            # Supprimer les labels inline
            for text in texts:
                text.set_text('')

            # Masquer les % trop petits
            total = sum(vals)
            for autotext, val in zip(autotexts, vals):
                if val / total * 100 < 3:
                    autotext.set_text('')
                else:
                    autotext.set_fontsize(8)

            # Légende externe
            ax1.legend(
                wedges,
                [f"{s} ({nb})" for nb, s in zip(vals, labs)],
                loc='upper left',
                bbox_to_anchor=(-0.35, 1.0),
                fontsize=7,
                framealpha=0.8
            )
            ax1.set_title('Répartition par catégorie', fontsize=13, fontweight='bold')

            # Barres horizontales — toutes les catégories
            ax2 = fig.add_subplot(1, 2, 2)
            ax2.barh(categories, nombres, color=colors)
            ax2.set_xlabel('Nombre de demandes', fontsize=11)
            ax2.set_title('Volume par catégorie', fontsize=13, fontweight='bold')
            ax2.invert_yaxis()
            for i, nombre in enumerate(nombres):
                ax2.text(nombre + 0.3, i, f' {nombre}', va='center', fontsize=9, fontweight='bold')
            ax2.tick_params(axis='y', labelsize=9)

            fig.tight_layout(pad=2.0)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Aucune donnée disponible pour cette période")
            no_data_label.setStyleSheet("font-size: 14px; color: #999; padding: 50px;")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)

        self.tabs.addTab(tab, "📂 Par catégorie")

    def create_rapport_domaine_tab(self):
        """Crée l'onglet rapport par domaine"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        query = """
            SELECT COALESCE(dom.libelle_domaine, 'Non défini') as domaine,
                   COUNT(*) as total,
                   SUM(CASE WHEN et.libelle_etat = 'Traitée' THEN 1 ELSE 0 END) as realisees,
                   SUM(CASE WHEN et.libelle_etat LIKE '%En cours%' THEN 1 ELSE 0 END) as encours,
                   SUM(CASE WHEN et.libelle_etat = 'À étudier' THEN 1 ELSE 0 END) as aetudier
            FROM demandes d
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY dom.libelle_domaine
            ORDER BY total DESC
        """
        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        if results:
            fig = Figure(figsize=(14, 6))
            ax = fig.add_subplot(111)

            domaines  = [row[0] for row in results]
            realisees = [row[2] for row in results]
            encours   = [row[3] for row in results]
            aetudier  = [row[4] for row in results]

            x = range(len(domaines))
            width = 0.6

            bars_r = ax.bar(x, realisees, width, label='Réalisées',  color='#4CAF50')
            bars_e = ax.bar(x, encours,   width, bottom=realisees,   label='En cours',  color='#2196F3')
            bars_a = ax.bar(x, aetudier,  width,
                            bottom=[r + e for r, e in zip(realisees, encours)],
                            label='À étudier', color='#FF9800')

            # Afficher le nombre dans chaque segment (seulement si > 0)
            for i, (r, e, a) in enumerate(zip(realisees, encours, aetudier)):
                # Segment Réalisées
                if r > 0:
                    ax.text(i, r / 2, str(r),
                            ha='center', va='center',
                            fontweight='bold', fontsize=9, color='white')
                # Segment En cours
                if e > 0:
                    ax.text(i, r + e / 2, str(e),
                            ha='center', va='center',
                            fontweight='bold', fontsize=9, color='white')
                # Segment À étudier
                if a > 0:
                    ax.text(i, r + e + a / 2, str(a),
                            ha='center', va='center',
                            fontweight='bold', fontsize=9, color='white')
                # Total au-dessus de la barre
                total = r + e + a
                ax.text(i, total + 0.3, str(total),
                        ha='center', va='bottom',
                        fontweight='bold', fontsize=9, color='black')

            ax.set_xlabel('Domaines', fontsize=12, fontweight='bold')
            ax.set_ylabel('Nombre de demandes', fontsize=12, fontweight='bold')
            ax.set_title('Situation des demandes par domaine', fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(domaines, rotation=45, ha='right')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)

            fig.tight_layout()
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Aucune donnée disponible")
            no_data_label.setStyleSheet("font-size: 14px; color: #999;")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)

        self.tabs.addTab(tab, "🏢 Par domaine")

    def create_rapport_nature_tab(self):
        """Crée l'onglet rapport par nature"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        query = """
            SELECT 
                COALESCE(n.libelle_nature, 'Non défini') as nature,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            WHERE date(d.date_reception) BETWEEN ? AND ?
            GROUP BY n.libelle_nature
            ORDER BY nombre DESC
        """

        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        if results:
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)

            natures = [row[0][:30] for row in results]
            nombres = [row[1] for row in results]

            colors = plt.cm.Paired(range(len(natures)))
            bars = ax.barh(natures, nombres, color=colors)

            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2,
                        f'{int(width)}', ha='left', va='center', fontweight='bold')

            ax.set_xlabel('Nombre de demandes', fontsize=12, fontweight='bold')
            ax.set_title('Répartition par nature', fontsize=14, fontweight='bold')
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=0.3)

            fig.tight_layout()

            canvas = FigureCanvas(fig)
            # toolbar = NavigationToolbar(canvas, tab)

            # layout.addWidget(toolbar)
            layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Aucune donnée disponible")
            no_data_label.setStyleSheet("font-size: 14px; color: #999;")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)

        self.tabs.addTab(tab, "🔍 Par nature")

    def create_rapport_evolution_tab(self):
        """Crée l'onglet évolutions"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        query = """
            SELECT COALESCE(et.libelle_etat, 'Non défini') as etat, COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            WHERE date(d.date_reception) BETWEEN ? AND ?
            AND n.libelle_nature = 'Evolution'
            GROUP BY et.libelle_etat
            ORDER BY nombre DESC
        """
        results = self.data_manager.execute_query(query, (self.date_debut, self.date_fin))

        if results:
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)

            etats = [row[0] for row in results]
            nombres = [row[1] for row in results]
            total = sum(nombres)

            # Couleurs par état — Annulée en rouge
            colors = []
            for e in etats:
                if 'nnul' in e:          # Annulée / Annulé
                    colors.append('#F44336')
                elif 'Réalis' in e or 'Traité' in e or 'Traite' in e:
                    colors.append('#4CAF50')
                elif 'cours' in e:
                    colors.append('#2196F3')
                else:
                    colors.append('#FF9800')

            # autopct personnalisé : affiche % ET nombre
            def make_autopct(values):
                def autopct(pct):
                    absolute = round(pct / 100. * sum(values))
                    return f'{pct:.1f}%\n({absolute})'
                return autopct

            wedges, texts, autotexts = ax.pie(
                nombres,
                autopct=make_autopct(nombres),
                startangle=90,
                colors=colors,
                pctdistance=0.75
            )

            # Supprimer labels inline, utiliser légende externe
            for text in texts:
                text.set_text('')

            # Style des pourcentages + nombres
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)

            # Légende externe avec état + nombre
            ax.legend(
                wedges,
                [f"{e} ({n})" for e, n in zip(etats, nombres)],
                loc='upper left',
                bbox_to_anchor=(-0.25, 1.0),
                fontsize=9,
                framealpha=0.8
            )

            ax.set_title('État des évolutions demandées', fontsize=14, fontweight='bold')
            fig.tight_layout(pad=2.0)

            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Aucune évolution trouvée pour cette période")
            no_data_label.setStyleSheet("font-size: 14px; color: #999;")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)

        self.tabs.addTab(tab, "📈 Évolutions")

    def create_rapport_metriques_tab(self):
        """Crée l'onglet métriques de délais"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # REQUÊTE 1 : Stats globales (calcul central : voir get_metriques_periode)
        metriques = self.data_manager.get_metriques_periode(self.date_debut, self.date_fin)

        # REQUÊTE 2 : Délais par domaine — alignée sur le même critère (état)
        query_domaine = """
            SELECT
                COALESCE(dom.libelle_domaine, 'Non défini') as domaine,
                COUNT(*) as nombre,
                ROUND(AVG(
                    CASE WHEN d.date_traitement IS NOT NULL
                         AND julianday(d.date_traitement) >= julianday(d.date_reception)
                    THEN julianday(d.date_traitement) - julianday(d.date_reception)
                    ELSE NULL END
                ), 1) as delai_moyen
            FROM demandes d
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            WHERE date(d.date_reception) BETWEEN ? AND ?
              AND (et.libelle_etat LIKE 'Trait%' OR et.libelle_etat LIKE 'Ferm%')
            GROUP BY dom.libelle_domaine
            ORDER BY nombre DESC
        """
        results = self.data_manager.execute_query(query_domaine, (self.date_debut, self.date_fin))

        # REQUÊTE 3 : Distribution des délais — alignée sur le même critère (état)
        query_distrib = """
            SELECT
            COALESCE(
                MAX(
                    CAST(julianday(d.date_traitement) - julianday(d.date_reception) AS INTEGER),
                    0
                ),
                0
            ) as delai_jours
        FROM demandes d
        LEFT JOIN etats et ON d.id_etat = et.id_etat
        WHERE date(d.date_reception) BETWEEN ? AND ?
          AND (et.libelle_etat LIKE 'Trait%' OR et.libelle_etat LIKE 'Ferm%')
        """
        distrib = self.data_manager.execute_query(query_distrib, (self.date_debut, self.date_fin))

        if metriques and results:
            total        = metriques['total']
            delai_moy    = metriques['delai_moyen'] if metriques['delai_moyen'] is not None else 0
            nb_realisees = metriques['realisees']

            fig = Figure(figsize=(14, 8))

            # --- KPIs ---
            ax1 = fig.add_subplot(2, 2, 1)
            ax1.axis('off')
            kpi_text  = "INDICATEURS CLÉS\n\n"
            kpi_text += f"Total demandes : {total}\n"
            kpi_text += f"Demandes réalisées : {nb_realisees}\n"
            kpi_text += f"Demandes en cours : {metriques['en_cours']}\n"
            if total > 0:
                kpi_text += f"Taux de réalisation : {nb_realisees / total * 100:.1f}%\n"
            else:
                kpi_text += "Taux de réalisation : 0%\n"
            kpi_text += f"Délai moyen : {delai_moy:.1f} jours" if delai_moy > 0 else "Délai moyen : N/A"
            ax1.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=13,
                     bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.8))
            ax1.text(0.5, 0.0, f"Hors calcul : demandes annulées, archivées, hors assistance ou non applicables "
                               f"({metriques['hors_calcul']})",
                     ha='center', va='bottom', fontsize=8, color='#64748B', wrap=True)
            ax1.set_title('Indicateurs', fontsize=12, fontweight='bold')

            # --- Délais par domaine ---
            ax2 = fig.add_subplot(2, 2, (2, 4))
            domaines = [row[0][:30] for row in results]
            nombres  = [row[1] for row in results]
            delais   = [row[2] if row[2] is not None else 0 for row in results]
            colors   = ['#F44336' if d > 15 else '#FF9800' if d > 7 else '#4CAF50' for d in delais]
            bars = ax2.barh(domaines, delais, color=colors)
            if delai_moy > 0:
                ax2.axvline(x=delai_moy, color='red', linestyle='--', linewidth=2,
                            label=f'Délai moyen {delai_moy:.1f}j')
            for bar, delai, nb in zip(bars, delais, nombres):
                width = bar.get_width()
                ax2.text(max(width + 0.2, 0.3),
                         bar.get_y() + bar.get_height() / 2,
                         f'{delai:.1f}j  ({nb} dem.)',
                         ha='left', va='center', fontweight='bold', fontsize=9)
            ax2.set_xlabel('Délai moyen (jours)', fontsize=12, fontweight='bold')
            ax2.set_title('Délais moyens de traitement par domaine', fontsize=14, fontweight='bold')
            ax2.invert_yaxis()
            ax2.legend()
            ax2.grid(axis='x', alpha=0.3)

            # --- Distribution des délais ---
            ax3 = fig.add_subplot(2, 2, 3)
            if distrib:
                delais_list = [row[0] if row[0] is not None else 0 for row in distrib]
                if delais_list:
                    n_bins = min(20, len(set(delais_list)))
                    counts, bins, patches = ax3.hist(
                        delais_list, bins=n_bins,
                        color='#2196F3', alpha=0.7, edgecolor='black'
                    )
                    for count, patch in zip(counts, patches):
                        if count > 0:
                            ax3.text(
                                patch.get_x() + patch.get_width() / 2,
                                patch.get_height() + 0.1,
                                str(int(count)),
                                ha='center', va='bottom',
                                fontsize=8, fontweight='bold', color='#1565C0'
                            )
                    ax3.set_xlabel('Délai (jours)', fontsize=10)
                    ax3.set_ylabel('Nombre de demandes', fontsize=10)
                    ax3.set_title(f'Distribution des délais ({len(delais_list)} demandes traitées)',
                                  fontsize=12, fontweight='bold')
                    ax3.grid(axis='y', alpha=0.3)

            fig.tight_layout()
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
        else:
            no_data_label = QLabel("Données insuffisantes pour calculer les métriques")
            no_data_label.setStyleSheet("font-size: 14px; color: #999;")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)

        self.tabs.addTab(tab, "Métriques")
