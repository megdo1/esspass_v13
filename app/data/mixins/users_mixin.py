"""Utilisateurs, rôles et droits."""

from datetime import datetime
from typing import Dict, List, Optional


class UsersMixin:
    """Utilisateurs, rôles et droits."""

    # ----------------------------------
    def get_utilisateur_id_by_nom(self, nom: str) -> Optional[int]:
        query = "SELECT id_utilisateur FROM utilisateurs WHERE nom = ? AND actif = 1"
        results = self._execute_query(query, (nom,))
        if results and len(results) > 0:
            return results[0][0]
        return None

    def get_or_create_utilisateur(self, nom: str, prenom: str = "", email: str = None, id_role: int = 2) -> Optional[
        int]:
        """
        Récupère l'ID d'un utilisateur existant ou le crée s'il n'existe pas
        
        Args:
            nom: Nom de l'utilisateur
            prenom: Prénom de l'utilisateur (vide par défaut)
            email: Email de l'utilisateur (généré automatiquement si None)
            id_role: ID du rôle (2 par défaut)
        
        Returns:
            int: L'ID de l'utilisateur (existant ou nouvellement créé), ou None en cas d'erreur
        """
        # Générer l'email si non fourni
        if email is None:
            email = f"{nom}@sncf.fr"

        try:
            with self._get_connection() as (conn, cursor):
                # Vérifier si l'utilisateur existe déjà
                cursor.execute("""
                    SELECT id_utilisateur 
                    FROM utilisateurs 
                    WHERE nom = ? AND actif = 1
                """, (nom,))

                user_result = cursor.fetchone()

                if user_result:
                    # L'utilisateur existe déjà
                    id_utilisateur = user_result[0]
                    print(f"✅ Utilisateur existant trouvé : ID {id_utilisateur}")
                    return id_utilisateur
                else:
                    # Créer un nouvel utilisateur
                    cursor.execute("""
                        INSERT INTO utilisateurs (nom, prenom, email, id_role)
                        VALUES (?, ?, ?, ?)
                    """, (nom, prenom, email, id_role))

                    id_utilisateur = cursor.lastrowid
                    conn.commit()
                    print(f"✨ Nouvel utilisateur créé : ID {id_utilisateur}")
                    return id_utilisateur

        except Exception as e:
            print(f"❌ Erreur lors de get_or_create_utilisateur : {e}")
            return None

    def is_current_user_admin(self) -> bool:
        """Vérifie si l'utilisateur connecté a le rôle Administrateur"""
        try:

            userwindows = self._get_windows_user()

            if userwindows.get("error"):
                return False

            # Récupérer l'utilisateur depuis la BD
            user = self.get_user_by_credentials(
                userwindows["lastname"],
                userwindows["email"]
            )

            if not user:
                return False

            # Vérifier si actif ET administrateur
            if not user.get("actif"):
                return False

            if user.get("role") != "Administrateur":
                return False

            return True

        except Exception as e:
            print(f"Erreur vérification admin: {e}")
            return False

    def is_current_user_actif(self) -> bool:
        """Vérifie si l'utilisateur connecté est bien actif """
        try:

            userwindows = self._get_windows_user()

            if userwindows.get("error"):
                return False

            # Récupérer l'utilisateur depuis la BD
            user = self.get_user_by_credentials(
                userwindows["lastname"],
                userwindows["email"]
            )

            if not user:
                return False

            # Vérifier si actif ET administrateur
            if not user.get("actif"):
                return False

            return True

        except Exception as e:
            print(f"Erreur vérification admin: {e}")
            return False

    def get_current_user(self) -> Dict[str, str]:
        """Récupère les informations de l'utilisateur connecté"""

        current_user = self._get_windows_user()

        query = """
            SELECT u.nom, u.prenom, r.libelle_role,u.id_utilisateur
            FROM utilisateurs u
            JOIN roles r ON u.id_role = r.id_role
            WHERE u.actif = 1
            AND email=?
        """
        params = [current_user.get('email')]

        # Certains comptes Outlook (ex. outlook.com) ne renvoient ni nom ni prénom :
        # dans ce cas l'email suffit à identifier l'utilisateur.
        lastname = current_user.get('lastname')
        if lastname:
            query += "            AND nom=?\n"
            params.append(lastname)

        results = self._execute_query(query, tuple(params))

        if results and len(results) > 0:
            row = results[0]
            return {
                'nom': row[0] or 'Inconnu',
                'prenom': row[1] or '',
                'role': row[2] or 'N/A',
                'id': row[3] or '-1',
                'date_connexion': datetime.now().strftime("%d/%m/%Y à %H:%M")
            }
        else:
            return None

    def get_id_user_by_name(self, name) -> int:
        if name:
            """Récupère les informations de l'utilisateur connecté"""
            query = """
                SELECT id_utilisateur
                FROM utilisateurs u
                JOIN roles r ON u.id_role = r.id_role
                WHERE u.nom=?
            """

            results = self._execute_query(query, (name,))

            if results and len(results) > 0:
                return results[0][0]
            else:
                return 'toto'
        else:
            return None

    def get_all_users(self) -> List[Dict]:
        """Récupère tous les utilisateurs actifs"""
        query = """
            SELECT u.id_utilisateur, u.nom, u.prenom, r.libelle_role
            FROM utilisateurs u
            JOIN roles r ON u.id_role = r.id_role
            WHERE u.actif = 1
            ORDER BY u.nom, u.prenom
        """

        results = self._execute_query(query)

        if results:
            return [
                {
                    'id': row[0],
                    'nom': row[1],
                    'prenom': row[2],
                    'role': row[3],
                    'nom_complet': f"{row[1]} {row[2]}"
                }
                for row in results
            ]
        return []

    def update_user(self, idutilisateur: int, nom: str, prenom: str, email: str,
                   idrole: int, actif: bool) -> bool:
        """
        Met à jour tous les attributs d'un utilisateur

        Args:
            idutilisateur: ID de l'utilisateur
            nom: Nouveau nom
            prenom: Nouveau prénom
            email: Nouvel email
            idrole: ID du nouveau rôle
            actif: Nouveau statut actif/inactif

        Returns:
            True si succès, False sinon
        """
        query = '''
            UPDATE utilisateurs 
            SET nom = ?, prenom = ?, email = ?, id_role = ?, actif = ? 
            WHERE id_utilisateur = ?
        '''

        success = self.execute_update(query, (nom, prenom, email, idrole, actif, idutilisateur))

        if success:
            print(f"✓ Utilisateur {prenom} {nom} (ID: {idutilisateur}) mis à jour avec succès")

        return success

    def get_role_id_by_libelle(self, libelle_role: str) -> Optional[int]:
        """
        Récupère l'ID du rôle à partir de son libellé

        Args:
            libelle_role: Libellé du rôle ('Consultant', 'Membre MCO', 'Administrateur')

        Returns:
            ID du rôle ou None si non trouvé
        """
        role_mapping = {
            'consultant': 'Consultant',
            'membre_mco': 'Membre MCO',
            'administrateur': 'Administrateur'
        }

        libelle = role_mapping.get(libelle_role, libelle_role)
        query = "SELECT id_role FROM roles WHERE libelle_role = ?"
        result = self._execute_query(query, (libelle,))

        if result and len(result) > 0:
            return result[0][0]

        print(f"❌ Rôle '{libelle}' non trouvé")
        return None

    def get_user_by_credentials(self, nom: str = None, email: str = None) -> Optional[Dict]:
        """
        Récupère un utilisateur par nom ou email avec ses informations de rôle

        Args:
            nom: Nom de l'utilisateur
            email: Email de l'utilisateur

        Returns:
            Dictionnaire avec les infos utilisateur ou None
        """
        query = """
            SELECT u.id_utilisateur, r.libelle_role, u.nom, u.prenom, u.email, u.actif
            FROM utilisateurs u
            LEFT JOIN roles r ON u.id_role = r.id_role
            WHERE u.nom = ? OR u.email = ?
        """

        results = self._execute_query(query, (nom, email))

        if results and len(results) > 0:
            row = results[0]
            return {
                'id_utilisateur': row[0],
                'role': row[1],
                'nom': row[2],
                'prenom': row[3],
                'email': row[4],
                'actif': row[5]
            }

        return None

    def create_user_with_role(self, nom: str, prenom: str, email: str,
                              id_role: int, actif: bool = False) -> bool:
        """
        Crée un nouvel utilisateur avec un rôle spécifique

        Args:
            nom: Nom de l'utilisateur
            prenom: Prénom de l'utilisateur
            email: Email de l'utilisateur
            id_role: ID du rôle à attribuer
            actif: Statut actif/inactif (False par défaut)

        Returns:
            True si succès, False sinon
        """
        query = """
            INSERT INTO utilisateurs (nom, prenom, email, id_role, actif, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        success = self._execute_update(query, (nom, prenom, email, id_role, actif))

        if success:
            print(f"✅ Utilisateur créé : {prenom} {nom} ({email})")

        return success

    def get_all_users_with_roles(self) -> List[Dict]:
        """
        Récupère tous les utilisateurs avec leurs informations complètes

        Returns:
            Liste de dictionnaires avec les informations utilisateurs
        """
        query = """
            SELECT u.id_utilisateur, u.nom, u.prenom, u.email, r.libelle_role, u.actif
            FROM utilisateurs u
            LEFT JOIN roles r ON u.id_role = r.id_role
            ORDER BY u.nom, u.prenom
        """

        results = self._execute_query(query)

        if results:
            return [
                {
                    'id_utilisateur': row[0],
                    'nom': row[1],
                    'prenom': row[2],
                    'email': row[3],
                    'libelle_role': row[4],
                    'actif': row[5],
                    'nom_complet': f"{row[1]} {row[2]}"
                }
                for row in results
            ]

        return []

    def update_user_role(self, id_utilisateur: int, id_role: int) -> bool:
        """
        Met à jour le rôle d'un utilisateur

        Args:
            id_utilisateur: ID de l'utilisateur
            id_role: ID du nouveau rôle

        Returns:
            True si succès, False sinon
        """
        query = "UPDATE utilisateurs SET id_role = ? WHERE id_utilisateur = ?"
        success = self._execute_update(query, (id_role, id_utilisateur))

        if success:
            print(f"✅ Rôle mis à jour pour l'utilisateur #{id_utilisateur}")

        return success

    def activate_user(self, id_utilisateur: int) -> bool:
        """
        Active un utilisateur

        Args:
            id_utilisateur: ID de l'utilisateur

        Returns:
            True si succès, False sinon
        """
        query = "UPDATE utilisateurs SET actif = 1 WHERE id_utilisateur = ?"
        success = self._execute_update(query, (id_utilisateur,))

        if success:
            print(f"✅ Utilisateur #{id_utilisateur} activé")

        return success

    def deactivate_user(self, id_utilisateur: int) -> bool:
        """
        Désactive un utilisateur

        Args:
            id_utilisateur: ID de l'utilisateur

        Returns:
            True si succès, False sinon
        """
        query = "UPDATE utilisateurs SET actif = 0 WHERE id_utilisateur = ?"
        success = self._execute_update(query, (id_utilisateur,))

        if success:
            print(f"✅ Utilisateur #{id_utilisateur} désactivé")

        return success

    def delete_user(self, id_utilisateur: int) -> bool:
        """
        Supprime définitivement un utilisateur

        Args:
            id_utilisateur: ID de l'utilisateur

        Returns:
            True si succès, False sinon
        """
        query = "DELETE FROM utilisateurs WHERE id_utilisateur = ?"
        success = self._execute_update(query, (id_utilisateur,))

        if success:
            print(f"⚠️ Utilisateur #{id_utilisateur} supprimé définitivement")

        return success

    def check_user_exists_by_email(self, email: str) -> bool:
        """
        Vérifie si un utilisateur existe avec cet email

        Args:
            email: Email à vérifier

        Returns:
            True si l'utilisateur existe, False sinon
        """
        query = "SELECT id_utilisateur FROM utilisateurs WHERE email = ?"
        result = self._execute_query(query, (email,))

        return result is not None and len(result) > 0

    def create_full_user(self, nom: str, prenom: str, email: str,
                         libelle_role: str, actif: bool = True) -> bool:
        """
        Crée un utilisateur complet avec parsing du nom et vérification du rôle

        Args:
            nom_complet: Nom complet (ex: "Jean Dupont")
            email: Email de l'utilisateur
            libelle_role: Libellé du rôle ('consultant', 'membre_mco', 'administrateur')
            actif: Statut actif/inactif

        Returns:
            True si succès, False sinon
        """
        # Vérifier si l'email existe déjà
        if self.check_user_exists_by_email(email):
            print(f"❌ Un utilisateur avec l'email {email} existe déjà")
            return False

        # Récupérer l'ID du rôle
        id_role = self.get_role_id_by_libelle(libelle_role)
        if not id_role:
            print(f"❌ Le rôle '{libelle_role}' n'existe pas")
            return False

        # Créer l'utilisateur
        return self.create_user_with_role(nom, prenom, email, id_role, actif)
