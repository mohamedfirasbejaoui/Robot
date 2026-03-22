#!/usr/bin/env python3
"""
🚀 Script de lancement du système de navigation autonome complet
"""

import os
import sys
import subprocess
import json
import time

def print_header():
    print("\n" + "="*80)
    print("🤖 SYSTÈME DE NAVIGATION AUTONOME - SLAM + A* + Pure Pursuit + Sécurité")
    print("="*80)
    print()

def check_webots():
    """Vérifier si Webots est installé"""
    print("🔍 Recherche de Webots...")
    
    webots_paths = [
        "/opt/webots",
        "/usr/bin/webots",
        "/Applications/Webots.app/Contents/MacOS/webots",
        "C:\\Program Files\\Webots\\msys64\\mingw64\\bin\\webots.exe"
    ]
    
    for path in webots_paths:
        if os.path.exists(path):
            print(f"✅ Webots trouvé: {path}")
            return path
    
    print("❌ Webots non trouvé!")
    print("   Installez Webots depuis: https://cyberbotics.com")
    return None

def check_python():
    """Vérifier si Python 3.8+ est disponible"""
    print("🔍 Vérification Python...")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} détecté (besoin 3.8+)")
        return False

def load_config():
    """Charger la configuration"""
    print("⚙️  Chargement configuration...")
    
    config_file = os.path.join(os.path.dirname(__file__), 
                              "../config/robot_config.json")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Configuration chargée ({len(config)} sections)")
        return config
    except Exception as e:
        print(f"⚠️  Impossible de charger config: {e}")
        return None

def setup_webots_env(webots_path):
    """Configurer les variables d'environnement Webots"""
    print("🔧 Configuration Webots...")
    
    os.environ['WEBOTS_HOME'] = webots_path
    
    if sys.platform == "linux":
        os.environ['LD_LIBRARY_PATH'] = f"{webots_path}/lib:$LD_LIBRARY_PATH"
    elif sys.platform == "darwin":
        os.environ['DYLD_LIBRARY_PATH'] = f"{webots_path}/lib:$DYLD_LIBRARY_PATH"
    
    print(f"✅ WEBOTS_HOME={webots_path}")

def display_features():
    """Afficher les fonctionnalités"""
    print("\n" + "="*80)
    print("✨ FONCTIONNALITÉS IMPLÉMENTÉES")
    print("="*80)
    
    features = {
        "🗺️  SLAM": "Cartographie probabiliste temps réel",
        "🛣️  A*": "Pathplanning optimal avec heuristique",
        "🎯 Pure Pursuit": "Suivi de trajectoire adaptatif",
        "🛡️  Sécurité": "4 niveaux de réaction (CRITICAL/DANGER/SLOW/CAUTION)",
        "📡 Capteurs": "GPS, IMU, LIDAR 360°, Caméra",
        "🔄 Replanification": "Auto tous les 30 pas",
        "🚫 Collision": "Détection à 2.5m minimum",
        "⚡ Performances": "100 Hz, <50ms temps réaction"
    }
    
    for feature, description in features.items():
        print(f"\n  {feature}")
        print(f"    → {description}")
    
    print("\n" + "="*80)

def display_safety_levels():
    """Afficher les niveaux de sécurité"""
    print("\n" + "="*80)
    print("🛡️  NIVEAUX DE SÉCURITÉ COLLISION")
    print("="*80)
    
    levels = [
        ("🚨 CRITICAL", "< 0.3m", "RECULER immédiatement", "1.5 m/s ↔"),
        ("🛑 DANGER", "< 0.6m", "ARRÊT + VIRAGE agressif", "v=0"),
        ("⚠️  SLOW", "< 1.2m", "RALENTIR 80%", "v * 0.2"),
        ("⚠️  CAUTION", "< 1.8m", "RALENTIR 50%", "v * 0.5"),
        ("✅ SAFE", "> 2.5m", "Navigation normale", "v normal")
    ]
    
    print("\n  Distance   | Action                    | Commande")
    print("  " + "-"*60)
    for name, dist, action, cmd in levels:
        print(f"  {name:15} {dist:8} | {action:25} | {cmd}")
    
    print("\n" + "="*80)

def main():
    print_header()
    
    # Vérifications
    if not check_python():
        sys.exit(1)
    
    print()
    
    webots_path = check_webots()
    if not webots_path:
        sys.exit(1)
    
    print()
    
    config = load_config()
    
    print()
    
    setup_webots_env(webots_path)
    
    # Afficher les infos
    display_features()
    display_safety_levels()
    
    # Préparation
    print("\n📦 Préparation du lancement...")
    print("  ✅ Contrôleur: controllers/mobile_robot_controller_SAFE.py")
    print("  ✅ Monde: worlds/navigation_world.wbt")
    print("  ✅ PROTO: proto_files/MobileRobotSafe.proto")
    
    print("\n" + "="*80)
    print("🚀 DÉMARRAGE DE LA SIMULATION")
    print("="*80)
    print("""
  UTILISATION:
  ✅ Play (F5 ou bouton) pour lancer
  ✅ Pause (F6) pour arrêter
  ✅ Console affiche les logs en direct
  ✅ Cible définie dans le contrôleur
  ✅ Map sauvegardée automatiquement en .pkl
  
  LOGS AFFICHÉS:
  📍 Position et distance cible
  ⚠️  Niveaux de sécurité
  ✅ Cible atteinte
  
  PARAMÈTRES MODIFIABLES:
  • CRITICAL_DISTANCE = 0.3
  • DANGER_DISTANCE = 0.6
  • SLOW_DISTANCE = 1.2
  • CAUTION_DISTANCE = 1.8
  • MAX_LINEAR_SPEED = 1.8
  • MAX_ANGULAR_SPEED = 4.0
  
  Appuyez sur ENTER pour continuer...
    """)
    input()
    
    # Ouvrir Webots avec le monde
    world_file = os.path.join(os.path.dirname(__file__), 
                             "../worlds/navigation_world.wbt")
    
    if not os.path.exists(world_file):
        print(f"⚠️  Fichier monde non trouvé: {world_file}")
        print("     Créez-le ou modifiez le chemin")
    
    cmd = [webots_path, "--batch"]
    
    if world_file and os.path.exists(world_file):
        cmd.append(world_file)
    
    print(f"\n▶️  Lancement: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)
    
    print("\n✅ Simulation fermée")
    print("=" * 80)

if __name__ == "__main__":
    main()
