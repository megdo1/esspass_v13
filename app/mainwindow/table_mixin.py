"""Affichage, filtrage et pagination des tableaux de résultats."""

from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox, QLineEdit
from PyQt5.QtCore import Qt
from app.dialogs.ui_graphdialog import GraphDialog


class TableMixin:
    """Affichage, filtrage et pagination des tableaux de résultats."""

    def display_table_for_view(self, df, table, widget, editable_col=None):
        print("DF shape:", df.shape)
        print("DF dtypes:", df.dtypes)
        print("DF head:", df.head())

        # Robustesse : tout en str, index simple, pas de category !
        df = df.astype(str).fillna("")
        df = df.reset_index(drop=True)
        widget.df_current = df
        widget.df_filtered = df  # ← on utilise df_filtered pour pagination
        widget.page_index = 0  # ← on commence toujours à la première page
        widget.filters_container.setVisible(True)

        self.refresh_table_page(widget, table, editable_col)

        widget.btn_prev.setVisible(True)
        widget.btn_next.setVisible(True)
        widget.label_page.setVisible(True)

    def on_filter_changed(self, widget, idx, val, editable_col=None):
        # Met à jour la valeur du filtre idx
        # Puis applique TOUS les filtres en appelant une version adaptée de apply_filters
        self.apply_filters(widget, editable_col)

    def create_filters_if_needed(self, widget, df, editable_col=None):
        # Supprime et recrée UNIQUEMENT si structure changée (nb colonnes)
        if hasattr(widget, "filters_editors") and len(widget.filters_editors) == len(df.columns):
            return  # déjà fait
        # sinon, supprime tous les filtres et recrée
        while widget.filters_layout.count():
            item = widget.filters_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        widget.filters_editors = []
        for i, col in enumerate(df.columns):
            edit = QLineEdit()
            edit.setPlaceholderText(str(col))
            edit.setFixedWidth(140)
            # Correction du bug "lambda" :
            edit.textChanged.connect(lambda val, idx=i: self.on_filter_changed(widget, idx, val, editable_col))
            widget.filters_layout.addWidget(edit)
            widget.filters_editors.append(edit)

    def ensure_filters_exist(self, widget, df, editable_col=None):
        # Si les filtres existent déjà et le nombre de colonnes est inchangé, ne rien faire
        if hasattr(widget, "filters_editors") and len(widget.filters_editors) == len(df.columns):
            return
        # Sinon, supprimer les anciens filtres et recréer
        while widget.filters_layout.count():
            item = widget.filters_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        widget.filters_editors = []
        for i, col in enumerate(df.columns):
            edit = QLineEdit()
            edit.setPlaceholderText(str(col))
            edit.setFixedWidth(140)
            # Correction du bug lambda
            edit.textChanged.connect(lambda val, idx=i: self.on_filter_changed(widget, idx, val, editable_col))
            widget.filters_layout.addWidget(edit)
            widget.filters_editors.append(edit)

    def apply_filters(self, widget, editable_col=None):
        df = widget.df_current
        if df is None:
            return
        df_filtered = df.copy()
        for i, edit in enumerate(widget.filters_editors):
            val = edit.text().strip()
            if val:
                col = df.columns[i]
                df_filtered = df_filtered[df_filtered[col].astype(str).str.contains(val, case=False, na=False)]

        df_filtered = df_filtered.astype(str).fillna("").reset_index(drop=True)
        widget.df_filtered = df_filtered
        widget.page_index = 0
        self.refresh_table_page(widget, widget.table, editable_col)

    def update_table_display(self, df, table, editable_col=None):

        df = df.astype(str).fillna("")
        df = df.reset_index(drop=True)

        # DÉFUSIONNER TOUTES LES CELLULES AVANT RÉAFFICHAGE
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                table.setSpan(row, col, 1, 1)

        table.clear()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)

        for i in range(len(df)):
            # Détection d’une ligne "Données manquantes" pour Visites cycliques
            is_missing = (
                    "Indicateur (Validation) en %" in df.columns and
                    str(df.at[i, "Indicateur (Validation) en %"]).strip().lower() == "données manquantes"
            )

            if is_missing:
                from PyQt5.QtGui import QBrush, QColor
                jaune_clair = QBrush(QColor(255, 255, 153))  # Jaune pâle

                # 1. Afficher l’infrapôle (1ère colonne)
                item_infrapole = QTableWidgetItem(str(df.at[i, "Infrapôles"]))
                item_infrapole.setFlags(item_infrapole.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 0, item_infrapole)

                # 2. Créer la cellule fusionnée pour le reste, fond jaune clair
                item_missing = QTableWidgetItem("Données manquantes")
                font = item_missing.font()
                font.setBold(True)
                item_missing.setFont(font)
                item_missing.setTextAlignment(Qt.AlignCenter)
                item_missing.setFlags(item_missing.flags() & ~Qt.ItemIsEditable)
                item_missing.setBackground(jaune_clair)

                # Fusionner toutes les colonnes sauf la 1ère (de 1 à N)
                table.setSpan(i, 1, 1, table.columnCount() - 1)
                table.setItem(i, 1, item_missing)
                # Vider les autres cellules fusionnées (optionnel)
                for j in range(2, table.columnCount()):
                    # table.setItem(i, j, QTableWidgetItem())
                    cell = QTableWidgetItem()
                    cell.setBackground(jaune_clair)
                    table.setItem(i, j, cell)
            else:
                for j in range(len(df.columns)):
                    value = str(df.iat[i, j])
                    if editable_col and df.columns[j] == editable_col:
                        item = QTableWidgetItem(value)
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                        table.setItem(i, j, item)
                    else:
                        item = QTableWidgetItem(value)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        table.setItem(i, j, item)

    def show_graph_dialog(self, key, widget):
        df = widget.df_current.copy() if widget.df_current is not None else self.indicators_by_view.get(key)
        if df is None or df.empty:
            QMessageBox.information(self, "Graphique", "Aucune donnée à exploiter.")
            return

        df = df.astype(str).fillna("").reset_index(drop=True)
        dlg = GraphDialog(df, key)
        dlg.exec_()

    def sync_commentaires_from_table(self, table, df, commentaire_col="Commentaires"):
        """
        Met à jour le DataFrame 'df' avec les valeurs de la colonne 'Commentaires' du QTableWidget 'table'.
        """
        if commentaire_col not in df.columns:
            return df
        df = df.copy()
        col_index = list(df.columns).index(commentaire_col)
        for row in range(table.rowCount()):
            new_val = table.item(row, col_index)
            if new_val:
                df.iat[row, col_index] = new_val.text()
        return df
