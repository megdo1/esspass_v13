-- =============================================================================
-- ES-PASS - Retour arrière du script 001 (table utilisateur_responsable)
-- =============================================================================
-- Supprime la table et son trigger. Les utilisateurs, les rôles et les demandes ne sont pas touchés :
-- les demandes déjà affectées conservent leur responsable.
-- Après ce retour, l'application revient à l'ancien comportement : les listes « Responsable »
-- proposent tous les utilisateurs actifs.
--
-- ATTENTION : la liste des responsables ES-PASS choisie par le client est PERDUE. Sauvegarder la base
-- avant, ou exporter la liste :
--   SELECT * FROM utilisateur_responsable;
-- =============================================================================

BEGIN TRANSACTION;

DROP TRIGGER IF EXISTS trg_utilisateur_responsable_suppression;
DROP TABLE IF EXISTS utilisateur_responsable;

COMMIT;
