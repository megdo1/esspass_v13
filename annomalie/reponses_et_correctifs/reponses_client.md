# ES-PASS – Réponses aux remontées client

Synthèse : **3 anomalies avérées** (corrigées ou corrigeables), **1 point d'explication** (indicateurs, remontés deux fois).

| # | Remontée | Verdict | Action |
|---|----------|---------|--------|
| 1 | Erreur critique à l'export du rapport COPIL (`fontlist-v330.json.matplotlib-lock`) | **Anomalie avérée** | Correctif livré (code) |
| 2 | Écart 77 demandes / 61 réalisées / 9 en cours (06→12/03) | Pas d'anomalie de calcul | Réponse + évolution proposée |
| 3 | « GAA » à remplacer par « GAIA » (interfaces SI) | **Anomalie de donnée avérée** | Script SQL livré |
| 4 | Date de traitement non saisissable à la création d'une demande déjà traitée | **Anomalie avérée** | Correctif livré (code) |
| 5 | Écart 67 demandes / 61 réalisées / 3 à étudier + 1 en cours (10→16/07) | Pas d'anomalie de calcul | Réponse (idem 2) |

---

## 1. Erreur à l'export du rapport COPIL

**Diagnostic.** Le message `FileNotFoundError … \AppData\Local\Temp\tmpXXXX\fontlist-v330.json.matplotlib-lock`
vient de la bibliothèque de graphiques (matplotlib). Dans l'application packagée, elle stocke son cache de polices dans un
**dossier temporaire créé au lancement**. Si ce dossier est supprimé pendant que l'application reste ouverte (nettoyage
automatique de `%TEMP%` par Windows ou par un outil de sécurité/IT), la génération d'un rapport échoue au moment d'écrire ce cache.
Ce n'est pas lié aux données ni au rapport sélectionné. J'ai reproduit exactement cette erreur en supprimant ce dossier en cours de session.

**Contournement immédiat (client).** Fermer puis relancer ES-PASS, puis relancer l'export.

**Correctif (livré dans le code).**
- Le cache matplotlib est désormais stocké dans un dossier **persistant** : `%LOCALAPPDATA%\ES-PIGC\matplotlib`
  (plus de dossier temporaire jetable).
- Par sécurité, l'application **recrée** ce dossier s'il a disparu avant chaque génération/export de rapport.

> Message au client : « Il s'agit d'une anomalie technique de l'application, sans impact sur vos données : un dossier
> temporaire utilisé pour la génération des graphiques pouvait être supprimé par Windows pendant que l'application restait
> ouverte. En attendant la prochaine version, relancer l'application suffit. Le correctif sera livré dans la prochaine version. »

*Réserve :* la cause exacte (nettoyage du dossier temporaire) est la plus probable d'après le message et le nom du dossier ; si l'erreur
se reproduisait après correctif, demander la ligne « Show Details… » complète.

---

## 2 et 5. Écarts entre le cadre « Indicateurs clés » et le listing

**Diagnostic : le calcul est correct, ce sont deux périmètres différents.**

Le cadre « Indicateurs clés » (onglet *Métriques*) calcule, sur les demandes dont la **date de réception** est dans la période :

- **Total demandes** = **toutes** les demandes reçues, quel que soit leur état ;
- **Demandes réalisées** = états **Traitée + Fermée** ;
- **Taux de réalisation** = réalisées / total.

Le listing PASS, lui, **masque par défaut** les demandes **Archivée** et **Annulée** (cases « Afficher les demandes archivées /
annulées » décochées). Les états **À étudier**, **Hors assistance** et **Non applicable** ne sont pas des « en cours » non plus.

Donc : `total − réalisées` = **En cours + À étudier + Annulée + Archivée + Hors assistance + Non applicable**.

- Cas du 06→12/03 : 77 − 61 = 16 = 9 « en cours » + **7 autres états** (à étudier, annulées, archivées, hors assistance, non applicable).
- Cas du 10→16/07 : 67 − 61 = 6 = 3 « à étudier » + 1 « en cours » + **2 autres** (très probablement annulées/archivées, masquées par défaut).

