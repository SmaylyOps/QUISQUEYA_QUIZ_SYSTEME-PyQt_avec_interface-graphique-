# -*- coding: utf-8 -*-
# ============================================================================
# IMPORTS
# ============================================================================

import sys
import json
import glob
import os
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# PyQt5 pour l'interface graphique
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QMessageBox, QListWidget,
    QStackedWidget, QGroupBox, QRadioButton, QButtonGroup, QScrollArea,
    QGridLayout, QFrame, QTextEdit, QComboBox, QSpinBox, QLineEdit,
    QInputDialog, QDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap

# Matplotlib pour les graphiques
import matplotlib
matplotlib.use('Qt5Agg')  # Backend PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


# ============================================================================
# CONSTANTES
# ============================================================================

FICHIER_SCORES = "scores.json"
DOSSIER_QUESTIONS = "questions"
DUREE_QUESTION = 20  # secondes par question
NOMBRE_QUESTIONS_MAX = 10

# Couleurs du thème
COULEUR_PRIMAIRE = "#2C3E50"
COULEUR_SECONDAIRE = "#3498DB"
COULEUR_SUCCES = "#27AE60"
COULEUR_ERREUR = "#E74C3C"
COULEUR_ATTENTION = "#F39C12"
COULEUR_FOND = "#ECF0F1"
COULEUR_TEXTE = "#2C3E50"


# ============================================================================
# MODÈLES DE DONNÉES
# ============================================================================

@dataclass
class Question:
    """Représente une question du quiz"""
    id: int
    theme: str
    niveau: str
    texte: str
    options: List[str]
    bonne_option: int

    def est_reponse_correcte(self, index: int) -> bool:
        """Vérifie si l'index correspond à la bonne réponse"""
        return index == self.bonne_option


@dataclass
class ReponseQuestion:
    """Stocke les informations d'une question et sa réponse"""
    numero: int
    question: Question
    reponse_choisie: Optional[int]
    est_correcte: bool
    temps_ecoule: bool
    temps_reponse: float = 0.0  # Temps pris pour répondre

    def obtenir_texte_reponse(self) -> str:
        """Retourne le texte de la réponse choisie"""
        if self.temps_ecoule:
            return " Temps écoulé - Aucune réponse"
        if self.reponse_choisie is None:
            return " Aucune réponse"
        if 0 <= self.reponse_choisie < len(self.question.options):
            return self.question.options[self.reponse_choisie]
        return "⚠ Réponse invalide"

    def obtenir_texte_bonne_reponse(self) -> str:
        """Retourne le texte de la bonne réponse"""
        if 0 <= self.question.bonne_option < len(self.question.options):
            return self.question.options[self.question.bonne_option]
        return "Inconnue"


# ============================================================================
# CLASSE DE STOCKAGE (SCORES)
# ============================================================================

