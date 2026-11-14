# ES-PASS — mémoire de projet (CLAUDE.md)

Application de bureau **Windows** de suivi des demandes d'assistance PIGC (SNCF Réseau).
Version courante : **1.3.0** (`app/version.py`, source unique du numéro de version).

## Stack et lancement
- Python 3, **PyQt5**, **SQLite sur partage réseau**, **Outlook via COM** (`pywin32`), pandas, matplotlib, openpyxl.
- Lancer : `python main.py` (Outlook doit être ouvert : l'identité de l'utilisateur et la collecte des mails en dépendent).
- Dépendances : `requirements.txt`. Packaging : PyInstaller (non versionné : `*.spec` ignoré).
- Configuration : `config/config.json` (clé `sqlite_path`) — **non versionné**, copier `config/config.example.json`.
  Le chemin est cherché dans le dossier courant, puis le dossier de l'application ; les `\` bruts sont tolérés.

## Architecture (`app/`)
| Dossier / fichier | Rôle |
|---|---|
| `data/data_manager.py` | `DataManager` : connexion SQLite, exécution des requêtes, cache des listes. Le reste est dans `data/mixins/` |
| `data/mixins/` | `config`, `referentiels` (chargement des listes), `referentiels_admin` (CRUD des listes), `users`, `demandes`, `collecte` (mails Outlook), `stats` (indicateurs) |
| `views/pass_view_v3.py` | Écran **Demandes** (`PassViewClean`) : assemble les mixins de `views/pass_v3/` (layout, table, filtres, actions, permissions, export) |
| `views/pass_v3/` | Dialogues (création, modification, duplication, détail du mail, traitement en masse, rapports) et mixins de l'écran Demandes |
| `views/referentiels_tab.py` | Onglet **Référentiels** de la Configuration (administrateur) |
| `views/pass_parametrage_view.py` | Écran Configuration (onglets Général, Colonnes, Référentiels) |
| `views/common_view_mixins.py` + `*_view.py` | Vues d'import de fichiers (Indicateurs OA, Préconisations, SAR, Visites) et leurs méthodes communes |
| `mainwindow/`, `ui_mainwindow_v3.py` | Fenêtre principale, navigation latérale, traitement des fichiers |
| `logic/`, `export/`, `es_workers/` | Calculs d'indicateurs, exports Excel, threads de travail |
| `styles/style.css` | **Thème global** (palette documentée en tête) ; `styles/icons/` icônes du thème |
| `utils/` | `auth.py` (rôles/permissions), `paths.py`, `logging_setup.py`, `mpl_cache.py`, `ui_helpers.py` |

## Règles de données (SQLite réseau)
- **Pas de WAL, pas de `mmap`** (partage réseau). `_get_connection` : `synchronous=FULL`, `busy_timeout=15000`, `journal_mode=DELETE`.
- Le schéma n'est **pas migré par le code** (aucun `ALTER/CREATE`). Les tables de référence ont une colonne `actif`.
- Les triggers SQL `calculate_priority_on_*` calculent la priorité P1–P4 avec les **libellés** `Faible/Moyen/Élevé` des impacts/urgences.
- Les listes sont **chargées au démarrage par instance** de `DataManager` ; `DataManager._instances` + `refresh_reference_data_all()` rafraîchissent le processus (pas les autres postes).
- Sous-catégories : le cache par catégorie est `sous_categories_ids_by_categorie` (le libellé seul est ambigu : plusieurs catégories partagent des noms).

## Règles métier à ne pas casser
- **États / impacts / urgences : lecture seule.** Libellés utilisés en dur par le workflow, les rapports et les triggers.
- Valeurs protégées : canal `CRP`, domaines `OA`/`OT`, natures `Anomalie`/`Evolution`.
- Référentiels : suppression physique seulement si 0 demande ; sinon désactivation ou « réaffecter puis supprimer ». Une valeur désactivée doit rester sélectionnée sur une ancienne demande (`ensure_combo_has_value`).
- **Indicateurs de période** (`StatsMixin.get_metriques_periode`, utilisé par l'onglet Métriques ET l'export Excel) :
  réalisées = Traitée + Fermée ; en cours = À étudier + En cours de traitement ; **hors calcul** = Archivée, Annulée, Hors assistance, Non applicable (exclus du total, du taux et du délai).
  Les autres onglets de rapports comptent toujours toutes les demandes.
- Rôles (`utils/auth.py`) : Consultant, Membre MCO, Administrateur. L'onglet Référentiels exige la permission `gerer_listes` (Administrateur) et le DataManager la revérifie.
- **Identité** : l'utilisateur est retrouvé par **e-mail** (Outlook peut renvoyer nom/prénom vides). Ne pas réintroduire de noms en dur.
- Le texte des boutons sert de **clé logique** dans plusieurs écrans (`text == "…"`) : ne pas le modifier.

