# server.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
import joblib
import json
import threading
import time
from collections import deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Charger le modèle entraîné
print("📦 Chargement du modèle...")
model = joblib.load('modele_detection_fuites.pkl')
print(f"✅ Modèle chargé!")
print(f"📊 Features attendues: {model.feature_names_in_}")
print(f"🎯 Classes: {model.classes_}")

# Stockage des données
donnees_capteurs = deque(maxlen=1000)  # Garde 1000 dernières mesures
alertes = []

# Seuils d'alerte - PLUS BAS pour détecter plus facilement
SEUIL_PROBABILITE = 0.3  # 30% (au lieu de 70%)
mode_fuite = False  # Variable globale pour le mode simulation

# ============================================
# ROUTES WEB PRINCIPALES
# ============================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/donnees')
def get_donnees():
    """Récupérer les dernières données"""
    return jsonify(list(donnees_capteurs))

@app.route('/api/alertes')
def get_alertes():
    """Récupérer les alertes"""
    return jsonify(alertes[-50:])  # 50 dernières alertes

# ============================================
# ROUTES DE SIMULATION
# ============================================

@app.route('/api/simuler-fuite', methods=['POST'])
def simuler_fuite():
    """Simuler une fuite avec valeurs progressives"""
    global mode_fuite
    print("🧪 SIMULATION: Fuite progressive")
    
    # Récupérer le niveau depuis la requête (ou défaut)
    data = request.get_json() or {}
    niveau = data.get('niveau', 'extreme')
    
    # Définir les valeurs selon le niveau
    niveaux = {
        'leger': {'vib': 90, 'temp': 38, 'press': 4.5, 'prob': '30-40%'},
        'moyen': {'vib': 150, 'temp': 55, 'press': 2.5, 'prob': '50-60%'},
        'eleve': {'vib': 250, 'temp': 75, 'press': 1.2, 'prob': '70-80%'},
        'extreme': {'vib': 400, 'temp': 100, 'press': 0.3, 'prob': '90-100%'}
    }
    
    valeurs = niveaux.get(niveau, niveaux['extreme'])
    
    sensor_data = {
        'vibration': valeurs['vib'],
        'temperature': valeurs['temp'],
        'pression': valeurs['press'],
        'simulation': True,
        'niveau': niveau,
        'type': f'FUITE_{niveau.upper()}',
        'timestamp': time.time()
    }
    
    # Activer le mode fuite
    mode_fuite = True
    
    # Traiter les données
    handle_sensor_data(sensor_data)
    
    # Désactiver après 5 secondes
    def desactiver_fuite():
        global mode_fuite
        time.sleep(5)
        mode_fuite = False
        print("✅ Fin de la simulation de fuite")
    
    threading.Thread(target=desactiver_fuite, daemon=True).start()
    
    return jsonify({
        'status': 'ok', 
        'message': f'Fuite simulée - Niveau {niveau} ({valeurs["prob"]})',
        'data': sensor_data
    })

@app.route('/api/test-toutes-valeurs', methods=['GET'])
def test_toutes_valeurs():
    """Tester toutes les combinaisons de valeurs"""
    resultats = []
    
    tests = [
        (50, 25, 6, "Normal"),
        (85, 42, 4.2, "Actuel (34%)"),
        (120, 48, 3.5, "Test 1"),
        (150, 55, 2.8, "Test 2"),
        (200, 65, 2.0, "Test 3"),
        (250, 75, 1.5, "Test 4"),
        (300, 85, 1.0, "Test 5"),
        (350, 95, 0.6, "Test 6"),
        (400, 105, 0.3, "Test 7"),
        (500, 120, 0.1, "Test 8"),
    ]
    
    for vib, temp, press, desc in tests:
        try:
            X = pd.DataFrame([[vib, temp, press]], 
                            columns=['Vibration (mm/s)', 'Temperature (°C)', 'Pressure (bar)'])
            prob = model.predict_proba(X)[0][1]
            pred = model.predict(X)[0]
            
            resultats.append({
                'description': desc,
                'vibration': vib,
                'temperature': temp,
                'pression': press,
                'probabilite': f"{prob:.1%}",
                'prob_brute': prob,
                'prediction': int(pred),
                'alerte': prob > SEUIL_PROBABILITE
            })
        except Exception as e:
            resultats.append({
                'description': desc,
                'erreur': str(e)
            })
    
    return jsonify(resultats)

