-- ES-PASS - Demandes dont la sous-catégorie n'appartient pas à la catégorie de la demande.
-- Cause (corrigée dans le code) : deux sous-catégories de même nom dans deux catégories différentes
-- (ex. "Rédiger un PV", "Circuits de validation", "Mise en qualité des données") étaient confondues
-- à l'enregistrement. A corriger via Gérer (choisir la bonne sous-catégorie) ou en administration.
SELECT d.id_demande, d.libelle,
       cat.libelle_categorie        AS categorie_de_la_demande,
       sc.libelle_sous_categorie    AS sous_categorie,
       catsc.libelle_categorie      AS categorie_de_la_sous_categorie
FROM demandes d
JOIN sous_categories sc   ON sc.id_sous_categorie = d.id_sous_categorie
LEFT JOIN categories cat  ON cat.id_categorie = d.id_categorie
LEFT JOIN categories catsc ON catsc.id_categorie = sc.id_categorie
WHERE d.id_categorie <> sc.id_categorie
ORDER BY d.date_reception DESC;
