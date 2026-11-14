import logging

logger = logging.getLogger(__name__)
"""Rôle de l'utilisateur et activation des boutons selon les permissions."""




class PermissionsMixin:
    """Rôle de l'utilisateur et activation des boutons selon les permissions."""

    def get_current_user_role(self):
        """Récupère le rôle de l'utilisateur connecté"""
        try:
            import os
            import win32com.client

            # Récupérer l'email de l'utilisateur
            try:
                outlook_app = win32com.client.GetActiveObject("Outlook.Application")
                namespace = outlook_app.GetNamespace("MAPI")
                user = namespace.CurrentUser
                nom_complet = user.Name
            except Exception:
                username = os.getenv("USERNAME")
                nom_complet = username

            # Récupérer le rôle depuis la BD
            query = """
                SELECT r.libelle_role
                FROM utilisateurs u
                LEFT JOIN roles r ON u.id_role = r.id_role
                WHERE u.nom = ? AND u.actif = 1
                LIMIT 1
            """
            result = self.data_manager.execute_query(query, (nom_complet,))

            if result:
                role = result[0][0]
                print(f"✅ Nom : {nom_complet}")
                print(f"✅ Rôle de l'utilisateur: {role}")
                return role

            print(f"❌ Aucun rôle trouvé pour l'utilisateur")
            return None

        except Exception as e:
            print(f"❌ Erreur lors de la récupération du rôle : {e}")
            return None

    def update_button_permissions(self):
        """Met à jour l'état de TOUS les boutons selon le rôle de l'utilisateur"""

        user_role = self.user_info['role']

        if not user_role:
            return

        # Déterminer les droits selon le rôle
        can_create = user_role in ['Membre MCO', 'Administrateur']
        can_treat = user_role in ['Membre MCO', 'Administrateur']
        can_manage_mass = user_role in ['Membre MCO', 'Administrateur']
        can_archive = user_role == 'Administrateur'
        can_export = user_role in ['Consultant', 'Membre MCO', 'Administrateur']
        can_reports = user_role in ['Consultant', 'Membre MCO', 'Administrateur']
        can_duplicate = user_role in ['Membre MCO', 'Administrateur']
        can_manage = user_role in ['Membre MCO', 'Administrateur']
        can_cancel = user_role in ['Membre MCO', 'Administrateur']
        can_update = user_role in ['Membre MCO', 'Administrateur']

        print(f"\n{'=' * 80}")
        print(f"🎛️ MISE À JOUR DE TOUS LES BOUTONS - Rôle: {user_role}")
        print(f"{'=' * 80}")

        # ========== BOUTONS GLOBAUX ==========
        print(f"\n📋 BOUTONS GLOBAUX :")

        # Nouvelle demande
        if hasattr(self, 'btn_nouvelle_demande'):
            self.btn_nouvelle_demande.setEnabled(can_create)
            self._update_button_style(self.btn_nouvelle_demande, can_create)
            print(f"  ➕ Nouvelle demande : {'✅ ACTIF' if can_create else '❌ GRISÉ'}")

        # Annuler masse
        if hasattr(self, 'btn_annuler_masse'):
            self.btn_annuler_masse.setEnabled(can_manage_mass)
            self._update_button_style(self.btn_annuler_masse, can_manage_mass)
            print(f"  🚫 Annuler (masse) : {'✅ ACTIF' if can_manage_mass else '❌ GRISÉ'}")

        # Archiver masse
        if hasattr(self, 'btn_archiver_masse'):
            self.btn_archiver_masse.setEnabled(can_archive)
            self._update_button_style(self.btn_archiver_masse, can_archive)
            print(f"  📦 Archiver (masse) : {'✅ ACTIF' if can_archive else '❌ GRISÉ'}")

        # Traiter masse
        if hasattr(self, 'btn_traiter_masse'):
            self.btn_traiter_masse.setEnabled(can_treat)
            self._update_button_style(self.btn_traiter_masse, can_treat)
            print(f"  ✅ Traiter (masse) : {'✅ ACTIF' if can_treat else '❌ GRISÉ'}")

        # Gérer masse
        if hasattr(self, 'btn_gerer_masse'):
            self.btn_gerer_masse.setEnabled(can_manage_mass)
            self._update_button_style(self.btn_gerer_masse, can_manage_mass)
            print(f"  ⚙️ Gérer (masse) : {'✅ ACTIF' if can_manage_mass else '❌ GRISÉ'}")

        # Exporter
        if hasattr(self, 'btn_exporter'):
            self.btn_exporter.setEnabled(can_export)
            self._update_button_style(self.btn_exporter, can_export)
            print(f"  💾 Exporter : {'✅ ACTIF' if can_export else '❌ GRISÉ'}")

        # Rapports
        if hasattr(self, 'btn_rapports'):
            self.btn_rapports.setEnabled(can_reports)
            self._update_button_style(self.btn_rapports, can_reports)
            print(f"  📊 Rapports : {'✅ ACTIF' if can_reports else '❌ GRISÉ'}")

        # Mettre à jour
        if hasattr(self, 'btn_update'):
            self.btn_update.setEnabled(can_update)
            self._update_button_style(self.btn_update, can_update)
            print(f"  🔄 Mettre à jour : {'✅ ACTIF' if can_update else '❌ GRISÉ'}")

        # ========== BOUTONS UNITAIRES (dans le tableau) ==========
        if hasattr(self, 'unit_buttons'):
            print(f"\n📋 BOUTONS UNITAIRES (dans le tableau) :")

            # Dupliquer
            if 'dupliquer' in self.unit_buttons:
                for btn in self.unit_buttons['dupliquer']:
                    btn.setEnabled(can_duplicate)
                    self._update_button_style(btn, can_duplicate)
                print(
                    f"  📋 Dupliquer ({len(self.unit_buttons['dupliquer'])} btn) : {'✅ ACTIF' if can_duplicate else '❌ GRISÉ'}")

            # Gérer
            if 'gerer' in self.unit_buttons:
                for btn in self.unit_buttons['gerer']:
                    btn.setEnabled(can_manage)
                    self._update_button_style(btn, can_manage)
                print(f"  ⚙️ Gérer ({len(self.unit_buttons['gerer'])} btn) : {'✅ ACTIF' if can_manage else '❌ GRISÉ'}")

            # Traiter
            if 'traiter' in self.unit_buttons:
                for btn in self.unit_buttons['traiter']:
                    btn.setEnabled(can_treat)
                    self._update_button_style(btn, can_treat)
                print(
                    f"  ✅ Traiter ({len(self.unit_buttons['traiter'])} btn) : {'✅ ACTIF' if can_treat else '❌ GRISÉ'}")

            # Annuler
            if 'annuler' in self.unit_buttons:
                for btn in self.unit_buttons['annuler']:
                    btn.setEnabled(can_cancel)
                    self._update_button_style(btn, can_cancel)
                print(
                    f"  🚫 Annuler ({len(self.unit_buttons['annuler'])} btn) : {'✅ ACTIF' if can_cancel else '❌ GRISÉ'}")

            # Archiver
            if 'archiver' in self.unit_buttons:
                for btn in self.unit_buttons['archiver']:
                    btn.setEnabled(can_archive)
                    self._update_button_style(btn, can_archive)
                print(
                    f"  📦 Archiver ({len(self.unit_buttons['archiver'])} btn) : {'✅ ACTIF' if can_archive else '❌ GRISÉ'}")

        print(f"{'=' * 80}\n")

    def _update_button_style(self, button, is_enabled):
        """Change UNIQUEMENT la couleur de background si inactif"""
        if not is_enabled:
            button.setStyleSheet("background: #E2E8F0 !important; color: #94A3B8;")

    def get_button_style(self, is_enabled):
        """Retourne le style CSS du bouton selon s'il est actif ou désactivé"""
        if is_enabled:
            # Style bouton ACTIF
            return """
                QPushButton {
                    background-color: #1F4E9C;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #1A4286;
                }
                QPushButton:pressed {
                    background-color: #143468;
                }
            """
        else:
            # Style bouton DÉSACTIVÉ (grisé)
            return """
                QPushButton {
                    background-color: #E2E8F0;
                    color: #94A3B8;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
            """
