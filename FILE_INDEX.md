# 📑 INDEX ET GUIDE DE NAVIGATION

## 🚀 Démarrage rapide

| OS | Commande |
|----|----------|
| **Windows** | Double-cliquer `launch.bat` |
| **Linux/macOS** | Exécuter `make launch` |

---

## 📂 Structure complète du dossier

```
Robot_Navigation_SLAM_Complete/          [DOSSIER RACINE - 88 KB]
│
├─ 📖 DOCUMENTATION (LIRE D'ABORD!)
│  ├─ README_FIRST.txt                   ← ⭐ COMMENCER ICI! (5 min)
│  ├─ docs/README.md                     ← Vue d'ensemble complète (20 min)
│  ├─ docs/INSTALLATION.md               ← Guide installation détaillé (15 min)
│  ├─ docs/UTILISATION.md                ← Guide utilisation complète (20 min)
│  └─ docs/SPECIFICATIONS.md             ← Spécifications techniques (30 min)
│
├─ 🚀 SCRIPTS DE LANCEMENT
│  ├─ launch.bat                         ← Windows: double-cliquer!
│  ├─ Makefile                           ← Linux/macOS: make launch
│  └─ scripts/launch_simulation.py       ← Script Python (cross-platform)
│
├─ 🤖 CODE ROBOT (Simulation Webots)
│  ├─ controllers/
│  │  └─ mobile_robot_controller_SAFE.py ← Contrôleur principal
│  │     ├─ SLAM (Occupancy Grid)
│  │     ├─ A* Pathplanning
│  │     ├─ Pure Pursuit
│  │     └─ 4 niveaux sécurité
│  │
│  ├─ proto_files/
│  │  └─ MobileRobotSafe.proto           ← Définition robot
│  │     ├─ 4 roues
│  │     ├─ GPS + IMU
│  │     ├─ LIDAR 360°
│  │     └─ Caméra
│  │
│  └─ worlds/
│     └─ navigation_world.wbt            ← Environnement simulation
│        ├─ Sol plat
│        ├─ 4 murs
│        ├─ 3 obstacles
│        ├─ Point de départ (bleu)
│        └─ Point d'arrivée (vert)
│
├─ ⚙️  CONFIGURATION
│  └─ config/
│     ├─ robot_config.json               ← Paramètres robot
│     │  ├─ Cinématique
│     │  ├─ Roues
│     │  ├─ Capteurs
│     │  └─ Sécurité
│     │
│     └─ navigation_params.json          ← Paramètres navigation
│        ├─ SLAM settings
│        ├─ A* settings
│        ├─ Pure Pursuit settings
│        ├─ Safety levels
│        └─ Debugging options
│
├─ 📚 DÉPENDANCES
│  └─ requirements.txt                   ← Python dependencies (AUCUNE externe!)
│
├─ 📝 VERSIONNING
│  ├─ CHANGELOG.md                       ← Historique des versions
│  ├─ .gitignore                         ← Fichiers à ignorer (git)
│  └─ README_FIRST.txt                   ← Lisezmoi en premier
│
└─ 🔗 WEBOTS (External)
   ├─ À télécharger depuis: https://cyberbotics.com
   └─ Version minimale requise: R2023b
```

---

## 📖 Fichiers par fonction

### 🎯 Pour DÉMARRER
1. **README_FIRST.txt** (5 min)
   - Intro rapide
   - Démarrage ultra-rapide
   - Problèmes courants

2. **launch.bat** / **Makefile** (1 clic)
   - Lancer la simulation
   - Vérifier dépendances
   - Ouvrir Webots

### 🚀 Pour INSTALLER
1. **docs/INSTALLATION.md** (15-30 min)
   - Prérequis système
   - Installation Webots
   - Copier fichiers
   - Vérifier installation
   - Dépannage détaillé

### 🎮 Pour UTILISER
1. **docs/UTILISATION.md** (20-40 min)
   - Démarrage
   - Paramètres modifiables
   - Analyse logs
   - Créer mondes perso
   - Exporter résultats
   - Dépannage avancé

### 🔧 Pour COMPRENDRE
1. **docs/SPECIFICATIONS.md** (30-60 min)
   - Spécifications robot
   - Dimensions physiques
   - SLAM détails
   - A* paramètres
   - Pure Pursuit math
   - Garanties sécurité
   - Performances

### 💻 Pour DÉVELOPPER
1. **controllers/mobile_robot_controller_SAFE.py** (1000+ lignes)
   - Code complet annoté
   - Modifiable facilement
   - Paramètres clairs
   - Classes bien structurées

---

## 🗺️ Cartes des modules

### Architecture logicielle
```
main() loop @ 20Hz
    ├─ sensors.read()
    ├─ slam.update() [every 3 steps]
    ├─ obstacles.analyze() [360°]
    ├─ planner.plan() [every 30 steps]
    ├─ tracker.follow()
    ├─ safety.check() [4 levels]
    └─ motors.drive()
```

