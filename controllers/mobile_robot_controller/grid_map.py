"""🗺️  GRID MAP MODULE — Grille d'occupation pour la navigation SLAM"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class GridCell:
    x: int
    y: int
    occupancy: float = 0.5
    visited: bool = False
    last_update: float = 0.0


class OccupancyGrid:
    """
    Grille d'occupation 2D pour le SLAM.

    Chaque cellule stocke une probabilité d'occupation dans [0, 1] :
      0.02 = libre avec certitude
      0.50 = inconnu (état initial)
      0.98 = occupé avec certitude

    Système de coordonnées :
      • L'origine monde (0, 0) est au centre de la grille.
      • Les coordonnées monde sont en mètres.
      • Les indices de grille sont des entiers dans [0, size[.
    """

    def __init__(self, resolution: float = 0.1, size: int = 1000):
        self.resolution = resolution
        self.size       = size
        self.origin_x   = size // 2
        self.origin_y   = size // 2
        # Initialisation de la grille (liste de listes pour compatibilité pickle)
        self.grid = [[GridCell(x, y) for y in range(size)] for x in range(size)]

    # ── Conversions coordonnées ─────────────────────────────────────────────

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convertit des coordonnées monde (m) en indices de grille."""
        gx = int(x / self.resolution) + self.origin_x
        gy = int(y / self.resolution) + self.origin_y
        return gx, gy

    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convertit des indices de grille en coordonnées monde (m)."""
        x = (grid_x - self.origin_x) * self.resolution
        y = (grid_y - self.origin_y) * self.resolution
        return x, y

    # ── Validité et état ────────────────────────────────────────────────────

    def is_valid(self, grid_x: int, grid_y: int) -> bool:
        """Retourne True si les indices sont dans les limites de la grille."""
        return 0 <= grid_x < self.size and 0 <= grid_y < self.size

    def is_occupied(self, grid_x: int, grid_y: int,
                    threshold: float = 0.6) -> bool:
        """Retourne True si la cellule est considérée occupée."""
        if not self.is_valid(grid_x, grid_y):
            return True   # hors grille = obstacle par défaut
        return self.grid[grid_x][grid_y].occupancy > threshold

    # ── Mise à jour probabiliste ────────────────────────────────────────────

    def update_cell(self, grid_x: int, grid_y: int,
                    occupied: bool, timestamp: float) -> None:
        """
        Met à jour la probabilité d'occupation avec un modèle logit simple.
          occupied=True  → +0.30 (clippé à 0.98)
          occupied=False → -0.20 (clippé à 0.02)
        """
        if not self.is_valid(grid_x, grid_y):
            return
        cell = self.grid[grid_x][grid_y]
        if occupied:
            cell.occupancy = min(0.98, cell.occupancy + 0.30)
        else:
            cell.occupancy = max(0.02, cell.occupancy - 0.20)
        cell.visited     = True
        cell.last_update = timestamp