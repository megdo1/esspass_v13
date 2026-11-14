-- ES-PASS - Demandes "Traitée" / "Fermée" sans date de traitement
-- (créées avant le correctif : la date n'était pas saisissable à la création).
-- Elles n'entrent pas dans le calcul du délai moyen. Pour les corriger : ouvrir la
-- demande (Gérer), le champ "Date de traitement" est proposé pour ces états.
SELECT d.id_demande, d.libelle, e.libelle_etat, d.date_reception
FROM demandes d
JOIN etats e ON e.id_etat = d.id_etat
WHERE e.libelle_etat IN ('Traitée', 'Fermée')
  AND (d.date_traitement IS NULL OR d.date_traitement = '')
ORDER BY d.date_reception DESC;
