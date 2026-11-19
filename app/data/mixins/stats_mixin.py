"""Indicateurs et statistiques du tableau de bord."""

from typing import Dict, List, Optional, Tuple


class StatsMixin:
    """Indicateurs et statistiques du tableau de bord."""

    # Définition des indicateurs de période (écran Métriques, export Excel) :
    #  - réalisées  = Traitée + Fermée
    #  - en cours   = À étudier + En cours de traitement
    #  - hors calcul = demandes qui ne sont ni réalisées ni "à réaliser" : exclues de TOUS les indicateurs
    ETATS_REALISES = ("Traitée", "Fermée")
    ETAT_A_ETUDIER = "À étudier"
    ETAT_EN_COURS_TRAITEMENT = "En cours de traitement"
    ETATS_HORS_CALCUL = ("Archivée", "Annulée", "Hors assistance", "Non applicable")
    # États masqués par défaut dans le tableau des demandes : une demande archivée ou annulée n'a plus
    # à être affectée, la tuile « non affectées » ne doit donc pas les compter.
    ETATS_MASQUES_PAR_DEFAUT = ("Archivée", "Annulée")

    def get_metriques_periode(self, date_debut: str, date_fin: str) -> Optional[Dict]:
        """
        Indicateurs clés des demandes REÇUES entre date_debut et date_fin (bornes incluses).

        Les demandes Archivée / Annulée / Hors assistance / Non applicable sont exclues du total,
        du taux de réalisation et du délai moyen ; leur nombre est restitué dans 'hors_calcul'.
        Retourne None en cas d'erreur SQL.
        """
        hors = ", ".join("?" for _ in self.ETATS_HORS_CALCUL)
        reals = ", ".join("?" for _ in self.ETATS_REALISES)
        query = f"""
            SELECT
                SUM(CASE WHEN COALESCE(et.libelle_etat, '') NOT IN ({hors}) THEN 1 ELSE 0 END),
                SUM(CASE WHEN et.libelle_etat IN ({reals}) THEN 1 ELSE 0 END),
                SUM(CASE WHEN et.libelle_etat = ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN et.libelle_etat = ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN COALESCE(et.libelle_etat, '') IN ({hors}) THEN 1 ELSE 0 END),
                ROUND(AVG(CASE WHEN COALESCE(et.libelle_etat, '') NOT IN ({hors})
                                AND d.date_traitement IS NOT NULL
                                AND julianday(d.date_traitement) >= julianday(d.date_reception)
                          THEN julianday(d.date_traitement) - julianday(d.date_reception)
                          ELSE NULL END), 1)
            FROM demandes d
            LEFT JOIN etats et ON d.id_etat = et.id_etat
            WHERE date(d.date_reception) BETWEEN ? AND ?
        """
        params = (*self.ETATS_HORS_CALCUL, *self.ETATS_REALISES, self.ETAT_A_ETUDIER,
                  self.ETAT_EN_COURS_TRAITEMENT, *self.ETATS_HORS_CALCUL, *self.ETATS_HORS_CALCUL,
                  date_debut, date_fin)
        rows = self._execute_query(query, params)
        if not rows:
            return None
        total, realisees, a_etudier, en_traitement, hors_calcul, delai = rows[0]
        total, realisees = total or 0, realisees or 0
        a_etudier, en_traitement, hors_calcul = a_etudier or 0, en_traitement or 0, hors_calcul or 0
        return {
            "total": total,
            "realisees": realisees,
            "a_etudier": a_etudier,
            "en_cours_traitement": en_traitement,
            "en_cours": a_etudier + en_traitement,
            "hors_calcul": hors_calcul,
            "delai_moyen": delai,
            "taux": round(realisees / total * 100, 1) if total else 0.0,
        }

    def get_nb_jours(self) -> int:
        """Récupère le nombre total de demandes"""
        query = "select CAST(valeur AS INTEGER) from parametres_app where cle='mail_days'"
        results = self._execute_query(query)

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_total_demandes(self) -> int:
        """Récupère le nombre total de demandes"""
        query = "SELECT COUNT(*) FROM demandes"
        results = self._execute_query(query)

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_demandes_recentes(self) -> int:
        """Compte les demandes reçues dans les dernières 24h"""
        query = """
            SELECT COUNT(*)
            FROM demandes
            WHERE date_reception >= datetime('now', '-1 day')
        """
        results = self._execute_query(query)

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_demandes_non_affectees(self) -> int:
        """Compte les demandes sans responsable, hors états masqués par défaut (Archivée, Annulée).

        Même périmètre que le tableau des demandes avec ses filtres par défaut, pour que la tuile et
        le tableau filtré sur « responsable vide » donnent le même nombre.
        """
        masques = ", ".join("?" for _ in self.ETATS_MASQUES_PAR_DEFAUT)
        query = f"""
            SELECT COUNT(*)
            FROM demandes d
            LEFT JOIN etats e ON d.id_etat = e.id_etat
            WHERE d.id_responsable IS NULL
              AND COALESCE(e.libelle_etat, '') NOT IN ({masques})
        """
        results = self._execute_query(query, self.ETATS_MASQUES_PAR_DEFAUT)

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_demandes_a_etudier(self) -> int:
        """Compte les demandes avec état 'À étudier'"""
        query = """
            SELECT COUNT(*)
            FROM demandes d
            JOIN etats e ON d.id_etat = e.id_etat
            WHERE e.libelle_etat = 'À étudier'
        """
        results = self._execute_query(query)

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_mes_demandes(self, id_utilisateur: int = None) -> int:
        """Compte les demandes affectées à un utilisateur"""
        # Accepte un identifiant, un dict utilisateur (clé 'id') ou None (= utilisateur connecté)
        if id_utilisateur is None:
            id_utilisateur = self.get_current_user()
        if isinstance(id_utilisateur, dict):
            id_utilisateur = id_utilisateur.get('id')
        if id_utilisateur is None or id_utilisateur == '-1':
            return 0

        query = """
            SELECT COUNT(*)
            FROM demandes d
			INNER JOIN etats e on e.id_etat=d.id_etat
            WHERE e.libelle_etat IN ('À étudier','En cours de traitement')
			AND d.id_responsable = ?
        """
        results = self._execute_query(query, (id_utilisateur,))

        if results and len(results) > 0:
            return results[0][0]
        return 0

    def get_dashboard_stats(self) -> Dict[str, int]:
        """Récupère toutes les statistiques du tableau de bord"""
        return {
            'recentes': self.get_demandes_recentes(),
            'non_affectees': self.get_demandes_non_affectees(),
            'a_etudier': self.get_demandes_a_etudier(),
            'mes_demandes': self.get_mes_demandes()
        }

    def get_rapport_sous_categories(self, date_debut: str, date_fin: str, categorie_filter: str = None) -> Optional[
        List[Tuple]]:
        """Récupère les statistiques par sous-catégorie avec filtre optionnel"""
        if categorie_filter:
            query = """
                SELECT 
                    COALESCE(sc.libelle_sous_categorie , 'Non défini') as sous_categorie,
                    COUNT(*) as nombre
                FROM demandes d
                LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
                LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
                WHERE d.date_reception BETWEEN ? AND ?
                 AND cat.libelle_categorie = ?
                GROUP BY sc.libelle_sous_categorie
                ORDER BY nombre DESC
            """
            return self._execute_query(query, (date_debut, date_fin, categorie_filter))
        else:
            query = """
                SELECT 
                    COALESCE(sc.libelle_sous_categorie, 'Non défini') as sous_categorie,
                    COUNT(*) as nombre
                FROM demandes d
                LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
                WHERE d.date_reception BETWEEN ? AND ?
                GROUP BY sc.libelle_sous_categorie
                ORDER BY nombre DESC
                LIMIT 15
            """
            return self._execute_query(query, (date_debut, date_fin))
