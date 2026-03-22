"""
Tests et Validation - Système de Navigation Industriel

Script pour tester et valider les différents composants du système
"""

import json
import math
import pickle
import time
from typing import List, Tuple

def test_mission_file_format():
    """Tester la validité du fichier de missions"""
    print("\n" + "=" * 70)
    print("🧪 TEST 1: Format du fichier missions")
    print("=" * 70)
    
    try:
        with open('missions.json', 'r') as f:
            missions = json.load(f)
        
        if not isinstance(missions, list):
            print("❌ Le fichier doit contenir une liste de missions")
            return False
        
        print(f"✅ Fichier chargé: {len(missions)} mission(s)")
        
        # Valider chaque mission
        valid_priorities = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW']
        
        for i, m in enumerate(missions):
            print(f"\n  Mission {i+1}:")
            
            # Vérifier champs requis
            required_fields = ['mission_id', 'pickup_point', 'delivery_point']
            for field in required_fields:
                if field not in m:
                    print(f"    ❌ Champ manquant: {field}")
                    return False
                else:
                    print(f"    ✓ {field}: {m[field]}")
            
            # Vérifier format des points
            for point_field in ['pickup_point', 'delivery_point']:
                point = m[point_field]
                if not isinstance(point, list) or len(point) != 2:
                    print(f"    ❌ {point_field} doit être [x, y]")
                    return False
                if not all(isinstance(coord, (int, float)) for coord in point):
                    print(f"    ❌ Coordonnées doivent être des nombres")
                    return False
            
            # Vérifier priorité
            priority = m.get('priority', 'NORMAL')
            if priority not in valid_priorities:
                print(f"    ⚠️  Priorité invalide: {priority}, utilisation de NORMAL")
            else:
                print(f"    ✓ Priorité: {priority}")
            
            # Vérifier poids (optionnel)
            if 'payload_weight' in m:
                weight = m['payload_weight']
                if not isinstance(weight, (int, float)) or weight < 0:
                    print(f"    ⚠️  Poids invalide: {weight}")
                else:
                    print(f"    ✓ Poids: {weight}kg")
        
        print("\n✅ Toutes les missions sont valides!")
        return True
        
    except FileNotFoundError:
        print("❌ Fichier missions.json non trouvé")
        print("   Création d'un fichier exemple...")
        create_example_missions()
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def create_example_missions():
    """Créer un fichier de missions exemple"""
    example = [
        {
            "mission_id": "TEST_001",
            "pickup_point": [2.0, 2.0],
            "delivery_point": [5.0, 5.0],
            "priority": "NORMAL",
            "payload_weight": 10.0,
            "status": "pending"
        },
        {
            "mission_id": "TEST_002",
            "pickup_point": [-3.0, 1.0],
            "delivery_point": [0.0, 4.0],
            "priority": "HIGH",
            "payload_weight": 5.0,
            "status": "pending"
        },
        {
            "mission_id": "TEST_003",
            "pickup_point": [1.0, -2.0],
            "delivery_point": [3.0, -5.0],
            "priority": "LOW",
            "payload_weight": 15.0,
            "status": "pending"
        }
    ]
    
    with open('missions.json', 'w') as f:
        json.dump(example, f, indent=2)
    
    print("✅ Fichier missions.json créé avec 3 missions exemple")

