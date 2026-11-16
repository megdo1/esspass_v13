# ES-PASS

Application de bureau **Windows** de suivi des demandes d'assistance PIGC et des données OA/OT (SNCF Réseau).

**Version : 1.3.0**

## Fonctionnalités

- **Demandes** : liste filtrable et triable, création, modification, duplication, traitement et archivage (unitaires ou en masse), détail d'une demande par double-clic (contenu du mail, liens, pièces jointes).
- **Collecte** des mails depuis un dossier Outlook, rattachement aux demandes existantes (fils de discussion).
- **Rapports** : catégories, domaines, natures, évolutions, métriques (délais, taux de réalisation), COPIL ; export Excel et PDF.
- **Indicateurs** OA / OT : import de fichiers, vérification, calcul, graphiques et exports (SAR, Préconisations, Visites cycliques, Indicateurs OA).
- **Configuration** : base de données, dossier Outlook et pièces jointes, colonnes du tableau, et **gestion des listes de valeurs** (canaux, domaines, catégories, sous-catégories, natures) réservée aux administrateurs.
- **Rôles** : Consultant, Membre MCO, Administrateur (droits appliqués sur les boutons et les écrans).

## Prérequis

- Windows
- Microsoft Outlook installé et ouvert (identification de l'utilisateur et collecte des mails via COM)
- Python 3.9 ou supérieur (développé et testé avec 3.11)
- Accès à la base SQLite de l'application (fichier `.db`, éventuellement sur un partage réseau)

## Installation

```bash
git clone https://github.com/megdo1/esspass_v13.git
cd esspass_v13
pip install -r requirements.txt
```

## Configuration

L'application lit `config/config.json`, **non versionné** car propre à chaque poste. Copiez le modèle puis renseignez le chemin de la base :

```bash
copy config\config.example.json config\config.json
```

```json
{
  "sqlite_path": "//serveur/partage/chemin/vers/ES_PASS.db"
}
```

Les autres paramètres (dossier Outlook, dossier des pièces jointes, nombre de jours de collecte, limite d'affichage) se règlent depuis l'écran **Configuration** de l'application.

## Lancement

```bash
python main.py
```

Fichiers créés par l'application :

| Fichier | Contenu |
|---|---|
| `%APPDATA%\ES-PIGC\app.log` | Journal de fonctionnement (rotation automatique) |
| `%LOCALAPPDATA%\ES-PIGC\matplotlib` | Cache des graphiques |

## Structure

```
main.py                    Point d'entrée
app/
  data/                    Accès à la base (DataManager) et mixins par domaine
  views/                   Écrans (Demandes, Référentiels, Configuration, Utilisateurs, indicateurs…)
  views/pass_v3/           Dialogues et composants de l'écran Demandes
  mainwindow/              Fenêtre principale et navigation
  logic/ · export/         Calculs d'indicateurs et exports Excel
  styles/                  Thème (style.css) et icônes
  utils/                   Droits, chemins, journalisation
config/                    Configuration locale (modèle fourni)
ressources/                Icônes et images
```

## Base de données

- SQLite utilisé sur **partage réseau** : pas de mode WAL, écritures sécurisées (`synchronous=FULL`) et délai d'attente de 15 s en cas d'accès simultané.
- Le programme ne modifie pas la structure de la base : aucune migration n'est appliquée au démarrage.
- Les états des demandes, les impacts et les urgences sont fixés par l'application (libellés utilisés par le calcul de priorité et les rapports).

## Packaging

Génération d'un exécutable avec PyInstaller (`pip install pyinstaller`). Veillez à inclure dans le build les ressources non Python : `app/styles/` (feuille de style et icônes) et `ressources/`.

## Données sensibles

Ne versionnez jamais `config/config.json`, les bases `.db`, les dossiers de sauvegarde, les rapports exportés ni les captures d'écran de production (voir `.gitignore`).

## Limites connues

- Les modèles Excel d'export des indicateurs (`ressources/modeles/`) ne sont pas fournis dans ce dépôt.
- Pas de tests automatisés pour le moment.

## Licence

Non définie (tous droits réservés par défaut).
