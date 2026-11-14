-- ============================================================================
-- ES-PASS - Correctif de libellé : "GAA" -> "GAIA"
-- Liste : sous-catégories de la catégorie "Interfaces SI"
--
-- A EXECUTER SUR LA BASE DE PRODUCTION (fichier .db), APRES UNE COPIE DE SAUVEGARDE.
-- Aucune demande n'est modifiée : elles référencent la sous-catégorie par son
-- identifiant, l'historique est donc conservé et affichera "GAIA".
-- Script rejouable sans risque (aucun effet si "GAA" n'existe plus).
-- Les utilisateurs doivent relancer l'application (les listes sont chargées au démarrage).
-- ============================================================================

-- 1) Avant
SELECT sc.id_sous_categorie, sc.libelle_sous_categorie, cat.libelle_categorie
FROM sous_categories sc
JOIN categories cat ON cat.id_categorie = sc.id_categorie
WHERE sc.libelle_sous_categorie IN ('GAA', 'GAIA');

-- 2) Correction
BEGIN TRANSACTION;

UPDATE sous_categories
SET libelle_sous_categorie = 'GAIA'
WHERE libelle_sous_categorie = 'GAA'
  AND id_categorie = (SELECT id_categorie FROM categories WHERE libelle_categorie = 'Interfaces SI')
  AND NOT EXISTS (
        SELECT 1 FROM sous_categories s2
        WHERE s2.libelle_sous_categorie = 'GAIA'
          AND s2.id_categorie = sous_categories.id_categorie);

COMMIT;

-- 3) Après (doit afficher une seule ligne "GAIA", aucune "GAA")
SELECT sc.id_sous_categorie, sc.libelle_sous_categorie, cat.libelle_categorie
FROM sous_categories sc
JOIN categories cat ON cat.id_categorie = sc.id_categorie
WHERE sc.libelle_sous_categorie IN ('GAA', 'GAIA');