class Stockage:
    """Gère la sauvegarde et le chargement des scores"""

    def __init__(self, chemin: str = FICHIER_SCORES) -> None:
        self.chemin = chemin
        if not os.path.isfile(self.chemin):
            self._creer_fichier_vide()

    def _creer_fichier_vide(self) -> None:
        """Crée un fichier de scores vide"""
        try:
            with open(self.chemin, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[Erreur] Impossible de créer {self.chemin}: {e}")

    def charger_tous(self) -> List[Dict[str, Any]]:
        """Charge tous les scores"""
        try:
            with open(self.chemin, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return []

    def sauvegarder_score(self, entree: Dict[str, Any]) -> None:
        """Sauvegarde un nouveau score"""
        tous_scores = self.charger_tous()
        tous_scores.append(entree)
        temp = f"{self.chemin}.tmp"
        try:
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(tous_scores, f, ensure_ascii=False, indent=2)
            os.replace(temp, self.chemin)
        except IOError as e:
            print(f"[Erreur] Impossible de sauvegarder le score: {e}")

    def top_n(self, n: int = 10, theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retourne les n meilleurs scores"""
        tous_scores = self.charger_tous()
        if theme:
            tous_scores = [s for s in tous_scores if s.get("theme") == theme]

        def cle_tri(s: Dict[str, Any]) -> tuple:
            return (-s.get("score_total", 0), -s.get("pourcentage", 0), s.get("date_heure", ""))

        tous_scores.sort(key=cle_tri)
        return tous_scores[:n]

    def obtenir_themes_depuis_scores(self) -> List[str]:
        """Retourne tous les thèmes uniques des scores enregistrés"""
        tous_scores = self.charger_tous()
        themes = {s.get("theme") for s in tous_scores if s.get("theme")}
        return sorted(themes)

    def compter_occurrences_joueur(self, nom_joueur: str) -> int:
        """Compte combien de fois un nom de joueur apparaît dans les scores"""
        tous_scores = self.charger_tous()
        compteur = sum(1 for s in tous_scores if s.get("joueur_nom", "").lower() == nom_joueur.lower())
        return compteur

    def obtenir_stats_joueur(self, nom_joueur: str) -> Dict[str, Any]:
        """Retourne les statistiques d'un joueur"""
        tous_scores = self.charger_tous()
        scores_joueur = [s for s in tous_scores if s.get("joueur_nom", "").lower() == nom_joueur.lower()]

        if not scores_joueur:
            return {"parties": 0}

        total_parties = len(scores_joueur)
        meilleur_score = max(scores_joueur, key=lambda x: x.get("score_total", 0))
        moyenne_pourcentage = sum(s.get("pourcentage", 0) for s in scores_joueur) / total_parties

        return {
            "parties": total_parties,
            "meilleur_score": meilleur_score.get("score_total", 0),
            "meilleur_pourcentage": meilleur_score.get("pourcentage", 0),
            "moyenne_pourcentage": round(moyenne_pourcentage, 1)
        }


# ============================================================================
# BANQUE DE QUESTIONS
# ============================================================================

class BanqueQuestions:
    """Gère le chargement et la sélection des questions"""

    def __init__(self, dossier: str = DOSSIER_QUESTIONS) -> None:
        self.questions: List[Question] = []
        self.dossier = dossier
        self._charger_questions()

    def _charger_questions(self) -> None:
        """Charge les questions depuis les fichiers JSON"""
        if os.path.isdir(self.dossier):
            motif = os.path.join(self.dossier, "*.json")
            fichiers = sorted(glob.glob(motif))
            for f in fichiers:
                self._charger_fichier(f)
        elif os.path.isfile("questions.json"):
            self._charger_fichier("questions.json")

    def _charger_fichier(self, chemin: str) -> None:
        """Charge un fichier JSON de questions"""
        try:
            with open(chemin, "r", encoding="utf-8") as f:
                donnees = json.load(f)
            if not isinstance(donnees, list):
                print(f"[Avertissement] {chemin} ne contient pas une liste de questions")
                return
            
            for element in donnees:
                if not all(k in element for k in ("id", "theme", "niveau", "texte", "options", "bonne_option")):
                    continue
                try:
                    q = Question(
                        id=int(element["id"]),
                        theme=str(element["theme"]),
                        niveau=str(element["niveau"]),
                        texte=str(element["texte"]),
                        options=list(element["options"]),
                        bonne_option=int(element["bonne_option"])
                    )
                    if not (0 <= q.bonne_option < len(q.options)):
                        continue
                    self.questions.append(q)
                except (ValueError, TypeError, KeyError) as e:
                    print(f"[Avertissement] Erreur lors du chargement de la question {element.get('id')}: {e}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"[Avertissement] Impossible de lire {chemin}: {e}")

    def lister_themes(self) -> List[str]:
        """Retourne la liste des thèmes disponibles"""
        return sorted({q.theme for q in self.questions})

    def filtrer(self, themes: Optional[List[str]] = None,
                niveaux: Optional[List[str]] = None) -> List[Question]:
        """Filtre les questions par thème et/ou niveau"""
        resultat = self.questions
        if themes:
            resultat = [q for q in resultat if q.theme in themes]
        if niveaux:
            resultat = [q for q in resultat if q.niveau in niveaux]
        return resultat

    def echantillonner_questions(self, nombre: int = 10, themes: Optional[List[str]] = None) -> List[Question]:
        """Retourne jusqu'à nombre questions (max 10)"""
        nombre = min(int(nombre), NOMBRE_QUESTIONS_MAX)
        reserve = self.filtrer(themes, niveaux=None)
        if not reserve:
            return []
        if len(reserve) <= nombre:
            random.shuffle(reserve)
            return reserve[:nombre]
        return random.sample(reserve, nombre)


# ============================================================================
# LOGIQUE DU JEU (MOTEUR DU QUIZ)
# ============================================================================

class MoteurQuiz:
    """Gère la logique du quiz (sans interface)"""
    
    def __init__(self, questions: List[Question], nom_joueur: str):
        self.questions = questions
        self.nom_joueur = nom_joueur
        self.index_question_actuelle = 0
        self.score = 0
        self.bonnes = 0
        self.mauvaises = 0
        self.temps_ecoules = 0
        self.historique_reponses: List[ReponseQuestion] = []
        self.horodatage_debut = time.time()
        self.horodatage_fin: Optional[float] = None
        
    def obtenir_question_actuelle(self) -> Optional[Question]:
        """Retourne la question actuelle"""
        if 0 <= self.index_question_actuelle < len(self.questions):
            return self.questions[self.index_question_actuelle]
        return None
    
    def obtenir_numero_question(self) -> int:
        """Retourne le numéro de la question actuelle (1-based)"""
        return self.index_question_actuelle + 1
    
    def obtenir_total_questions(self) -> int:
        """Retourne le nombre total de questions"""
        return len(self.questions)
    
    def est_termine(self) -> bool:
        """Vérifie si le quiz est terminé"""
        return self.index_question_actuelle >= len(self.questions)
    
    def enregistrer_reponse(self, index_reponse: Optional[int], temps_ecoule: bool, temps_reponse: float = 0.0):
        """Enregistre une réponse et met à jour le score"""
        question = self.obtenir_question_actuelle()
        if question is None:
            return
        
        est_correcte = False
        if not temps_ecoule and index_reponse is not None:
            est_correcte = question.est_reponse_correcte(index_reponse)
        
        if est_correcte:
            self.bonnes += 1
            self.score += 1
        else:
            self.mauvaises += 1
            if temps_ecoule:
                self.temps_ecoules += 1
        
        # Enregistrer dans l'historique
        reponse = ReponseQuestion(
            numero=self.obtenir_numero_question(),
            question=question,
            reponse_choisie=index_reponse,
            est_correcte=est_correcte,
            temps_ecoule=temps_ecoule,
            temps_reponse=temps_reponse
        )
        self.historique_reponses.append(reponse)
        
        # Passer à la question suivante
        self.index_question_actuelle += 1
    
    def obtenir_resultats(self) -> Dict[str, Any]:
        """Retourne les résultats du quiz"""
        self.horodatage_fin = time.time()
        duree = int(self.horodatage_fin - self.horodatage_debut)
        total = len(self.questions)
        pourcentage = round((self.bonnes / total) * 100, 1) if total > 0 else 0.0
        
        return {
            "id_partie": f"{self.nom_joueur}_{int(time.time())}",
            "joueur_nom": self.nom_joueur,
            "date_heure": datetime.now(timezone.utc).isoformat(),
            "theme": self.questions[0].theme if len(set(q.theme for q in self.questions)) == 1 else "mix",
            "niveau": self.questions[0].niveau if len(set(q.niveau for q in self.questions)) == 1 else "mix",
            "nombre_questions": total,
            "bonnes": self.bonnes,
            "mauvaises": self.mauvaises,
            "temps_ecoules": self.temps_ecoules,
            "score_total": self.score,
            "pourcentage": pourcentage,
            "duree_seconds": duree
        }


# ============================================================================
# WIDGET GRAPHIQUE MATPLOTLIB
# ============================================================================

class GraphiqueWidget(QWidget):
    """Widget qui affiche un graphique matplotlib intégré dans PyQt"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def afficher_graphique_resultats(self, resultats: Dict[str, Any]):
        """Affiche un graphique des résultats du quiz"""
        self.figure.clear()
        
        # Créer 2 sous-graphiques
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        # Graphique 1 : Camembert des résultats
        bonnes = resultats.get("bonnes", 0)
        mauvaises = resultats.get("mauvaises", 0) - resultats.get("temps_ecoules", 0)
        temps_ecoules = resultats.get("temps_ecoules", 0)
        
        labels = []
        sizes = []
        colors = []
        
        if bonnes > 0:
            labels.append(f'Bonnes\n({bonnes})')
            sizes.append(bonnes)
            colors.append('#27AE60')
        
        if mauvaises > 0:
            labels.append(f'Mauvaises\n({mauvaises})')
            sizes.append(mauvaises)
            colors.append('#E74C3C')
        
        if temps_ecoules > 0:
            labels.append(f'Temps écoulé\n({temps_ecoules})')
            sizes.append(temps_ecoules)
            colors.append('#F39C12')
        
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Répartition des réponses', fontsize=12, fontweight='bold')
        
        # Graphique 2 : Barres horizontales
        categories = ['Bonnes', 'Mauvaises', 'Temps écoulé']
        valeurs = [bonnes, mauvaises, temps_ecoules]
        couleurs = ['#27AE60', '#E74C3C', '#F39C12']
        
        ax2.barh(categories, valeurs, color=couleurs)
        ax2.set_xlabel('Nombre de questions', fontsize=10)
        ax2.set_title('Détail des résultats', fontsize=12, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        # Ajuster l'espacement
        self.figure.tight_layout()
        self.canvas.draw()
    
    def afficher_graphique_classement(self, scores: List[Dict[str, Any]]):
        """Affiche un graphique du classement"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if not scores:
            ax.text(0.5, 0.5, 'Aucune donnée à afficher', 
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Limiter à 10 scores maximum
        scores = scores[:10]
        
        noms = [s.get("joueur_nom", "")[:10] for s in scores]
        pourcentages = [s.get("pourcentage", 0) for s in scores]
        
        # Créer un dégradé de couleurs
        colors = plt.cm.viridis([i/len(scores) for i in range(len(scores))])
        
        bars = ax.barh(noms, pourcentages, color=colors)
        ax.set_xlabel('Pourcentage de réussite (%)', fontsize=10)
        ax.set_title('Top 10 des meilleurs scores', fontsize=12, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(axis='x', alpha=0.3)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                   f'{width:.1f}%', ha='left', va='center', fontsize=9)
        
        self.figure.tight_layout()
        self.canvas.draw()


# ============================================================================
# FENÊTRE DE QUIZ 
# ============================================================================

class FenetreQuiz(QWidget):
    """Fenêtre principale du quiz avec questions et timer"""
    
    signal_quiz_termine = pyqtSignal(dict)
    signal_quiz_abandonne = pyqtSignal()
    
    def __init__(self, moteur: MoteurQuiz, parent=None):
        super().__init__(parent)
        self.moteur = moteur
        self.temps_restant = DUREE_QUESTION
        self.temps_debut_question = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._mise_a_jour_timer)
        
        self._initialiser_ui()
        self._afficher_question()
    
    def _initialiser_ui(self):
        """Initialise l'interface utilisateur"""
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(20)
        
        # === EN-TÊTE ===
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COULEUR_PRIMAIRE};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        layout_header = QVBoxLayout()
        
        # Titre
        self.label_titre = QLabel("QUISQUEYA QUIZ")
        self.label_titre.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
        """)
        self.label_titre.setAlignment(Qt.AlignCenter)
        
        # Informations joueur et progression
        self.label_info = QLabel(f"Joueur : {self.moteur.nom_joueur}")
        self.label_info.setStyleSheet("color: white; font-size: 14px;")
        self.label_info.setAlignment(Qt.AlignCenter)
        
        self.label_progression = QLabel(f"Question 1/{self.moteur.obtenir_total_questions()}")
        self.label_progression.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.label_progression.setAlignment(Qt.AlignCenter)
        
        layout_header.addWidget(self.label_titre)
        layout_header.addWidget(self.label_info)
        layout_header.addWidget(self.label_progression)
        header.setLayout(layout_header)
        
        # === ZONE TIMER ET SCORE ===
        zone_info = QHBoxLayout()
        
        # Timer
        self.label_timer = QLabel(f" {DUREE_QUESTION}s")
        self.label_timer.setStyleSheet(f"""
            QLabel {{
                background-color: {COULEUR_ATTENTION};
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 8px;
            }}
        """)
        self.label_timer.setAlignment(Qt.AlignCenter)
        
        # Score
        self.label_score = QLabel(f"Score : 0")
        self.label_score.setStyleSheet(f"""
            QLabel {{
                background-color: {COULEUR_SUCCES};
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
            }}
        """)
        self.label_score.setAlignment(Qt.AlignCenter)
        
        zone_info.addWidget(self.label_timer)
        zone_info.addStretch()
        zone_info.addWidget(self.label_score)
        
        # === ZONE QUESTION ===
        self.group_question = QGroupBox()
        self.group_question.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border: 2px solid {COULEUR_SECONDAIRE};
                border-radius: 10px;
                padding: 20px;
                font-size: 14px;
            }}
        """)
        layout_question = QVBoxLayout()
        
        # Texte de la question
        self.label_question = QLabel()
        self.label_question.setWordWrap(True)
        self.label_question.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)
        
        layout_question.addWidget(self.label_question)
        self.group_question.setLayout(layout_question)
        
        # === ZONE RÉPONSES (SCROLLABLE) ===
        scroll_reponses = QScrollArea()
        scroll_reponses.setWidgetResizable(True)
        scroll_reponses.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.group_reponses = QWidget()
        self.layout_reponses = QVBoxLayout()
        self.layout_reponses.setSpacing(10)
        self.button_group = QButtonGroup()
        self.boutons_reponses = []
        
        self.group_reponses.setLayout(self.layout_reponses)
        scroll_reponses.setWidget(self.group_reponses)
        
        # === BOUTON ABANDONNER ===
        self.btn_abandonner = QPushButton(" Abandonner le quiz")
        self.btn_abandonner.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_ERREUR};
                color: white;
                font-size: 14px;
                padding: 10px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        self.btn_abandonner.clicked.connect(self._abandonner_quiz)
        
        # === ASSEMBLAGE ===
        layout_principal.addWidget(header)
        layout_principal.addLayout(zone_info)
        layout_principal.addWidget(self.group_question)
        layout_principal.addWidget(scroll_reponses, 1)
        layout_principal.addWidget(self.btn_abandonner)
        
        self.setLayout(layout_principal)
    
    def _afficher_question(self):
        question = self.moteur.obtenir_question_actuelle()
        if question is None:
            self._terminer_quiz()
            return
        
        # Mettre à jour les informations
        self.label_progression.setText(
            f"Question {self.moteur.obtenir_numero_question()}/{self.moteur.obtenir_total_questions()}"
        )
        self.label_score.setText(f" Score : {self.moteur.score}")
        
        # Afficher la question
        self.label_question.setText(f" {question.texte}")
        
        # Créer les boutons de réponse
        for btn in self.boutons_reponses:
            self.button_group.removeButton(btn)
            btn.deleteLater()
        self.boutons_reponses.clear()
        
        for i, option in enumerate(question.options):
            btn = QPushButton(f"{i+1}. {option}")
            
            btn.setMinimumHeight(50)  # Hauteur pour le texte long
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    color: {COULEUR_TEXTE};
                    font-size: 11px;
                    padding: 15px;
                    border: 2px solid {COULEUR_SECONDAIRE};
                    border-radius: 8px;
                    text-align: left;
                    qproperty-wordWrap: true;
                }}
                QPushButton:hover {{
                    background-color: {COULEUR_SECONDAIRE};
                    color: white;
                    border-color: {COULEUR_PRIMAIRE};
                }}
            """)
            
            btn.clicked.connect(lambda checked, idx=i: self._repondre(idx))
            self.layout_reponses.addWidget(btn)
            self.boutons_reponses.append(btn)
            self.button_group.addButton(btn)
        
        # Ajouter un stretch à la fin
        self.layout_reponses.addStretch()
        
        # Démarrer le timer
        self.temps_restant = DUREE_QUESTION
        self.temps_debut_question = time.time()
        self.timer.start(1000)
        self._mise_a_jour_timer()
    
    def _mise_a_jour_timer(self):
        """Met à jour l'affichage du timer"""
        self.temps_restant -= 1
        self.label_timer.setText(f"⏱ {self.temps_restant}s")
        
        # Changer la couleur selon le temps restant
        if self.temps_restant <= 5:
            self.label_timer.setStyleSheet(f"""
                QLabel {{
                    background-color: {COULEUR_ERREUR};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 8px;
                }}
            """)
        elif self.temps_restant <= 10:
            self.label_timer.setStyleSheet(f"""
                QLabel {{
                    background-color: {COULEUR_ATTENTION};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 8px;
                }}
            """)
        
        # Temps écoulé
        if self.temps_restant <= 0:
            self.timer.stop()
            self._temps_ecoule()
    
    def _repondre(self, index_reponse: int):
        """Gère la réponse de l'utilisateur"""
        self.timer.stop()
        
        # Calculer le temps de réponse
        temps_reponse = time.time() - self.temps_debut_question
        
        # Désactiver tous les boutons
        for btn in self.boutons_reponses:
            btn.setEnabled(False)
        
        # Colorer le bouton cliqué et la bonne réponse
        question = self.moteur.obtenir_question_actuelle()
        est_correct = question.est_reponse_correcte(index_reponse)
        
        if est_correct:
            self.boutons_reponses[index_reponse].setStyleSheet(f"""
                QPushButton {{
                    background-color: {COULEUR_SUCCES};
                    color: white;
                    font-size: 15px;
                    padding: 15px;
                    border: 2px solid #229954;
                    border-radius: 8px;
                    text-align: left;
                }}
            """)
        else:
            # Réponse incorrecte en rouge
            self.boutons_reponses[index_reponse].setStyleSheet(f"""
                QPushButton {{
                    background-color: {COULEUR_ERREUR};
                    color: white;
                    font-size: 15px;
                    padding: 15px;
                    border: 2px solid #C0392B;
                    border-radius: 8px;
                    text-align: left;
                }}
            """)
            # Bonne réponse en vert
            self.boutons_reponses[question.bonne_option].setStyleSheet(f"""
                QPushButton {{
                    background-color: {COULEUR_SUCCES};
                    color: white;
                    font-size: 15px;
                    padding: 15px;
                    border: 2px solid #229954;
                    border-radius: 8px;
                    text-align: left;
                }}
            """)
        
        # Enregistrer la réponse
        self.moteur.enregistrer_reponse(index_reponse, False, temps_reponse)
        
        # Passer à la question suivante après 2 secondes
        QTimer.singleShot(2000, self._question_suivante)
    
    def _temps_ecoule(self):
        """Gère le cas où le temps est écoulé"""
        # Désactiver tous les boutons
        for btn in self.boutons_reponses:
            btn.setEnabled(False)
        
        # Afficher la bonne réponse
        question = self.moteur.obtenir_question_actuelle()
        self.boutons_reponses[question.bonne_option].setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_ATTENTION};
                color: white;
                font-size: 15px;
                padding: 15px;
                border: 2px solid #E67E22;
                border-radius: 8px;
                text-align: left;
            }}
        """)
        
        # Enregistrer comme temps écoulé
        self.moteur.enregistrer_reponse(None, True, DUREE_QUESTION)
        
        # Passer à la question suivante
        QTimer.singleShot(2500, self._question_suivante)
    
    def _question_suivante(self):
        """Passe à la question suivante ou termine le quiz"""
        if self.moteur.est_termine():
            self._terminer_quiz()
        else:
            self._afficher_question()
    
    def _terminer_quiz(self):
        """Termine le quiz et émet le signal avec les résultats"""
        resultats = self.moteur.obtenir_resultats()
        self.signal_quiz_termine.emit(resultats)
    
    def _abandonner_quiz(self):
        """Gère l'abandon du quiz"""
        reponse = QMessageBox.question(
            self,
            "Abandonner le quiz",
            "Voulez-vous vraiment abandonner le quiz ?\n\nVotre progression sera perdue.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reponse == QMessageBox.Yes:
            self.timer.stop()
            self.signal_quiz_abandonne.emit()


# ============================================================================
# FENÊTRE DE RÉSULTATS
# ============================================================================

class FenetreResultats(QWidget):
    """Fenêtre affichant les résultats du quiz avec graphiques"""
    
    signal_retour_menu = pyqtSignal()
    signal_afficher_revision = pyqtSignal()
    
    def __init__(self, resultats: Dict[str, Any], historique: List[ReponseQuestion], parent=None):
        super().__init__(parent)
        self.resultats = resultats
        self.historique = historique
        self._initialiser_ui()
    
    def _initialiser_ui(self):
        """Initialise l'interface utilisateur"""
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(15)
        
        # === TITRE ===
        label_titre = QLabel("🎉 RÉSULTATS DU QUIZ")
        label_titre.setStyleSheet(f"""
            QLabel {{
                background-color: {COULEUR_PRIMAIRE};
                color: white;
                font-size: 28px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
            }}
        """)
        label_titre.setAlignment(Qt.AlignCenter)
        
        # === INFORMATIONS ===
        group_info = QGroupBox("Informations de la partie")
        group_info.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border: 2px solid {COULEUR_SECONDAIRE};
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout_info = QVBoxLayout()
        
        joueur = self.resultats.get("joueur_nom", "Inconnu")
        total = self.resultats.get("nombre_questions", 0)
        bonnes = self.resultats.get("bonnes", 0)
        pourcentage = self.resultats.get("pourcentage", 0)
        score = self.resultats.get("score_total", 0)
        duree = self.resultats.get("duree_seconds", 0)
        
        info_text = f"""
        <p style='font-size: 16px; color: {COULEUR_TEXTE};'>
        <b>👤 Joueur :</b> {joueur}<br>
        <b>✅ Bonnes réponses :</b> {bonnes}/{total} ({pourcentage}%)<br>
        <b>💯 Score total :</b> {score} points<br>
        <b>⏱ Durée :</b> {duree // 60} min {duree % 60} s
        </p>
        """
        
        label_info = QLabel(info_text)
        label_info.setWordWrap(True)
        layout_info.addWidget(label_info)
        group_info.setLayout(layout_info)
        
        # === GRAPHIQUE ===
        self.graphique = GraphiqueWidget()
        self.graphique.afficher_graphique_resultats(self.resultats)
        
        # === BOUTONS ===
        layout_boutons = QHBoxLayout()
        
        btn_revision = QPushButton("📚 Réviser les questions")
        btn_revision.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_SECONDAIRE};
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #2980B9;
            }}
        """)
        btn_revision.clicked.connect(self.signal_afficher_revision.emit)
        
        btn_menu = QPushButton("🏠 Retour au menu")
        btn_menu.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_SUCCES};
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
        """)
        btn_menu.clicked.connect(self.signal_retour_menu.emit)
        
        layout_boutons.addWidget(btn_revision)
        layout_boutons.addWidget(btn_menu)
        
        # === ASSEMBLAGE ===
        layout_principal.addWidget(label_titre)
        layout_principal.addWidget(group_info)
        layout_principal.addWidget(self.graphique)
        layout_principal.addLayout(layout_boutons)
        
        self.setLayout(layout_principal)


