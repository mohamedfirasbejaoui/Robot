"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          MAP VISUALIZER — Navigation Industrielle                           ║
║          Visualisation live : carte SLAM · position robot · chemin A*      ║
║          Obstacles · statistiques PPO · heatmap de couverture               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Utilisation :
    python map_visualizer.py                  → utilise map.pkl dans le répertoire courant
    python map_visualizer.py /path/to/map.pkl → carte spécifiée
    python map_visualizer.py --live           → mode live (mise à jour automatique)
"""

import pickle
import json
import os
import sys
import time
import argparse
import math
import threading

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch

# Chemin du dossier contenant ce script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Polices ──────────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    'font.family':       'monospace',
    'axes.titlesize':    10,
    'axes.labelsize':    9,
    'xtick.labelsize':   7,
    'ytick.labelsize':   7,
    'axes.titleweight':  'bold',
    'figure.facecolor':  '#0d1117',
    'axes.facecolor':    '#161b22',
    'axes.edgecolor':    '#30363d',
    'axes.labelcolor':   '#8b949e',
    'xtick.color':       '#8b949e',
    'ytick.color':       '#8b949e',
    'text.color':        '#c9d1d9',
    'grid.color':        '#21262d',
    'grid.linewidth':    0.5,
})

# Palettes
CMAP_OCC   = LinearSegmentedColormap.from_list('occ',
    ['#0d1117', '#1f6feb', '#388bfd', '#f78166', '#ff6e6e'], N=256)
CMAP_VISIT = LinearSegmentedColormap.from_list('visit',
    ['#0d1117', '#21262d', '#238636', '#2ea043', '#56d364'], N=256)
CMAP_COLL  = LinearSegmentedColormap.from_list('coll',
    ['#0d1117', '#30363d', '#f0883e', '#f85149', '#ff0000'], N=256)

ROBOT_COLOR  = '#58a6ff'
GOAL_COLOR   = '#3fb950'
PATH_COLOR   = '#f0883e'
ARROW_COLOR  = '#e3b341'

# ═════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ═════════════════════════════════════════════════════════════════════════════

def load_grid(map_path):
    """Charge l'OccupancyGrid depuis le fichier pickle."""
    if not os.path.exists(map_path):
        return None
    try:
        with open(map_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[WARN] Impossible de charger la carte: {e}")
        return None

def load_viz_state(state_path):
    """Charge l'état live (position robot, chemin, etc.) depuis viz_state.json."""
    if not os.path.exists(state_path):
        return None
    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def grid_to_matrices(grid):
    """Convertit l'OccupancyGrid en matrices numpy (occupancy, visited)."""
    size = grid.size
    occ  = np.zeros((size, size), dtype=np.float32)
    vis  = np.zeros((size, size), dtype=np.float32)
    for i in range(size):
        for j in range(size):
            cell = grid.grid[i][j]
            occ[i, j] = cell.occupancy
            vis[i, j] = 1.0 if cell.visited else 0.0
    return occ, vis

def get_extent(grid):
    """Étendue [xmin, xmax, ymin, ymax] en mètres."""
    half = grid.size / 2 * grid.resolution
    return [-half, half, -half, half]

def crop_matrix(mat, margin_cells=50):
    """
    Retourne la sous-matrice autour de la zone visitée +margin,
    ainsi que l'étendue monde correspondante.
    """
    visited_idx = np.argwhere(mat > 0.5)
    if len(visited_idx) == 0:
        return mat, None
    r0 = max(0, visited_idx[:, 0].min() - margin_cells)
    r1 = min(mat.shape[0], visited_idx[:, 0].max() + margin_cells + 1)
    c0 = max(0, visited_idx[:, 1].min() - margin_cells)
    c1 = min(mat.shape[1], visited_idx[:, 1].max() + margin_cells + 1)
    return mat[r0:r1, c0:c1], (r0, r1, c0, c1)

def cells_to_world(grid, r0, r1, c0, c1):
    """Convertit des indices de sous-matrice en extent monde [x0,x1,y0,y1]."""
    x0, y0 = grid.grid_to_world(r0, c0)
    x1, y1 = grid.grid_to_world(r1, c1)
    return [x0, x1, y0, y1]


# ═════════════════════════════════════════════════════════════════════════════
# PANNEAU DE STATISTIQUES
# ═════════════════════════════════════════════════════════════════════════════

def build_stats_text(grid, viz_state):
    """Retourne une liste de lignes pour le panneau stats."""
    size  = grid.size
    total = size * size
    occ, vis = grid_to_matrices(grid)
    visited_n  = int(np.sum(vis > 0.5))
    occupied_n = int(np.sum(occ > 0.6))
    free_n     = int(np.sum(occ < 0.4))
    coverage   = 100 * visited_n / total

    lines = [
        "══ CARTE ══════════════════",
        f"  Taille      : {size}×{size} cellules",
        f"  Résolution  : {grid.resolution} m/cellule",
        f"  Zone        : {size*grid.resolution:.0f}m × {size*grid.resolution:.0f}m",
        f"  Couverture  : {coverage:.2f}%",
        f"  Visitées    : {visited_n:,}",
        f"  Obstacles   : {occupied_n:,}",
        f"  Libres      : {free_n:,}",
        "",
        "══ ROBOT ═══════════════════",
    ]

    if viz_state:
        r = viz_state.get('robot', {})
        t = viz_state.get('target')
        s = viz_state.get('stats', {})
        o = viz_state.get('obs', {})
        lines += [
            f"  Pos X       : {r.get('x', 0):.3f} m",
            f"  Pos Y       : {r.get('y', 0):.3f} m",
            f"  Cap (yaw)   : {math.degrees(r.get('yaw', 0)):.1f}°",
            "",
            "══ CAPTEURS ════════════════",
            f"  Front       : {o.get('front',  0):.2f} m",
            f"  Gauche      : {o.get('left',   0):.2f} m",
            f"  Droite      : {o.get('right',  0):.2f} m",
            f"  Min obs     : {o.get('min_all',0):.2f} m",
        ]
        if t:
            dx = t['x'] - r.get('x', 0); dy = t['y'] - r.get('y', 0)
            dist = math.sqrt(dx*dx + dy*dy)
            lines += [
                "",
                "══ CIBLE ═══════════════════",
                f"  Cible X     : {t['x']:.2f} m",
                f"  Cible Y     : {t['y']:.2f} m",
                f"  Distance    : {dist:.2f} m",
            ]
        if s:
            lines += [
                "",
                "══ PPO ═════════════════════",
                f"  Updates     : {s.get('updates', 0)}",
                f"  Steps       : {s.get('steps', 0):,}",
                f"  Maîtrise    : {s.get('mastery', 0)*100:.1f}%",
                f"  Niveau      : {s.get('level', '?')}",
                f"  Confiance   : {s.get('rl_conf', 0)*100:.1f}%",
            ]
    else:
        lines += ["  (en attente du robot…)"]
    return lines


# ═════════════════════════════════════════════════════════════════════════════
# VISUALISATEUR PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

class LiveMapVisualizer:
    """
    Fenêtre matplotlib avec :
      • Subplot 1 : Carte d'occupation (bleu=libre → rouge=obstacle)
      • Subplot 2 : Carte de couverture (zones explorées)
      • Subplot 3 : Panneau de statistiques texte
      • Overlay commun : position robot, cap, chemin A*, cible
    """

    REFRESH_MS = 1000    # intervalle de rafraîchissement en millisecondes

    def __init__(self, map_path, state_path, live=False, crop=True):
        self.map_path   = map_path
        self.state_path = state_path
        self.live       = live
        self.crop       = crop

        self.grid       = None
        self.viz_state  = None
        self._anim      = None

        # Éléments graphiques (mis à jour en live)
        self._robot_patches   = []
        self._goal_patches    = []
        self._path_lines      = []
        self._obstacle_arrows = []
        self._occ_im          = None
        self._vis_im          = None
        self._stats_texts     = []

    # ── Construction de la figure ───────────────────────────────────────────

    def _build_figure(self):
        self.fig = plt.figure(figsize=(18, 8), facecolor='#0d1117')
        self.fig.canvas.manager.set_window_title("🤖 Navigation RL — Live Map")

        gs = GridSpec(1, 3, figure=self.fig,
                      width_ratios=[5, 5, 2.2],
                      left=0.04, right=0.98,
                      top=0.92, bottom=0.08,
                      wspace=0.12)

        self.ax_occ  = self.fig.add_subplot(gs[0])
        self.ax_vis  = self.fig.add_subplot(gs[1])
        self.ax_stat = self.fig.add_subplot(gs[2])

        for ax in (self.ax_occ, self.ax_vis):
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.4)

        self.ax_stat.axis('off')
        self.ax_stat.set_facecolor('#0d1117')

        # Titres
        self.ax_occ.set_title("🗺️  Carte d'Occupation", color='#58a6ff', pad=8)
        self.ax_vis.set_title("🔍  Zones Explorées",     color='#56d364', pad=8)
        self.ax_stat.set_title("📊  Statistiques",        color='#e3b341', pad=8)

        # Colorbars
        sm1 = plt.cm.ScalarMappable(cmap=CMAP_OCC,   norm=plt.Normalize(0, 1))
        sm2 = plt.cm.ScalarMappable(cmap=CMAP_VISIT, norm=plt.Normalize(0, 1))
        cb1 = self.fig.colorbar(sm1, ax=self.ax_occ,  fraction=0.03, pad=0.02)
        cb2 = self.fig.colorbar(sm2, ax=self.ax_vis,  fraction=0.03, pad=0.02)
        cb1.set_label('Probabilité d\'occupation', color='#8b949e')
        cb2.set_label('Degré d\'exploration',      color='#8b949e')
        cb1.ax.yaxis.set_tick_params(color='#8b949e')
        cb2.ax.yaxis.set_tick_params(color='#8b949e')
        plt.setp(cb1.ax.yaxis.get_ticklabels(), color='#8b949e')
        plt.setp(cb2.ax.yaxis.get_ticklabels(), color='#8b949e')

        # Légende commune (commune aux deux axes)
        legend_elems = [
            mlines.Line2D([0], [0], marker='o',  color='w', markerfacecolor=ROBOT_COLOR, markersize=8, label='Robot'),
            mlines.Line2D([0], [0], marker='*',  color='w', markerfacecolor=GOAL_COLOR,  markersize=10, label='Cible'),
            mlines.Line2D([0], [0], color=PATH_COLOR, linewidth=1.5, label='Chemin A*'),
        ]
        self.ax_occ.legend(handles=legend_elems, loc='upper right',
                           facecolor='#161b22', edgecolor='#30363d',
                           labelcolor='#c9d1d9', fontsize=7)

        # Titre global
        self.fig.suptitle(
            "Navigation par Deep Reinforcement Learning — PPO + A*",
            color='#c9d1d9', fontsize=12, fontweight='bold', y=0.97
        )

        # Bouton sauvegarde
        self.fig.text(0.5, 0.01,
            "[ Fermer la fenêtre pour quitter ]  |  [ S = sauvegarder PNG ]",
            ha='center', va='bottom', color='#8b949e', fontsize=7)

        self.fig.canvas.mpl_connect('key_press_event', self._on_key)

    # ── Rendu initial ───────────────────────────────────────────────────────

    def _render_maps(self):
        """Premier rendu complet des imshow (occupation + couverture)."""
        occ, vis = grid_to_matrices(self.grid)
        ext = get_extent(self.grid)

        if self.crop:
            vis_crop, bounds = crop_matrix(vis, margin_cells=60)
            if bounds is not None:
                r0, r1, c0, c1 = bounds
                occ_crop = occ[r0:r1, c0:c1]
                ext = cells_to_world(self.grid, r0, r1, c0, c1)
            else:
                occ_crop = occ; vis_crop = vis
        else:
            occ_crop = occ; vis_crop = vis

        self._occ_im = self.ax_occ.imshow(
            occ_crop.T, cmap=CMAP_OCC, origin='lower',
            extent=ext, vmin=0, vmax=1, interpolation='nearest', aspect='auto')
        self._vis_im = self.ax_vis.imshow(
            vis_crop.T, cmap=CMAP_VISIT, origin='lower',
            extent=ext, vmin=0, vmax=1, interpolation='nearest', aspect='auto')

        # Origine
        for ax in (self.ax_occ, self.ax_vis):
            ax.plot(0, 0, '+', color='#8b949e', markersize=10, markeredgewidth=1.5)
            ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)')

        self._map_extent = ext

    def _update_maps(self):
        """Met à jour uniquement les données imshow sans recréer les axes."""
        occ, vis = grid_to_matrices(self.grid)
        ext = get_extent(self.grid)

        if self.crop:
            vis_crop, bounds = crop_matrix(vis, margin_cells=60)
            if bounds is not None:
                r0, r1, c0, c1 = bounds
                occ_crop = occ[r0:r1, c0:c1]
                ext = cells_to_world(self.grid, r0, r1, c0, c1)
            else:
                occ_crop = occ; vis_crop = vis
        else:
            occ_crop = occ; vis_crop = vis

        if self._occ_im is not None:
            self._occ_im.set_data(occ_crop.T)
            self._occ_im.set_extent(ext)
            self._vis_im.set_data(vis_crop.T)
            self._vis_im.set_extent(ext)
        else:
            self._render_maps()

        self._map_extent = ext

    # ── Overlay robot / chemin / cible ──────────────────────────────────────

    def _clear_overlays(self):
        for p in self._robot_patches:   p.remove()
        for p in self._goal_patches:    p.remove()
        for l in self._path_lines:      l.remove()
        self._robot_patches.clear()
        self._goal_patches.clear()
        self._path_lines.clear()

    def _draw_overlays(self):
        """Dessine robot, cap, chemin et cible sur les deux axes."""
        if self.viz_state is None: return
        r   = self.viz_state.get('robot', {})
        t   = self.viz_state.get('target')
        pth = self.viz_state.get('path', [])

        rx   = r.get('x', 0); ry = r.get('y', 0)
        ryaw = r.get('yaw', 0)
        obs  = self.viz_state.get('obs', {})

        for ax in (self.ax_occ, self.ax_vis):
            # Robot : cercle + flèche de cap
            circ = Circle((rx, ry), radius=0.18,
                           facecolor=ROBOT_COLOR, edgecolor='white',
                           linewidth=1.0, alpha=0.9, zorder=10)
            ax.add_patch(circ)
            self._robot_patches.append(circ)

            # Flèche de direction
            arrow_len = 0.45
            ax_end = rx + arrow_len * math.cos(ryaw)
            ay_end = ry + arrow_len * math.sin(ryaw)
            arr = ax.annotate("", xy=(ax_end, ay_end), xytext=(rx, ry),
                              arrowprops=dict(arrowstyle='->', color=ARROW_COLOR,
                                              lw=2.0),
                              zorder=11)
            self._robot_patches.append(arr)

            # Cible
            if t:
                star, = ax.plot(t['x'], t['y'], '*',
                                color=GOAL_COLOR, markersize=12,
                                markeredgecolor='white', markeredgewidth=0.5,
                                zorder=12)
                self._goal_patches.append(star)
                # Ligne robot → cible
                line, = ax.plot([rx, t['x']], [ry, t['y']], '--',
                                color=GOAL_COLOR, linewidth=0.6,
                                alpha=0.35, zorder=8)
                self._goal_patches.append(line)

            # Chemin A*
            if len(pth) >= 2:
                xs = [p[0] for p in pth]; ys = [p[1] for p in pth]
                ln, = ax.plot(xs, ys, '-',
                              color=PATH_COLOR, linewidth=1.6,
                              alpha=0.85, zorder=9)
                self._path_lines.append(ln)
                # Waypoints
                wp, = ax.plot(xs[1:], ys[1:], 'o',
                              color=PATH_COLOR, markersize=3,
                              alpha=0.6, zorder=9)
                self._path_lines.append(wp)

            # Indicateur obstacle (arc de cercle si obstacle détecté)
            min_obs = obs.get('min_all', 10.0)
            if min_obs < 1.5:
                obs_circle = Circle((rx, ry), radius=min_obs,
                                    fill=False, edgecolor='#f85149',
                                    linewidth=1.0, linestyle=':', alpha=0.5, zorder=7)
                ax.add_patch(obs_circle)
                self._robot_patches.append(obs_circle)

    # ── Panneau stats texte ─────────────────────────────────────────────────

    def _update_stats_panel(self):
        for t in self._stats_texts: t.remove()
        self._stats_texts.clear()
        self.ax_stat.clear(); self.ax_stat.axis('off')
        self.ax_stat.set_facecolor('#0d1117')
        self.ax_stat.set_title("📊  Statistiques", color='#e3b341', pad=8)

        lines = build_stats_text(self.grid, self.viz_state)
        y = 0.97; lh = 0.041
        for line in lines:
            color = '#c9d1d9'
            if line.startswith('══'): color = '#58a6ff'
            if line.startswith('  RL conf') or line.startswith('  Maîtrise'): color = '#56d364'
            if line.startswith('  Min obs') and self.viz_state:
                mo = self.viz_state.get('obs', {}).get('min_all', 10.0)
                color = '#f85149' if mo < 0.5 else '#f0883e' if mo < 1.0 else '#c9d1d9'
            t = self.ax_stat.text(0.04, y, line,
                                  transform=self.ax_stat.transAxes,
                                  fontsize=7.5, color=color,
                                  va='top', fontfamily='monospace')
            self._stats_texts.append(t)
            y -= lh
            if y < 0.02: break

        # Timestamp
        ts = time.strftime("%H:%M:%S")
        t2 = self.ax_stat.text(0.97, 0.01,
            f"⏱ {ts}" + (" 🔴 LIVE" if self.live else ""),
            transform=self.ax_stat.transAxes,
            fontsize=7, color='#3fb950' if self.live else '#8b949e',
            ha='right', va='bottom')
        self._stats_texts.append(t2)

    # ── Callback animation ──────────────────────────────────────────────────

    def _animate(self, frame):
        changed = False

        # Recharger la carte (peut évoluer)
        new_grid = load_grid(self.map_path)
        if new_grid is not None:
            self.grid = new_grid; changed = True

        # Recharger l'état live
        new_state = load_viz_state(self.state_path)
        if new_state is not None:
            self.viz_state = new_state; changed = True

        if not changed or self.grid is None:
            return

        try:
            self._clear_overlays()
            self._update_maps()
            self._draw_overlays()
            self._update_stats_panel()
        except Exception as e:
            print(f"[WARN] Erreur render: {e}")

    # ── Événements clavier ──────────────────────────────────────────────────

    def _on_key(self, event):
        if event.key == 's':
            fname = f"map_snapshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
            self.fig.savefig(fname, dpi=200, bbox_inches='tight',
                             facecolor=self.fig.get_facecolor())
            print(f"✅ Snapshot sauvegardé : {fname}")
        elif event.key == 'r':
            # Forcer rechargement complet
            self._occ_im = None; self._vis_im = None
            print("🔄 Rechargement forcé")
        elif event.key == 'c':
            self.crop = not self.crop
            print(f"✂️  Crop {'activé' if self.crop else 'désactivé'}")

    # ── Point d'entrée ──────────────────────────────────────────────────────

    def run(self):
        """Lance la visualisation (bloquant jusqu'à fermeture de fenêtre)."""
        self.grid      = load_grid(self.map_path)
        self.viz_state = load_viz_state(self.state_path)

        if self.grid is None:
            print("❌ Aucune carte disponible.")
            print("   Lancez le contrôleur du robot pour générer une carte.")
            return

        self._build_figure()
        self._render_maps()
        self._draw_overlays()
        self._update_stats_panel()

        if self.live:
            print(f"🔴 Mode LIVE — rafraîchissement toutes les {self.REFRESH_MS} ms")
            print("   Appuyez sur [S] pour sauvegarder, [C] pour toggle crop, [R] pour recharger")
            self._anim = FuncAnimation(
                self.fig, self._animate,
                interval=self.REFRESH_MS,
                cache_frame_data=False,
                blit=False
            )
        else:
            print("📸 Mode statique — [S] sauvegarder, [R] recharger, fermer pour quitter")

        plt.show()

    # ── Export PNG simple ───────────────────────────────────────────────────

    def export_png(self, out_path):
        self.grid      = load_grid(self.map_path)
        self.viz_state = load_viz_state(self.state_path)
        if self.grid is None:
            print("❌ Aucune carte à exporter."); return
        self._build_figure()
        self._render_maps()
        self._draw_overlays()
        self._update_stats_panel()
        self.fig.savefig(out_path, dpi=200, bbox_inches='tight',
                         facecolor=self.fig.get_facecolor())
        plt.close(self.fig)
        print(f"✅ Exporté : {out_path}")


