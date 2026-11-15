"""Dialogue de détail d'un mail (corps, pièces jointes, réponse)."""

from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel
from PyQt5.QtCore import Qt
import os
import subprocess
from app.utils.ui_helpers import show_info, show_warning, show_error
from app.views.pass_v3.demande_dialogs import EditDemandeDialog


from PyQt5.QtCore import QUrl  # noqa: F401  (type des liens cliqués)
from PyQt5.QtGui import QCursor, QDesktopServices
from PyQt5.QtWidgets import QToolTip

import logging
logger = logging.getLogger(__name__)



class MailDetailsDialog(QDialog):
    """Dialogue pour afficher les détails complets d'un mail"""

    def __init__(self, demande_data, datamanager, parent=None):
        super().__init__(parent)
        # ✅ Configurer les flags de fenêtre pour permettre réduire/maximiser
        self.setWindowFlags(
            Qt.Window |  # Fenêtre indépendante
            Qt.WindowMinimizeButtonHint |  # Bouton réduire
            Qt.WindowMaximizeButtonHint |  # Bouton maximiser
            Qt.WindowCloseButtonHint  # Bouton fermer
        )
        self.setWindowModality(Qt.NonModal)
        self.demande_data = demande_data
        self.datamanager = datamanager
        self.parent = parent  # Ajouter parent pour pouvoir rafraîchir après modification
        self.setWindowTitle(f"Détails du mail - {demande_data.get('sujet', 'Sans sujet')}")
        self.setMinimumSize(900, 700)
        self.initui()

    def initui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # En-tête avec informations principales
        header_group = QGroupBox("📧 Informations du mail")
        header_group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }
        """)
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)

        sujet = self.demande_data.get('sujet', 'NA')
        demandeur = self.demande_data.get('demandeur', 'NA')
        date_reception = self.demande_data.get('datereception', 'NA')

        lbl_sujet = QLabel(f"<b>Sujet :</b> {sujet}")
        lbl_sujet.setWordWrap(True)
        lbl_demandeur = QLabel(f"<b>Demandeur :</b> {demandeur}")
        lbl_date = QLabel(f"<b>Date de réception :</b> {date_reception}")

        header_layout.addWidget(lbl_sujet)
        header_layout.addWidget(lbl_demandeur)
        header_layout.addWidget(lbl_date)

        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)

        # Récupérer les échanges emails depuis la table echanges_emails
        id_demande = self.demande_data.get('id_demande')
        echanges = self.datamanager.get_echanges_by_demande(id_demande) if id_demande else []

        nb_echanges = len(echanges) if echanges else 0
        mail_group = QGroupBox(f"📩 Contenu du mail ({nb_echanges} échange(s))")
        mail_group.setStyleSheet("""
            QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #2F855A; }
        """)
        mail_layout = QVBoxLayout()

        # ✅ CHANGEMENT 1 : QTextEdit → QTextBrowser
        from PyQt5.QtWidgets import QTextBrowser
        self.text_corps = QTextBrowser()  # ← Changer ici
        self.text_corps.setReadOnly(True)
        self.text_corps.setOpenExternalLinks(False)
        # Pas de navigation interne : un clic sur un lien vidait le contenu du mail.
        # On ouvre nous-mêmes les liens (http, https, mailto) et on affiche l'adresse au survol.
        self.text_corps.setOpenLinks(False)
        self.text_corps.anchorClicked.connect(self.open_link)
        self.text_corps.highlighted[QUrl].connect(self.show_link_target)

        # ✅ CHANGEMENT 2 : Corps du mail - Afficher en HTML avec images inline
        if echanges:
            contenu_complet = []
            for echange in echanges:
                expediteur = echange[1] if len(echange) > 1 else "Inconnu"
                date_recep = echange[2] if len(echange) > 2 else "NA"
                contenu = echange[3] if len(echange) > 3 else ""
                type_msg = echange[4] if len(echange) > 4 else "DEMANDE"

                icone = "📧" if type_msg == "DEMANDE" else "💬"

                # ✅ Construire du HTML au lieu de texte brut
                contenu_complet.append("<hr style='border: 1px solid #ccc; margin: 10px 0;'>")
                contenu_complet.append(f"<p style='margin: 5px 0;'><strong>{icone} {type_msg}</strong></p>")
                contenu_complet.append(f"<p style='margin: 5px 0;'><strong>De :</strong> {expediteur}</p>")
                contenu_complet.append(f"<p style='margin: 5px 0;'><strong>Date :</strong> {date_recep}</p>")
                contenu_complet.append("<hr style='border: 1px solid #eee; margin: 10px 0;'>")

                # ✅ Remplacer les CID par les vrais chemins d'images
                if contenu:
                    html_content = self.replace_cid_with_images(contenu, id_demande)
                    contenu_complet.append(html_content)
                else:
                    contenu_complet.append("<p><em>Aucun contenu</em></p>")
                contenu_complet.append("<br>")

            # ✅ Afficher en HTML
            self.text_corps.setHtml("".join(contenu_complet))
        else:
            resume = self.demande_data.get('resume', 'Aucun contenu disponible')
            # ✅ Remplacer les CID même dans le résumé
            html_resume = self.replace_cid_with_images(resume, id_demande)
            self.text_corps.setHtml(html_resume)

        mail_layout.addWidget(self.text_corps)
        mail_group.setLayout(mail_layout)
        main_layout.addWidget(mail_group, 1)

        # Pièces jointes
        pieces_jointes = []
        if id_demande:
            try:
                pieces_jointes = self.datamanager.get_pieces_jointes_by_demande(id_demande)
                # print(f"DEBUG: {len(pieces_jointes)} pièces jointes trouvées pour la demande {id_demande}")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des pièces jointes : {e}")

        if pieces_jointes and len(pieces_jointes) > 0:
            pj_group = QGroupBox(f"📎 Pièces jointes ({len(pieces_jointes)})")
            pj_group.setStyleSheet("""
                QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #B45309; }
            """)
            pj_layout = QVBoxLayout()

            for pj in pieces_jointes:
                pj_line = QHBoxLayout()

                nom_fichier = pj[3] if len(pj) > 2 else "Fichier inconnu"
                chemin = pj[2] if len(pj) > 3 else ""
                taille = pj[4] if len(pj) > 4 else 0

                # Formater la taille
                if taille > 1024 * 1024:
                    taille_str = f"{taille / (1024 * 1024):.2f} Mo"
                elif taille > 1024:
                    taille_str = f"{taille / 1024:.2f} Ko"
                else:
                    taille_str = f"{taille} octets"

                lbl_nom = QLabel(f"📄 {nom_fichier} ({taille_str})")

                btn_ouvrir = QPushButton("Ouvrir")
                btn_ouvrir.setFixedWidth(100)
                btn_ouvrir.setStyleSheet("""
                    QPushButton {
                        background-color: #1F4E9C;
                        color: white;
                        padding: 5px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #1A4286;
                    }
                """)
                btn_ouvrir.clicked.connect(lambda checked, c=chemin: self.open_attachment(c))

                pj_line.addWidget(lbl_nom)
                pj_line.addStretch()
                pj_line.addWidget(btn_ouvrir)

                pj_layout.addLayout(pj_line)

            pj_group.setLayout(pj_layout)
            main_layout.addWidget(pj_group)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Bouton "Répondre au mail"
        btn_repondre = QPushButton("✉️ Répondre au mail")
        btn_repondre.setFixedHeight(40)
        btn_repondre.setStyleSheet("""
            QPushButton {
                background-color: #2F855A;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #276749;
            }
        """)
        btn_repondre.clicked.connect(self.reply_mail)

        # ✅ NOUVEAU : Bouton "Modifier la demande"
        btn_modifier = QPushButton("📝 Modifier la demande")
        btn_modifier.setFixedHeight(40)
        btn_modifier.setStyleSheet("""
            QPushButton {
                background-color: #1F4E9C;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1A4286;
            }
            QPushButton:disabled {
                background-color: #CBD5E0;
                color: #718096;
            }
        """)
        btn_modifier.clicked.connect(self.edit_demande)
        if not self.datamanager.current_user_can('gerer'):
            btn_modifier.setEnabled(False)
            btn_modifier.setToolTip("Votre rôle ne permet pas de modifier une demande.")

        # Bouton "Fermer"
        btn_fermer = QPushButton("❌ Fermer")
        btn_fermer.setFixedHeight(40)
        btn_fermer.setFixedWidth(120)
        btn_fermer.setStyleSheet("""
            QPushButton {
                background-color: #C53030;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_fermer.clicked.connect(self.close)

        btn_layout.addWidget(btn_repondre)
        btn_layout.addWidget(btn_modifier)  # ✅ Ajouter le bouton
        btn_layout.addStretch()
        btn_layout.addWidget(btn_fermer)

        main_layout.addLayout(btn_layout)

    def replace_cid_with_images(self, html_content, id_demande):
        """
        Remplace les références cid: par les chemins des images stockées
        """
        import os

        if not html_content:
            return ""

        noms_par_cid = {}   # content_id -> nom du fichier (sert de libellé si l'image est introuvable)

        # Récupérer toutes les images inline de cette demande
        try:
            images_inline = self.datamanager.get_images_inline_by_demande(id_demande)

            for image in images_inline:
                content_id = image.get('content_id')
                chemin_fichier = image.get('chemin_fichier')  # ✅ Déjà le chemin complet

                if content_id and chemin_fichier:
                    # Nettoyer le content_id (enlever < et > si présents)
                    content_id_clean = content_id.strip('<>').strip()
                    noms_par_cid[content_id_clean] = image.get('nom_fichier')

                    # ✅ Utiliser directement le chemin de la base (comme pour le bouton Ouvrir)
                    # Convertir les \ en / pour l'URL file:///
                    chemin_pour_url = chemin_fichier.replace('\\', '/')

                    # Vérifier que le fichier existe
                    if not os.path.exists(chemin_fichier):
                        logger.warning(f"⚠️ Image introuvable : {chemin_fichier}")
                        continue

                    # Remplacer toutes les occurrences de cid:
                    patterns = [
                        (f'src="cid:{content_id_clean}"', f'src="file:///{chemin_pour_url}"'),
                        (f"src='cid:{content_id_clean}'", f'src="file:///{chemin_pour_url}"'),
                        (f'src=cid:{content_id_clean}', f'src="file:///{chemin_pour_url}"'),
                        # Avec < et >
                        (f'src="cid:<{content_id_clean}>"', f'src="file:///{chemin_pour_url}"'),
                        (f"src='cid:<{content_id_clean}>'", f'src="file:///{chemin_pour_url}"'),
                    ]

                    for pattern, replacement in patterns:
                        html_content = html_content.replace(pattern, replacement)

                    logger.info(f"✅ Image remplacée : cid:{content_id_clean} -> {chemin_fichier}")

        except Exception as e:
            logger.error(f"❌ Erreur remplacement CID: {e}")

        return self.rendre_liens_images_visibles(html_content, noms_par_cid)

    def rendre_liens_images_visibles(self, html_content, noms_par_cid):
        """Un lien qui ne contient qu'une image introuvable (ex. boutons Approuver / Refuser d'un mail
        ServiceNow) serait invisible, donc inutilisable : on affiche à la place un libellé cliquable."""
        import html as html_lib
        import re

        profondeur = 0
        remplacements = []
        for m in re.finditer(r'<a\b[^>]*>|</a\s*>|<img\b[^>]*>', html_content, flags=re.I):
            balise = m.group(0).lower()
            if balise.startswith('</a'):
                profondeur = max(0, profondeur - 1)
            elif balise.startswith('<a'):
                profondeur += 1
            elif profondeur > 0:
                src = re.search(r'src\s*=\s*["\']?cid:<?([^"\'>\s]+?)>?["\'\s>]', m.group(0) + ' ', flags=re.I)
                if not src:
                    continue          # image déjà résolue (file:///) ou non-cid
                alt = re.search(r'alt\s*=\s*["\']([^"\']+)', m.group(0), flags=re.I)
                nom = (alt.group(1) if alt else noms_par_cid.get(src.group(1)) or "")
                nom = re.sub(r'\.(png|jpe?g|gif|bmp)$', '', nom, flags=re.I)
                nom = re.sub(r'[_\-]+', ' ', nom).strip()
                if not nom or nom.lower() == 'image':
                    nom = "lien"
                libelle = html_lib.escape(nom[:1].upper() + nom[1:])
                remplacements.append((m.start(), m.end(), f"<span>🔗 {libelle}</span>"))
        for debut, fin, texte in reversed(remplacements):
            html_content = html_content[:debut] + texte + html_content[fin:]
        return html_content

    LIENS_AUTORISES = ("http", "https", "mailto")

    def open_link(self, url):
        """Ouvre un lien du mail (navigateur ou client de messagerie). Seuls http, https et mailto sont autorisés."""
        if url is None or url.isEmpty():
            return
        schema = url.scheme().lower()
        if schema == "cid":      # image intégrée au mail, pas une adresse
            return
        if schema not in self.LIENS_AUTORISES:
            show_warning(self, "Lien non ouvert", f"Ce type de lien n'est pas pris en charge : {schema or 'inconnu'}")
            return
        if not QDesktopServices.openUrl(url):
            show_warning(self, "Lien", f"Impossible d'ouvrir le lien :\n{url.toString()}")

    def show_link_target(self, url):
        """Affiche l'adresse du lien survolé."""
        if url is None or url.isEmpty() or url.scheme().lower() == "cid":
            QToolTip.hideText()
        else:
            QToolTip.showText(QCursor.pos(), url.toString()[:300], self.text_corps)

    def open_attachment(self, chemin):
        """Ouvre une pièce jointe"""
        if not chemin or not os.path.exists(chemin):
            show_warning(self, "Erreur", f"Fichier introuvable : {chemin}")
            return

        try:
            if os.name == 'nt':
                os.startfile(chemin)
            else:
                subprocess.call(['xdg-open', chemin])
        except Exception as e:
            show_warning(self, "Erreur", f"Impossible d'ouvrir le fichier : {str(e)}")


    def reply_mail(self):
        """Ouvre Outlook avec une réponse pré-remplie en HTML avec images inline"""
        try:
            import win32com.client
            import os
            import re

            destinataire = self.demande_data.get("demandeur", "")
            sujet = self.demande_data.get("sujet", "")
            id_demande = self.demande_data.get("id_demande")

            # Récupérer le contenu HTML
            corps_html_original = self.text_corps.toHtml()

            # Créer un nouvel email Outlook
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)  # 0 = olMailItem

            mail.To = destinataire
            mail.Subject = f"RE: {sujet}"

            # ✅ Récupérer toutes les images inline de cette demande
            images_inline = self.datamanager.get_images_inline_by_demande(id_demande) if id_demande else []

            # Dictionnaire pour mapper les chemins de fichiers vers les CIDs
            cid_mapping = {}

            # Attacher les images et créer les CIDs
            for idx, image in enumerate(images_inline):
                chemin_fichier = image.get("chemin_fichier")
                content_id_original = image.get("content_id", "").strip("<>")

                if chemin_fichier and os.path.exists(chemin_fichier):
                    # Attacher l'image
                    attachment = mail.Attachments.Add(chemin_fichier)

                    # Générer un CID unique
                    cid = f"image_{idx}_{content_id_original}" if content_id_original else f"image_{idx}"

                    # Configurer l'attachement comme inline
                    attachment.PropertyAccessor.SetProperty(
                        "http://schemas.microsoft.com/mapi/proptag/0x3712001F",  # PR_ATTACH_CONTENT_ID
                        cid
                    )

                    # Mapper le chemin de fichier vers le CID
                    cid_mapping[chemin_fichier.replace("\\", "/")] = cid
                    cid_mapping[chemin_fichier.replace("\\", "\\\\")] = cid
                    cid_mapping[chemin_fichier] = cid

            # ✅ Remplacer les chemins de fichiers par les CIDs dans le HTML
            html_modifie = corps_html_original

            for chemin, cid in cid_mapping.items():
                # Remplacer toutes les variantes de chemins
                patterns = [
                    f'src="{chemin}"',
                    f"src='{chemin}'",
                    f'src="file:///{chemin}"',
                    f"src='file:///{chemin}'",
                ]

                replacement = f'src="cid:{cid}"'

                for pattern in patterns:
                    html_modifie = html_modifie.replace(pattern, replacement)

            # Construire le corps de l'email avec le HTML modifié
            corps_reponse = f"""
            <html>
            <body>
            <p>&nbsp;</p>
            <p>&nbsp;</p>
            <hr style="border: 1px solid #ccc;">
            <p><strong>------- Message original -------</strong></p>
            {html_modifie}
            </body>
            </html>
            """

            mail.HTMLBody = corps_reponse

            # Afficher l'email
            mail.Display()

        except Exception as e:
            logger.exception("Erreur non gérée")
            show_error(self, "Erreur", f"Impossible d'ouvrir Outlook:\n{str(e)}")

    def edit_demande(self):
        """NOUVELLE MÉTHODE : Ouvre le dialogue de modification EditDemandeDialog"""
        id_demande = self.demande_data.get('id_demande')

        if not id_demande:
            show_warning(self, "Erreur", "Impossible de modifier : ID de demande introuvable.")
            return
        if not self.datamanager.current_user_can('gerer'):
            show_warning(self, "Droits insuffisants", "Votre rôle ne permet pas de modifier une demande.")
            return
        if id_demande in self.parent.open_dialogs:
            # Si déjà ouverte, la remettre au premier plan
            existing_dialog = self.parent.open_dialogs[id_demande]
            existing_dialog.activateWindow()
            existing_dialog.raise_()
            show_info(
                self,
                "Demande déjà ouverte",
                f"La demande #{id_demande} est déjà ouverte dans une autre fenêtre."
            )
            return
        # ✅ Créer le dialogue
        dialog = EditDemandeDialog(id_demande, self.datamanager , parent=self.parent)
        
        # ✅ ENREGISTRER DANS self.parent.open_dialogs
        self.parent.open_dialogs[id_demande] = dialog

        # ✅ Stocker une référence pour éviter la destruction
        if not hasattr(self, '_edit_dialogs'):
            self._edit_dialogs = []
        self._edit_dialogs.append(dialog)


        dialog.finished.connect(lambda result: self.on_dialog_closed(id_demande, result))

        # ✅ Afficher en non-modal
        dialog.show()

    def on_dialog_closed(self, id_demande, result):
        # Retirer de la liste
        if id_demande in self.parent.open_dialogs:
            del self.parent.open_dialogs[id_demande]

        # Rafraîchir si sauvegardé
        if result == QDialog.Accepted:
            # Rafraîchir les données affichées
            self.demande_data = self.datamanager.get_demande_by_id(id_demande)
            self.parent.load_demandes_table()