### Hiérarchie de contrôle
```
Global Navigation (A* planner)
    ↓
Local Path Following (Pure Pursuit)
    ↓
Obstacle Avoidance (Safety 4 levels)
    ↓
Motor Commands (Kinematics inverse)
```

### Flux de données
```
Sensors (20 Hz)
    ├─ GPS → Position
    ├─ IMU → Orientation
    └─ LIDAR → Obstacles
        ↓
    SLAM (6.7 Hz)
    + A* (2 Hz)
    + Pure Pursuit (20 Hz)
    + Safety (20 Hz)
        ↓
    Motor Commands
```

---

## ⚡ Quick Reference Commands

### Windows
```cmd
# Lancer
launch.bat

# Dans une autre fenêtre
cd Robot_Navigation_SLAM_Complete
python scripts\launch_simulation.py
```

### Linux
```bash
# Lancer
make launch

# Ou manuel
python3 scripts/launch_simulation.py

# Installer dépendances optionnelles
make install

# Nettoyer
make clean
```

### macOS
```bash
# Même que Linux
make launch

# Si problème Python
python3 scripts/launch_simulation.py
```

---

## 🎯 Tâches courantes

### Modifier la cible
**Fichier:** `controllers/mobile_robot_controller_SAFE.py`
**Ligne:** ~500
```python
target = (0.0, 10.0)  # Changer x, y
```

### Changer la vitesse max
**Fichier:** `controllers/mobile_robot_controller_SAFE.py`
**Ligne:** ~125
```python
MAX_LINEAR_SPEED = 1.8  # Augmenter/réduire
```

### Ajuster la sécurité
**Fichier:** `controllers/mobile_robot_controller_SAFE.py`
**Ligne:** ~120-125
```python
CRITICAL_DISTANCE = 0.3      # Reculer
DANGER_DISTANCE = 0.6        # Arrêt
SLOW_DISTANCE = 1.2          # Ralentir 80%
CAUTION_DISTANCE = 1.8       # Ralentir 50%
```

### Créer un monde perso
**Fichier:** `worlds/navigation_world.wbt`
**Logiciel:** Webots (interface graphique)
**Documention:** Voir `docs/UTILISATION.md`

### Analyser la carte
**Fichier généré:** `map.pkl`
**Visualiser avec:**
```python
import pickle
import matplotlib.pyplot as plt
with open('map.pkl', 'rb') as f:
    grid = pickle.load(f)
plt.imshow(grid, cmap='gray')
plt.show()
```

---

## ✅ Vérifications d'installation

```bash
# 1. Python installé?
python3 --version
# Output: Python 3.8+

# 2. Webots installé?
webots --version
# Output: R2023b

# 3. Fichiers présents?
ls -la controllers/mobile_robot_controller_SAFE.py
ls -la worlds/navigation_world.wbt

# 4. Lancer test
make launch  # Linux/macOS
# Ou: launch.bat (Windows)
```

---

## 🐛 Dépannage rapide

| Problème | Solution | Fichier |
|----------|----------|---------|
| Python not found | Réinstaller + ajouter PATH | - |
| Webots not found | Télécharger https://cyberbotics.com | - |
| Robot ne bouge pas | Vérifier F5 activé | UTILISATION.md |
| LIDAR ne voit rien | Vérifier enable() | mobile_robot_controller_SAFE.py ligne 150 |
| Fichiers manquants | Vérifier téléchargement complet | README_FIRST.txt |

**Pour plus:** Voir `docs/INSTALLATION.md` et `docs/UTILISATION.md`

---

## 📊 Statistiques fichiers

| Type | Nombre | Taille |
|------|--------|--------|
| Documentation | 5 | 45 KB |
| Code Python | 2 | 25 KB |
| Configuration | 3 | 8 KB |
| Scripts | 3 | 5 KB |
| Webots (proto, world) | 2 | 5 KB |
| **Total** | **15** | **88 KB** |

---

## 🎓 Ordre de lecture recommandé

1. ⭐ **README_FIRST.txt** (2 min)
   - Vue d'ensemble

2. 📖 **docs/README.md** (10 min)
   - Fonctionnalités
   - Architecture

3. 🚀 **docs/INSTALLATION.md** (15 min)
   - Mettre en place

4. 🎮 **docs/UTILISATION.md** (20 min)
   - Utiliser le système

5. 🔧 **docs/SPECIFICATIONS.md** (30 min)
   - Comprendre la tech

6. 💻 **Code source** (2+ heures)
   - Développer/modifier

---

## 📞 Support

### Documentation locale
- Tous les `.md` fichiers
- README_FIRST.txt
- Code commenté

### Webots Help
- File → Help
- https://cyberbotics.com/docs

### Debugger
- Webots Console (Ctrl+Alt+C)
- Python logs
- robot_navigation.log

---

## 🎉 C'est tout!

**Vous avez un système complet prêt à l'emploi.**

Prochaine étape: **Lancer!**

```bash
make launch    # Linux/macOS
launch.bat     # Windows
```

---

**Version:** 1.0
**Date:** 2026-03-22
**Status:** ✅ Production Ready