# ═════════════════════════════════════════════════════════════════════════════
# ANALYSE DÉTAILLÉE (mode console)
# ═════════════════════════════════════════════════════════════════════════════

def analyze_map(grid):
    occ, vis = grid_to_matrices(grid)
    total        = grid.size ** 2
    visited_n    = int(np.sum(vis > 0.5))
    free_n       = int(np.sum(occ < 0.4))
    occupied_n   = int(np.sum(occ > 0.6))
    uncertain_n  = total - free_n - occupied_n
    coverage     = 100 * visited_n / total

    print("\n" + "═"*65)
    print("📊  ANALYSE DE LA CARTE")
    print("═"*65)
    print(f"\n🗺️  Grille : {grid.size}×{grid.size}  |  {grid.resolution} m/cellule  "
          f"|  {grid.size*grid.resolution:.0f}m×{grid.size*grid.resolution:.0f}m")
    print(f"\n📈 Exploration :")
    print(f"   Cellules totales    : {total:,}")
    print(f"   Visitées            : {visited_n:,}  ({coverage:.3f}%)")
    print(f"   Non visitées        : {total-visited_n:,}")
    print(f"\n🎯 Occupation :")
    print(f"   Libres (occ < 0.4)  : {free_n:,}  ({100*free_n/total:.3f}%)")
    print(f"   Obstacles(occ > 0.6): {occupied_n:,}  ({100*occupied_n/total:.3f}%)")
    print(f"   Incertaines         : {uncertain_n:,}  ({100*uncertain_n/total:.3f}%)")

    # Recherche de la zone active
    vis_crop, bounds = crop_matrix(vis, margin_cells=20)
    if bounds:
        r0, r1, c0, c1 = bounds
        x0, y0 = grid.grid_to_world(r0, c0)
        x1, y1 = grid.grid_to_world(r1, c1)
        print(f"\n📐 Zone active détectée :")
        print(f"   X : [{x0:.1f}, {x1:.1f}] m  →  {x1-x0:.1f} m")
        print(f"   Y : [{y0:.1f}, {y1:.1f}] m  →  {y1-y0:.1f} m")
    print("═"*65 + "\n")