*Vérification sur les données de démonstration* (même requête que le rapport) : semaine du 23→27/02 : total 43 = 34 traitées + 6 en cours +
2 annulées + 1 non applicable ; le listing par défaut n'en affiche que 41 (les 2 annulées sont masquées).

**Comment le client peut rapprocher les chiffres.** Dans la liste : filtrer sur la période, **cocher « Afficher les demandes archivées »
et « Afficher les demandes annulées »**, puis compter par colonne *État*. La somme redonne exactement le total du rapport.

> Message au client : « Les chiffres sont cohérents : le total du rapport compte toutes les demandes reçues sur la période, y compris
> celles au statut Annulée, Archivée, Hors assistance, Non applicable ou À étudier. Le listing masque par défaut les archivées et les
> annulées. Les 7 (resp. 2) demandes d'écart correspondent à ces statuts : en cochant "Afficher les demandes archivées" et "annulées" et en
> comptant par État, vous retrouvez le total du rapport. Si vous le souhaitez, envoyez-nous l'export Excel de la période pour que nous
> vérifiions le détail ligne à ligne. Nous vous proposons d'afficher dans le rapport la répartition par état pour éviter cette
> ambiguïté. »

**Évolution proposée (non réalisée, à valider)** : afficher sous le cadre « Indicateurs clés » (et dans l'export Excel) la ventilation
« dont : En cours x · À étudier y · Annulées z · Archivées … », et préciser que « réalisées = Traitée + Fermée ». Option métier à décider avec le
client : exclure du dénominateur du taux les demandes Annulée / Non applicable / Hors assistance.

---

## 3. Libellé « GAA » → « GAIA »

**Diagnostic.** Anomalie de **donnée** (table `sous_categories`, catégorie « Interfaces SI »), pas de code : ce libellé n'est référencé
nulle part dans l'application et il n'existe pas d'écran d'administration des sous-catégories.

**Correctif.** Script `correctif_GAA_vers_GAIA.sql` (fourni, testé sur une copie, rejouable) à exécuter sur la base de production **après
sauvegarde du fichier .db**. Les demandes déjà créées référencent la sous-catégorie par identifiant : leur historique affichera « GAIA ».
Les utilisateurs doivent **relancer l'application** (les listes sont chargées au démarrage).

> Message au client : « C'est corrigé côté base dès l'exécution du script d'administration ; le libellé "GAIA" apparaîtra dans la liste après
> redémarrage de l'application, y compris sur les demandes existantes. »

---

## 4. Date de traitement non saisissable à la création

**Diagnostic : anomalie avérée.** Le formulaire de création n'avait pas de champ « Date de traitement » et l'enregistrement ne la
prenait pas en compte. Une demande créée directement à l'état « Traitée » restait donc **sans date de traitement**, et n'entrait pas dans le calcul du
délai moyen (vérifié en base : `date_traitement` vide).

**Correctif (livré dans le code).** Dans « Créer une nouvelle demande », lorsque l'état est **Traitée** ou **Fermée**, un champ **Date de traitement**
(calendrier, aujourd'hui par défaut) apparaît et est enregistré ; il est masqué pour les autres états. Une date future est refusée (comme dans la modification d'une demande).
Testé : états À étudier / En cours (aucune date), Traitée (date du jour), Fermée (date choisie).

**Point d'attention.** La date de **réception** reste fixée automatiquement à la date de création. Pour saisir un ticket reçu plus tôt et déjà traité,
le délai sera calculé depuis la création ; si le besoin existe, nous proposons de rendre aussi la date de réception modifiable.

**Rattrapage des demandes existantes.** Le script `requete_demandes_traitees_sans_date.sql` liste les demandes Traitée/Fermée sans date de traitement (sur la base
de démonstration : 7). Elles se complètent via *Gérer* → champ « Date de traitement ».

> Message au client : « Corrigé : un champ "Date de traitement" apparaît désormais à la création dès que l'état est Traitée ou Fermée. Pour les
> demandes déjà créées sans date, vous pouvez la renseigner via Gérer ; nous pouvons aussi vous fournir la liste de celles concernées. »
