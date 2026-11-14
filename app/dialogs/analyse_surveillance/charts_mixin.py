"""Construction des graphiques (donuts, barres empilées, camemberts)."""

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ChartsMixin:
    """Construction des graphiques (donuts, barres empilées, camemberts)."""

    def _tab_donut_utm_df(self, titre: str, df_utm, return_container=False):
        import numpy as np
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib import gridspec

        cont = QWidget()
        v = QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 0, 0)

        # Larger figure + constrained layout (no tight_layout warnings)
        fig = Figure(figsize=(11.5, 7.6), constrained_layout=True)
        canvas = FigureCanvas(fig)

        # Two columns: left = donut, right = dedicated legend pane
        gs = gridspec.GridSpec(nrows=1, ncols=2, figure=fig, width_ratios=[3.4, 1.0])
        ax = fig.add_subplot(gs[0, 0])
        ax_leg = fig.add_subplot(gs[0, 1])
        ax_leg.axis("off")  # legend-only area

        if df_utm is None or df_utm.empty:
            ax.text(0.5, 0.5, "Aucune donnée", ha="center", va="center")
            ax.axis("off")
        else:
            labels = df_utm["UTM"].astype(str).tolist()
            sizes = df_utm["Nombre"].astype(int).tolist()
            pcts = df_utm["Pourcentage"].astype(float).tolist()

            # Donut a bit thicker so it reads well at larger size
            wedges, _ = ax.pie(
                sizes,
                startangle=90,
                counterclock=False,
                wedgeprops=dict(width=0.36)
            )
            ax.axis("equal")
            ax.margins(0.02)

            # --- Smarter label ventilation (left/right split + vertical spreading)
            angles = [(w.theta1 + w.theta2) / 2.0 for w in wedges]
            r_label = 1.16
            raw = np.array([[r_label * np.cos(np.deg2rad(a)),
                             r_label * np.sin(np.deg2rad(a))] for a in angles])

            left = [i for i, (x, _) in enumerate(raw) if x < 0]
            right = [i for i, (x, _) in enumerate(raw) if x >= 0]

            # gap depends on how many labels we have
            base_gap = 0.06 + 0.55 / max(len(labels), 4)

            def spread(idxs, min_gap=base_gap):
                pts = sorted([(i, raw[i, 1]) for i in idxs], key=lambda t: t[1])
                if not pts: return
                ys = [p[1] for p in pts]
                for k in range(1, len(ys)):
                    if ys[k] - ys[k - 1] < min_gap:
                        ys[k] = ys[k - 1] + min_gap
                for (idx, _), y_new in zip(pts, ys):
                    raw[idx, 1] = y_new

            spread(left);
            spread(right)

            # tiny alternated jiggle to avoid perfect alignments
            for k in range(len(raw)):
                raw[k, 1] += (0.02 if k % 2 else -0.02)

            # Place labels with connectors
            for i, w in enumerate(wedges):
                n = sizes[i]
                pct_val = float(pcts[i])
                pct_txt = "<0.1%" if (n > 0 and 0 < pct_val < 0.05) else f"{pct_val:.1f}%"
                txt = f"{n} ({pct_txt})"

                x, y = raw[i]
                # push text a bit further than the anchor side
                xytext = (1.38 * (1 if x >= 0 else -1), y)

                theta = np.deg2rad(angles[i])
                x0, y0 = (0.86 * np.cos(theta), 0.86 * np.sin(theta))  # on the ring

                ax.annotate(
                    txt,
                    xy=(x0, y0),
                    xytext=xytext,
                    ha='left' if x >= 0 else 'right',
                    va='center',
                    fontsize=11,
                    clip_on=False,
                    zorder=3,
                    arrowprops=dict(
                        arrowstyle='-',
                        shrinkA=0, shrinkB=0,
                        connectionstyle='arc3,rad=0.18'
                    )
                )

            # Legend in its own axes (always visible, never overlaps)
            # Use the actual wedges as handles to keep colors consistent
            ax_leg.legend(
                wedges, labels,
                loc='center',
                frameon=False,
                fontsize=11,
                handlelength=1.4,
                borderaxespad=0.0
            )

        ax.set_title(titre, loc="left", fontsize=13, pad=8)

        v.addWidget(canvas)
        return cont if return_container else cont

    def _tab_bar_hstack_cat_urgences_df(self, titre: str, df_cat, return_container=False):
        import numpy as np

        if df_cat is not None and not df_cat.empty:
            df_cat = df_cat[(df_cat["U0s"] > 0) | (df_cat["U1s"] > 0)]

        cont = QWidget();
        v = QVBoxLayout(cont);
        v.setContentsMargins(0, 0, 0, 0)
        # fig = Figure(figsize=(7.4, 5.0));
        # après :
        fig = Figure(figsize=(7.8, 5.4))  # un cran plus grand
        canvas = FigureCanvas(fig);
        ax = fig.add_subplot(111)

        if df_cat is None or df_cat.empty:
            ax.text(0.5, 0.5, "Aucune donnée", ha="center", va="center");
            ax.axis("off")
        else:
            cats = df_cat["Catégorie"].astype(str).tolist()[::-1]
            u0 = df_cat["U0s"].astype(int).tolist()[::-1]
            u1 = df_cat["U1s"].astype(int).tolist()[::-1]
            tot = df_cat["Total"].astype(int).tolist()[::-1]
            y = np.arange(len(cats))

            """# b0 = ax.barh(y, u0, label="U0", height=0.55)
            b0 = ax.barh(y, u0, label="U0", height=0.75)
            # b1 = ax.barh(y, u1, left=u0, label="U1", height=0.55)
            b1 = ax.barh(y, u1, left=u0, label="U1", height=0.75)

            for rect, val in zip(b0, u0):
                if val: ax.text(rect.get_x() + rect.get_width() / 2, rect.get_y() + rect.get_height() / 2, f"{val}",
                                ha="center", va="center", fontsize=9)
            for rect, val in zip(b1, u1):
                if val: ax.text(rect.get_x() + rect.get_width() / 2, rect.get_y() + rect.get_height() / 2, f"{val}",
                                ha="center", va="center", fontsize=10, fontweight="bold")

            for yy, total, leftsum in zip(y, tot, (np.array(u0) + np.array(u1)).tolist()):
                ax.text(leftsum + 1, yy, f"{total}", va="center", fontsize=11, fontweight="bold", color="#1f77b4")"""

            # Déterminer la largeur max pour ajuster les limites X
            max_val = max(tot) if tot else 0
            offset = max_val * 0.05  # marge = 5% de la plus grande valeur
            ax.set_xlim(0, max_val + offset)

            # Tracer les barres
            b0 = ax.barh(y, u0, label="U0", height=0.75)
            b1 = ax.barh(y, u1, left=u0, label="U1", height=0.75)

            # Étiquettes internes U0
            for rect, val in zip(b0, u0):
                if val:
                    ax.text(rect.get_x() + rect.get_width() / 2,
                            rect.get_y() + rect.get_height() / 2,
                            f"{val}", ha="center", va="center", fontsize=9)

            # Étiquettes internes U1
            for rect, val in zip(b1, u1):
                if val:
                    ax.text(rect.get_x() + rect.get_width() / 2,
                            rect.get_y() + rect.get_height() / 2,
                            f"{val}", ha="center", va="center", fontsize=10, fontweight="bold")

            # Totaux — placés avec plus de marge à droite
            for yy, total, leftsum in zip(y, tot, (np.array(u0) + np.array(u1)).tolist()):
                ax.text(leftsum + (offset * 0.5), yy,  # décalage proportionnel
                        f"{total}", va="center", fontsize=11,
                        fontweight="bold", color="#1f77b4")

            ax.set_yticks(y);
            ax.set_yticklabels(cats);
            ax.invert_yaxis()
            # ax.legend(loc="upper left");
            # Légende à droite, hors de la zone de tracé
            ax.legend(
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                borderaxespad=0.,
                frameon=False
            )

            # ax.set_xlabel("Nombre")

            ax.set_ylim(-0.5, len(cats) - 0.5)
            ax.set_xlabel("Nombre")
            ax.set_title(titre, loc="left", fontsize=12, pad=6)

        ax.set_title(titre, loc="left", fontsize=11, pad=6)
        # hoho
        ax.grid(axis='x', linestyle=':', linewidth=0.7, alpha=0.6)
        ax.set_axisbelow(True)

        # fig.tight_layout(rect=[0.02, 0.04, 0.96, 0.96])
        # fig.tight_layout(rect=[0.02, 0.04, 0.88, 0.96])
        fig.tight_layout(rect=[0.02, 0.04, 0.80, 0.96])  # 0.80 au lieu de 0.96 pour réserver de l’espace légende
        v.addWidget(canvas)
        return cont if return_container else cont

    def _draw_pie(self, ax, labels_statut, sizes, pcts, titre=""):
        """
        Dessine un camembert avec étiquettes externes 'nombre (xx%)' déchevauchées
        et traits de liaison depuis chaque secteur.
        """
        import numpy as np

        # camembert
        wedges, _ = ax.pie(
            sizes,
            startangle=90,
            counterclock=False
        )
        ax.axis('equal')

        # Prépare les positions polaires des étiquettes
        # angle au centre de chaque wedge
        angles = [(w.theta1 + w.theta2) / 2.0 for w in wedges]
        # coordonnées brutes à rayon r_label (légèrement extérieur au disque)
        r_label = 1.12
        raw_pos = np.array([[r_label * np.cos(np.deg2rad(a)), r_label * np.sin(np.deg2rad(a))] for a in angles])

        # Sépare gauche/droite pour éviter les croisements
        left_idx = [i for i, (x, _) in enumerate(raw_pos) if x < 0]
        right_idx = [i for i, (x, _) in enumerate(raw_pos) if x >= 0]

        def spread(indexes, min_gap=0.09):
            # Écarte les y sur un même côté pour éviter les chevauchements
            pts = sorted([(i, raw_pos[i, 1]) for i in indexes], key=lambda t: t[1])
            if not pts: return
            y = [p[1] for p in pts]
            y_sorted = y[:]
            for k in range(1, len(y_sorted)):
                if y_sorted[k] - y_sorted[k - 1] < min_gap:
                    y_sorted[k] = y_sorted[k - 1] + min_gap
            # Applique le nouvel ordonnancement aux positions
            for (orig, _), newy in zip(pts, y_sorted):
                raw_pos[orig, 1] = newy

        spread(left_idx, min_gap=0.10)
        spread(right_idx, min_gap=0.10)

        # Place les étiquettes + traits (leaders)
        for i, w in enumerate(wedges):
            """n = sizes[i]
            pct = int(round(pcts[i]))
            txt = f"{n} ({pct}%)"

            x, y = raw_pos[i]
            # point d’ancrage (légèrement plus loin que le rayon du texte)
            xytext = (1.22 * np.sign(x), y)

            # Trait de liaison : du bord du wedge -> point proche de l’étiquette
            # On prend le point sur le cercle de rayon 1 (bord du disque) aligné avec l’angle du wedge
            theta = np.deg2rad(angles[i])
            x0, y0 = (np.cos(theta), np.sin(theta))  # bord du disque
            # annotation
            ax.annotate(
                txt,
                xy=(x0, y0),
                xytext=xytext,
                ha='left' if x >= 0 else 'right',
                va='center',
                fontsize=9,
                arrowprops=dict(
                    arrowstyle='-',
                    shrinkA=0, shrinkB=0,
                    connectionstyle='angle3,angleA=0,angleB=90'
                )
            )"""
            n = sizes[i]
            pct_val = float(pcts[i])  # vient du DF (déjà en 1 décimale)

            # Format anti "0%"
            if n > 0 and 0 < pct_val < 0.05:
                pct_txt = "<0.1%"
            else:
                pct_txt = f"{pct_val:.1f}%"

            txt = f"{n} ({pct_txt})"

            x, y = raw_pos[i]
            xytext = (1.22 * (1 if x >= 0 else -1), y)

            theta = np.deg2rad(angles[i])
            x0, y0 = (np.cos(theta), np.sin(theta))

            ax.annotate(
                txt,
                xy=(x0, y0),
                xytext=xytext,
                ha='left' if x >= 0 else 'right',
                va='center',
                fontsize=9,
                arrowprops=dict(
                    arrowstyle='-',
                    shrinkA=0, shrinkB=0,
                    connectionstyle='angle3,angleA=0,angleB=90'
                )
            )

        # Légende statuts à droite
        ax.legend(wedges, labels_statut, loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
        # Légende statuts à droite (plus loin)
        """ax.legend(wedges, labels_statut,
                  loc='center left',
                  bbox_to_anchor=(1.30, 0.5),  # avant: 1.02
                  fontsize=9,
                  borderaxespad=0.,
                  frameon=False)"""

    def _build_pie_widget(self, categorie, df_cat):
        cont = QWidget()
        v = QVBoxLayout(cont)
        v.setContentsMargins(0,0,0,0)

        # Titre du camembert (ex: "VI 2")
        lbl = QLabel(f"{categorie} 2")
        lbl.setStyleSheet("font-weight: bold;")
        v.addWidget(lbl)

        if df_cat is None or df_cat.empty:
            v.addWidget(QLabel("Aucune donnée"))
            return cont

        # Figure
        fig = Figure(figsize=(5.2, 3.6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        labels_statut = df_cat["Statut"].tolist()
        sizes = [int(x) for x in df_cat["Nombre"].tolist()]
        pcts = df_cat["Pourcentage"].tolist()

        # Texte sur secteurs = "nombre (xx%)"
        # On met les vraies étiquettes en annotation, et la légende à droite avec le libellé de statut.
        wedge, _ = ax.pie(
            sizes,
            startangle=90,
            counterclock=False
        )
        ax.axis('equal')

        # Annote chaque wedge avec "nombre (xx%)"
        # On s’aligne sur le rendu de l’exemple (nombre + pourcentage entre parenthèses)
        import numpy as np
        ang = np.cumsum([0] + [w.theta2 - w.theta1 for w in wedge])  # cumul des angles
        for w, n, pct in zip(wedge, sizes, pcts):
            theta = (w.theta2 + w.theta1) / 2.0
            x = np.cos(np.deg2rad(theta))
            y = np.sin(np.deg2rad(theta))
            ax.annotate(f"{n} ({int(round(pct))}%)",
                        xy=(x, y), xytext=(1.12*x, 1.12*y),
                        ha='center', va='center', fontsize=9,
                        arrowprops=dict(arrowstyle='-'))

        # Légende à droite avec les libellés 'Statut'
        ax.legend(wedge, labels_statut, loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
        fig.tight_layout()
        v.addWidget(canvas)
        return cont