@app.route('/api/forcer-alerte', methods=['POST'])
def forcer_alerte():
    """Forcer une alerte immédiate (contourne le modèle)"""
    print("🚨 ALERTE FORCÉE MANUELLEMENT!")
    
    # Créer une alerte forcée
    alerte = {
        'timestamp': time.time(),
        'message': "🚨 ALERTE MANUELLE FORCÉE!",
        'donnees': {
            'vibration': 999,
            'temperature': 999,
            'pression': 0,
            'forcee': True
        },
        'probabilite': 1.0
    }
    
    alertes.append(alerte)
    
    # Envoyer au dashboard
    socketio.emit('alerte', alerte)
    
    # Envoyer commande ESP32
    socketio.emit('commande_esp32', {
        'action': 'activer_vibreur', 
        'duree': 5000,  # 5 secondes
        'force': True
    })
    
    return jsonify({'status': 'ok', 'message': 'Alerte forcée envoyée'})

@app.route('/api/analyser-modele', methods=['GET'])
def analyser_modele():
    """Analyser le comportement du modèle"""
    return test_toutes_valeurs()  # Réutilise la même fonction

@app.route('/api/effacer-alertes', methods=['POST'])
def effacer_alertes():
    """Effacer toutes les alertes"""
    global alertes
    alertes = []
    print("🗑️ Alertes effacées")
    socketio.emit('alertes_effacees', {})
    return jsonify({'status': 'ok', 'message': 'Alertes effacées'})

# ============================================
# ROUTE POUR ESP32
# ============================================

@app.route('/api/esp32/commande', methods=['POST'])
def commander_esp32():
    """Envoyer une commande directe à l'ESP32"""
    commande = request.json
    print(f"📡 Commande ESP32: {commande}")
    
    # Relayer la commande via socket
    socketio.emit('commande_esp32', commande)
    
    return jsonify({'status': 'ok', 'message': 'Commande envoyée'})

# ============================================
# RECEPTION DONNEES CAPTEURS
# ============================================

@socketio.on('data_capteurs')
def handle_sensor_data(data):
    """Reçoit les données de l'ESP32"""
    global mode_fuite
    
    # Ajouter timestamp
    data['timestamp'] = time.time()
    donnees_capteurs.append(data)
    
    # Prédire avec le modèle
    prediction = predire_fuite(data)
    
    # Ajouter la prédiction aux données
    data['prediction'] = prediction
    
    # Diffuser à tous les dashboards connectés
    socketio.emit('nouvelle_donnee', data)
    
    # Vérifier si alerte nécessaire (SEUIL À 30% MAINTENANT!)
    if prediction['fuite_detectee'] and prediction['probabilite'] > SEUIL_PROBABILITE:
        alerte = {
            'timestamp': time.time(),
            'message': f"⚠️ FUITE DÉTECTÉE! Probabilité: {prediction['probabilite']:.1%}",
            'donnees': data,
            'probabilite': prediction['probabilite']
        }
        alertes.append(alerte)
        
        # Envoyer alerte au dashboard
        socketio.emit('alerte', alerte)
        
        # Envoyer commande à l'ESP32
        socketio.emit('commande_esp32', {
            'action': 'activer_vibreur', 
            'duree': 3000,
            'probabilite': prediction['probabilite']
        })
        
        print(f"🚨 ALERTE: Fuite détectée avec probabilité {prediction['probabilite']:.1%}")
        
        # Activer le mode fuite
        mode_fuite = True