## Interface et pièges
- Ne **jamais retrouver un widget par son style ou son titre** (ex. `"font-size: 48px" in styleSheet()`) : changer un style casse silencieusement le rafraîchissement. Utiliser des références explicites (`kpi_value_labels`, `info_user_labels`, `info_collecte_labels`).
- QSS : `border` sur `QTableWidget::item` casse le retour à la ligne ; le triangle en bordures d'une `QComboBox` s'affiche comme un trait (utiliser une image) ; `QGroupBox::title` en `subcontrol-origin: padding`.
- Les `url()` des icônes du thème sont résolus en absolu dans `MainWindow.initUI` (indépendant du dossier courant).
- Préférer une fenêtre dédiée à `QMessageBox` quand les boutons ont des libellés longs (`SuppressionDialog`).
- `app/views/pass_v3/mail_dialog.py` : le contenu d'un mail est le **HTML intégral** de `echanges_emails.contenu` ; les images `cid:` sont dans le dossier `pj_path` **propre à chaque utilisateur** ; liens ouverts uniquement en `http/https/mailto`.
- Écran Demandes : double-clic sur une ligne = détail (`on_demande_double_clic`, même méthode que le bouton 👁).
- Export des rapports : le cache matplotlib est `%LOCALAPPDATA%\ES-PIGC\matplotlib` (fixé dans `main.py` avant tout import) pour éviter l'erreur de dossier temporaire supprimé.

## Travailler sur ce projet
- Windows + PowerShell/Git Bash. Lancer les scripts Python avec **`python -X utf8`** (sinon accents/emojis cassés en console redirigée).
- Rendu hors-écran pour vérifier l'UI : `QT_QPA_PLATFORM=offscreen` **et** `QT_QPA_FONTDIR=C:/Windows/Fonts` (sinon aucun texte). Les `QMessageBox` modales plantent en offscreen.
- Méthode de modification sans régression utilisée jusqu'ici : copie de travail, comparaison avant/après (AST, bytecode des méthodes, instantané sémantique de l'écran), tests sur **copie** de la base ; ne jamais écrire dans la base de production ni modifier `config.json` dans un test.
- Les outils de vérification utilisés (hors dépôt) : banc d'instanciation Qt hors-écran, sondes de bytecode via le MRO, tests de `DataManager` sur copie de base. À réintégrer sous `tests/` si on veut une CI.
- Modèles Excel attendus dans `ressources/modeles/` (référencés par `app/ressources.py`, **non versionnés**).
- Code supprimé ou remplacé : conservé hors dépôt dans `_archive/` (ignoré).

## Données sensibles — ne pas committer
`config/config.json`, `*.db`, `sauvegardes/`, rapports exportés (`rapport_PASS_*`), captures d'écran du client (`annomalie/*.png`).

## Journal des versions
### 1.3.0
- **Anomalies corrigées** : erreur critique à l'export COPIL (cache matplotlib temporaire) ; écarts des indicateurs (statuts exclus + export Excel aligné sur l'écran) ; date de traitement saisissable à la création ; liens des mails cliquables (un clic vidait le contenu) et boutons-images invisibles remplacés par un libellé ; sous-catégories homonymes enregistrées dans la mauvaise catégorie ; valeur désactivée effacée à l'enregistrement.
- **Évolutions** : onglet Référentiels (CRUD des listes, droits administrateur) ; écran Demandes compact (tableau ≈ 4 → 14 lignes visibles) ; double-clic pour le détail ; nouvelle charte graphique ; Métriques avec « Demandes en cours » et mention « Hors calcul » ; fiabilisation de la base partagée, journal `%APPDATA%\ES-PIGC\app.log`, découpage du code en mixins.
- Aucun changement de schéma de base. Détail des livrables : `annomalie/reponses_et_correctifs/` (mail de livraison, requêtes SQL de rattrapage).

## Pistes ouvertes
- Date de réception modifiable à la création d'une demande.
- Étendre l'exclusion des statuts aux autres onglets de rapports.
- Ordre d'affichage personnalisable des valeurs des listes.
- Tests automatiques (`DataManager`, `logic_*`) et CI ; dédoublonnage plus poussé des 4 vues d'import (classe de base à hooks).
- `get_mes_demandes` (`StatsMixin`) affecte un dictionnaire à `id_utilisateur` : bug probable à valider.
- En-tête du détail d'un mail (`MailDetailsDialog`) : la « Date de réception » lit la clé `datereception` au lieu de `date_reception` et affiche toujours « NA ».
- `AppUserModelID` Windows (`main.py`) volontairement inchangé (épinglage de la barre des tâches).
