"""
🤖 SYSTÈME DE NAVIGATION AVANCÉ AVEC SLAM EN TEMPS RÉEL
Utilise grid_map.py pour la cartographie
Commandes: echo "x,y" > command.txt
"""

from controller import Robot
import math
import os
import time
import pickle
import random
import heapq
from grid_map import OccupancyGrid, GridCell

# ═══════════════════════════════════════════════════════════════════════════
# CLASSE POUR LA PLANIFICATION DE CHEMIN A*
# ═══════════════════════════════════════════════════════════════════════════

class AStarPlanner:
    """Planificateur de chemin A* pour navigation globale"""
    def __init__(self, occupancy_grid):
        self.grid = occupancy_grid
        self.resolution = occupancy_grid.resolution
        
    def plan_path(self, start_world, goal_world):
        """Planifier un chemin du start au goal en évitant les obstacles"""
        # Convertir en coordonnées grille
        start_grid = self.grid.world_to_grid(start_world[0], start_world[1])
        goal_grid = self.grid.world_to_grid(goal_world[0], goal_world[1])
        
        # Vérifier si les coordonnées sont valides
        if not self.grid.is_valid(goal_grid[0], goal_grid[1]):
            return None
        
        # Vérifier si le goal est libre
        if self.grid.is_occupied(goal_grid[0], goal_grid[1]):
            # Chercher une cellule libre proche
            goal_grid = self._find_free_neighbor(goal_grid)
            if not goal_grid:
                return None
        
        # File de priorité pour A*
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        
        # Dictionnaires pour les parents et les coûts
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}
        
        closed_set = set()
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current in closed_set:
                continue
                
            if current == goal_grid or self._heuristic(current, goal_grid) < 2:
                # Chemin trouvé
                return self._reconstruct_path(came_from, current, start_grid)
            
            closed_set.add(current)
            
            # Explorer les voisins (8 directions)
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Vérifier les limites
                if not self.grid.is_valid(neighbor[0], neighbor[1]):
                    continue
                
                # Vérifier si la cellule est libre
                if self.grid.is_occupied(neighbor[0], neighbor[1]):
                    continue
                
                # Coût du mouvement (diagonale plus chère)
                move_cost = math.sqrt(dx*dx + dy*dy) if dx != 0 and dy != 0 else 1.0
                tentative_g = g_score.get(current, 0) + move_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return None  # Pas de chemin trouvé
    
    def _find_free_neighbor(self, grid_coord, radius=5):
        """Trouver une cellule libre proche"""
        x, y = grid_coord
        for r in range(1, radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = x + dx, y + dy
                    if self.grid.is_valid(nx, ny) and not self.grid.is_occupied(nx, ny):
                        return (nx, ny)
        return None
    
    def _heuristic(self, a, b):
        """Heuristique pour A* (distance euclidienne)"""
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
    
    def _reconstruct_path(self, came_from, current, start):
        """Reconstruire le chemin depuis came_from"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        
        # Inverser pour avoir du start au goal
        path.reverse()
        
        # Convertir en coordonnées monde
        world_path = []
        for grid_x, grid_y in path:
            world_x, world_y = self.grid.grid_to_world(grid_x, grid_y)
            world_path.append((world_x, world_y))
        
        return world_path


# ═══════════════════════════════════════════════════════════════════════════
# INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════

robot = Robot()
timestep = int(robot.getBasicTimeStep())

# Récupérer tous les devices
gps = robot.getDevice("gps")
gps.enable(timestep)

imu = robot.getDevice("imu")
imu.enable(timestep)

lidar = robot.getDevice("lidar")
lidar.enable(timestep)
lidar.enablePointCloud()

# Paramètres LiDAR
lidar_fov = lidar.getFov()
lidar_max_range = lidar.getMaxRange()
lidar_horizontal_resolution = lidar.getHorizontalResolution()
if lidar_horizontal_resolution > 0:
    lidar_angle_increment = lidar_fov / lidar_horizontal_resolution
else:
    lidar_angle_increment = 0.01

# Moteurs
motors = []
for name in [
    "front_left_wheel_motor",
    "front_right_wheel_motor",
    "rear_left_wheel_motor",
    "rear_right_wheel_motor",
]:
    m = robot.getDevice(name)
    m.setPosition(float("inf"))
    m.setVelocity(0.0)
    motors.append(m)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Déterminer le chemin du répertoire du contrôleur
controller_dir = os.path.dirname(os.path.abspath(__file__))
command_file = os.path.join(controller_dir, "command.txt")
map_file = os.path.join(controller_dir, "map.pkl")
log_file = os.path.join(controller_dir, "navigation_log.txt")

# Paramètres du robot
WHEEL_RADIUS = 0.1
WHEEL_BASE = 0.5
MAX_SPEED = 6.0
MAX_LINEAR_SPEED = 1.5
MAX_ANGULAR_SPEED = 2.0

# Paramètres de navigation
GOAL_THRESHOLD = 0.3  # Distance pour considérer atteint
OBSTACLE_THRESHOLD = 0.8  # Distance min aux obstacles
DANGER_DISTANCE = 0.5
SAFE_DISTANCE = 1.0
PATH_REPLAN_INTERVAL = 50  # Replanifier tous les 50 pas de temps

# ═══════════════════════════════════════════════════════════════════════════
# GRILLE D'OCCUPATION (SLAM)
# ═══════════════════════════════════════════════════════════════════════════

# Charger la carte existante ou créer une nouvelle
if os.path.exists(map_file):
    try:
        with open(map_file, 'rb') as f:
            occupancy_grid = pickle.load(f)
        print("🗺️  Carte chargée!")
    except:
        occupancy_grid = OccupancyGrid(resolution=0.1, size=300)
        print("📍 Nouvelle carte créée (échec chargement)")
else:
    occupancy_grid = OccupancyGrid(resolution=0.1, size=300)
    print("📍 Nouvelle carte créée")

# Initialiser les composants
path_planner = AStarPlanner(occupancy_grid)

# Variables d'état
current_path = []
path_index = 0
last_replan_time = 0
goal_position = None
exploration_mode = False

def save_map():
    """Sauvegarder la carte"""
    try:
        with open(map_file, 'wb') as f:
            pickle.dump(occupancy_grid, f)
        print("💾 Carte sauvegardée")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

def log_message(message):
    """Écrire dans le fichier de log"""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def update_map_from_lidar(robot_x, robot_y, robot_angle):
    """Mettre à jour la carte avec les données LiDAR (SLAM)"""
    ranges = lidar.getRangeImage()
    if not ranges:
        return
    
    num_points = len(ranges)
    current_time = time.time()
    
    # SLAM: Mettre à jour la grille
    for i, r in enumerate(ranges):
        if r >= lidar_max_range * 0.99 or math.isinf(r) or math.isnan(r):
            continue  # Pas de détection
        
        # Angle absolu du rayon
        angle = robot_angle - lidar_fov/2 + i * lidar_angle_increment
        
        # Position de l'obstacle en coordonnées monde
        obs_x = robot_x + r * math.cos(angle)
        obs_y = robot_y + r * math.sin(angle)
        
        # Marquer comme occupé
        grid_x, grid_y = occupancy_grid.world_to_grid(obs_x, obs_y)
        occupancy_grid.update_cell(grid_x, grid_y, True, current_time)
        
        # Marquer le chemin jusqu'à l'obstacle comme libre
        steps = int(r / occupancy_grid.resolution)
        for step in range(max(1, min(steps, 30))):  # Limiter pour performance
            t = step / max(steps, 1)
            free_x = robot_x + t * r * math.cos(angle)
            free_y = robot_y + t * r * math.sin(angle)
            free_grid_x, free_grid_y = occupancy_grid.world_to_grid(free_x, free_y)
            
            occupancy_grid.update_cell(free_grid_x, free_grid_y, False, current_time)

def find_exploration_targets():
    """Trouver des cibles d'exploration (frontières inconnues)"""
    frontier_cells = []
    
    # Parcourir la grille pour trouver les cellules frontière
    step = max(1, occupancy_grid.size // 40)  # Échantillonnage pour performance
    for x in range(0, occupancy_grid.size, step):
        for y in range(0, occupancy_grid.size, step):
            cell = occupancy_grid.grid[x][y]
            
            # Si la cellule n'est pas visitée, chercher des voisins visités
            if not cell.visited:
                # Vérifier les 4 voisins
                neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
                has_visited_neighbor = False
                
                for nx, ny in neighbors:
                    if occupancy_grid.is_valid(nx, ny) and occupancy_grid.grid[nx][ny].visited:
                        has_visited_neighbor = True
                        break
                
                if has_visited_neighbor:
                    # Convertir en coordonnées monde
                    wx, wy = occupancy_grid.grid_to_world(x, y)
                    frontier_cells.append((wx, wy))
    
    return frontier_cells

# ═══════════════════════════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════

def inverse_kinematics(v_lin, v_ang):
    """Calculer les vitesses des roues"""
    omega_left = (v_lin - v_ang * WHEEL_BASE / 2.0) / WHEEL_RADIUS
    omega_right = (v_lin + v_ang * WHEEL_BASE / 2.0) / WHEEL_RADIUS
    
    omega_left = max(-MAX_SPEED, min(MAX_SPEED, omega_left))
    omega_right = max(-MAX_SPEED, min(MAX_SPEED, omega_right))
    
    return omega_left, omega_right

def apply_velocities(omega_left, omega_right):
    """Appliquer les vitesses aux moteurs"""
    motors[0].setVelocity(omega_left)   # front_left
    motors[2].setVelocity(omega_left)   # rear_left
    motors[1].setVelocity(omega_right)  # front_right
    motors[3].setVelocity(omega_right)  # rear_right

def analyze_obstacles_detailed():
    """Analyse détaillée des obstacles avec segmentation"""
    ranges = lidar.getRangeImage()
    if not ranges or len(ranges) < 10:
        return {
            'front': 10.0, 'left': 10.0, 'right': 10.0,
            'min_all': 10.0, 'obstacle_detected': False,
            'left_clear': True, 'right_clear': True, 'front_clear': True
        }
    
    # Nettoyer les valeurs
    clean_ranges = []
    for r in ranges:
        if math.isinf(r) or math.isnan(r):
            clean_ranges.append(10.0)
        else:
            clean_ranges.append(r)
    
    n = len(clean_ranges)
    sector_size = max(1, n // 8)
    
    # Diviser en secteurs
    front_start = max(0, n//2 - sector_size)
    front_end = min(n, n//2 + sector_size)
    front = clean_ranges[front_start:front_end] if front_start < front_end else [10.0]
    
    left = clean_ranges[:n//3] if n//3 > 0 else [10.0]
    right = clean_ranges[2*n//3:] if 2*n//3 < n else [10.0]
    
    # Calculer les distances minimales
    result = {
        'front': min(front) if front else 10.0,
        'left': min(left) if left else 10.0,
        'right': min(right) if right else 10.0,
        'min_all': 10.0,
        'obstacle_detected': False,
        'left_clear': True,
        'right_clear': True,
        'front_clear': True
    }
    
    result['min_all'] = min(result['front'], result['left'], result['right'])
    result['obstacle_detected'] = result['min_all'] < OBSTACLE_THRESHOLD
    result['front_clear'] = result['front'] > SAFE_DISTANCE
    result['left_clear'] = result['left'] > SAFE_DISTANCE
    result['right_clear'] = result['right'] > SAFE_DISTANCE
    
    return result

def follow_path(current_x, current_y, current_yaw):
    """Suivre le chemin planifié"""
    global current_path, path_index
    
    if not current_path or path_index >= len(current_path):
        return None
    
    # Cible courante sur le chemin
    target_x, target_y = current_path[path_index]
    
    # Distance à la cible courante
    dx = target_x - current_x
    dy = target_y - current_y
    dist_to_target = math.sqrt(dx*dx + dy*dy)
    
    # Si on a atteint la cible courante, passer à la suivante
    if dist_to_target < GOAL_THRESHOLD:
        path_index += 1
        if path_index >= len(current_path):
            return None  # Fin du chemin
        target_x, target_y = current_path[path_index]
    
    # Calculer les vitesses
    dx = target_x - current_x
    dy = target_y - current_y
    distance = math.sqrt(dx*dx + dy*dy)
    
    desired_angle = math.atan2(dy, dx)
    angle_error = desired_angle - current_yaw
    
    while angle_error > math.pi:
        angle_error -= 2 * math.pi
    while angle_error < -math.pi:
        angle_error += 2 * math.pi
    
    v_lin = min(MAX_LINEAR_SPEED, distance * 0.5)
    v_ang = angle_error * 2.0
    
    # Limiter les vitesses
    v_ang = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, v_ang))
    
    # Évitement d'obstacles
    obs = analyze_obstacles_detailed()
    if obs['obstacle_detected']:
        if not obs['front_clear']:
            v_lin = 0.3
            if obs['left_clear']:
                v_ang = 1.5
            elif obs['right_clear']:
                v_ang = -1.5
            else:
                # Bloqué, tourner sur place
                v_lin = 0
                v_ang = 2.0 if random.random() > 0.5 else -2.0
    
    # Appliquer les vitesses
    omega_left, omega_right = inverse_kinematics(v_lin, v_ang)
    apply_velocities(omega_left, omega_right)
    
    return target_x, target_y

def navigate_to_target(target_x, target_y, x, y, yaw, step_count):
    """Naviguer vers la cible avec planification de chemin"""
    global current_path, path_index, last_replan_time, goal_position, exploration_mode
    
    # Distance à la cible finale
    dx = target_x - x
    dy = target_y - y
    distance_to_goal = math.sqrt(dx*dx + dy*dy)
    
    # Atteint?
    if distance_to_goal < GOAL_THRESHOLD:
        apply_velocities(0, 0)
        current_path = []
        exploration_mode = False
        log_message(f"Cible atteinte à ({x:.2f}, {y:.2f})")
        return True
    
    # Si on a changé de cible, replanifier
    if goal_position != (target_x, target_y):
        goal_position = (target_x, target_y)
        current_path = []
        path_index = 0
        exploration_mode = False
    
    # Replanifier périodiquement ou si le chemin est vide
    if not current_path or (step_count - last_replan_time) > PATH_REPLAN_INTERVAL:
        last_replan_time = step_count
        
        # Planifier un chemin
        new_path = path_planner.plan_path((x, y), (target_x, target_y))
        
        if new_path and len(new_path) > 1:
            current_path = new_path
            path_index = 0
            exploration_mode = False
            log_message(f"Chemin planifié: {len(current_path)} points")
        else:
            # Pas de chemin trouvé, mode exploration
            if not exploration_mode:
                log_message("⚠️ Pas de chemin direct, activation mode exploration")
                exploration_mode = True
    
    # Suivre le chemin si disponible
    if current_path:
        result = follow_path(x, y, yaw)
        if result is None:
            # Fin du chemin, replanifier
            current_path = []
        return False
    else:
        # Mode exploration
        frontiers = find_exploration_targets()
        if frontiers:
            # Aller vers la frontière la plus proche
            frontiers.sort(key=lambda p: math.sqrt((p[0]-x)**2 + (p[1]-y)**2))
            explore_x, explore_y = frontiers[0]
            
            dx = explore_x - x
            dy = explore_y - y
            dist = math.sqrt(dx*dx + dy*dy)
            
            desired_angle = math.atan2(dy, dx)
            angle_error = desired_angle - yaw
            
            while angle_error > math.pi:
                angle_error -= 2 * math.pi
            while angle_error < -math.pi:
                angle_error += 2 * math.pi
            
            v_lin = min(MAX_LINEAR_SPEED * 0.7, dist * 0.3)
            v_ang = angle_error * 2.0
            v_ang = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, v_ang))
            
            # Évitement d'obstacles
            obs = analyze_obstacles_detailed()
            if obs['obstacle_detected'] and not obs['front_clear']:
                v_lin = 0.2
                if obs['left_clear']:
                    v_ang = 1.5
                elif obs['right_clear']:
                    v_ang = -1.5
            
            omega_left, omega_right = inverse_kinematics(v_lin, v_ang)
            apply_velocities(omega_left, omega_right)
        else:
            # Plus de frontières, recherche en spirale
            spiral_angle = (step_count * 0.01) % (2*math.pi)
            spiral_radius = 1.0 + (step_count * 0.01)
            explore_x = x + spiral_radius * math.cos(spiral_angle)
            explore_y = y + spiral_radius * math.sin(spiral_angle)
            
            dx = explore_x - x
            dy = explore_y - y
            desired_angle = math.atan2(dy, dx)
            angle_error = desired_angle - yaw
            
            while angle_error > math.pi:
                angle_error -= 2 * math.pi
            while angle_error < -math.pi:
                angle_error += 2 * math.pi
            
            v_lin = 0.5
            v_ang = angle_error * 2.0
            v_ang = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, v_ang))
            
            omega_left, omega_right = inverse_kinematics(v_lin, v_ang)
            apply_velocities(omega_left, omega_right)
    
    return False

# ═══════════════════════════════════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════
loop_start = time.time()
target = None
last_command = ""
step_count = 0
last_map_save = 0

print("🚀 SYSTÈME DE NAVIGATION OPÉRATIONNEL")
print(f"📝 Fichier commandes: {command_file}")
print("💡 Utilisation: echo '3.0,2.0' > command.txt")
print("🗺️  SLAM activé - Construction de la carte en temps réel")
print("🧭 Planification A* active")
print("═" * 60)

while robot.step(timestep) != -1:
    step_count += 1
    
    # Lire position et orientation
    pos = gps.getValues()
    x, y = pos[0], pos[1]
    yaw = imu.getRollPitchYaw()[2]
    
    # SLAM: Mettre à jour la carte avec LiDAR
    if step_count % 5 == 0:
        update_map_from_lidar(x, y, yaw)
    
    # Lire nouvelle commande
    if os.path.exists(command_file):
        try:
            with open(command_file, 'r') as f:
                command = f.read().strip()
            
            if command and command != last_command:
                last_command = command
                try:
                    parts = command.split(',')
                    if len(parts) >= 2:
                        target = (float(parts[0].strip()), float(parts[1].strip()))
                        print(f"\n🎯 NOUVELLE CIBLE: ({target[0]:.2f}, {target[1]:.2f})")
                        print(f"📍 Position actuelle: ({x:.2f}, {y:.2f})")
                        log_message(f"Nouvelle cible: ({target[0]:.2f}, {target[1]:.2f})")
                except ValueError:
                    print(f"❌ Format invalide: {command}")
        except:
            pass
    
    # Naviguer vers la cible
    if target:
        reached = navigate_to_target(target[0], target[1], x, y, yaw, step_count)
        
        if reached:
            print(f"✅ CIBLE ATTEINTE!")
            log_message(f"Cible atteinte à ({x:.2f}, {y:.2f})")
            target = None
            apply_velocities(0, 0)
        else:
            # Affichage périodique
            if step_count % 100 == 0:
                dx = target[0] - x
                dy = target[1] - y
                dist = math.sqrt(dx*dx + dy*dy)
                
                obs = analyze_obstacles_detailed()
                print(f"📍 Position: ({x:.2f}, {y:.2f}) | Distance: {dist:.2f}m")
                print(f"   Obstacles: Devant={obs['front']:.2f}m, Gauche={obs['left']:.2f}m, Droite={obs['right']:.2f}m")
    else:
        apply_velocities(0, 0)
    
    # Sauvegarder la carte périodiquement
    if step_count % 200 == 0:
        save_map()
        
        # Statistiques
        total_cells = occupancy_grid.size ** 2
        visited_cells = 0
        for x in range(occupancy_grid.size):
            for y in range(occupancy_grid.size):
                if occupancy_grid.grid[x][y].visited:
                    visited_cells += 1
        
        coverage = (visited_cells / total_cells) * 100
        print(f"📊 Couverture carte: {coverage:.1f}%")

print("\n🛑 Arrêt du système...")
save_map()
log_message("Système arrêté")
print("✅ Carte sauvegardée")
loop_time = time.time() - loop_start
if loop_time > timestep/1000.0:
    print(f"⚠️ Boucle trop lente : {loop_time*1000:.1f} ms (timestep={timestep} ms)")