# ============================================================================
# FENÊTRE DE RÉVISION
# ============================================================================

class FenetreRevision(QWidget):
    """Fenêtre de révision des questions et réponses"""
    
    signal_fermer = pyqtSignal()
    
    def __init__(self, historique: List[ReponseQuestion], parent=None):
        super().__init__(parent)
        self.historique = historique
        self._initialiser_ui()
    
    def _initialiser_ui(self):
        """Initialise l'interface utilisateur"""
        layout_principal = QVBoxLayout()
        
        # === TITRE ===
        label_titre = QLabel("📚 RÉVISION DES QUESTIONS")
        label_titre.setStyleSheet(f"""
            QLabel {{
                background-color: {COULEUR_PRIMAIRE};
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
            }}
        """)
        label_titre.setAlignment(Qt.AlignCenter)
        
        # === ZONE DE SCROLL POUR LES QUESTIONS ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ECF0F1;
            }
        """)
        
        widget_contenu = QWidget()
        layout_contenu = QVBoxLayout()
        layout_contenu.setSpacing(15)
        
        # Ajouter chaque question
        for rep in self.historique:
            frame_question = self._creer_frame_question(rep)
            layout_contenu.addWidget(frame_question)
        
        widget_contenu.setLayout(layout_contenu)
        scroll_area.setWidget(widget_contenu)
        
        # === BOUTON FERMER ===
        btn_fermer = QPushButton("🏠 Retour au menu")
        btn_fermer.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_SUCCES};
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
        """)
        btn_fermer.clicked.connect(self.signal_fermer.emit)
        
        # === ASSEMBLAGE ===
        layout_principal.addWidget(label_titre)
        layout_principal.addWidget(scroll_area)
        layout_principal.addWidget(btn_fermer)
        
        self.setLayout(layout_principal)
    
    def _creer_frame_question(self, rep: ReponseQuestion) -> QFrame:
        """Crée un frame pour une question avec sa réponse"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {COULEUR_SECONDAIRE};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        # Numéro et statut
        if rep.temps_ecoule:
            statut = " Temps écoulé"
            couleur_statut = COULEUR_ATTENTION
        elif rep.est_correcte:
            statut = "✅ CORRECT"
            couleur_statut = COULEUR_SUCCES
        else:
            statut = "❌ INCORRECT"
            couleur_statut = COULEUR_ERREUR
        
        label_header = QLabel(f"Question {rep.numero} - {statut}")
        label_header.setStyleSheet(f"""
            QLabel {{
                color: {couleur_statut};
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        
        # Texte de la question
        label_question = QLabel(f" {rep.question.texte}")
        label_question.setWordWrap(True)
        label_question.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2C3E50;
                margin: 10px 0px;
            }
        """)
        
        layout.addWidget(label_header)
        layout.addWidget(label_question)
        
        # Options
        for i, opt in enumerate(rep.question.options):
            label_opt = QLabel(f"{i+1}. {opt}")
            label_opt.setWordWrap(True)
            
            # Colorer selon le contexte
            if i == rep.question.bonne_option:
                # Bonne réponse
                label_opt.setStyleSheet(f"""
                    QLabel {{
                        background-color: {COULEUR_SUCCES};
                        color: white;
                        padding: 8px;
                        border-radius: 5px;
                        font-weight: bold;
                    }}
                """)
            elif rep.reponse_choisie is not None and i == rep.reponse_choisie:
                # Réponse choisie (incorrecte)
                label_opt.setStyleSheet(f"""
                    QLabel {{
                        background-color: {COULEUR_ERREUR};
                        color: white;
                        padding: 8px;
                        border-radius: 5px;
                    }}
                """)
            else:
                label_opt.setStyleSheet("""
                    QLabel {
                        padding: 8px;
                        color: #7F8C8D;
                    }
                """)
            
            layout.addWidget(label_opt)
        
        # Informations supplémentaires
        if rep.temps_reponse > 0 and not rep.temps_ecoule:
            label_temps = QLabel(f" Temps de réponse : {rep.temps_reponse:.1f}s")
            label_temps.setStyleSheet("color: #7F8C8D; font-size: 12px; margin-top: 5px;")
            layout.addWidget(label_temps)
        
        frame.setLayout(layout)
        return frame


# ============================================================================
# FENÊTRE DE CLASSEMENT
# ============================================================================

class FenetreClassement(QWidget):
    """Fenêtre affichant le classement des scores"""
    
    signal_fermer = pyqtSignal()
    
    def __init__(self, stockage: Stockage, banque: BanqueQuestions, parent=None):
        super().__init__(parent)
        self.stockage = stockage
        self.banque = banque
        self._initialiser_ui()
    
    def _initialiser_ui(self):
        """Initialise l'interface utilisateur"""
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(15)
        
        # === TITRE ===
        label_titre = QLabel("🏆 CLASSEMENT")
        label_titre.setStyleSheet(f"""
            QLabel {{
                background-color: {COULEUR_PRIMAIRE};
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
            }}
        """)
        label_titre.setAlignment(Qt.AlignCenter)
        
        # === FILTRES ===
        group_filtres = QGroupBox("Filtres")
        group_filtres.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border: 2px solid {COULEUR_SECONDAIRE};
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout_filtres = QHBoxLayout()
        
        # Nombre de scores
        label_nb = QLabel("Nombre de scores :")
        self.spin_nombre = QSpinBox()
        self.spin_nombre.setMinimum(1)
        self.spin_nombre.setMaximum(50)
        self.spin_nombre.setValue(10)
        self.spin_nombre.valueChanged.connect(self._actualiser_classement)
        
        # Thème
        label_theme = QLabel("Thème :")
        self.combo_theme = QComboBox()
        themes = ["Tous"] + self.banque.lister_themes()
        self.combo_theme.addItems(themes)
        self.combo_theme.currentTextChanged.connect(self._actualiser_classement)
        
        layout_filtres.addWidget(label_nb)
        layout_filtres.addWidget(self.spin_nombre)
        layout_filtres.addWidget(label_theme)
        layout_filtres.addWidget(self.combo_theme)
        layout_filtres.addStretch()
        group_filtres.setLayout(layout_filtres)
        
        # === LISTE DES SCORES ===
        self.liste_scores = QListWidget()
        self.liste_scores.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #3498DB;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #BDC3C7;
            }
            QListWidget::item:hover {
                background-color: #ECF0F1;
            }
        """)
        
        # === GRAPHIQUE ===
        self.graphique = GraphiqueWidget()
        
        # === BOUTON FERMER ===
        btn_fermer = QPushButton("🏠 Retour au menu")
        btn_fermer.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_SUCCES};
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
        """)
        btn_fermer.clicked.connect(self.signal_fermer.emit)
        
        # === ASSEMBLAGE ===
        layout_principal.addWidget(label_titre)
        layout_principal.addWidget(group_filtres)
        layout_principal.addWidget(self.liste_scores, 1)
        layout_principal.addWidget(self.graphique, 1)
        layout_principal.addWidget(btn_fermer)
        
        self.setLayout(layout_principal)
        
        # Charger les scores initiaux
        self._actualiser_classement()
    
    def _actualiser_classement(self):
        """Actualise l'affichage du classement"""
        nombre = self.spin_nombre.value()
        theme_selectionne = self.combo_theme.currentText()
        theme = None if theme_selectionne == "Tous" else theme_selectionne
        
        scores = self.stockage.top_n(nombre, theme)
        
        # Mettre à jour la liste
        self.liste_scores.clear()
        if not scores:
            self.liste_scores.addItem("Aucun score enregistré pour le moment.")
        else:
            for i, s in enumerate(scores, start=1):
                medaille = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                joueur = s.get("joueur_nom", "Inconnu")
                score = s.get("score_total", 0)
                bonnes = s.get("bonnes", 0)
                total = s.get("nombre_questions", 0)
                pourcentage = s.get("pourcentage", 0)
                date = s.get("date_heure", "")[:10]
                
                texte = f"{medaille} {joueur} - {score} pts ({bonnes}/{total} = {pourcentage}%) - {date}"
                self.liste_scores.addItem(texte)
        
        # Mettre à jour le graphique
        self.graphique.afficher_graphique_classement(scores)


