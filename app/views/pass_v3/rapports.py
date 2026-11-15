"""Dialogues de génération et de visualisation des rapports."""

from PyQt5.QtWidgets import QWidget, QGroupBox, QComboBox, QTabWidget
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QDialog, QLabel
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from app.utils.decorators import busy_cursor_no_args
from app.utils.mpl_cache import ensure_mpl_cache_dir
from app.utils.ui_helpers import show_info, show_warning
from app.views.pass_v3.rapport_tabs_mixin import RapportTabsMixin
from app.views.pass_v3.rapport_export_mixin import RapportExportMixin
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE RAPPORTCOPILVIEWERDIALOG - Rapport COPIL
# ============================================================================
class RapportCOPILViewerDialog(QDialog):
    """Dialogue pour visualiser le rapport COPIL"""
    
    def __init__(self, datamanager, selected_trimestres, parent=None):
        super().__init__(parent)
        self.datamanager = datamanager
        self.selected_trimestres = selected_trimestres
        
        # Titre de la fenêtre
        trim_labels = [f"T{t['q']}/{t['year']}" for t in selected_trimestres]
        titre = " + ".join(trim_labels) if len(trim_labels) <= 3 else f"{len(trim_labels)} trimestres"
        
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(f"Rapport COPIL - {titre}")
        self.setMinimumSize(1400, 900)
        
        self.initui()
        self.generate_reports()
    
    def initui(self):
        mainlayout = QVBoxLayout(self)
        
        # Titre avec période
        trim_labels = [f"T{t['q']} {t['year']}" for t in self.selected_trimestres]
        titre_periode = " + ".join(trim_labels)
        
        titlelabel = QLabel(f"TENDANCE DE L'ASSISTANCE PIGC\n{titre_periode}")
        titlelabel.setStyleSheet("font-size: 16px; font-weight: bold; color: #475569; padding: 10px;")
        titlelabel.setAlignment(Qt.AlignCenter)
        mainlayout.addWidget(titlelabel)
        
        # Zone de graphiques avec scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scrollcontent = QWidget()
        self.scrolllayout = QVBoxLayout(scrollcontent)
        scroll.setWidget(scrollcontent)
        mainlayout.addWidget(scroll)
        
        # Boutons d'export
        buttonslayout = QHBoxLayout()
        buttonslayout.addStretch()
        
        btnexportexcel = QPushButton("📊 Exporter en Excel")
        btnexportexcel.setStyleSheet("padding: 10px 20px; background: #2F855A; color: white; font-weight: bold;")
        btnexportexcel.clicked.connect(self.export_excel)
        buttonslayout.addWidget(btnexportexcel)
        
        btnexportpdf = QPushButton("📄 Exporter en PDF")
        btnexportpdf.setStyleSheet("padding: 10px 20px; background: #1F4E9C; color: white; font-weight: bold;")
        btnexportpdf.clicked.connect(self.export_pdf)
        buttonslayout.addWidget(btnexportpdf)
        
        btnclose = QPushButton("❌ Fermer")
        btnclose.setStyleSheet("padding: 10px 20px;")
        btnclose.clicked.connect(self.close)
        buttonslayout.addWidget(btnclose)
        
        mainlayout.addLayout(buttonslayout)
    
    @busy_cursor_no_args
    def generate_reports(self):
        """Génère tous les graphiques du rapport COPIL"""
        ensure_mpl_cache_dir()
        # Créer une grande figure avec 4 sous-graphiques
        fig = Figure(figsize=(16, 10))
        
        # 1. Catégories d'assistance (graphique en barres vertical)
        ax1 = fig.add_subplot(2, 3, 1)
        self.create_categories_chart(ax1)
        
        # 2. Répartition mensuelle (graphique en barres)
        ax2 = fig.add_subplot(2, 3, 2)
        self.create_monthly_distribution(ax2)
        
        # 3. Anomalies / Évolutions (camembert)
        ax3 = fig.add_subplot(2, 3, 3)
        self.create_anomalies_evolutions_pie(ax3)
        
        # 4. Répartition par domaine (camembert)
        ax4 = fig.add_subplot(2, 1, 2)
        self.create_domaines_pie(ax4)
        
        fig.tight_layout()
        fig.subplots_adjust(right=0.85)
        canvas = FigureCanvas(fig)
        self.scrolllayout.addWidget(canvas)
    
    def get_date_range_for_trimestres(self):
        """Calcule la plage de dates pour les trimestres sélectionnés"""
        date_ranges = []
        for trim in self.selected_trimestres:
            year = trim["year"]
            q = trim["q"]
            
            if q == 1:
                start = f"{year}-01-01"
                end = f"{year}-03-31"
            elif q == 2:
                start = f"{year}-04-01"
                end = f"{year}-06-30"
            elif q == 3:
                start = f"{year}-07-01"
                end = f"{year}-09-30"
            else:  # q == 4
                start = f"{year}-10-01"
                end = f"{year}-12-31"
            
            date_ranges.append((start, end))
        
        return date_ranges
    
    def create_categories_chart(self, ax):
        """Graphique des catégories d'assistance — barres verticales colorées comme le modèle COPIL"""
        date_ranges = self.get_date_range_for_trimestres()

        query = """
            SELECT
                COALESCE(cat.libelle_categorie, 'Non définie') as categorie,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            WHERE """ + " OR ".join([
                f"(date(d.date_reception) BETWEEN '{start}' AND '{end}')"
                for start, end in date_ranges
            ]) + """
            GROUP BY cat.libelle_categorie
            ORDER BY nombre DESC
        """

        results = self.datamanager.execute_query(query)

        if results:
            categories = [row[0][:25] for row in results]
            nombres    = [row[1] for row in results]

            # Palette de couleurs variées comme le modèle de référence
            palette = [
                '#4472C4', '#ED7D31', '#A9D18E', '#FFC000', '#5B9BD5',
                '#70AD47', '#FF0000', '#002060', '#92D050', '#0070C0',
                '#7030A0', '#C00000', '#FF6600', '#00B050', '#843C0C'
            ]
            colors = [palette[i % len(palette)] for i in range(len(categories))]

            bars = ax.bar(range(len(categories)), nombres, color=colors,
                          alpha=0.85, edgecolor='white', linewidth=0.5)

            # Valeur au-dessus de chaque barre
            for bar, nombre in zip(bars, nombres):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,
                        str(nombre),
                        ha='center', va='bottom',
                        fontweight='bold', fontsize=8)

            # Labels en dessous des barres, inclinés comme le modèle
            ax.set_xticks(range(len(categories)))
            ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=7)

            trim_labels = " + ".join([f"T{t['q']}/{t['year']}" for t in self.selected_trimestres])
            ax.set_title(f"Catégories d'assistance\n{trim_labels}",
                         fontsize=11, fontweight='bold')
            ax.set_ylabel('Nombre de demandes', fontsize=9)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

    
    def create_monthly_distribution(self, ax):
        """Répartition mensuelle (barres verticales colorées)"""
        date_ranges = self.get_date_range_for_trimestres()
        
        query = """
            SELECT 
                strftime('%Y-%m', d.date_reception) as mois,
                COUNT(*) as nombre
            FROM demandes d
            WHERE """ + " OR ".join([f"(date(d.date_reception) BETWEEN '{start}' AND '{end}')" 
                                     for start, end in date_ranges]) + """
            GROUP BY mois
            ORDER BY mois
        """
        
        results = self.datamanager.execute_query(query)
        
        if results:
            mois_labels = []
            nombres = []
            for row in results:
                year_month = row[0]
                year, month = year_month.split('-')
                mois_names = ['Janv', 'Fév', 'Mars', 'Avr', 'Mai', 'Juin', 
                              'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
                mois_label = mois_names[int(month) - 1]
                mois_labels.append(mois_label)
                nombres.append(row[1])
            
            # Couleurs variées pour chaque mois
            colors = ['#2196F3', '#FFC107', '#4CAF50', '#9C27B0', '#FF9800', '#00BCD4',
                      '#E91E63', '#FF5722', '#8BC34A', '#795548', '#CDDC39', '#607D8B']
            colors = colors[:len(mois_labels)]
            
            bars = ax.bar(mois_labels, nombres, color=colors, alpha=0.7, edgecolor='black')
            
            # Afficher les valeurs
            for bar, nombre in zip(bars, nombres):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height + 1,
                        str(nombre), ha='center', va='bottom', fontweight='bold', fontsize=9)
            
            ax.set_ylabel('Nombre de demandes', fontsize=10)
            ax.set_title('Répartition mensuelle', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
    
    def create_anomalies_evolutions_pie(self, ax):
        """Camembert Anomalies / Évolutions avec nombre affiché"""
        date_ranges = self.get_date_range_for_trimestres()

        query = """
            SELECT
                CASE
                    WHEN nat.libelle_nature LIKE '%volution%' OR nat.libelle_nature LIKE '%Evolution%' THEN 'Évolutions'
                    ELSE 'Anomalies'
                END as type,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN natures nat ON d.id_nature = nat.id_nature
            WHERE """ + " OR ".join([
                f"(date(d.date_reception) BETWEEN '{start}' AND '{end}')"
                for start, end in date_ranges
            ]) + """
            AND nat.libelle_nature in ('Anomalie','Evolution')
            GROUP BY type
        """

        results = self.datamanager.execute_query(query)

        if not results:
            ax.text(0.5, 0.5, 'Aucune donnée', ha='center', va='center',
                    transform=ax.transAxes, fontsize=12)
            return

        labels = [row[0] for row in results]
        sizes  = [row[1] for row in results]
        total  = sum(sizes)
        colors = ['#2196F3', '#F44336']

        # Label avec nom + nombre + pourcentage
        labels_avec_nb = [f"{row[0]}\n({row[1]})" for row in results]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels_avec_nb,
            autopct=lambda pct: f'{pct:.0f}%',
            colors=colors,
            startangle=90,
            pctdistance=0.6,
            textprops={'fontsize': 11, 'fontweight': 'bold'}
        )

        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_fontsize(12)
            autotext.set_color('white')

        for text in texts:
            text.set_fontsize(10)
            text.set_fontweight('bold')

        ax.set_title('Anomalies / Évolutions', fontsize=12, fontweight='bold')

        # Légende avec total
        ax.legend(
            [f"{row[0]} : {row[1]} ({row[1]/total*100:.0f}%)" for row in results],
            loc='lower center',
            bbox_to_anchor=(0.5, -0.15),
            fontsize=9,
            frameon=True
        )

    
        
    def create_domaines_pie(self, ax):
        """Camembert de répartition par domaine avec regroupement 'Autres' pour les petites portions"""
        date_ranges = self.get_date_range_for_trimestres()

        query = """
            SELECT
                COALESCE(dom.libelle_domaine, 'Non défini') as domaine,
                COUNT(*) as nombre
            FROM demandes d
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            WHERE """ + " OR ".join([
                f"(date(d.date_reception) BETWEEN '{start}' AND '{end}')"
                for start, end in date_ranges
            ]) + """
            GROUP BY dom.libelle_domaine
            ORDER BY nombre DESC
        """

        results = self.datamanager.execute_query(query)

        if not results:
            ax.text(0.5, 0.5, 'Aucune donnée', ha='center', va='center',
                    transform=ax.transAxes, fontsize=12)
            return

        total = sum(row[1] for row in results)

        # Seuil : regrouper les portions < 3% dans "Autres"
        seuil = 0.03
        principales = []
        autres_total = 0

        for row in results:
            domaine, nombre = row[0], row[1]
            if nombre / total >= seuil:
                principales.append((domaine, nombre))
            else:
                autres_total += nombre

        if autres_total > 0:
            principales.append(('Autres', autres_total))

        labels = [f"{row[0]}\n({row[1]})" for row in principales]
        sizes  = [row[1] for row in principales]

        # Palette de couleurs
        palette = [
            '#4472C4', '#ED7D31', '#A9D18E', '#FFC000', '#5B9BD5',
            '#70AD47', '#FF0000', '#002060', '#92D050', '#BFBFBF'
        ]
        colors = [palette[i % len(palette)] for i in range(len(sizes))]
        # "Autres" toujours en gris
        if autres_total > 0:
            colors[-1] = '#BFBFBF'

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct=lambda pct: f'{pct:.0f}%' if pct >= 3 else '',
            colors=colors,
            startangle=140,
            pctdistance=0.75,
            textprops={'fontsize': 9}
        )

        # Style des pourcentages
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)

        # Style des labels
        for text in texts:
            text.set_fontsize(8)

        ax.set_title('Répartition par domaine', fontsize=14, fontweight='bold')

        # Légende détaillée pour "Autres" si présent
        if autres_total > 0:
            autres_details = [
                (row[0], row[1])
                for row in results
                if row[1] / total < seuil
            ]
            detail_lines = [f"  • {dom} : {nb}" for dom, nb in autres_details]
            detail_text = f"Autres ({autres_total}) :\n" + "\n".join(detail_lines)

            ax.text(
                1.05, 0.0,
                detail_text,
                transform=ax.transAxes,
                fontsize=7.5,
                verticalalignment='bottom',
                bbox=dict(
                    boxstyle='round,pad=0.4',
                    facecolor='#F5F5F5',
                    edgecolor='#BFBFBF',
                    alpha=0.9
                )
            )

    
    def export_excel(self):
        """Export des données en Excel"""
        show_info(self, "Export Excel", "Fonctionnalité d'export Excel à implémenter")
    
    def export_pdf(self):
        """Export en PDF"""
        show_info(self, "Export PDF", "Fonctionnalité d'export PDF à implémenter")


