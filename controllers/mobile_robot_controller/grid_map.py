"""🗺️ GRID MAP MODULE"""

from dataclasses import dataclass
from typing import Tuple

@dataclass
class GridCell:
    x: int
    y: int
    occupancy: float = 0.5
    visited: bool = False
    last_update: float = 0.0

class OccupancyGrid:
    def __init__(self, resolution: float = 0.1, size: int = 300):
        self.resolution = resolution
        self.size = size
        self.grid = [[GridCell(x, y) for y in range(size)] for x in range(size)]
        self.origin_x = size // 2
        self.origin_y = size // 2
    
    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        grid_x = int(x / self.resolution) + self.origin_x
        grid_y = int(y / self.resolution) + self.origin_y
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        x = (grid_x - self.origin_x) * self.resolution
        y = (grid_y - self.origin_y) * self.resolution
        return x, y
    
    def is_valid(self, grid_x: int, grid_y: int) -> bool:
        return 0 <= grid_x < self.size and 0 <= grid_y < self.size
    
    def is_occupied(self, grid_x: int, grid_y: int, threshold: float = 0.6) -> bool:
        if not self.is_valid(grid_x, grid_y):
            return True
        return self.grid[grid_x][grid_y].occupancy > threshold
    
    def update_cell(self, grid_x: int, grid_y: int, occupied: bool, timestamp: float):
        if not self.is_valid(grid_x, grid_y):
            return
        cell = self.grid[grid_x][grid_y]
        if occupied:
            cell.occupancy = min(0.98, cell.occupancy + 0.3)
        else:
            cell.occupancy = max(0.02, cell.occupancy - 0.2)
        cell.visited = True
        cell.last_update = timestamp
