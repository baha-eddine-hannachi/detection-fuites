# 🔍 Système de Détection de Fuites

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Flask](https://img.shields.io/badge/flask-2.0+-red)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 📋 Table des matières
- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API Documentation](#-api-documentation)
- [Dashboard](#-dashboard)
- [Modèle ML](#-modèle-ml)
- [ESP32](#-esp32)
- [Déploiement](#-déploiement)
- [Dépannage](#-dépannage)
- [Contribuer](#-contribuer)
- [Licence](#-licence)

## 🎯 Aperçu

Système complet de **détection de fuites en temps réel** utilisant l'intelligence artificielle. Ce projet combine :
- **ESP32** pour l'acquisition de données capteurs
- **Modèle Machine Learning** (Random Forest) pour la prédiction
- **Dashboard web interactif** pour la visualisation
- **Alertes en temps réel** avec activation de vibreur

## ✨ Fonctionnalités

### 📊 Dashboard en temps réel
- Graphique dynamique des 3 capteurs
- Statistiques en direct
- Alertes visuelles avec code couleur
- Timer de simulation

### 🤖 Intelligence Artificielle
- Modèle Random Forest entraîné
- Prédiction de fuite avec probabilité
- Seuil d'alerte configurable (30%)

### 📡 Communication
- Socket.IO pour temps réel
- API REST complète
- Compatible ESP32

### 🚨 Alertes
- Dashboard rouge avec animation
- Activation du vibreur ESP32
- Historique des alertes
- Simulation à 100%

## 🏗 Architecture
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐
│ ESP32 │────▶│ Serveur │────▶│ Modèle │────▶│Dashboard│
│Capteurs │ │ Flask │ │ ML │ │ Web │
└─────────┘ └──────────┘ └─────────┘ └─────────┘
│ │ │
▼ ▼ ▼
┌──────────┐ ┌─────────┐ ┌─────────┐
│ Base de │ │Alertes │ │Vibreur │
│ données │ │Email/SMS│ │ LED │
└──────────┘ └─────────┘ └─────────┘

## 📦 Installation

### Prérequis
- Python 3.8 ou supérieur
- ESP32 (optionnel)
- Navigateur web moderne

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-username/detection-fuites.git
cd detection-fuites
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate


3. Installer les dépendances
pip install -r requirements.txt

4. Vérifier le modèle
# Vérifier que le fichier modèle existe
ls modele_detection_fuites.pkl

# Configuration serveur
PORT=5000
HOST=0.0.0.0
DEBUG=True

# Seuils d'alerte
SEUIL_PROBABILITE=0.3

# ESP32 (si connecté)
ESP32_IP=192.168.1.100

📁 detection-fuites/
├── 📄 server.py                 # Serveur principal
├── 📄 modele_detection_fuites.pkl # Modèle ML
├── 📁 templates/
│   └── 📄 dashboard.html        # Interface web
├── 📄 requirements.txt          # Dépendances
├── 📄 README.md                  # Documentation
└── 📄 .gitignore                 # Fichiers ignorés

Démarrer le serveur
python server.py
