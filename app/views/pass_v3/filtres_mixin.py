"""Tri, filtres et sélection dans les en-têtes du tableau des demandes."""

from PyQt5.QtWidgets import QWidget, QMenu, QAction
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QHBoxLayout, QDialog
from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from app.views.pass_v3.widgets import PopupFiltre
import logging

logger = logging.getLogger(__name__)


class FiltresMixin:
    """Tri, filtres et sélection dans les en-têtes du tableau des demandes."""

    def on_header_clicked_combined(self, logicalindex):
        """CLIC GAUCHE pour cocher/décocher les checkboxes"""
        if logicalindex == 0:
            total = 0
            selected = 0
            # Colonne 0 = colonne des checkbox

            # Compter TOUTES les lignes (visibles ET cachées) pour la désélection
            total_all = 0
            selected_all = 0
            for row in range(self.table.rowCount()):
                total_all += 1
                checkboxwidget = self.table.cellWidget(row, 0)
                if checkboxwidget:
                    checkbox = checkboxwidget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_all += 1

            # Compter uniquement les lignes visibles
            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                total += 1
                checkboxwidget = self.table.cellWidget(row, 0)
                if checkboxwidget:
                    checkbox = checkboxwidget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected += 1

            # Déterminer si on coche ou décoche
            # Si au moins une demande est cochée (visible ou cachée), on décoche TOUT
            # Sinon, on coche uniquement les visibles
            selectall = (selected_all == 0)

            if selectall:
                # SÉLECTION : cocher uniquement les lignes VISIBLES
                for row in range(self.table.rowCount()):
                    if self.table.isRowHidden(row):
                        continue
                    checkboxwidget = self.table.cellWidget(row, 0)
                    if checkboxwidget:
                        checkbox = checkboxwidget.findChild(QCheckBox)
                        if checkbox:
                            checkbox.blockSignals(True)
                            checkbox.setChecked(True)
                            checkbox.blockSignals(False)
            else:
                # DÉSÉLECTION : décocher TOUTES les lignes (visibles ET cachées)
                for row in range(self.table.rowCount()):
                    checkboxwidget = self.table.cellWidget(row, 0)
                    if checkboxwidget:
                        checkbox = checkboxwidget.findChild(QCheckBox)
                        if checkbox:
                            checkbox.blockSignals(True)
                            checkbox.setChecked(False)
                            checkbox.blockSignals(False)

            self.update_selection_count()
        else:
            # Autres colonnes : afficher le filtre
            self.afficherPopupFiltre(logicalindex)

    def afficherMenuEntete(self, pos):
        """Affiche le menu contextuel sur l'en-tête avec options de tri et filtre"""
        header = self.table.horizontalHeader()
        index = header.logicalIndexAt(pos)

        if index < 0:
            return

        # Ignorer la colonne 0 (checkbox)
        if index == 0:
            # Gérer le clic sur la colonne checkbox
            total = 0
            selected = 0

            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                total += 1
                checkboxwidget = self.table.cellWidget(row, 0)
                if checkboxwidget:
                    checkbox = checkboxwidget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected += 1

            selectall = not (selected == total and total > 0)

            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                checkboxwidget = self.table.cellWidget(row, 0)
                if checkboxwidget:
                    checkbox = checkboxwidget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(selectall)
                        checkbox.blockSignals(False)

            self.update_selection_count()
            return

        # Pour les autres colonnes : afficher le menu contextuel
        menu = QMenu(self)

        # ========== ACTIONS DE TRI ==========
        actiontriasc = QAction("⬆ Trier de A → Z", self)
        actiontriasc.triggered.connect(lambda: self.trierColonne(index, Qt.AscendingOrder))
        menu.addAction(actiontriasc)

        actiontridesc = QAction("⬇ Trier de Z → A", self)
        actiontridesc.triggered.connect(lambda: self.trierColonne(index, Qt.DescendingOrder))
        menu.addAction(actiontridesc)

        menu.addSeparator()

        # ========== ACTION DE FILTRAGE ==========

        # ========== ACTION EFFACER FILTRE ==========
        if self.mots_cles[index]:
            actioneffacerfiltre = QAction("❌ Effacer le filtre", self)
            actioneffacerfiltre.triggered.connect(lambda: self.effacerFiltre(index))
            menu.addAction(actioneffacerfiltre)

        # ========== ACTION EFFACER TRI ==========

        menu.exec(header.mapToGlobal(pos))

    def trierColonne(self, index, ordre):
        """Trie la colonne selon l'ordre spécifié (croissant ou décroissant) - UNIQUEMENT SUR LES LIGNES VISIBLES"""
        logger.info(f"🔄 Tri de la colonne {index} - Ordre: {'ASC' if ordre == Qt.AscendingOrder else 'DESC'}")
        # ✅ AJOUTEZ CES LIGNES : Réinitialiser les tris des autres colonnes
        for col in range(self.table.columnCount()):
            if col != index:
                self.ordre_tri[col] = None

        self.ordre_tri[index] = ordre

        # ========== ÉTAPE 1 : COLLECTER LES DONNÉES DES LIGNES VISIBLES ==========
        lignes_donnees = []

        for row in range(self.table.rowCount()):
            # IMPORTANT : Ne traiter que les lignes VISIBLES (pas cachées par le filtre)
            if self.table.isRowHidden(row):
                continue

            # Récupérer l'ID de la demande
            iditem = self.table.verticalHeaderItem(row)
            if not iditem:
                continue

            try:
                iddemande = int(iditem.text())
            except Exception:
                logger.debug("Exception ignorée dans trierColonne", exc_info=True)
                continue

            # Récupérer la valeur de la cellule à trier
            item = self.table.item(row, index)
            if item:
                valeur = item.text()
            else:
                valeur = ""

            # Stocker : (ID demande, valeur pour tri, toutes les données de la ligne)
            ligne_complete = {
                'iddemande': iddemande,
                'valeur_tri': valeur,
                'row_originale': row,
                'donnees': []
            }

            # Récupérer toutes les cellules de la ligne
            for col in range(self.table.columnCount()):
                cellitem = self.table.item(row, col)
                if cellitem:
                    ligne_complete['donnees'].append({
                        'col': col,
                        'text': cellitem.text(),
                        'background': cellitem.background(),
                        'foreground': cellitem.foreground(),
                        'alignment': cellitem.textAlignment()
                    })
                else:
                    ligne_complete['donnees'].append({
                        'col': col,
                        'widget': self.table.cellWidget(row, col)
                    })

            lignes_donnees.append(ligne_complete)

        logger.info(f"📊 Nombre de lignes visibles à trier : {len(lignes_donnees)}")

        # ========== ÉTAPE 2 : TRI INTELLIGENT ==========
        def cle_tri(ligne):
            valeur = ligne['valeur_tri']
            try:
                return (0, int(valeur))  # ✅ D'abord essayer en tant qu'entier
            except Exception:
                try:
                    return (0, float(valeur.replace(',', '.')))  # ✅ Puis en tant que décimal
                except Exception:
                    return (1, valeur.lower())  # ✅ Sinon alphabétique

        reverse = (ordre == Qt.DescendingOrder)
        lignes_donnees.sort(key=cle_tri, reverse=reverse)

        # ========== ÉTAPE 3 : SAUVEGARDER L'ÉTAT DES CHECKBOXES ==========
        checkboxes_etat = {}
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            iditem = self.table.verticalHeaderItem(row)
            if iditem:
                try:
                    iddemande = int(iditem.text())
                    checkboxwidget = self.table.cellWidget(row, 0)
                    if checkboxwidget:
                        checkbox = checkboxwidget.findChild(QCheckBox)
                        if checkbox:
                            checkboxes_etat[iddemande] = checkbox.isChecked()
                except Exception:
                    logger.debug("Exception ignorée dans trierColonne", exc_info=True)

        # ========== ÉTAPE 5 : RÉORGANISER LES LIGNES VISIBLES DANS LE TABLEAU ==========
        # Créer un mapping : position actuelle -> position cible
        lignes_visibles = [i for i in range(self.table.rowCount()) if not self.table.isRowHidden(i)]

        if len(lignes_visibles) == len(lignes_donnees):
            # Pour chaque ligne triée, la placer à sa nouvelle position
            for idx, ligne in enumerate(lignes_donnees):
                row_cible = lignes_visibles[idx]
                iddemande = ligne['iddemande']

                # Mettre à jour l'ID dans le header vertical
                self.table.verticalHeaderItem(row_cible).setText(str(iddemande))

                # Réinsérer toutes les données de la ligne
                for cell_data in ligne['donnees']:
                    col = cell_data['col']

                    if 'text' in cell_data:
                        # Cellule avec texte
                        item = QTableWidgetItem(cell_data['text'])
                        item.setBackground(cell_data['background'])
                        item.setForeground(cell_data['foreground'])
                        item.setTextAlignment(cell_data['alignment'])
                        self.table.setItem(row_cible, col, item)
                    elif 'widget' in cell_data and cell_data['widget']:
                        # Cellule avec widget - on doit le recréer
                        # Pour la colonne 0 (checkbox)
                        if col == 0:
                            checkbox = QCheckBox()
                            checkbox.setStyleSheet("margin-left: 10px")
                            checkbox_widget = QWidget()
                            checkbox_layout = QHBoxLayout(checkbox_widget)
                            checkbox_layout.addWidget(checkbox)
                            checkbox_layout.setAlignment(Qt.AlignCenter)
                            checkbox_layout.setContentsMargins(0, 0, 0, 0)
                            self.table.setCellWidget(row_cible, col, checkbox_widget)
                            checkbox.stateChanged.connect(self.update_selection_count)

                            # Restaurer l'état de la checkbox
                            if iddemande in checkboxes_etat:
                                checkbox.blockSignals(True)
                                checkbox.setChecked(checkboxes_etat[iddemande])
                                checkbox.blockSignals(False)
                        else:
                            # Pour les autres widgets (boutons d'action), les recréer
                            self.table.setCellWidget(row_cible, col, self.create_actions_widget(row_cible))

        # ========== ÉTAPE 6 : DÉBLOQUER LES SIGNAUX ==========
        self.table.blockSignals(False)

        # ========== ÉTAPE 7 : METTRE À JOUR LES INDICATEURS ==========
        self.majHeaderIndicateurs()
        self.update_selection_count()

        logger.info(f"✅ Tri terminé sur {len(lignes_donnees)} lignes visibles")

    def update_header_checkbox_display(self):
        """Met à jour l'affichage de la checkbox d'en-tête"""
        selected = self.get_selected_demandes()
        total = self.table.rowCount()

        header_item = self.table.horizontalHeaderItem(0)
        if header_item:
            if len(selected) == 0:
                header_item.setText("☐")  # Vide
            elif len(selected) == total:
                header_item.setText("☑")  # Toutes cochées
            else:
                header_item.setText("◫")  # Partiellement cochées

    def update_selection_count(self):
        """Met à jour le compteur et l'affichage de l'en-tête"""
        selected = self.get_selected_demandes()
        count = len(selected)

        if hasattr(self, 'selection_label'):
            self.selection_label.setText(f"{count} demande(s) sélectionnée(s)")

        self.update_header_checkbox_display()

    def appliquer_filtres(self):
        """Recharge le tableau quand un filtre change"""
        logger.info(f"🔄 Filtres : Archivées={self.cb_archives.isChecked()}, "
              f"Annulées={self.cb_annulees.isChecked()}, Traitées={self.cb_realisees.isChecked()}")
        self.load_demandes_table()

    def effacerFiltre(self, index):
        """Efface le filtre actif sur une colonne"""
        logger.debug(f"❌ Effacement du filtre sur la colonne {index}")
        self.mots_cles[index] = []
        if index in self.etat_coches_col:
            self.etat_coches_col[index] = {}
        self.filtrerDonnees()
        self.majHeaderIndicateurs()

    def effacerTri(self, index):
        """Efface le tri actif sur une colonne"""
        logger.info(f"↺ Effacement du tri sur la colonne {index}")
        self.ordre_tri[index] = None
        self.load_demandes_table()
        self.majHeaderIndicateurs()

    def majHeaderIndicateurs(self):
        """Met à jour les indicateurs visuels (filtre + tri) dans les en-têtes"""
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            if not item or col >= len(self.header_labels):
                continue

            texte = self.header_labels[col]

            # Indicateur de filtre
            if self.mots_cles[col]:
                texte += " 🔍"

            # Indicateur de tri
            if self.ordre_tri[col] == Qt.AscendingOrder:
                texte += " ⬆"
            elif self.ordre_tri[col] == Qt.DescendingOrder:
                texte += " ⬇"

            item.setText(texte)

    def afficherPopupFiltre(self, index):
        """Affiche le popup de filtre par checkboxes"""
        self.colonneactive = index

        # Récupérer toutes les valeurs uniques de la colonne
        uniques = []

        for i in range(self.table.rowCount()):
            # print(f"\n--- Ligne {i} ---")

            # Filtrer selon les autres colonnes actives
            visibleparautres = True
            for col in range(self.table.columnCount()):
                if col == index:
                    continue  # on ignore le filtre de la colonne en cours

                item = self.table.item(i, col)
                if not item:
                    # print(f"  Col {col}: PAS D'ITEM")
                    continue

                valeur_cellule = item.text()
                # print(f"  Col {col}: '{valeur_cellule}' | Filtre: {self.mots_cles[col]}")

                if self.mots_cles[col]:
                    # Si c'est une date-heure, comparer uniquement la partie date
                    if self.is_date_format(valeur_cellule):
                        date_cellule = valeur_cellule[:10]
                        if date_cellule not in self.mots_cles[col]:
                            visibleparautres = False
                            break
                    else:
                        if valeur_cellule not in self.mots_cles[col]:
                            visibleparautres = False
                            break

            # print(f"  visibleparautres: {visibleparautres}")
            # print(f"  isRowHidden: {self.table.isRowHidden(i)}")

            # Vérifier si la ligne est cachée OU ne respecte pas les autres filtres
            if not visibleparautres or self.table.isRowHidden(i):
                # print(f"  ⏭️ LIGNE IGNORÉE")
                continue

            # 2) si la ligne passe les autres filtres ET est visible, on prend la valeur
            itemcol = self.table.item(i, index)
            if itemcol:
                txt = itemcol.text()
                # print(f"  ✅ Valeur collectée: '{txt}'")

                # ========== DÉTECTION DE COLONNE DATE/DATETIME ==========
                if self.is_date_format(txt):
                    date_only = txt[:10]
                    if date_only not in uniques:
                        uniques.append(date_only)
                else:
                    # Valeur normale (texte complet)
                    if txt not in uniques:
                        uniques.append(txt)
            # else:
            # print(f"  ⚠️ PAS D'ITEM pour la colonne {index}")

        # print(f"\n✅ Valeurs uniques collectées: {uniques}")
        # print(f"📊 Nombre de valeurs: {len(uniques)}")

        # Initialiser l'état des checkboxes pour cette colonne
        if index not in self.etat_coches_col:
            self.etat_coches_col[index] = {v: True for v in uniques}

        etatcoches = self.etat_coches_col[index]

        # Ajouter les nouvelles valeurs qui n'existaient pas encore dans le dict
        for v in uniques:
            if v not in etatcoches:
                etatcoches[v] = True

        # Affichage du dialog popup scrollable - position plus robuste
        popup = PopupFiltre(uniques, etatcoches, parent=self)
        header = self.table.horizontalHeader()

        # Décalage interne du header quand on scrolle horizontalement
        header_offset = header.offset()  # même sens que le scroll

        # Position logique du début de la section
        section_x = header.sectionPosition(index)

        # X dans le repère visible du header (corrigé du scroll)
        x_in_header = section_x - header_offset

        # Point juste sous l'en-tête de cette colonne
        local_point = QtCore.QPoint(x_in_header, header.height())

        # Coordonnées écran
        global_pos = header.mapToGlobal(local_point)

        popup.move(global_pos)

        if popup.exec() == QDialog.Accepted:
            selection = [val for val in uniques if etatcoches.get(val, True)]

            if not self.mots_cles[index] and selection == uniques and popup.recherche.text().strip():
                selection = popup.filtered

            if set(selection) == set(uniques):
                selection = []

            self.mots_cles[index] = selection
            self.filtrerDonnees()
            self.majHeaderIndicateurs()

    def is_date_format(self, text):
        """
        Vérifie si le texte est une date au format YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS
        """
        if not text or len(text) < 10:
            return False

        # Vérifier si les 10 premiers caractères sont au format YYYY-MM-DD
        date_part = text[:10]

        # Format attendu : 4 chiffres, tiret, 2 chiffres, tiret, 2 chiffres
        try:
            parts = date_part.split('-')
            if len(parts) != 3:
                return False

            year, month, day = parts
            if len(year) == 4 and len(month) == 2 and len(day) == 2:
                # Vérifier que ce sont bien des chiffres
                int(year)
                int(month)
                int(day)
                return True
        except Exception:
            logger.debug("Exception ignorée dans is_date_format", exc_info=True)
            return False

        return False

    def filtrerDonnees(self):
        """Filtre les lignes selon les critères actifs"""
        for ligne in range(self.table.rowCount()):
            afficher = True

            for col in range(self.table.columnCount()):
                item = self.table.item(ligne, col)
                if not item:  # Sécurité pour cellules vides
                    continue

                if self.mots_cles[col]:
                    valeur_cellule = item.text()

                    # ========== GESTION SPÉCIALE POUR LES DATES ==========
                    # Si la valeur contient une date-heure et que le filtre contient des dates seules
                    if self.is_date_format(valeur_cellule):
                        # Extraire la partie date uniquement
                        date_cellule = valeur_cellule[:10]
                        if date_cellule not in self.mots_cles[col]:
                            afficher = False
                            break
                    else:
                        # Comparaison normale pour les textes
                        if valeur_cellule not in self.mots_cles[col]:
                            afficher = False
                            break

            self.table.setRowHidden(ligne, not afficher)