# ═════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Visualisateur de carte pour le robot de navigation RL")
    parser.add_argument('map_file', nargs='?',
                        default=os.path.join(SCRIPT_DIR, 'map.pkl'),
                        help='Chemin vers le fichier map.pkl')
    parser.add_argument('--live',   action='store_true',
                        help='Mode live : rafraîchissement automatique')
    parser.add_argument('--export', metavar='FILE',
                        help='Exporter la visualisation en PNG et quitter')
    parser.add_argument('--no-crop', action='store_true',
                        help='Désactiver le recadrage automatique')
    parser.add_argument('--state', metavar='FILE',
                        default=os.path.join(SCRIPT_DIR, 'viz_state.json'),
                        help='Fichier d\'état live (viz_state.json)')
    args = parser.parse_args()

    print("═"*65)
    print("🗺️   VISUALISATEUR — Navigation RL")
    print("═"*65)
    print(f"   Carte       : {args.map_file}")
    print(f"   État live   : {args.state}")
    print(f"   Mode        : {'LIVE 🔴' if args.live else 'STATIQUE'}")
    print(f"   Crop auto   : {'Non' if args.no_crop else 'Oui'}")
    print()

    viz = LiveMapVisualizer(
        map_path   = args.map_file,
        state_path = args.state,
        live       = args.live,
        crop       = not args.no_crop,
    )

    if args.export:
        viz.export_png(args.export)
        return

    # Analyse console
    grid = load_grid(args.map_file)
    if grid:
        analyze_map(grid)
    else:
        print("⚠️  Carte non disponible, la fenêtre attendra le premier chargement.")

    viz.run()


if __name__ == "__main__":
    main()