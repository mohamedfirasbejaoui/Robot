# 🎮 GUIDE D'UTILISATION COMPLET

## 📖 Table des matières
1. [Démarrage rapide](#-démarrage-rapide)
2. [Cibles et navigation](#-cibles-et-navigation)
3. [Paramètres de sécurité](#-paramètres-de-sécurité)
4. [Analyse des logs](#-analyse-des-logs)
5. [Créer vos propres mondes](#-créer-vos-propres-mondes)
6. [Exporter et analyser les résultats](#-exporter-et-analyser-les-résultats)

---

## 🚀 Démarrage rapide

### Lancer la simulation (3 étapes)

#### Windows
```bash
cd C:\Users\VotreNom\Robot_Navigation_SLAM_Complete
python scripts\launch_simulation.py
```

#### Linux/macOS
```bash
cd ~/Robot_Navigation_SLAM_Complete
python3 scripts/launch_simulation.py
```

**Vous verrez:**
```
================================================================================
🤖 SYSTÈME DE NAVIGATION AUTONOME - SLAM + A* + Pure Pursuit + Sécurité
================================================================================

✨ FONCTIONNALITÉS IMPLÉMENTÉES
...
🛡️  NIVEAUX DE SÉCURITÉ COLLISION
...

🚀 DÉMARRAGE DE LA SIMULATION

Appuyez sur ENTER pour continuer...
```

Appuyez sur ENTER → Webots s'ouvre avec le monde

### Une fois dans Webots

1. **Voir le robot bleu** au point de départ (bas de la carte)
2. **Appuyer F5** (Play) ou cliquer le bouton Play
3. **Robot commence à naviguer** vers la cible verte (haut)
4. **Console affiche les logs** en direct

---

## 🎯 Cibles et navigation

### Cible par défaut

La cible est définie à **x=0, y=10** (haut de la carte)

```python
# Dans: controllers/mobile_robot_controller_SAFE.py
# Ligne ~500, fonction loop()

if target is None and step_count == 100:
    target = (0.0, 10.0)  # Cible par défaut
    print(f"\n🎯 CIBLE: ({target[0]:.2f}, {target[1]:.2f})\n")
```

### Modifier la cible

#### Option 1: Modifier dans le code
```python
# Changer (0.0, 10.0) en votre cible:
target = (5.0, 8.0)      # Diagonale
target = (-10.0, 5.0)    # À gauche
target = (0.0, -10.0)    # Vers le bas
```

#### Option 2: Cibles multiples (exploration)
```python
# Modifier la boucle principale:
goals = [(0.0, 10.0), (10.0, 0.0), (0.0, -10.0)]
goal_idx = 0

if target is None:
    target = goals[goal_idx]
    goal_idx = (goal_idx + 1) % len(goals)
    print(f"\n🎯 CIBLE #{goal_idx}: {target}\n")
```

### Déboguer la navigation

**Logs affichés:**

| Log | Signification |
|-----|---|
| `📍 (x,y) \| Dist: 12.34m` | Position actuelle et distance cible |
| `✅ ATTEINT! (10.00, 10.00)` | Cible atteinte! |
| `⚠️  CAUTION! 1.75m < 1.8m` | Zone d'attention (ralentir 50%) |
| `⚠️  SLOW! 0.95m < 1.2m` | Zone danger (ralentir 80%) |
| `🛑 DANGER! 0.55m < 0.6m` | Zone critique (arrêt + virage) |
| `🚨 CRITICAL! 0.25m < 0.3m` | Très proche (reculer) |
| `⚠️ BLOQUÉ - Replanification` | Robot coincé, replan en cours |

---

## 🛡️ Paramètres de sécurité

### Les 4 niveaux de sécurité

```
Distance | Niveau   | Action              | Commande
---------|----------|---------------------|----------
< 0.3m   | CRITICAL | Reculer             | v = -1.5 m/s
< 0.6m   | DANGER   | Arrêt + virage      | v = 0, ω agressif
< 1.2m   | SLOW     | Ralentir 80%        | v *= 0.2
< 1.8m   | CAUTION  | Ralentir 50%        | v *= 0.5
> 2.5m   | SAFE     | Navigation normale  | v normal
```

### Modifier les seuils

**Changer dans le code (ligne ~120-125):**

```python
# SEUILS DE SÉCURITÉ - Modifiables!
CRITICAL_DISTANCE = 0.3       # Reculer
DANGER_DISTANCE = 0.6         # Arrêt
SLOW_DISTANCE = 1.2           # Ralentir 80%
CAUTION_DISTANCE = 1.8        # Ralentir 50%
SAFE_DISTANCE = 2.5           # Normal

# Vitesses
MAX_LINEAR_SPEED = 1.8        # m/s (plus rapide = plus risqué)
MAX_ANGULAR_SPEED = 4.0       # rad/s
```

### Exemples d'ajustement

#### Pour un robot PLUS RAPIDE (mais moins sûr):
```python
CRITICAL_DISTANCE = 0.5
DANGER_DISTANCE = 1.0
SLOW_DISTANCE = 2.0
MAX_LINEAR_SPEED = 3.0  # Plus rapide
```

#### Pour un robot PLUS SÛRE (mais plus lent):
```python
CRITICAL_DISTANCE = 0.1
DANGER_DISTANCE = 0.3
SLOW_DISTANCE = 0.8
CAUTION_DISTANCE = 1.2
MAX_LINEAR_SPEED = 0.8  # Plus lent
```

---

## 📊 Analyse des logs

### Comprendre les statistiques

**Chaque 40 pas (~0.67 secondes):**
```
📍 (1.25,-9.87) | Dist: 19.45m | Min obs: 8.50m
```

**Décoder:**
- `(1.25,-9.87)` = Position actuelle (X, Y) en mètres
- `Dist: 19.45m` = Distance jusqu'à la cible
- `Min obs: 8.50m` = Obstacle le plus proche

**Quand le robot approche:**
```
⚠️  CAUTION! 1.75m < 1.8m - Modérer
```
= Obstacle à 1.75m (< 1.8m) → Ralentir 50%

### Vérifier si ça marche bien

✅ **BON:**
```
📍 (0.12, 5.34) | Dist: 4.67m | Min obs: 5.20m
📍 (0.18, 6.45) | Dist: 3.55m | Min obs: 6.10m
📍 (0.04, 7.89) | Dist: 2.11m | Min obs: 7.30m
✅ ATTEINT! (0.02, 10.00)
```
→ Robot avance progressivement, détecte les obstacles, atteint la cible!

❌ **MAUVAIS:**
```
📍 (0.01, -9.99) | Dist: 19.99m | Min obs: 1.05m
🛑 DANGER! 0.55m < 0.6m - ARRÊT + VIRAGE
🛑 DANGER! 0.55m < 0.6m - ARRÊT + VIRAGE
⚠️ BLOQUÉ - Replanification
```
→ Robot coincé, n'avance pas. Augmentez `DANGER_DISTANCE`.

---

## 🌍 Créer vos propres mondes

### Éditer le monde Webots

1. **Ouvrir le monde:**
   - File → Open World → `worlds/navigation_world.wbt`

2. **Ajouter des obstacles:**
   - Cliquer: Add → Solid
   - Transformer → Scaling (redimensionner)
   - Physics → Enable

3. **Placer le robot:**
   - Translation du robot → Position de départ
   - Exemple: `translation 0 -10 0` (bas)

4. **Placer la cible:**
   - Éditer le Solid "target"
   - Translation → Position cible
   - Exemple: `translation 0 10 0` (haut)

### Créer un labyrinthe

Exemple de code VRML pour labyrinthe:

```vrml
# Mur horizontal
DEF MAZE_WALL1 Solid {
  translation 0 5 0.5
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.5 0.3 0.3 }
      geometry Box { size 10 1 1 }
    }
  ]
  boundingObject Box { size 10 1 1 }
  physics Physics { }
}

# Mur vertical
DEF MAZE_WALL2 Solid {
  translation 5 0 0.5
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.5 0.3 0.3 }
      geometry Box { size 1 10 1 }
    }
  ]
  boundingObject Box { size 1 10 1 }
  physics Physics { }
}
```

### Obstacles courants

```vrml
# Cylindre
geometry Cylinder { radius 0.5 height 1 }

# Boîte
geometry Box { size 1 1 1 }

# Sphère
geometry Sphere { radius 0.5 }
```

---

## 📁 Exporter et analyser les résultats

### Carte SLAM sauvegardée

Après chaque simulation, la carte est sauvegardée:

```python
# Automatiquement créé dans le répertoire du contrôleur:
map.pkl
```

### Charger et afficher la carte

```python
import pickle
import numpy as np
import matplotlib.pyplot as plt

# Charger
with open('map.pkl', 'rb') as f:
    grid = pickle.load(f)

# Afficher
plt.figure(figsize=(12, 12))
plt.imshow(grid, cmap='gray', origin='upper')
plt.colorbar(label='Probabilité occupation')
plt.title('Occupancy Grid Map')
plt.xlabel('X (cellules)')
plt.ylabel('Y (cellules)')
plt.show()
```

### Générer des statistiques

```python
# Dans le contrôleur, ajouter:
stats = {
    'target_reached': reached,
    'distance_traveled': sum(math.hypot(...) for ...),
    'time_seconds': step_count / 20,  # 20 Hz
    'min_obstacle': min_all,
    'collisions': collision_count
}

with open('stats.json', 'w') as f:
    json.dump(stats, f)
```

---

## 🔍 Dépannage avancé

### Robot ne va pas en avant

**Causes possibles:**
1. Cible trop proche (< 0.3m)
2. Obstacle directement en avant
3. Moteurs désactivés

**Solution:**
```python
# Vérifier moteurs dans setup():
for m in motors:
    m.setPosition(float('inf'))  # ← Important!
    m.setVelocity(0.0)
```

### Robot tourne en boucle

**Causes possibles:**
1. Cible impossible à atteindre
2. Obstacles bloquants
3. SLAM imprécis

**Solution:**
```python
# Ajouter dans navigate():
if len(position_history) > 20:
    if moved < 0.15:  # Pas avancé
        print("🔄 STUCK - Retrying...")
        current_path = []  # Forcer replan
```

### LIDAR ne détecte rien

**Causes possibles:**
1. LIDAR désactivé
2. Pas d'obstacles à proximité
3. Obstacles en dehors du champ de vue

**Solution:**
```python
# Vérifier dans setup():
lidar = robot.getDevice("lidar")
lidar.enable(timestep)  # ← Obligatoire!

# Tester manuellement:
ranges = lidar.getRangeImage()
print(f"Ranges count: {len(ranges)}")
print(f"Min: {min(ranges):.2f}, Max: {max(ranges):.2f}")
```

---

## ✅ CHECKLIST D'UTILISATION

Avant de lancer:
- [ ] Python 3.8+ installé
- [ ] Webots R2023b+ installé
- [ ] Fichiers copiés dans Webots
- [ ] Monde `navigation_world.wbt` trouvé
- [ ] Contrôleur `mobile_robot_controller_SAFE.py` existe

Au lancement:
- [ ] Webots s'ouvre
- [ ] Monde charge sans erreur
- [ ] Robot visible (bleu)
- [ ] Cible visible (verte)
- [ ] Pas d'erreur rouge dans la console

Pendant la simulation:
- [ ] F5 lancé (Play activé)
- [ ] Robot commence à bouger
- [ ] Logs affichés
- [ ] Robot détourne les obstacles
- [ ] Atteint la cible ou se replan

Après simulation:
- [ ] Pas de crash
- [ ] Map sauvegardée (map.pkl)
- [ ] Cible atteinte ou tentée

---

## 🎓 CONSEILS AVANCÉS

### Optimiser la vitesse
```python
# Robot trop lent?
LIN_GAIN = 1.2          # Augmenter (risque + oscillations)
MAX_LINEAR_SPEED = 2.5  # Augmenter
```

### Améliorer le suivi
```python
# Robot dévie de la trajectoire?
ANG_GAIN = 4.0          # Augmenter (plus agressif)
LOOKAHEAD_DIST = 1.2    # Augmenter (anticipe plus)
```

### Réduire les oscillations
```python
# Robot oscille trop?
CMD_HISTORY_LEN = 7     # Augmenter (lisse plus)
ANG_GAIN = 2.0          # Réduire (moins agressif)
```

---

## 🚀 PROCHAINES ÉTAPES

1. ✅ Tester avec la cible par défaut
2. ✅ Modifier la cible et relancer
3. ✅ Créer un labyrinthe personnalisé
4. ✅ Ajuster les paramètres de sécurité
5. ✅ Analyser la carte générée
6. ✅ Exporter les résultats

---

## 🎉 C'EST TOUT!

Vous avez un robot de navigation complet et fonctionnel!

**Bon succès avec votre simulation!** 🤖✨