class RapportViewerDialog(RapportTabsMixin, RapportExportMixin, QDialog):
    """Dialogue pour visualiser les rapports avec matplotlib"""

    def __init__(self, data_manager, periode_text, date_debut, date_fin, rapports_selectionnes, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.periode_text = periode_text
        self.date_debut = date_debut
        self.date_fin = date_fin
        self.rapports_selectionnes = rapports_selectionnes

        # ✅ AJOUTER ces lignes pour permettre agrandir/réduire/maximiser
        self.setWindowFlags(
            Qt.Window |  # Fenêtre indépendante
            Qt.WindowMinimizeButtonHint |  # Bouton réduire
            Qt.WindowMaximizeButtonHint |  # Bouton maximiser
            Qt.WindowCloseButtonHint  # Bouton fermer
        )

        self.setWindowTitle(f"📊 Rapports PASS - {periode_text}")
        self.setMinimumSize(1200, 800)


        self.init_ui()
        self.generate_reports()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Titre
        title_label = QLabel(f"📊 Rapports et Statistiques - {self.periode_text}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #475569; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        from datetime import datetime
        # Convertir les dates du format YYYY-MM-DD vers DD/MM/YYYY
        date_debut_format = datetime.strptime(self.date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')
        date_fin_format = datetime.strptime(self.date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
        # Sous-titre avec période
        period_label = QLabel(f"Période du {date_debut_format} au {date_fin_format}")

        # period_label = QLabel(f"Période : du {self.date_debut} au {self.date_fin}")
        period_label.setStyleSheet("font-size: 12px; color: #666; padding: 5px;")
        period_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(period_label)

        # Onglets pour chaque type de rapport
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        btn_export_excel = QPushButton("📊 Exporter en Excel")
        btn_export_excel.setStyleSheet("background: #2F855A; color: white; font-weight: bold; padding: 10px 20px;")
        btn_export_excel.clicked.connect(self.export_to_excel)
        buttons_layout.addWidget(btn_export_excel)

        btn_export_pdf = QPushButton("📄 Exporter en PDF")
        btn_export_pdf.setStyleSheet("background: #1F4E9C; color: white; font-weight: bold; padding: 10px 20px;")
        btn_export_pdf.clicked.connect(self.export_to_pdf)
        buttons_layout.addWidget(btn_export_pdf)

        buttons_layout.addStretch()

        btn_close = QPushButton("❌ Fermer")
        btn_close.setStyleSheet("padding: 10px 20px;")
        btn_close.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_close)

        main_layout.addLayout(buttons_layout)

    @busy_cursor_no_args
    def generate_reports(self):
        """Génère tous les rapports sélectionnés"""
        ensure_mpl_cache_dir()
        erreurs_avant = self.data_manager.error_count
        if self.rapports_selectionnes.get('categorie'):
            self.create_rapport_categorie_tab()
            self.create_rapport_sous_categorie_tab()   # toujours lié à catégorie
        if self.rapports_selectionnes.get('domaine'):
            self.create_rapport_domaine_tab()
        if self.rapports_selectionnes.get('nature'):
            self.create_rapport_nature_tab()
        if self.rapports_selectionnes.get('evolution'):
            self.create_rapport_evolution_tab()
        if self.rapports_selectionnes.get('metriques'):
            self.create_rapport_metriques_tab()
        if self.rapports_selectionnes.get('copil'):
            self.create_rapport_copil_tab()

        if self.data_manager.error_count > erreurs_avant:
            show_warning(self, "Données incomplètes",
                         "Une erreur d'accès à la base est survenue pendant la génération : certains "
                         "rapports peuvent être vides ou incomplets.\n\n"
                         f"{self.data_manager.last_error}")


    def _copil_refresh_charts(self, chartarea):
        ensure_mpl_cache_dir()
        """Régénère les graphiques COPIL"""
        selected_trimestres = [
            data for data, cb in self.copil_trim_checkboxes if cb.isChecked()
        ]

        old_widget = chartarea.widget()
        if old_widget:
            old_widget.deleteLater()

        content = QWidget()
        contentlayout = QVBoxLayout(content)
        chartarea.setWidget(content)

        if not selected_trimestres:
            label = QLabel("Veuillez sélectionner au moins un trimestre.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #999; font-size: 13px; padding: 40px;")
            contentlayout.addWidget(label)
            return

        selected_trimestres.sort(key=lambda x: (x['year'], x['q']))

        helper = RapportCOPILViewerDialog(self.data_manager, selected_trimestres, self)

        fig = Figure(figsize=(16, 10))
        ax1 = fig.add_subplot(2, 3, 1)
        ax2 = fig.add_subplot(2, 3, 2)
        ax3 = fig.add_subplot(2, 3, 3)
        ax4 = fig.add_subplot(2, 1, 2)

        helper.create_categories_chart(ax1)
        helper.create_monthly_distribution(ax2)
        helper.create_anomalies_evolutions_pie(ax3)
        helper.create_domaines_pie(ax4)

        fig.tight_layout()
        fig.subplots_adjust(right=0.85)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(700)
        contentlayout.addWidget(canvas)


class RapportsDialog(QDialog):
    """Dialogue pour générer des rapports statistiques"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setWindowTitle("📊 Génération de Rapports")
        self.setMinimumSize(900, 700)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Titre
        title_label = QLabel("📊 RAPPORTS ET STATISTIQUES")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #475569; padding: 15px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Zone de sélection de période
        period_group = QGroupBox("📅 Sélection de la période")
        period_group.setMinimumHeight(120)
        period_group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #475569; }")
        period_layout = QHBoxLayout()

        self.combo_periode = QComboBox()
        self.combo_periode.addItems([
            "Cette semaine",
            "Ce mois",
            "Ce trimestre",
            "Cette année",
            "Période personnalisée"
        ])
        self.combo_periode.currentTextChanged.connect(self.on_periode_changed)
        period_layout.addWidget(QLabel("Période :"))
        period_layout.addWidget(self.combo_periode)

        # Dates personnalisées (masquées par défaut)
        self.label_date_debut = QLabel("Du :")
        self.date_debut = QLineEdit()
        self.date_debut.setPlaceholderText("JJ/MM/AAAA")
        self.label_date_fin = QLabel("Au :")
        self.date_fin = QLineEdit()
        self.date_fin.setPlaceholderText("JJ/MM/AAAA")

        period_layout.addWidget(self.label_date_debut)
        period_layout.addWidget(self.date_debut)
        period_layout.addWidget(self.label_date_fin)
        period_layout.addWidget(self.date_fin)

        # Masquer par défaut
        self.label_date_debut.setVisible(False)
        self.date_debut.setVisible(False)
        self.label_date_fin.setVisible(False)
        self.date_fin.setVisible(False)

        period_layout.addStretch()
        period_group.setLayout(period_layout)
        main_layout.addWidget(period_group)

        # Zone de sélection des rapports
        reports_group = QGroupBox("📋 Types de rapports disponibles")
        reports_group.setMinimumHeight(300)
        reports_group.setStyleSheet(
            "QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; } QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }")
        reports_layout = QVBoxLayout()

        self.check_categorie = QCheckBox("📂 Situation des demandes par catégorie/sous-catégorie")
        self.check_domaine = QCheckBox("🏢 Situation des demandes par domaine")
        self.check_nature = QCheckBox("🔍 Répartition des demandes par natures confirmées")
        self.check_evolution = QCheckBox("📈 Situation des évolutions demandées par les utilisateurs")
        self.check_metriques = QCheckBox("⏱️ Métriques sur les délais de traitement et de prise en charge")
        # Séparateur
        separator = QLabel("─" * 50)
        separator.setStyleSheet("color: #CBD5E1; padding: 2px;")
        

        # Rapport COPIL — décoché par défaut
        self.check_copil = QCheckBox("📊 Rapport COPIL - Tendance de l'Assistance PIGC (par trimestre)")
        self.check_copil.setChecked(False)
        self.check_copil.setStyleSheet("font-weight: bold; color: #0F766E; padding: 4px;")
        

        
        # Cocher tous par défaut
        self.check_categorie.setChecked(True)
        self.check_domaine.setChecked(True)
        self.check_nature.setChecked(True)
        self.check_evolution.setChecked(True)
        self.check_metriques.setChecked(True)

        reports_layout.addWidget(self.check_categorie)
        reports_layout.addWidget(self.check_domaine)
        reports_layout.addWidget(self.check_nature)
        reports_layout.addWidget(self.check_evolution)
        reports_layout.addWidget(self.check_metriques)
        reports_layout.addWidget(separator)
        reports_layout.addWidget(self.check_copil)

        # Bouton tout sélectionner/désélectionner
        btn_toggle_layout = QHBoxLayout()
        btn_select_all = QPushButton("✅ Tout sélectionner")
        btn_select_all.clicked.connect(self.select_all)
        btn_deselect_all = QPushButton("❌ Tout désélectionner")
        btn_deselect_all.clicked.connect(self.deselect_all)
        btn_toggle_layout.addWidget(btn_select_all)
        btn_toggle_layout.addWidget(btn_deselect_all)
        btn_toggle_layout.addStretch()
        reports_layout.addLayout(btn_toggle_layout)

        reports_group.setLayout(reports_layout)
        main_layout.addWidget(reports_group)

        

        # Boutons d'action
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.setStyleSheet("padding: 10px 20px;")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("📊 Générer")
        btn_generate.setStyleSheet(
            "background: #2F855A; color: white; font-weight: bold; padding: 10px 30px; font-size: 13px;")
        btn_generate.clicked.connect(self.generate_report)
        buttons_layout.addWidget(btn_generate)

        main_layout.addLayout(buttons_layout)

    def on_periode_changed(self):
        """Affiche/masque les champs de dates personnalisées"""
        is_custom = self.combo_periode.currentText() == "Période personnalisée"
        self.label_date_debut.setVisible(is_custom)
        self.date_debut.setVisible(is_custom)
        self.label_date_fin.setVisible(is_custom)
        self.date_fin.setVisible(is_custom)

    def select_all(self):
        """Sélectionne tous les rapports"""
        self.check_categorie.setChecked(True)
        self.check_domaine.setChecked(True)
        self.check_nature.setChecked(True)
        self.check_evolution.setChecked(True)
        self.check_metriques.setChecked(True)
        self.check_copil.setChecked(True)

    def deselect_all(self):
        """Désélectionne tous les rapports"""
        self.check_categorie.setChecked(False)
        self.check_domaine.setChecked(False)
        self.check_nature.setChecked(False)
        self.check_evolution.setChecked(False)
        self.check_metriques.setChecked(False)
        self.check_copil.setChecked(False)

    def get_date_range(self):
        """Retourne la plage de dates selon la période sélectionnée"""
        from datetime import datetime, timedelta

        now = datetime.now()
        periode = self.combo_periode.currentText()

        if periode == "Cette semaine":
            start = now - timedelta(days=now.weekday())
            end = now
        elif periode == "Ce mois":
            start = now.replace(day=1)
            end = now
        elif periode == "Ce trimestre":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_start_month, day=1)
            end = now
        elif periode == "Cette année":
            start = now.replace(month=1, day=1)
            end = now
        elif periode == "Période personnalisée":
            try:
                start = datetime.strptime(self.date_debut.text(), '%d/%m/%Y')
                end = datetime.strptime(self.date_fin.text(), '%d/%m/%Y')
            except Exception:
                logger.debug("Exception ignorée dans get_date_range", exc_info=True)
                return None, None
        else:
            return None, None

        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    
    def generate_report(self):
        """Génère et affiche le rapport dans une nouvelle fenêtre"""
        if not any([
            self.check_categorie.isChecked(),
            self.check_domaine.isChecked(),
            self.check_nature.isChecked(),
            self.check_evolution.isChecked(),
            self.check_metriques.isChecked(),
            self.check_copil.isChecked()
        ]):
            show_warning(self, "Aucune sélection", "Veuillez sélectionner au moins un type de rapport.")
            return

        date_debut, date_fin = self.get_date_range()
        if not date_debut or not date_fin:
            show_warning(self, "Dates invalides", "Veuillez saisir des dates valides au format JJ/MM/AAAA.")
            return

        # Créer le dictionnaire des rapports sélectionnés
        rapports_selectionnes = {
            'categorie': self.check_categorie.isChecked(),
            'domaine': self.check_domaine.isChecked(),
            'nature': self.check_nature.isChecked(),
            'evolution': self.check_evolution.isChecked(),
            'metriques': self.check_metriques.isChecked(),
            'copil':      self.check_copil.isChecked()
        }
         
        # Ouvrir la fenêtre de visualisation
        viewer = RapportViewerDialog(
            self.data_manager,
            self.combo_periode.currentText(),
            date_debut,
            date_fin,
            rapports_selectionnes,
            self
        )
        viewer.exec_()
