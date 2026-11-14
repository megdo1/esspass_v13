# app/widgets/sauvegardes_combo.py
import os, json
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import logging

logger = logging.getLogger(__name__)

def _parse_date(s):
    if not s:
        return datetime.min
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(str(s), fmt)
        except Exception:
            logger.debug("Exception ignorée dans _parse_date", exc_info=True)
            continue
    return datetime.min

def load_sauvegardes_metadata(dir_saves=None):
    """Lit sauvegardes/metadata.json et renvoie une liste de dicts ([] si absent/erreur)."""
    if dir_saves is None:
        dir_saves = os.path.join(os.getcwd(), "sauvegardes")
    path = os.path.join(dir_saves, "metadata.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        logger.debug("Exception ignorée dans load_sauvegardes_metadata", exc_info=True)
        return []

def populate_sauvegardes_combo(combo, sauvegardes_metadata,
                               *, category_order=None, with_icons=True,
                               placeholder="Choisir une sauvegarde", min_width=320):
    """
    Remplit un QComboBox avec:
      - un placeholder non sélectionnable
      - des entêtes de catégories non sélectionnables (gras)
      - items triés par date_valeur décroissante
      - metadata attaché sur chaque item (Qt.UserRole)
    """
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(placeholder)
    model = combo.model()
    index0 = model.index(0, 0)
    model.setData(index0, 0, Qt.UserRole - 1)  # désactive le placeholder

    # groupement par catégorie
    by_cat = {}
    for md in sauvegardes_metadata:
        cat = str(md.get("categorie", "(Sans catégorie)")).strip() or "(Sans catégorie)"
        by_cat.setdefault(cat, []).append(md)

    # ordre des catégories
    cats = list(by_cat.keys())
    if category_order:
        pref = [c for c in category_order if c in by_cat]
        others = sorted([c for c in cats if c not in pref], key=lambda x: x.lower())
        cats = pref + others
    else:
        cats = sorted(cats, key=lambda x: x.lower())

    icon = QIcon.fromTheme("media-floppy") if with_icons else QIcon()

    for cat in cats:
        # Entête de catégorie
        header_text = f"— {cat} —"
        combo.addItem(header_text)
        idx = combo.count() - 1
        idx_model = model.index(idx, 0)
        model.setData(idx_model, 0, Qt.UserRole - 1)          # désactive l'entête
        font = QFont(combo.font()); font.setBold(True)
        model.setData(idx_model, font, Qt.FontRole)           # gras

        # Items triés par date de valeur (desc)
        items = sorted(by_cat[cat], key=lambda m: _parse_date(m.get("date_valeur")), reverse=True)
        for md in items:
            nom = md.get("nom_sauvegarde", "Sans nom")
            date_valeur = md.get("date_valeur", "")
            text = f"   •  {nom}   ({date_valeur})"
            if with_icons:
                combo.addItem(icon, text)
            else:
                combo.addItem(text)
            row = combo.count() - 1
            row_index = model.index(row, 0)
            model.setData(row_index, md, Qt.UserRole)         # attache le dict metadata

    # Style (identique partout)
    combo.setStyleSheet(f"""
        QComboBox {{
            border: 1px solid #aaa;
            border-radius: 6px;
            padding: 4px 12px 4px 8px;
            font-size: 13px;
            background: white;
            min-width: {min_width}px;
        }}
        QComboBox:focus {{
            border: 1.5px solid #1F4E9C;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid #1F4E9C;
            padding: 4px;
            outline: 0;
            selection-background-color: #E8EEF9;
            selection-color: #0B1F3F;
        }}
        QComboBox QAbstractItemView::item {{
            height: 28px;
            padding: 2px 8px;
        }}
    """)
    combo.blockSignals(False)