# ============================================================================
# FENÊTRE PRINCIPALE (MENU) - AVEC TYPEWRITER
# ============================================================================

class FenetrePrincipale(QMainWindow):
    """Fenêtre principale de l'application"""
    
    def __init__(self):
        super().__init__()
        self.banque = BanqueQuestions()
        self.stockage = Stockage()
        self.nom_joueur = ""
        
        self._initialiser_ui()
        self._verifier_questions()
    
    def _initialiser_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Quisqueya Quiz Système")
        self.setMinimumSize(1000, 700)
        
        # Widget central avec pile de fenêtres
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Créer le menu principal
        self._creer_menu_principal()
        
        # Appliquer un style global
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COULEUR_FOND};
            }}
        """)
    
    def _verifier_questions(self):
        """Vérifie que des questions sont disponibles"""
        if not self.banque.questions:
            QMessageBox.warning(
                self,
                "Aucune question",
                "Aucune question n'a été trouvée.\n\n"
                "Veuillez ajouter des fichiers JSON de questions dans le dossier 'questions/'."
            )
    
    def _creer_menu_principal(self):
        """Crée le menu principal"""
        widget_menu = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # === TITRE AVEC EFFET TYPEWRITER ===
        self.label_titre = TypewriterLabel([
            " QUISQUEYA QUIZ SYSTÈME",
            " Bienvenue dans le jeu"
                    ])
        self.label_titre.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 {COULEUR_PRIMAIRE}, 
                                           stop:1 {COULEUR_SECONDAIRE});
                color: white;
                font-size: 36px;
                font-weight: bold;
                padding: 30px;
                border-radius: 15px;
                min-height: 100px;
            }}
        """)
        self.label_titre.setAlignment(Qt.AlignCenter)
        
        # === BOUTONS DU MENU ===
        style_bouton = f"""
            QPushButton {{
                background-color: {COULEUR_SECONDAIRE};
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COULEUR_PRIMAIRE};
            }}
        """
        
        btn_jouer = QPushButton("🎮 JOUER")
        btn_jouer.setStyleSheet(style_bouton)
        btn_jouer.clicked.connect(self._menu_jouer)
        
        btn_classement = QPushButton("🏆 CLASSEMENT")
        btn_classement.setStyleSheet(style_bouton)
        btn_classement.clicked.connect(self._afficher_classement)
        
        btn_instructions = QPushButton("📖 INSTRUCTIONS")
        btn_instructions.setStyleSheet(style_bouton)
        btn_instructions.clicked.connect(self._afficher_instructions)
        
        btn_quitter = QPushButton("❌ QUITTER")
        btn_quitter.setStyleSheet(f"""
            QPushButton {{
                background-color: {COULEUR_ERREUR};
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        btn_quitter.clicked.connect(self.close)
        
        # === ASSEMBLAGE ===
        layout.addWidget(self.label_titre)
        layout.addWidget(btn_jouer)
        layout.addWidget(btn_classement)
        layout.addWidget(btn_instructions)
        layout.addStretch()
        layout.addWidget(btn_quitter)
        
        widget_menu.setLayout(layout)
        self.stack.addWidget(widget_menu)
    
    def _menu_jouer(self):
        """Affiche le menu de sélection du mode de jeu"""
        # Demander le nom du joueur
        nom, ok = QInputDialog.getText(
            self,
            "Nom du joueur",
            "Entrez votre nom ou pseudo :"
        )
        
        if not ok or not nom.strip():
            nom = "Joueur"
        
        self.nom_joueur = nom.strip()
        
        # Vérifier si le joueur existe déjà
        occurrences = self.stockage.compter_occurrences_joueur(self.nom_joueur)
        
        if occurrences > 0:
            stats = self.stockage.obtenir_stats_joueur(self.nom_joueur)
            msg = f"Le nom '{self.nom_joueur}' est déjà enregistré avec {occurrences} partie(s).\n\n"
            msg += f"Meilleur score : {stats['meilleur_score']} points ({stats['meilleur_pourcentage']}%)\n"
            if occurrences > 1:
                msg += f"Moyenne : {stats['moyenne_pourcentage']}%\n"
            msg += "\nÊtes-vous cette même personne ?"
            
            reponse = QMessageBox.question(
                self,
                "Joueur existant",
                msg,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reponse == QMessageBox.No:
                QMessageBox.information(
                    self,
                    "Changement de nom",
                    "Veuillez choisir un autre nom."
                )
                return
        
        # Afficher le sous-menu de sélection du mode
        dialog = QDialog(self)
        dialog.setWindowTitle("Mode de jeu")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        label = QLabel("Choisissez un mode de jeu :")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        btn_rapide = QPushButton("⚡ Mode Rapide (10 questions aléatoires)")
        btn_rapide.clicked.connect(lambda: self._lancer_quiz(None, dialog))
        
        btn_theme = QPushButton("🎨 Mode Thème (choisir un thème)")
        btn_theme.clicked.connect(lambda: self._choisir_theme(dialog))
        
        btn_annuler = QPushButton("Annuler")
        btn_annuler.clicked.connect(dialog.reject)
        
        layout.addWidget(label)
        layout.addWidget(btn_rapide)
        layout.addWidget(btn_theme)
        layout.addWidget(btn_annuler)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _choisir_theme(self, dialog_parent):
        """Permet de choisir un thème"""
        themes = self.banque.lister_themes()
        
        if not themes:
            QMessageBox.warning(self, "Aucun thème", "Aucun thème disponible.")
            return
        
        theme, ok = QInputDialog.getItem(
            self,
            "Choisir un thème",
            "Sélectionnez un thème :",
            themes,
            0,
            False
        )
        
        if ok and theme:
            dialog_parent.accept()
            self._lancer_quiz([theme], None)
    
    def _lancer_quiz(self, themes: Optional[List[str]], dialog_parent):
        """Lance le quiz avec les paramètres donnés"""
        if dialog_parent:
            dialog_parent.accept()
        
        # Échantillonner les questions
        questions = self.banque.echantillonner_questions(10, themes)
        
        if not questions:
            QMessageBox.warning(self, "Aucune question", "Aucune question disponible pour ce thème.")
            return
        
        # Créer le moteur de quiz
        moteur = MoteurQuiz(questions, self.nom_joueur)
        
        # Créer et afficher la fenêtre de quiz
        fenetre_quiz = FenetreQuiz(moteur)
        fenetre_quiz.signal_quiz_termine.connect(self._afficher_resultats)
        fenetre_quiz.signal_quiz_abandonne.connect(self._retour_menu)
        
        self.stack.addWidget(fenetre_quiz)
        self.stack.setCurrentWidget(fenetre_quiz)
    
    def _afficher_resultats(self, resultats: Dict[str, Any]):
        """Affiche les résultats du quiz"""
        # Sauvegarder le score
        self.stockage.sauvegarder_score(resultats)
        
        # Récupérer le moteur de quiz pour l'historique
        fenetre_quiz = self.stack.currentWidget()
        historique = fenetre_quiz.moteur.historique_reponses
        
        # Créer et afficher la fenêtre de résultats
        fenetre_resultats = FenetreResultats(resultats, historique)
        fenetre_resultats.signal_retour_menu.connect(self._retour_menu)
        fenetre_resultats.signal_afficher_revision.connect(
            lambda: self._afficher_revision(historique)
        )
        
        self.stack.addWidget(fenetre_resultats)
        self.stack.setCurrentWidget(fenetre_resultats)
    
    def _afficher_revision(self, historique: List[ReponseQuestion]):
        """Affiche la fenêtre de révision"""
        fenetre_revision = FenetreRevision(historique)
        fenetre_revision.signal_fermer.connect(self._retour_menu)
        
        self.stack.addWidget(fenetre_revision)
        self.stack.setCurrentWidget(fenetre_revision)
    
    def _afficher_classement(self):
        """Affiche le classement"""
        fenetre_classement = FenetreClassement(self.stockage, self.banque)
        fenetre_classement.signal_fermer.connect(self._retour_menu)
        
        self.stack.addWidget(fenetre_classement)
        self.stack.setCurrentWidget(fenetre_classement)
    
    def _afficher_instructions(self):
        """Affiche les instructions"""
        instructions = """
        <h2>📖 COMMENT JOUER ?</h2>
        <ul>
        <li>Une partie contient jusqu'à 10 questions</li>
        <li>Chaque bonne réponse vaut 1 point</li>
        <li>Vous avez 20 secondes par question</li>
        <li>Cliquez sur un bouton pour répondre</li>
        </ul>
        
        <h2>🏆 SCORES</h2>
        <ul>
        <li>Vos scores sont sauvegardés automatiquement</li>
        <li>Consultez le classement dans le menu principal</li>
        </ul>
        
        <h2>🎮 MODES DE JEU</h2>
        <ul>
        <li><b>Mode Rapide :</b> 10 questions, tous thèmes</li>
        <li><b>Mode Thème :</b> choisissez un thème spécifique</li>
        </ul>
        
        <h2>📚 RÉVISION</h2>
        <ul>
        <li>À la fin du quiz, vous pouvez réviser toutes les questions</li>
        <li>Visualisez vos réponses et les bonnes réponses</li>
        </ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Instructions")
        msg.setTextFormat(Qt.RichText)
        msg.setText(instructions)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
    
    def _retour_menu(self):
        """Retourne au menu principal"""
        # Nettoyer les widgets inutiles
        while self.stack.count() > 1:
            widget = self.stack.widget(1)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        
        # Retourner au menu
        self.stack.setCurrentIndex(0)
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        reponse = QMessageBox.question(
            self,
            "Quitter",
            "Voulez-vous vraiment quitter l'application ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reponse == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


# ============================================================================
# WIDGET TYPEWRITER LABEL 
# ============================================================================

class TypewriterLabel(QLabel):
    """
    QLabel avec effet de machine à écrire qui alterne entre plusieurs textes.
    
    Le texte s'écrit caractère par caractère, attend, puis s'efface caractère
    par caractère avant de passer au texte suivant dans une boucle infinie.
    """
    
    def __init__(self, textes: List[str], parent=None):
        """
        Initialise le TypewriterLabel.
        
        Args:
            textes: Liste des textes à afficher en alternance
            parent: Widget parent
        """
        super().__init__(parent)
        
        self.textes = textes  # Liste des textes à afficher
        self.index_texte_actuel = 0  # Index du texte actuellement affiché
        self.texte_actuel = ""  # Texte en cours de construction
        self.position_caractere = 0  # Position dans le texte
        self.est_en_ecriture = True  # True = écriture, False = effacement
        self.est_en_pause = False  # True si en pause entre écriture et effacement
        
        # Configuration des timers
        self.vitesse_ecriture = 80  # Millisecondes entre chaque caractère (écriture)
        self.vitesse_effacement = 40  # Millisecondes entre chaque caractère (effacement)
        self.duree_pause = 700  # Millisecondes de pause après l'écriture complète
        
        # Timer principal pour l'animation
        self.timer = QTimer()
        self.timer.timeout.connect(self._animer)
        
        # Démarrer l'animation
        self.demarrer()
    
    def demarrer(self):
        """Démarre l'animation du typewriter"""
        self.timer.start(self.vitesse_ecriture)
    
    def arreter(self):
        """Arrête l'animation du typewriter"""
        self.timer.stop()
    
    def _animer(self):
        """
        Méthode appelée à chaque tick du timer pour animer le texte.
        
        Gère l'écriture, la pause et l'effacement du texte.
        """
        # Si en pause, attendre avant de passer à l'effacement
        if self.est_en_pause:
            self.est_en_pause = False
            self.est_en_ecriture = False
            self.timer.setInterval(self.vitesse_effacement)
            return
        
        # Récupérer le texte cible
        texte_cible = self.textes[self.index_texte_actuel]
        
        # MODE ÉCRITURE
        if self.est_en_ecriture:
            if self.position_caractere < len(texte_cible):
                # Ajouter le caractère suivant
                self.position_caractere += 1
                self.texte_actuel = texte_cible[:self.position_caractere]
                self.setText(self.texte_actuel)
            else:
                # Écriture terminée, passer en pause
                self.est_en_pause = True
                self.timer.setInterval(self.duree_pause)
        
        # MODE EFFACEMENT
        else:
            if self.position_caractere > 0:
                # Retirer le dernier caractère
                self.position_caractere -= 1
                self.texte_actuel = texte_cible[:self.position_caractere]
                self.setText(self.texte_actuel)
            else:
                # Effacement terminé, passer au texte suivant
                self.index_texte_actuel = (self.index_texte_actuel + 1) % len(self.textes)
                self.est_en_ecriture = True
                self.position_caractere = 0
                self.timer.setInterval(self.vitesse_ecriture)
    
    def definir_vitesses(self, vitesse_ecriture: int, vitesse_effacement: int, duree_pause: int):
        """
        Permet de personnaliser les vitesses de l'animation.
        
        Args:
            vitesse_ecriture: Millisecondes entre chaque caractère lors de l'écriture
            vitesse_effacement: Millisecondes entre chaque caractère lors de l'effacement
            duree_pause: Millisecondes de pause après l'écriture complète
        """
        self.vitesse_ecriture = vitesse_ecriture
        self.vitesse_effacement = vitesse_effacement
        self.duree_pause = duree_pause
        
        # Mettre à jour l'intervalle du timer selon l'état actuel
        if self.est_en_ecriture:
            self.timer.setInterval(self.vitesse_ecriture)
        else:
            self.timer.setInterval(self.vitesse_effacement)


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

def main():
    
    # Créer l'application Qt
    app = QApplication(sys.argv)
    
    # Configurer le style de l'application (Fusion pour un look moderne)
    app.setStyle("Fusion")
    
    # Configuration optionnelle de la palette de couleurs
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COULEUR_FOND))
    palette.setColor(QPalette.WindowText, QColor(COULEUR_TEXTE))
    palette.setColor(QPalette.Base, QColor("white"))
    palette.setColor(QPalette.AlternateBase, QColor(COULEUR_FOND))
    palette.setColor(QPalette.ToolTipBase, QColor("white"))
    palette.setColor(QPalette.ToolTipText, QColor(COULEUR_TEXTE))
    palette.setColor(QPalette.Text, QColor(COULEUR_TEXTE))
    palette.setColor(QPalette.Button, QColor(COULEUR_SECONDAIRE))
    palette.setColor(QPalette.ButtonText, QColor("white"))
    palette.setColor(QPalette.BrightText, QColor("white"))
    palette.setColor(QPalette.Highlight, QColor(COULEUR_SECONDAIRE))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    app.setPalette(palette)
    
    # Créer et afficher la fenêtre principale
    fenetre = FenetrePrincipale()
    fenetre.show()
    
    # Lancer la boucle d'événements et quitter proprement
    sys.exit(app.exec_())


# ============================================================================
# LANCEMENT DE L'APPLICATION
# ============================================================================

if __name__ == "__main__":
    """
    Bloc de garde pour éviter l'exécution lors de l'importation.
    Lance l'application uniquement si ce fichier est exécuté directement.
    """
    main()