def test_pathfinding_algorithm():
    """Tester l'algorithme de planification"""
    print("\n" + "=" * 70)
    print("🧪 TEST 2: Algorithme de planification A*")
    print("=" * 70)
    
    # Import local pour éviter erreurs si pas dans Webots
    try:
        # Simulation simplifiée
        print("\n✅ Test de l'heuristique:")
        
        # Test distance euclidienne
        p1 = (0, 0)
        p2 = (3, 4)
        expected = 5.0  # Triangle 3-4-5
        actual = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        
        print(f"   Distance ({p1} → {p2}): {actual:.2f}")
        assert abs(actual - expected) < 0.01, "Erreur calcul distance"
        print(f"   ✓ Heuristique correcte")
        
        print("\n✅ Test normalisation d'angle:")
        test_angles = [
            (math.pi * 1.5, math.pi * 1.5),  # Pas de changement
            (math.pi * 2.5, math.pi * 0.5),  # Normalisation
            (-math.pi * 0.5, -math.pi * 0.5), # Négatif OK
        ]
        
        for angle_in, expected_out in test_angles:
            # Normaliser
            angle_normalized = angle_in
            while angle_normalized > math.pi:
                angle_normalized -= 2 * math.pi
            while angle_normalized < -math.pi:
                angle_normalized += 2 * math.pi
            
            print(f"   Angle {angle_in:.2f} → {angle_normalized:.2f} (attendu: {expected_out:.2f})")
            assert abs(angle_normalized - expected_out) < 0.01, "Erreur normalisation"
        
        print("   ✓ Normalisation correcte")
        
        print("\n✅ Test voisinage 8-directions:")
        directions = [
            (0, 1, 1.0),    # Nord
            (1, 0, 1.0),    # Est
            (0, -1, 1.0),   # Sud
            (-1, 0, 1.0),   # Ouest
            (1, 1, 1.414),  # Nord-Est
            (1, -1, 1.414), # Sud-Est
            (-1, -1, 1.414),# Sud-Ouest
            (-1, 1, 1.414)  # Nord-Ouest
        ]
        
        print(f"   Nombre de directions: {len(directions)}")
        assert len(directions) == 8, "Doit avoir 8 directions"
        
        # Vérifier coûts diagonaux
        for dx, dy, cost in directions:
            expected_cost = math.sqrt(dx*dx + dy*dy)
            print(f"   Direction ({dx:2d}, {dy:2d}): coût={cost:.3f} (attendu: {expected_cost:.3f})")
            assert abs(cost - expected_cost) < 0.01, f"Coût incorrect pour ({dx},{dy})"
        
        print("   ✓ Voisinage correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        return False

def test_kinematics():
    """Tester la cinématique inverse"""
    print("\n" + "=" * 70)
    print("🧪 TEST 3: Cinématique inverse")
    print("=" * 70)
    
    WHEEL_RADIUS = 0.1
    WHEEL_BASE = 0.5
    MAX_SPEED = 6.0
    
    def inverse_kinematics(v_lin, v_ang):
        omega_left = (v_lin - v_ang * WHEEL_BASE / 2.0) / WHEEL_RADIUS
        omega_right = (v_lin + v_ang * WHEEL_BASE / 2.0) / WHEEL_RADIUS
        omega_left = max(-MAX_SPEED, min(MAX_SPEED, omega_left))
        omega_right = max(-MAX_SPEED, min(MAX_SPEED, omega_right))
        return omega_left, omega_right
    
    test_cases = [
        # (v_lin, v_ang, description)
        (1.0, 0.0, "Ligne droite"),
        (0.0, 1.0, "Rotation sur place (gauche)"),
        (0.0, -1.0, "Rotation sur place (droite)"),
        (1.0, 0.5, "Virage à gauche"),
        (1.0, -0.5, "Virage à droite"),
    ]
    
    for v_lin, v_ang, desc in test_cases:
        omega_l, omega_r = inverse_kinematics(v_lin, v_ang)
        print(f"\n  {desc}:")
        print(f"    Entrée: v_lin={v_lin:.2f} m/s, v_ang={v_ang:.2f} rad/s")
        print(f"    Sortie: ω_left={omega_l:.2f} rad/s, ω_right={omega_r:.2f} rad/s")
        
        # Vérifications
        assert abs(omega_l) <= MAX_SPEED, "Vitesse gauche dépasse max"
        assert abs(omega_r) <= MAX_SPEED, "Vitesse droite dépasse max"
        
        # Pour ligne droite, vitesses doivent être égales
        if v_ang == 0.0:
            assert abs(omega_l - omega_r) < 0.01, "Ligne droite: vitesses inégales"
            print(f"    ✓ Ligne droite validée")
        
        # Pour rotation sur place, vitesses opposées
        if v_lin == 0.0 and v_ang != 0.0:
            assert abs(omega_l + omega_r) < 0.01, "Rotation: vitesses pas opposées"
            print(f"    ✓ Rotation validée")
    
    print("\n✅ Cinématique inverse correcte!")
    return True

def test_map_file():
    """Tester la présence et validité du fichier carte"""
    print("\n" + "=" * 70)
    print("🧪 TEST 4: Fichier de carte")
    print("=" * 70)
    
    map_file = 'factory_map.pkl'
    
    try:
        with open(map_file, 'rb') as f:
            grid = pickle.load(f)
        
        print(f"✅ Carte chargée: {map_file}")
        print(f"   Taille: {grid.size}x{grid.size}")
        print(f"   Résolution: {grid.resolution}m/cellule")
        
        # Compter cellules visitées
        visited = sum(1 for row in grid.grid for cell in row if cell.visited)
        total = grid.size * grid.size
        coverage = (visited / total) * 100
        
        print(f"   Cellules visitées: {visited}/{total} ({coverage:.1f}%)")
        
        if coverage < 5:
            print("   ⚠️  Couverture faible - Le robot n'a pas beaucoup exploré")
        elif coverage < 30:
            print("   ✓ Couverture correcte")
        else:
            print("   ✓ Bonne couverture!")
        
        return True
        
    except FileNotFoundError:
        print(f"⚠️  Aucune carte trouvée: {map_file}")
        print("   Ceci est normal si le robot n'a jamais été lancé")
        print("   La carte sera créée au premier lancement")
        return True  # Pas une erreur
    except Exception as e:
        print(f"❌ Erreur chargement carte: {e}")
        return False

def calculate_mission_statistics(missions_file='missions.json'):
    """Calculer des statistiques sur les missions"""
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES DES MISSIONS")
    print("=" * 70)
    
    try:
        with open(missions_file, 'r') as f:
            missions = json.load(f)
        
        if not missions:
            print("⚠️  Aucune mission")
            return
        
        # Compter par statut
        statuses = {}
        priorities = {}
        total_weight = 0.0
        total_distance = 0.0
        
        for m in missions:
            status = m.get('status', 'pending')
            statuses[status] = statuses.get(status, 0) + 1
            
            priority = m.get('priority', 'NORMAL')
            priorities[priority] = priorities.get(priority, 0) + 1
            
            total_weight += m.get('payload_weight', 0.0)
            
            # Calculer distance
            p1 = m['pickup_point']
            p2 = m['delivery_point']
            dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            total_distance += dist
        
        print(f"\n📦 Nombre total de missions: {len(missions)}")
        
        print(f"\n📊 Par statut:")
        for status, count in statuses.items():
            print(f"   {status}: {count}")
        
        print(f"\n⚡ Par priorité:")
        for priority, count in priorities.items():
            print(f"   {priority}: {count}")
        
        print(f"\n📏 Distances:")
        print(f"   Distance totale: {total_distance:.1f}m")
        print(f"   Distance moyenne: {total_distance/len(missions):.1f}m")
        
        print(f"\n⚖️  Charges:")
        print(f"   Poids total: {total_weight:.1f}kg")
        print(f"   Poids moyen: {total_weight/len(missions):.1f}kg")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

def run_all_tests():
    """Exécuter tous les tests"""
    print("\n" + "═" * 70)
    print("🧪 SUITE DE TESTS - Système de Navigation Industriel")
    print("═" * 70)
    
    tests = [
        ("Format missions", test_mission_file_format),
        ("Algorithme A*", test_pathfinding_algorithm),
        ("Cinématique", test_kinematics),
        ("Fichier carte", test_map_file),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Erreur dans {name}: {e}")
            results.append((name, False))
    
    # Statistiques missions
    try:
        calculate_mission_statistics()
    except:
        pass
    
    # Résumé
    print("\n" + "═" * 70)
    print("📋 RÉSUMÉ DES TESTS")
    print("═" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n  🎉 Tous les tests sont passés!")
    else:
        print("\n  ⚠️  Certains tests ont échoué")
    
    print("═" * 70 + "\n")

if __name__ == "__main__":
    run_all_tests()