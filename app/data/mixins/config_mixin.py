"""Configuration des colonnes et paramètres applicatifs (par utilisateur)."""




class ConfigMixin:
    """Configuration des colonnes et paramètres applicatifs (par utilisateur)."""

    def get_colonnes_config(self, visible_only=True):
        """
        Récupère la configuration des colonnes depuis la BD
        
        Args:
            visible_only: Si True, ne retourne que les colonnes visibles
        
        Returns:
            list: Liste de dictionnaires avec la config de chaque colonne
        """
        id_utilisateur = self.get_current_user() or {}
        id_user = id_utilisateur.get("id", -1)
        colonnes = []

        # 1) Essayer config spécifique utilisateur
        if visible_only:
            query_user = """
                SELECT nom_colonne, libelle_affiche, champ_demande, largeur_defaut,
                   visible, ordre_affichage, alignement, tronquer_longueur, type_colonne
                FROM colonnes_config
                WHERE id_utilisateur = ? AND visible = 1
                ORDER BY ordre_affichage
            """
        else:
            query_user = """
                SELECT nom_colonne, libelle_affiche, champ_demande, largeur_defaut,
                   visible, ordre_affichage, alignement, tronquer_longueur, type_colonne
                FROM colonnes_config
                WHERE id_utilisateur = ?
                ORDER BY ordre_affichage
            """
        rows = self.execute_query(query_user, (id_user,))

        # 2) Si aucune ligne => fallback config par défaut (id_user IS NULL)
        if not rows or len(rows) == 0:
            if visible_only:
                query_def = """
                    SELECT nom_colonne, libelle_affiche, champ_demande, largeur_defaut,
                   visible, ordre_affichage, alignement, tronquer_longueur, type_colonne
                FROM colonnes_config
                WHERE id_utilisateur IS NULL AND visible = 1
                ORDER BY ordre_affichage
                """
            else:
                query_def = """
                    SELECT nom_colonne, libelle_affiche, champ_demande, largeur_defaut,
                   visible, ordre_affichage, alignement, tronquer_longueur, type_colonne
                FROM colonnes_config
                WHERE id_utilisateur IS NULL
                ORDER BY ordre_affichage
                """
            rows = self.execute_query(query_def, ())

        if not rows:
            return []

        for row in rows:
            colonnes.append({
                "nom": row[0],
                "libelle": row[1],
                "champ": row[2],
                "largeur": row[3],
                "visible": row[4],
                "ordre": row[5],
                "alignement": row[6],
                "tronquer": row[7],
                "type": row[8],
            })
        return colonnes

    def update_colonne_config(self, nom_colonne, visible=None, largeur=None, ordre=None):
        """
        Met à jour la configuration d'une colonne
        
        Args:
            nom_colonne: Nom de la colonne à mettre à jour
            visible: 1 pour visible, 0 pour cachée (optionnel)
            largeur: Largeur en pixels (optionnel)
            ordre: Ordre d'affichage (optionnel)
        """
        updates = []
        params = []

        if visible is not None:
            updates.append("visible = ?")
            params.append(visible)

        if largeur is not None:
            updates.append("largeur_defaut = ?")
            params.append(largeur)

        if ordre is not None:
            updates.append("ordre_affichage = ?")
            params.append(ordre)

        if not updates:
            return

        params.append(nom_colonne)

        query = f"""
            UPDATE colonnes_config
            SET {', '.join(updates)}
            WHERE nom_colonne = ?
        """

        self.execute_update(query, params)

    def update_colonnes_bulk(self, colonnes_data):
        """Met à jour plusieurs colonnes avec DELETE + INSERT en transaction unique"""
        id_utilisateur = self.get_current_user() or {}
        id_user = id_utilisateur.get("id", -1)

        try:
            # ✅ Récupérer le tuple (conn, cursor)
            with self._get_connection() as (conn, cursor):
                cursor.execute("BEGIN TRANSACTION")

                # DELETE
                cursor.execute(
                    "DELETE FROM colonnes_config WHERE id_utilisateur = ?",
                    (id_user,)
                )

                # INSERT avec executemany
                insert_query = """
                    INSERT INTO colonnes_config
                        (nom_colonne, libelle_affiche, champ_demande,
                         largeur_defaut, visible, ordre_affichage,
                         alignement, tronquer_longueur, type_colonne, id_utilisateur)
                    SELECT nom_colonne, libelle_affiche, champ_demande,
                           ?, ?, ?, alignement, tronquer_longueur, type_colonne, ?
                    FROM colonnes_config
                    WHERE nom_colonne = ? AND id_utilisateur IS NULL
                """

                params_list = [
                    (
                        col.get("largeur", 100),
                        col.get("visible", 1),
                        col.get("ordre", 0),
                        id_user,
                        col["nom"]
                    )
                    for col in colonnes_data
                ]

                cursor.executemany(insert_query, params_list)
                conn.commit()

            return True

        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour de la config: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reset_colonnes_default(self):
        """Réinitialise toutes les colonnes aux valeurs par défaut"""
        try:
            # Réactiver toutes les colonnes
            self.execute_update("""
                UPDATE colonnes_config
                SET visible = 1
            """)

            print("✅ Colonnes réinitialisées aux valeurs par défaut")
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Erreur lors de la réinitialisation: {e}")
            return False

    def get_parametre(self, cle, default=None):
        """
        Récupère la valeur d'un paramètre
        
        Args:
            cle: Clé du paramètre
            default: Valeur par défaut si le paramètre n'existe pas
        
        Returns:
            Valeur du paramètre convertie selon son type ou default
        """
        id_utilisateur = self.get_current_user() or {}
        id_user = id_utilisateur.get("id", -1)
        try:
            row = self.execute_query("""
                SELECT valeur, type_valeur FROM parametres_app WHERE cle = ? and id_utilisateur = ?
            """, (cle, id_user))
            if not row or len(row) == 0:
                row = self.execute_query("""
                                SELECT valeur, type_valeur FROM parametres_app WHERE cle = ? 
                            """, (cle,))
            if row:
                valeur, type_valeur = row
                # Conversion selon le type
                if type_valeur == 'int':
                    return int(valeur) if valeur else 0
                elif type_valeur == 'bool':
                    return valeur.lower() in ('true', '1', 'yes')
                else:
                    return valeur

            return default
        except Exception as e:
            print(f"⚠️ Erreur lecture paramètre {cle}: {e}")
            return default

    def get_all_parametres(self):
        """
        Récupère tous les paramètres
        
        Returns:
            dict: Dictionnaire {cle: valeur}
        """
        parametres = {}
        id_utilisateur = self.get_current_user() or {}
        id_user = id_utilisateur.get("id", -1)

        try:
            rows = self.execute_query("""
                SELECT cle, valeur, type_valeur FROM parametres_app where id_utilisateur = ?
            """, (id_user,))
            if not rows or len(rows) == 0:
                rows = self.execute_query("""
                               SELECT cle, valeur, type_valeur FROM parametres_app
                           """)

            for cle, valeur, type_valeur in rows:
                if type_valeur == 'int':
                    parametres[cle] = int(valeur) if valeur else 0
                elif type_valeur == 'bool':
                    parametres[cle] = valeur.lower() in ('true', '1', 'yes') if valeur else False
                else:
                    parametres[cle] = valeur

        except Exception as e:
            print(f"⚠️ Erreur lecture paramètres: {e}")

        return parametres

    def set_parametre(self, cle, valeur):
        """
        Définit la valeur d'un paramètre
        
        Args:
            cle: Clé du paramètre
            valeur: Valeur à définir
        
        Returns:
            bool: True si succès
        """

        try:
            valeur_str = str(valeur)

            self.execute_update("""
                INSERT INTO parametres_app (cle, valeur)
                VALUES (?, ?)
                ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
            """, (cle, valeur_str))

            return True

        except Exception as e:
            print(f"⚠️ Erreur écriture paramètre {cle}: {e}")
            self.conn.rollback()
            return False

    def update_parametres_bulk(self, parametres_dict):
        """
        Met à jour plusieurs paramètres en une transaction unique - VERSION OPTIMISÉE

        Args:
            parametres_dict: Dictionnaire {cle: valeur}

        Returns:
            bool: True si succès, False sinon
        """
        id_utilisateur = self.get_current_user() or {}
        id_user = id_utilisateur.get("id", -1)

        try:
            # ✅ Utiliser get_connection() correctement avec tuple
            with self._get_connection() as (conn, cursor):
                cursor.execute("BEGIN TRANSACTION")

                # DELETE tous les paramètres de l'utilisateur
                cursor.execute(
                    "DELETE FROM parametres_app WHERE id_utilisateur = ?",
                    (id_user,)
                )

                # INSERT avec executemany
                insert_query = """
                    INSERT INTO parametres_app (cle, valeur, description, type_valeur, id_utilisateur)
                    SELECT cle, ?, description, type_valeur, ?
                    FROM parametres_app
                    WHERE cle = ? AND id_utilisateur IS NULL
                """

                # Préparer tous les paramètres
                params_list = [
                    (str(valeur), id_user, cle)
                    for cle, valeur in parametres_dict.items()
                ]

                # executemany : INSERT batch
                cursor.executemany(insert_query, params_list)

                # COMMIT
                conn.commit()

            print(f"✅ {len(parametres_dict)} paramètres mis à jour")
            return True

        except Exception as e:
            print(f"⚠️ Erreur mise à jour paramètres: {e}")
            import traceback
            traceback.print_exc()
            return False
