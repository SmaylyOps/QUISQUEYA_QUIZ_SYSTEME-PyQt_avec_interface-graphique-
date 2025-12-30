# 🎯 Quisqueya Quiz Système

## Un projet Python pur, pensé comme une vraie application

**Quisqueya Quiz Système** est une application de quiz en **ligne de commande (CLI)** conçue, structurée et développée **exclusivement en Python**.

Ici, Python n’est pas un simple script d’automatisation : c’est le **cœur complet du projet**. De la logique du jeu à la gestion du temps, des fichiers et des scores, tout repose sur les capacités du langage.

Le programme est proposé sous deux formes :

*  un **fichier Python (.py)** lisible, modifiable et pédagogique
*  une **application Windows (.exe)** compilée avec **PyInstaller**, utilisable sans Python installé

---

## 🚀 Ce que fait réellement l’application

Quisqueya Quiz Système simule un **jeu éducatif complet** en console :

* Pose des questions chronométrées
* Analyse les réponses de l’utilisateur (numéro ou texte, sans sensibilité aux accents)
* Gère plusieurs modes de jeu
* Calcule et sauvegarde les scores
* Construit un historique et un classement des joueurs
* Permet une révision détaillée après chaque partie

Le tout est exécuté **uniquement avec Python**, sans framework externe.

---

##  Python au centre du projet

### Pourquoi Python ?

Le projet a été volontairement conçu pour exploiter les **fondamentaux avancés de Python** :

* Programmation orientée objet (classes, responsabilités claires)
* Gestion du temps et des threads
* Lecture et écriture de fichiers JSON
* Manipulation de chaînes et normalisation des entrées utilisateur
* Structuration d’un programme complet et maintenable

Aucune dépendance lourde, aucun artifice : **Python fait tout**.

### Technologies et modules utilisés

* **Python 3** (langage principal)
* Modules standards :

  * `json` – persistance des données
  * `os` – gestion des fichiers
  * `time` – chronométrage
  * `random` – sélection aléatoire des questions
  * `threading` – gestion du temps sans bloquer le programme
  * `dataclasses` – structuration propre des données
* **PyInstaller** – transformation du script Python en exécutable Windows

---

## 📂 Organisation du projet

La structure du projet reflète une approche claire et professionnelle :

```text
quisqueya-quiz/
│
├── QUISQUEYA_QUIZ_SYSTEME.py   # Code source Python (logique complète)
├── QUISQUEYA_QUIZ_SYSTEME.exe  # Exécutable Windows généré depuis Python
├── questions/                  # Banque de questions (fichiers JSON)
├── scores.json                 # Historique et classement des scores
└── README.md                   # Documentation du projet
```

Chaque fichier a un rôle précis, facilitant la lecture, la maintenance et l’évolution du programme.

---

## ▶️ Exécution du programme

### 🐍 Exécution avec Python

**Prérequis :** Python 3 installé sur la machine

```bash
QUISQUEYA_QUIZ_SYSTEME.py
```

Cette option permet de lire, modifier et comprendre directement le code Python.

---

### 🖥 Exécution via l’application Windows (.exe)

1. Lancer `QUISQUEYA_QUIZ_SYSTEME.exe`
2. Aucun environnement Python requis

L’exécutable est une **conversion directe du programme Python**, sans perte de fonctionnalités.

---

## 📝 Structure des questions (JSON)

Les questions sont volontairement externalisées afin de séparer **logique Python** et **contenu pédagogique** :

```json
[
  {
    "id": 1,
    "theme": "Culture générale",
    "niveau": "Facile",
    "texte": "Quelle est la capitale d’Haïti ?",
    "options": ["Cap-Haïtien", "Port-au-Prince", "Gonaïves"],
    "bonne_option": 1
  }
]
```

Cette approche permet d’ajouter ou modifier des questions **sans toucher au code Python**.

---

## 📊 Scores et logique métier

* Les scores sont automatiquement sauvegardés dans un fichier JSON
* Le classement est recalculé à chaque partie
* Les statistiques par joueur sont générées dynamiquement

Toute la logique est gérée par des **structures Python**, sans base de données externe.

---

## 👥 Auteurs

* **Smayly Chrislend DUMEZIL**
  Étudiant en **Génie Électrique**
  Code étudiant : **DU216309**

* **Jorguinio MARCELIN**
  Étudiant en **Génie Informatique**
  Code étudiant : **MA245905**

---

## 🎓 Cadre pédagogique

**Projet 7 – Application Console “Quiz Python”**
```
Objectif principal : démontrer la capacité à concevoir une **application complète en Python**, en utilisant :

* les boucles
* la programmation orientée objet
* la gestion de fichiers
* la structuration d’un projet réel

### Compétences développées

* Maîtrise approfondie du langage Python
* Conception d’un programme CLI robuste
* Séparation logique / données
* Création d’un exécutable Windows à partir d’un script Python
```
---

## 📄 Licence

Projet libre d’utilisation à des fins **éducatives et personnelles**.

---

✨ *Quisqueya Quiz Système illustre comment Python, seul, peut devenir une véritable application.*
