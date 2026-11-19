-- =============================================================================
-- ES-PASS - Script 001 : table des responsables (utilisateur_responsable)
-- =============================================================================
-- Objet     : le client choisit lui-même, depuis l'écran Utilisateurs, quels utilisateurs
--             sont « Responsable ES-PASS ». Seuls ceux-ci sont proposés dans les listes
--             « Responsable » des demandes (Gérer, Créer, Dupliquer, Traitement en masse).
-- Schéma    : crée la table `utilisateur_responsable` et un trigger de nettoyage.
--             Aucune table existante n'est modifiée.
-- Données   : initialise la liste avec les utilisateurs ACTIFS déjà responsables d'au moins
--             une demande (pour que les listes ne soient pas vides après la mise à jour).
-- Idempotent: peut être rejoué sans risque (IF NOT EXISTS / INSERT OR IGNORE).
-- Retour    : 001_utilisateur_responsable_rollback.sql
--
-- AVANT D'EXÉCUTER
--   1. Faire une sauvegarde du fichier de base de données (copie du .db) et fermer ES-PASS
--      sur tous les postes (la base est partagée : éviter toute écriture pendant le script).
--   2. Exécuter sur la base de production, une seule fois :
--        sqlite3 chemin\vers\ES_PASS.db ".read scripts/sql/001_utilisateur_responsable.sql"
--      ou, avec DB Browser for SQLite : onglet « Exécuter le SQL », coller ce fichier,
--      exécuter, puis « Écrire les modifications ».
--
-- SANS CE SCRIPT l'application continue de fonctionner : tant que la table n'existe pas, les
-- listes de responsables proposent tous les utilisateurs actifs (ancien comportement) et la case
-- « Responsable ES-PASS » de l'écran Utilisateurs est grisée.
-- =============================================================================

BEGIN TRANSACTION;

-- 1. Table : un utilisateur est responsable ES-PASS s'il a une ligne ici.
CREATE TABLE IF NOT EXISTS utilisateur_responsable (
    id_utilisateur INTEGER PRIMARY KEY,
    date_ajout     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ajoute_par     INTEGER,                      -- id_utilisateur de l'administrateur (NULL = script)
    FOREIGN KEY (id_utilisateur) REFERENCES utilisateurs (id_utilisateur) ON DELETE CASCADE
);

-- 2. Nettoyage : supprimer un utilisateur retire aussi sa ligne (SQLite n'applique pas toujours les
--    clés étrangères ; ce trigger évite qu'un identifiant réutilisé hérite d'un ancien statut).
CREATE TRIGGER IF NOT EXISTS trg_utilisateur_responsable_suppression
AFTER DELETE ON utilisateurs
BEGIN
    DELETE FROM utilisateur_responsable WHERE id_utilisateur = OLD.id_utilisateur;
END;

-- 3. Initialisation : utilisateurs actifs déjà responsables d'au moins une demande.
INSERT OR IGNORE INTO utilisateur_responsable (id_utilisateur)
SELECT DISTINCT u.id_utilisateur
FROM utilisateurs u
JOIN demandes d ON d.id_responsable = u.id_utilisateur
WHERE u.actif = 1;

-- OPTION (à décommenter si besoin) : ajouter aussi tous les Membres MCO et Administrateurs actifs.
-- INSERT OR IGNORE INTO utilisateur_responsable (id_utilisateur)
-- SELECT u.id_utilisateur
-- FROM utilisateurs u
-- JOIN roles r ON r.id_role = u.id_role
-- WHERE u.actif = 1 AND r.libelle_role IN ('Membre MCO', 'Administrateur');

COMMIT;

-- =============================================================================
-- VÉRIFICATIONS (lecture seule, à lancer après le script)
-- =============================================================================
-- Responsables enregistrés :
--   SELECT u.id_utilisateur, u.nom, u.prenom, u.email, ur.date_ajout
--   FROM utilisateur_responsable ur JOIN utilisateurs u ON u.id_utilisateur = ur.id_utilisateur
--   ORDER BY u.nom, u.prenom;
--
-- Demandes affectées à quelqu'un qui n'est pas (ou plus) responsable ES-PASS :
--   SELECT d.id_responsable, COUNT(*) AS nb_demandes
--   FROM demandes d
--   LEFT JOIN utilisateur_responsable ur ON ur.id_utilisateur = d.id_responsable
--   WHERE d.id_responsable IS NOT NULL AND ur.id_utilisateur IS NULL
--   GROUP BY d.id_responsable;
