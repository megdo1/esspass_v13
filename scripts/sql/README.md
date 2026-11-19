# Scripts de modification de la base de données

L'application **ne modifie jamais le schéma** de la base (aucun `CREATE`/`ALTER` dans le code) : les évolutions
de structure sont fournies ici, sous forme de scripts à exécuter **manuellement**, une fois, sur la base de
production.

| Script | Objet | Retour arrière |
|---|---|---|
| `001_utilisateur_responsable.sql` | Table `utilisateur_responsable` : liste des responsables ES-PASS, gérée depuis l'écran Utilisateurs | `001_utilisateur_responsable_rollback.sql` |

## Procédure

1. **Sauvegarder** le fichier de base de données (copie du `.db`).
2. **Fermer ES-PASS** sur tous les postes (la base est partagée sur le réseau).
3. Exécuter le script : `sqlite3 chemin\vers\ES_PASS.db ".read scripts/sql/001_utilisateur_responsable.sql"`,
   ou le coller dans l'onglet « Exécuter le SQL » de DB Browser for SQLite, puis « Écrire les modifications ».
4. Lancer les requêtes de vérification en bas du script.
5. Relancer ES-PASS (Administrateur) : écran **Utilisateurs**, colonne et case « Responsable ES-PASS ».

Les scripts sont **rejouables** (`IF NOT EXISTS`, `INSERT OR IGNORE`).

## Compatibilité

L'application fonctionne avec ou sans le script 001. Tant que la table `utilisateur_responsable` n'existe pas,
les listes « Responsable » proposent tous les utilisateurs actifs (comportement d'avant) et la case
« Responsable ES-PASS » est grisée avec une infobulle.
