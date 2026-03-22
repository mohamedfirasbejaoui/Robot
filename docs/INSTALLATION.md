# 🚀 GUIDE D'INSTALLATION COMPLET

## Prérequis Système

### Windows 10/11
- ✅ Python 3.8+ (https://www.python.org)
- ✅ Webots R2023b+ (https://cyberbotics.com)
- ✅ 500MB espace disque
- ✅ RAM: 4GB minimum

### Linux (Ubuntu 20.04+)
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip
```

### macOS 10.15+
```bash
# Installer Homebrew si absent
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python
brew install python3
```

---

## 📥 INSTALLATION ÉTAPE PAR ÉTAPE

### Étape 1️⃣: Télécharger et extraire

#### Windows
```bash
# Télécharger le fichier ZIP
# Extraire dans: C:\Users\VotreNom\Robot_Navigation_SLAM_Complete

cd C:\Users\VotreNom\Robot_Navigation_SLAM_Complete
```

#### Linux/macOS
```bash
# Télécharger et extraire
unzip Robot_Navigation_SLAM_Complete.zip
cd Robot_Navigation_SLAM_Complete
pwd  # Affiche le chemin complet
```

### Étape 2️⃣: Installer Webots

**Windows:**
1. Télécharger depuis https://cyberbotics.com/download
2. Installer (accepter tous les chemins par défaut)
3. Webots s'installe normalement dans: `C:\Program Files\Webots`

**Linux:**
```bash
# Snap (recommandé)
sudo snap install webots --classic

# Ou compilation depuis source
wget https://github.com/cyberbotics/webots/releases/download/R2023b/webots-R2023b-x86-64.tar.bz2
tar xjf webots-R2023b-x86-64.tar.bz2
```

**macOS:**
```bash
# Télécharger depuis https://cyberbotics.com
# Ou via Homebrew
brew install --cask webots
```

### Étape 3️⃣: Vérifier l'installation

#### Windows (CMD ou PowerShell)
```cmd
python --version
REM Doit afficher: Python 3.8+

webots --version
REM Doit afficher: webots R2023b (ou plus récent)
```

#### Linux/macOS (Terminal)
```bash
python3 --version
# Output: Python 3.8+

which webots
# Output: /usr/bin/webots (ou autre chemin)
```

### Étape 4️⃣: Copier les fichiers Webots (Important!)

#### Windows
```cmd
REM Trouver le répertoire Webots
REM Par défaut: C:\Program Files\Webots

REM Copier le contrôleur
copy controllers\mobile_robot_controller_SAFE.py ^
"C:\Program Files\Webots\projects\robots\robotis\turtlebot3\controllers\"

REM Copier le PROTO
copy proto_files\MobileRobotSafe.proto ^
"C:\Program Files\Webots\projects\robots\robotis\turtlebot3\protos\"

REM Copier le monde
copy worlds\navigation_world.wbt ^
"C:\Program Files\Webots\projects\robots\robotis\turtlebot3\worlds\"
```

#### Linux
```bash
# Trouver Webots
WEBOTS_HOME=$(which webots | sed 's/\/bin\/webots//')
echo "Webots trouvé dans: $WEBOTS_HOME"

# Copier les fichiers
cp controllers/mobile_robot_controller_SAFE.py \
   $WEBOTS_HOME/projects/robots/robotis/turtlebot3/controllers/

cp proto_files/MobileRobotSafe.proto \
   $WEBOTS_HOME/projects/robots/robotis/turtlebot3/protos/

cp worlds/navigation_world.wbt \
   $WEBOTS_HOME/projects/robots/robotis/turtlebot3/worlds/
```

#### macOS
```bash
WEBOTS_HOME="/Applications/Webots.app/Contents"

cp controllers/mobile_robot_controller_SAFE.py \
   "$WEBOTS_HOME/projects/robots/robotis/turtlebot3/controllers/"

cp proto_files/MobileRobotSafe.proto \
   "$WEBOTS_HOME/projects/robots/robotis/turtlebot3/protos/"

cp worlds/navigation_world.wbt \
   "$WEBOTS_HOME/projects/robots/robotis/turtlebot3/worlds/"
```

### Étape 5️⃣: Vérifier que tout est en place

```bash
# Linux/macOS
ls -la /opt/webots/projects/robots/robotis/turtlebot3/controllers/
# Doit montrer: mobile_robot_controller_SAFE.py

# Windows
dir "C:\Program Files\Webots\projects\robots\robotis\turtlebot3\controllers\"
REM Doit afficher: mobile_robot_controller_SAFE.py
```

---

## ▶️ PREMIÈRE UTILISATION

### Méthode 1️⃣: Lancer avec le script Python (RECOMMANDÉ)

#### Windows
```cmd
cd C:\Users\VotreNom\Robot_Navigation_SLAM_Complete
python scripts\launch_simulation.py
```

#### Linux/macOS
```bash
cd ~/Robot_Navigation_SLAM_Complete
python3 scripts/launch_simulation.py
```

**Le script va:**
✅ Vérifier Python 3.8+
✅ Détecter Webots
✅ Afficher les fonctionnalités
✅ Ouvrir Webots avec le monde

### Méthode 2️⃣: Lancer manuellement dans Webots

1. **Ouvrir Webots**
   - Windows: Cliquer sur l'icône Webots
   - Linux: `webots` dans terminal
   - macOS: Ouvrir Applications → Webots

2. **Charger le monde**
   - File → Open World
   - Naviguer vers: `worlds/navigation_world.wbt`
   - Ouvrir

3. **Vérifier le robot**
   - Dans l'arborescence de gauche, voir "MobileRobot"
   - Pas d'erreur rouge

4. **Lancer la simulation**
   - Appuyer sur **F5** (Play)
   - Robot doit commencer à bouger
   - Logs apparaissent dans la console

---

## 🔧 DÉPANNAGE

### Problème: "Python not found"
**Solution:**
```bash
# Windows: Ajouter Python au PATH
# Aller dans: Paramètres → Variables d'environnement
# Ajouter: C:\Users\VotreNom\AppData\Local\Programs\Python\Python311

# Linux/macOS:
export PATH="/usr/bin/python3:$PATH"
python3 scripts/launch_simulation.py
```

### Problème: "Webots not found"
**Solution:**
```bash
# Vérifier l'installation
# Windows:
"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe" --version

# Linux:
/snap/bin/webots --version

# macOS:
/Applications/Webots.app/Contents/MacOS/webots --version
```

### Problème: "mobile_robot_controller_SAFE.py: No such file"
**Solution:**
✅ Vérifier que le fichier a bien été copié
✅ Utiliser chemin absolu dans Webots
✅ Redémarrer Webots

### Problème: Robot ne bouge pas
**Solution:**
- Vérifier: Play est activé (F5)?
- Vérifier: Console sans erreur?
- Vérifier: Moteurs sont activés?
```python
# Dans le contrôleur, ligne 30:
motors[0].setPosition(float('inf'))  # ← Important!
motors[0].setVelocity(0.0)
```

### Problème: LIDAR ne voit rien
**Solution:**
```python
# Vérifier dans le contrôleur:
lidar = robot.getDevice("lidar")
lidar.enable(timestep)  # ← Important!
```

### Problème: "No module named 'pickle'" (Python 2)
**Solution:**
```bash
# Utiliser Python 3:
python3 scripts/launch_simulation.py
# NON:
python scripts/launch_simulation.py  # ← Python 2, éviter!
```

---

## ✅ VÉRIFICATION D'INSTALLATION

Après tout, tester:

```bash
# 1. Python OK?
python3 -c "import pickle, math, heapq; print('✅ Python OK')"

# 2. Webots OK?
webots --version

# 3. Fichiers en place?
ls -la controllers/mobile_robot_controller_SAFE.py
ls -la proto_files/MobileRobotSafe.proto
ls -la worlds/navigation_world.wbt

# 4. Lancer le test
python3 scripts/launch_simulation.py
```

**Tous les tests passent? 🎉 C'est prêt!**

---

## 🚀 UTILISATION RAPIDE

### 1. Lancer la simulation
```bash
python3 scripts/launch_simulation.py
```

### 2. Appuyer F5 (Play)

### 3. Robot navigue automatiquement vers la cible (0, 10)

### 4. Voir les logs dans la console:
```
📍 (x,y) | Dist: 12.34m | Min obs: 8.50m
⚠️  CAUTION! 1.75m < 1.8m - Modérer
✅ ATTEINT! (10.00, 10.00)
```

### 5. Modifier la cible dans le code:
```python
# Ligne ~500 dans mobile_robot_controller_SAFE.py
if target is None and step_count == 100:
    target = (15.0, 5.0)  # ← Votre cible!
```

---

## 📚 FICHIERS IMPORTANTS

| Fichier | Fonction |
|---------|----------|
| `controllers/mobile_robot_controller_SAFE.py` | Contrôleur principal (SLAM + A* + Pure Pursuit) |
| `proto_files/MobileRobotSafe.proto` | Définition du robot |
| `worlds/navigation_world.wbt` | Environnement de simulation |
| `config/robot_config.json` | Paramètres du robot |
| `scripts/launch_simulation.py` | Script de lancement |
| `docs/README.md` | Documentation complète |

---

## 🎓 PROCHAINES ÉTAPES

Après installation réussie:

1. **Lire** `docs/README.md`
2. **Tester** avec la cible par défaut (0, 10)
3. **Modifier** les paramètres de sécurité si nécessaire
4. **Créer** vos propres mondes (obstacles différents)
5. **Exporter** la carte générée (map.pkl)

---

## 🆘 BESOIN D'AIDE?

### Logs Webots
- **File → View → Console**
- Affiche tous les messages Python
- Erreurs en rouge

### Fichier de log
```python
# Les logs se sauvegardent dans:
# ~/robot_navigation_YYYYMMDD_HHMMSS.log
```

### Forum
- Webots: https://cyberbotics.com/community
- Vérifier les issues existantes

---

## 🎉 C'EST PRÊT!

✅ Installation complète
✅ Tous les fichiers en place
✅ Prêt à naviguer!

**BON SUCCÈS!** 🚀
