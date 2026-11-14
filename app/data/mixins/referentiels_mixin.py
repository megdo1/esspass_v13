"""Listes de valeurs et référentiels (canaux, domaines, états...)."""

from typing import List, Optional, Tuple


class ReferentielsMixin:
    """Listes de valeurs et référentiels (canaux, domaines, états...)."""

    def _load_reference_data(self):
        """Charge toutes les listes de valeurs et mappings au démarrage"""
        try:
            # Tables de référence simples
            tables_config = {
                'canaux': ('id_canal', 'libelle_canal'),
                'domaines': ('id_domaine', 'libelle_domaine'),
                'categories': ('id_categorie', 'libelle_categorie'),
                'natures': ('id_nature', 'libelle_nature'),
                'impacts': ('id_impact', 'libelle_impact'),
                'urgences': ('id_urgence', 'libelle_urgence'),
                'etats': ('id_etat', 'libelle_etat')
            }

            for table_name, (id_col, libelle_col) in tables_config.items():
                query = f"SELECT {id_col}, {libelle_col} FROM {table_name} WHERE actif = 1 ORDER BY {libelle_col}"
                results = self._execute_query(query)

                if results:
                    self.liste_valeurs[table_name] = [row[1] for row in results]
                    self.id_mapping[table_name] = {row[1]: row[0] for row in results}
                else:
                    self.liste_valeurs[table_name] = []
                    self.id_mapping[table_name] = {}

            # Sous-catégories avec catégorie parente
            query_sc = """
                SELECT sc.id_sous_categorie, sc.libelle_sous_categorie, c.libelle_categorie
                FROM sous_categories sc
                JOIN categories c ON sc.id_categorie = c.id_categorie
                WHERE sc.actif = 1
                ORDER BY c.libelle_categorie, sc.libelle_sous_categorie
            """
            results_sc = self._execute_query(query_sc)

            if results_sc:
                for id_sc, libelle_sc, libelle_cat in results_sc:
                    if libelle_cat not in self.sous_categories_by_categorie:
                        self.sous_categories_by_categorie[libelle_cat] = []
                    self.sous_categories_by_categorie[libelle_cat].append(libelle_sc)
                    self.sous_categories_id_mapping[libelle_sc] = id_sc
                    self.sous_categories_ids_by_categorie.setdefault(libelle_cat, {})[libelle_sc] = id_sc

            # Utilisateurs
            query_users = "SELECT id_utilisateur, nom || ' ' || prenom FROM utilisateurs WHERE actif = 1"
            results_users = self._execute_query(query_users)

            if results_users:
                self.liste_valeurs['utilisateurs'] = [row[1] for row in results_users]
                self.id_mapping['utilisateurs'] = {row[1]: row[0] for row in results_users}
            else:
                self.liste_valeurs['utilisateurs'] = []
                self.id_mapping['utilisateurs'] = {}

            print("✅ Données de référence chargées")

        except Exception as e:
            print(f"❌ Erreur chargement données référence : {e}")

    def get_categories_list(self, date_debut: str, date_fin: str) -> Optional[List[Tuple]]:
        """Récupère la liste des catégories disponibles pour le filtre"""
        query = """
            SELECT DISTINCT COALESCE(cat.libelle_categorie, 'Non défini')
            FROM demandes d
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            WHERE d.date_reception BETWEEN ? AND ?
            ORDER BY cat.libelle_categorie
        """
        return self._execute_query(query, (date_debut, date_fin))

    def get_etat_id_by_libelle(self, libelle: str) -> Optional[int]:
        """
        Récupère l'ID d'un état par son libellé

        Args:
            libelle: Libellé de l'état ('Annulée', 'Archivée', etc.)

        Returns:
            ID de l'état ou None si non trouvé
        """
        query = "SELECT id_etat FROM etats WHERE libelle_etat = ? AND actif = 1"
        results = self._execute_query(query, (libelle,))

        if results and len(results) > 0:
            return results[0][0]
        return None

    def get_id_by_libelle(self, table_name: str, libelle: str, default: int = None) -> Optional[int]:
        """
        Récupère l'ID d'une entité par son libellé avec une valeur par défaut
        
        Args:
            table_name: Nom de la table ('canaux', 'domaines', 'categories', 'natures', 'impacts', 'urgences', 'etats')
            libelle: Libellé de l'entité à rechercher
            default: Valeur par défaut si le libellé n'est pas trouvé (None par défaut)
        
        Returns:
            int: L'ID de l'entité, ou la valeur par défaut si non trouvé
        """
        return self.id_mapping.get(table_name, {}).get(libelle, default)

    def get_liste_valeurs(self, table: str) -> List[str]:
        """Récupère une liste de valeurs (déjà chargée au démarrage)"""
        return self.liste_valeurs.get(table, [])