def predire_fuite(data):
    """
    Utilise le modèle ML pour prédire une fuite
    """
    try:
        # Extraire les valeurs
        vibration = data.get('vibration', data.get('Vibration (mm/s)', 0))
        temperature = data.get('temperature', data.get('Temperature (°C)', data.get('temp', 0)))
        pression = data.get('pression', data.get('Pressure (bar)', data.get('pressure', data.get('p', 0))))
        
        # Créer un DataFrame
        X = pd.DataFrame([[
            vibration,
            temperature, 
            pression
        ]], columns=['Vibration (mm/s)', 'Temperature (°C)', 'Pressure (bar)'])
        
        print(f"🔍 Analyse: Vib={vibration:.2f}, Temp={temperature:.2f}, Press={pression:.2f}")
        
        # Prédire
        probabilites = model.predict_proba(X)[0]
        probabilite_fuite = float(probabilites[1])
        prediction = model.predict(X)[0]
        
        print(f"📊 Résultat: Prédiction={prediction}, Prob fuite={probabilite_fuite:.2%}")
        
        return {
            'fuite_detectee': bool(prediction == 1),
            'probabilite': probabilite_fuite,
            'normal': float(probabilites[0])
        }
        
    except Exception as e:
        print(f"❌ Erreur de prédiction: {str(e)}")
        return {
            'fuite_detectee': False,
            'probabilite': 0.0,
            'normal': 1.0,
            'erreur': str(e)
        }

# ============================================
# SIMULATION AUTOMATIQUE
# ============================================

def simulation_donnees():
    """Simule des données en attendant l'ESP32"""
    print("🔄 Simulation démarrée - envoi de données toutes les secondes")
    compteur = 0
    global mode_fuite
    temps_fuite = 0
    
    while True:
        try:
            # Générer des données normales
            vibration = np.random.normal(50, 15)
            temperature = np.random.normal(25, 3)
            pression = np.random.normal(6, 1)
            
            # Si en mode fuite, valeurs extrêmes
            if mode_fuite:
                temps_fuite += 1
                # Valeurs PROGRESSIVES pour voir l'évolution
                facteur = min(temps_fuite, 5) / 5  # 0.2 à 1.0
                
                vibration = 150 + (250 * facteur) + np.random.uniform(-10, 10)
                temperature = 55 + (40 * facteur) + np.random.uniform(-3, 3)
                pression = max(0.2, 2.5 - (2.0 * facteur)) + np.random.uniform(-0.2, 0.2)
                
                if temps_fuite >= 5:
                    mode_fuite = False
                    temps_fuite = 0
                    print("✅ Retour à la normale")
            
            data = {
                'vibration': float(max(0, vibration)),
                'temperature': float(max(0, temperature)),
                'pression': float(max(0.1, pression)),
                'simulation': True,
                'mode_fuite': mode_fuite,
                'id': compteur
            }
            
            compteur += 1
            handle_sensor_data(data)
            
        except Exception as e:
            print(f"❌ Erreur simulation: {e}")
            
        time.sleep(1)

# Démarrer la simulation
simulation_thread = threading.Thread(target=simulation_donnees, daemon=True)
simulation_thread.start()

# ============================================
# DEMARRAGE
# ============================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 SERVEUR DE DÉTECTION DE FUITES - VERSION COMPLÈTE")
    print("="*70)
    print(f"📡 Serveur: http://localhost:5000")
    print(f"📊 Modèle: {type(model).__name__}")
    print(f"🔍 Features: {model.feature_names_in_}")
    print(f"🎯 Classes: {model.classes_}")
    print(f"⚠️ Seuil d'alerte: {SEUIL_PROBABILITE:.0%} (plus sensible)")
    print("\n" + "-"*70)
    print("🖱️ ROUTES DISPONIBLES:")
    print("-"*70)
    print("🎮 SIMULATIONS:")
    print("   POST /api/simuler-fuite           - Fuite progressive (avec niveaux)")
    print("   POST /api/forcer-alerte           - ALERTE IMMÉDIATE (contourne modèle)")
    print("   GET  /api/test-toutes-valeurs     - Teste toutes les valeurs")
    print("   GET  /api/analyser-modele         - Analyse le comportement")
    print("\n🗑️ GESTION:")
    print("   POST /api/effacer-alertes         - Efface toutes les alertes")
    print("\n📡 ESP32:")
    print("   POST /api/esp32/commande          - Commande directe ESP32")
    print("="*70 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)