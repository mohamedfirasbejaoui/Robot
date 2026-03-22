"""
Visualisateur de Carte - Système de Navigation Industriel

Permet de visualiser la carte générée par le robot et les trajectoires planifiées
"""

import pickle
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import os
import sys
sys.path.append(os.path.dirname(__file__))

from grid_map import OccupancyGrid, GridCell


class MapVisualizer:
    """Visualisateur de carte d'occupation"""
    
    def __init__(self, map_file='factory_map.pkl'):
        self.map_file = map_file
        self.grid = None
        
    def load_map(self):
        """Charger la carte depuis le fichier"""
        if not os.path.exists(self.map_file):
            print(f"❌ Fichier non trouvé: {self.map_file}")
            return False
        
        try:
            with open(self.map_file, 'rb') as f:
                self.grid = pickle.load(f)
            print(f"✅ Carte chargée: {self.map_file}")
            return True
        except Exception as e:
            print(f"❌ Erreur chargement: {e}")
            return False
    
    def create_occupancy_matrix(self):
        """Créer une matrice d'occupation pour visualisation"""
        size = self.grid.size
        matrix = np.zeros((size, size))
        visited_matrix = np.zeros((size, size))
        
        for i in range(size):
            for j in range(size):
                cell = self.grid.grid[i][j]
                matrix[i][j] = cell.occupancy
                visited_matrix[i][j] = 1.0 if cell.visited else 0.0
        
        return matrix, visited_matrix
    
    def visualize(self, show_visited=True, save_file=None):
        """Visualiser la carte"""
        if self.grid is None:
            print("❌ Carte non chargée")
            return
        
        occupancy, visited = self.create_occupancy_matrix()
        
        # Créer figure avec 2 subplots
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # Colormap personnalisée: blanc (libre) -> rouge (occupé)
        colors = ['white', 'yellow', 'orange', 'red']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('occupancy', colors, N=n_bins)
        
        # Carte d'occupation
        ax1 = axes[0]
        im1 = ax1.imshow(occupancy.T, cmap=cmap, origin='lower', 
                        extent=self.get_extent(), vmin=0, vmax=1)
        ax1.set_title('Carte d\'Occupation', fontsize=14, fontweight='bold')
        ax1.set_xlabel('X (mètres)', fontsize=12)
        ax1.set_ylabel('Y (mètres)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Ajouter origine
        ax1.plot(0, 0, 'go', markersize=10, label='Origine')
        ax1.legend()
        
        # Colorbar
        cbar1 = plt.colorbar(im1, ax=ax1)
        cbar1.set_label('Probabilité d\'occupation', fontsize=10)
        
        # Carte des zones visitées
        ax2 = axes[1]
        im2 = ax2.imshow(visited.T, cmap='binary', origin='lower',
                        extent=self.get_extent(), vmin=0, vmax=1)
        ax2.set_title('Zones Explorées', fontsize=14, fontweight='bold')
        ax2.set_xlabel('X (mètres)', fontsize=12)
        ax2.set_ylabel('Y (mètres)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Ajouter origine
        ax2.plot(0, 0, 'go', markersize=10, label='Origine')
        ax2.legend()
        
        # Statistiques
        total_cells = self.grid.size * self.grid.size
        visited_cells = np.sum(visited)
        occupied_cells = np.sum(occupancy > 0.6)
        coverage = (visited_cells / total_cells) * 100
        
        stats_text = f"""
        Statistiques de la carte:
        • Taille: {self.grid.size}x{self.grid.size} cellules
        • Résolution: {self.grid.resolution}m/cellule
        • Zone totale: {(self.grid.size * self.grid.resolution):.1f}m x {(self.grid.size * self.grid.resolution):.1f}m
        • Cellules visitées: {int(visited_cells)}/{total_cells} ({coverage:.1f}%)
        • Obstacles détectés: {int(occupied_cells)} cellules
        """
        
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout(rect=[0, 0.08, 1, 1])
        
        if save_file:
            plt.savefig(save_file, dpi=300, bbox_inches='tight')
            print(f"✅ Carte sauvegardée: {save_file}")
        
        plt.show()
    
    def get_extent(self):
        """Obtenir les limites de la carte en coordonnées monde"""
        half_size = self.grid.size / 2
        limit = half_size * self.grid.resolution
        return [-limit, limit, -limit, limit]
    
    def analyze_map(self):
        """Analyser et afficher des statistiques détaillées"""
        if self.grid is None:
            print("❌ Carte non chargée")
            return
        
        occupancy, visited = self.create_occupancy_matrix()
        
        total_cells = self.grid.size * self.grid.size
        visited_cells = np.sum(visited)
        free_cells = np.sum(occupancy < 0.4)
        occupied_cells = np.sum(occupancy > 0.6)
        unknown_cells = np.sum((occupancy >= 0.4) & (occupancy <= 0.6))
        
        print("\n" + "=" * 70)
        print("📊 ANALYSE DE LA CARTE")
        print("=" * 70)
        print(f"\n🗺️  Informations générales:")
        print(f"   Taille grille: {self.grid.size} x {self.grid.size} cellules")
        print(f"   Résolution: {self.grid.resolution} m/cellule")
        print(f"   Zone couverte: {(self.grid.size * self.grid.resolution):.1f}m x {(self.grid.size * self.grid.resolution):.1f}m")
        
        print(f"\n📈 Exploration:")
        print(f"   Cellules totales: {total_cells}")
        print(f"   Cellules visitées: {int(visited_cells)} ({(visited_cells/total_cells)*100:.2f}%)")
        print(f"   Cellules non visitées: {int(total_cells - visited_cells)} ({((total_cells-visited_cells)/total_cells)*100:.2f}%)")
        
        print(f"\n🎯 Occupation:")
        print(f"   Libre (< 40%): {int(free_cells)} cellules ({(free_cells/total_cells)*100:.2f}%)")
        print(f"   Occupé (> 60%): {int(occupied_cells)} cellules ({(occupied_cells/total_cells)*100:.2f}%)")
        print(f"   Incertain (40-60%): {int(unknown_cells)} cellules ({(unknown_cells/total_cells)*100:.2f}%)")
        
        # Zones les plus récentes
        print(f"\n🕐 Fraîcheur des données:")
        recent_updates = 0
        for row in self.grid.grid:
            for cell in row:
                if cell.visited and cell.last_update > 0:
                    recent_updates += 1
        
        print(f"   Cellules avec timestamp: {recent_updates}")
        
        print("=" * 70 + "\n")
    
    def export_to_image(self, filename='factory_map.png'):
        """Exporter la carte en image PNG"""
        if self.grid is None:
            print("❌ Carte non chargée")
            return
        
        occupancy, _ = self.create_occupancy_matrix()
        
        # Créer image (0 = libre/blanc, 255 = occupé/noir)
        img = ((1.0 - occupancy) * 255).astype(np.uint8)
        
        plt.figure(figsize=(10, 10))
        plt.imshow(img.T, cmap='gray', origin='lower')
        plt.title('Carte d\'Occupation - Vue Export', fontsize=14, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Image exportée: {filename}")

def main():
    """Point d'entrée principal"""
    print("=" * 70)
    print("🗺️  VISUALISATEUR DE CARTE - Robot Industriel")
    print("=" * 70)
    
    # Fichier de carte
    map_file = 'factory_map.pkl'
    if len(sys.argv) > 1:
        map_file = sys.argv[1]
    
    # Créer visualisateur
    viz = MapVisualizer(map_file)
    
    # Charger carte
    if not viz.load_map():
        print("\n⚠️  Aucune carte disponible.")
        print("   Lancez d'abord le robot pour générer une carte.")
        return
    
    # Analyser
    viz.analyze_map()
    
    # Menu
    while True:
        print("\n" + "─" * 70)
        print("Options:")
        print("  1. Visualiser la carte")
        print("  2. Exporter en PNG")
        print("  3. Sauvegarder visualisation")
        print("  4. Réanalyser")
        print("  5. Quitter")
        print("─" * 70)
        
        choice = input("\nChoix (1-5): ").strip()
        
        if choice == '1':
            print("\n📊 Génération de la visualisation...")
            viz.visualize()
        
        elif choice == '2':
            filename = input("Nom du fichier PNG (factory_map.png): ").strip()
            if not filename:
                filename = 'factory_map.png'
            viz.export_to_image(filename)
        
        elif choice == '3':
            filename = input("Nom du fichier (map_visualization.png): ").strip()
            if not filename:
                filename = 'map_visualization.png'
            print("\n📊 Génération de la visualisation...")
            viz.visualize(save_file=filename)
        
        elif choice == '4':
            # Recharger et analyser
            if viz.load_map():
                viz.analyze_map()
        
        elif choice == '5':
            print("\n👋 Au revoir!")
            break
        
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    main()