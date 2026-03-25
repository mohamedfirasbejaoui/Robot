"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        SYSTÈME DE NAVIGATION PAR DEEP REINFORCEMENT LEARNING (PPO)          ║
║        Algorithme : Proximal Policy Optimization (Actor-Critic)              ║
║        Implémentation : 100% NumPy — aucune dépendance externe               ║
║                                                                              ║
║  Fixes v2 :                                                                  ║
║   • Suppression totale des vitesses négatives (plus de recul intempestif)   ║
║   • Filtre passe-bas sur vitesses finales (alpha stable)                     ║
║   • Basculement RL↔A* déterministe (plus de random.random())                ║
║   • Suivi de chemin avec lookahead dynamique                                 ║
║   • Récupération de blocage orientée par les capteurs                        ║
║   • Décelération progressive à l'approche des waypoints                     ║
║   • Export JSON de l'état pour visualisation live                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

#!/usr/bin/env python3

from controller import Robot
import math
import os
import time
import json
import pickle
import heapq
import numpy as np
from grid_map import OccupancyGrid, GridCell


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — RÉSEAU DE NEURONES (NumPy)
# ═════════════════════════════════════════════════════════════════════════════

class AdamOptimizer:
    def __init__(self, shape_W, shape_b, lr=3e-4, beta1=0.9, beta2=0.999, eps=1e-8):
        self.lr = lr; self.beta1 = beta1; self.beta2 = beta2; self.eps = eps
        self.t  = 0
        self.mW = np.zeros(shape_W); self.vW = np.zeros(shape_W)
        self.mb = np.zeros(shape_b); self.vb = np.zeros(shape_b)

    def step(self, W, b, dW, db):
        self.t += 1
        bc1 = 1 - self.beta1 ** self.t
        bc2 = 1 - self.beta2 ** self.t
        self.mW = self.beta1 * self.mW + (1 - self.beta1) * dW
        self.vW = self.beta2 * self.vW + (1 - self.beta2) * dW ** 2
        W -= self.lr * (self.mW / bc1) / (np.sqrt(self.vW / bc2) + self.eps)
        self.mb = self.beta1 * self.mb + (1 - self.beta1) * db
        self.vb = self.beta2 * self.vb + (1 - self.beta2) * db ** 2
        b -= self.lr * (self.mb / bc1) / (np.sqrt(self.vb / bc2) + self.eps)
        return W, b


class DenseLayer:
    def __init__(self, in_dim, out_dim, activation='relu', lr=3e-4):
        scale = np.sqrt(2.0 / in_dim) if activation == 'relu' else np.sqrt(1.0 / in_dim)
        self.W = np.random.randn(in_dim, out_dim).astype(np.float32) * scale
        self.b = np.zeros(out_dim, dtype=np.float32)
        self.activation = activation
        self.opt = AdamOptimizer(self.W.shape, self.b.shape, lr=lr)
        self._x = None; self._z = None

    def forward(self, x):
        x = np.atleast_2d(np.asarray(x, dtype=np.float32))
        self._x = x
        self._z = x @ self.W + self.b
        if self.activation == 'relu':  return np.maximum(0.0, self._z)
        if self.activation == 'tanh':  return np.tanh(self._z)
        return self._z

    def backward(self, grad):
        grad = np.atleast_2d(grad)
        if self.activation == 'relu':  dz = grad * (self._z > 0).astype(np.float32)
        elif self.activation == 'tanh': dz = grad * (1.0 - np.tanh(self._z) ** 2)
        else: dz = grad
        dW = self._x.T @ dz / len(self._x)
        db = dz.mean(axis=0)
        dx = dz @ self.W.T
        self.W, self.b = self.opt.step(self.W, self.b, dW, db)
        return dx

    def get_weights(self): return {'W': self.W.copy(), 'b': self.b.copy()}
    def set_weights(self, d):
        self.W = d['W'].copy().astype(np.float32)
        self.b = d['b'].copy().astype(np.float32)


class ActorCriticNetwork:
    """
    Réseau Actor-Critic partagé pour PPO.
    Architecture : Input → Shared(256,256) → Actor(64,action_dim) / Critic(64,1)
    """
    def __init__(self, state_dim, action_dim, hidden=256, actor_hidden=64, lr=3e-4):
        self.state_dim  = state_dim
        self.action_dim = action_dim
        self.sh1   = DenseLayer(state_dim,   hidden,       'relu', lr)
        self.sh2   = DenseLayer(hidden,      hidden,       'relu', lr)
        self.a1    = DenseLayer(hidden,      actor_hidden, 'relu', lr)
        self.a_out = DenseLayer(actor_hidden, action_dim,  'tanh', lr)
        self.c1    = DenseLayer(hidden,      actor_hidden, 'relu', lr)
        self.c_out = DenseLayer(actor_hidden, 1,           'linear', lr)
        self.log_std = np.full(action_dim, -0.5, dtype=np.float32)
        self.log_std_opt = AdamOptimizer((action_dim,), (action_dim,), lr=lr)
        self.log_std_opt.mb = np.zeros(action_dim, dtype=np.float32)
        self.log_std_opt.vb = np.zeros(action_dim, dtype=np.float32)

    def _shared_forward(self, x):
        return self.sh2.forward(self.sh1.forward(x))

    def forward_both(self, x):
        h  = self._shared_forward(x)
        ha = self.a1.forward(h);    mean = self.a_out.forward(ha)
        hc = self.c1.forward(h);    val  = self.c_out.forward(hc).squeeze(-1)
        return mean, val

    def sample_action(self, state_1d):
        x    = state_1d.reshape(1, -1).astype(np.float32)
        mean, val = self.forward_both(x)
        std  = np.exp(np.clip(self.log_std, -3.0, 1.0))
        noise = np.random.randn(*mean.shape).astype(np.float32)
        action = mean + std * noise
        log_prob = ActorCriticNetwork._log_prob(action, mean, std)
        return action.squeeze(), float(log_prob.squeeze()), float(np.atleast_1d(val).squeeze())

    def evaluate_batch(self, states, actions):
        mean, val = self.forward_both(states)
        std  = np.exp(np.clip(self.log_std, -3.0, 1.0))
        lp   = ActorCriticNetwork._log_prob(actions, mean, std)
        ent  = float(np.sum(self.log_std + 0.5 * (1.0 + np.log(2 * np.pi))))
        return lp, val, ent

    @staticmethod
    def _log_prob(actions, mean, std):
        return -0.5 * np.sum(
            ((actions - mean) / (std + 1e-8)) ** 2
            + 2.0 * np.log(std + 1e-8) + np.log(2.0 * np.pi), axis=-1)

    def save(self, path):
        data = {
            'sh1': self.sh1.get_weights(), 'sh2': self.sh2.get_weights(),
            'a1':  self.a1.get_weights(),  'a_out': self.a_out.get_weights(),
            'c1':  self.c1.get_weights(),  'c_out': self.c_out.get_weights(),
            'log_std': self.log_std.copy(),
        }
        with open(path, 'wb') as f: pickle.dump(data, f)

    def load(self, path):
        with open(path, 'rb') as f: d = pickle.load(f)
        self.sh1.set_weights(d['sh1']); self.sh2.set_weights(d['sh2'])
        self.a1.set_weights(d['a1']);   self.a_out.set_weights(d['a_out'])
        self.c1.set_weights(d['c1']);   self.c_out.set_weights(d['c_out'])
        self.log_std = d['log_std'].copy()
        print("✅ Poids du modèle chargés.")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — AGENT PPO
# ═════════════════════════════════════════════════════════════════════════════

class RolloutBuffer:
    def __init__(self, capacity=2048):
        self.capacity = capacity
        self.clear()

    def clear(self):
        self.states=[]; self.actions=[]; self.rewards=[]
        self.values=[]; self.log_probs=[]; self.dones=[]

    def add(self, state, action, reward, value, log_prob, done):
        self.states.append(state.astype(np.float32))
        self.actions.append(action.astype(np.float32))
        self.rewards.append(float(reward))
        self.values.append(float(value))
        self.log_probs.append(float(log_prob))
        self.dones.append(float(done))

    def __len__(self): return len(self.states)
    def is_ready(self, min_size=512): return len(self) >= min_size


class PPOAgent:
    def __init__(self, state_dim=42, action_dim=2):
        self.network    = ActorCriticNetwork(state_dim, action_dim)
        self.buffer     = RolloutBuffer(capacity=2048)
        self.gamma      = 0.99;  self.gae_lam  = 0.95
        self.clip_eps   = 0.2;   self.vf_coef  = 0.5
        self.ent_coef   = 0.01;  self.ppo_epochs = 8
        self.batch_size = 128
        self.total_steps = 0; self.update_count = 0
        self.episode_count = 0; self.recent_losses = []

    def act(self, state):
        return self.network.sample_action(state)

    def remember(self, state, action, reward, value, log_prob, done):
        self.buffer.add(state, action, reward, value, log_prob, done)
        self.total_steps += 1

    def update(self, last_value=0.0):
        if not self.buffer.is_ready(self.batch_size): return None
        states  = np.array(self.buffer.states,    dtype=np.float32)
        actions = np.array(self.buffer.actions,   dtype=np.float32)
        old_lp  = np.array(self.buffer.log_probs, dtype=np.float32)
        advantages, returns = self._compute_gae(last_value)
        adv = ((advantages - advantages.mean()) / (advantages.std() + 1e-8)).astype(np.float32)
        ret = returns.astype(np.float32)
        total_loss = 0.0; n_updates = 0
        for _ in range(self.ppo_epochs):
            idx = np.random.permutation(len(states))
            for start in range(0, len(states) - self.batch_size + 1, self.batch_size):
                bi = idx[start:start + self.batch_size]
                total_loss += self._ppo_step(states[bi], actions[bi], adv[bi], ret[bi], old_lp[bi])
                n_updates  += 1
        self.buffer.clear(); self.update_count += 1
        avg_loss = total_loss / max(n_updates, 1)
        self.recent_losses.append(avg_loss)
        if len(self.recent_losses) > 50: self.recent_losses.pop(0)
        return avg_loss

    def _compute_gae(self, last_value):
        rewards = np.array(self.buffer.rewards, dtype=np.float32)
        values  = np.array(self.buffer.values,  dtype=np.float32)
        dones   = np.array(self.buffer.dones,   dtype=np.float32)
        n = len(rewards); adv = np.zeros(n, dtype=np.float32); gae = 0.0
        for t in reversed(range(n)):
            nv = values[t + 1] if t < n - 1 else last_value
            nd = dones[t + 1]  if t < n - 1 else 0.0
            delta = rewards[t] + self.gamma * nv * (1 - nd) - values[t]
            gae   = delta + self.gamma * self.gae_lam * (1 - nd) * gae
            adv[t] = gae
        return adv, adv + values

    def _ppo_step(self, states, actions, advantages, returns, old_log_probs):
        net = self.network; n = len(states)
        h_sh1 = net.sh1.forward(states); h_sh2 = net.sh2.forward(h_sh1)
        h_a1  = net.a1.forward(h_sh2);   means = net.a_out.forward(h_a1)
        h_c1  = net.c1.forward(h_sh2);   vals  = net.c_out.forward(h_c1).squeeze(-1)
        std   = np.exp(np.clip(net.log_std, -3.0, 1.0)).astype(np.float32)
        log_probs = ActorCriticNetwork._log_prob(actions, means, std)
        ratio     = np.exp(np.clip(log_probs - old_log_probs, -10.0, 10.0))
        clipped   = np.clip(ratio, 1 - self.clip_eps, 1 + self.clip_eps) * advantages
        policy_loss = -np.mean(np.minimum(ratio * advantages, clipped))
        value_loss  = np.mean((vals - returns) ** 2)
        entropy     = float(np.sum(net.log_std + 0.5 * (1.0 + np.log(2 * np.pi))))
        total_loss  = policy_loss + self.vf_coef * value_loss - self.ent_coef * entropy
        unclipped   = (ratio * advantages) <= clipped
        d_lp_d_mean = (actions - means) / (std ** 2 + 1e-8)
        grad_mean   = -(advantages * ratio)[:, None] * d_lp_d_mean * unclipped[:, None] / n
        g  = net.a_out.backward(grad_mean); g  = net.a1.backward(g)
        g2 = net.c_out.backward((2.0 * self.vf_coef * (vals - returns) / n).reshape(-1, 1))
        g2 = net.c1.backward(g2)
        gs = net.sh2.backward(g + g2); net.sh1.backward(gs)
        d_ls = -(advantages * ratio)[:, None] * ((actions-means)**2/(std**2+1e-8)-1.0) * unclipped[:, None] / n
        d_ls = np.mean(d_ls, axis=0) - self.ent_coef
        net.log_std, _ = net.log_std_opt.step(net.log_std, np.zeros_like(net.log_std), d_ls, np.zeros_like(net.log_std))
        net.log_std = np.clip(net.log_std, -3.0, 1.0)
        return float(total_loss)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — NORMALISATION EN LIGNE
# ═════════════════════════════════════════════════════════════════════════════

class RunningNormalization:
    def __init__(self, shape, clip=5.0):
        self.mean  = np.zeros(shape, dtype=np.float32)
        self.var   = np.ones(shape,  dtype=np.float32)
        self.count = 0; self.clip = clip

    def update_and_normalize(self, x):
        x = np.asarray(x, dtype=np.float32)
        self.count += 1
        alpha    = 1.0 / self.count
        old_mean = self.mean.copy()
        self.mean = (1.0 - alpha) * self.mean + alpha * x
        self.var  = (1.0 - alpha) * self.var  + alpha * (x - old_mean) * (x - self.mean)
        return np.clip((x - self.mean) / (np.sqrt(self.var) + 1e-8), -self.clip, self.clip)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CURRICULUM LEARNING
# ═════════════════════════════════════════════════════════════════════════════

class CurriculumManager:
    LEVELS = [
        {'name': 'Débutant', 'dist': (1.0, 3.0),  'obs_penalty': 1.0, 'step_penalty': 0.005},
        {'name': 'Élève',    'dist': (2.0, 6.0),  'obs_penalty': 1.5, 'step_penalty': 0.008},
        {'name': 'Avancé',   'dist': (4.0, 12.0), 'obs_penalty': 2.0, 'step_penalty': 0.010},
        {'name': 'Expert',   'dist': (6.0, 25.0), 'obs_penalty': 3.0, 'step_penalty': 0.012},
    ]
    def __init__(self):
        self.level = 0; self.success_streak = 0; self.fail_streak = 0
        self.promote_at = 5; self.demote_at = 8

    @property
    def cfg(self): return self.LEVELS[self.level]

    def on_success(self):
        self.success_streak += 1; self.fail_streak = 0
        if self.success_streak >= self.promote_at and self.level < len(self.LEVELS) - 1:
            self.level += 1; self.success_streak = 0
            print(f"🎓 Niveau {self.level} : {self.cfg['name']}")

    def on_failure(self):
        self.fail_streak += 1; self.success_streak = 0
        if self.fail_streak >= self.demote_at and self.level > 0:
            self.level -= 1; self.fail_streak = 0
            print(f"⬇️  Retour niveau {self.level} : {self.cfg['name']}")

    def __repr__(self):
        return (f"Curriculum(niveau={self.level}, nom={self.cfg['name']}, "
                f"streak={self.success_streak}✓/{self.fail_streak}✗)")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — MAP MASTERY
# ═════════════════════════════════════════════════════════════════════════════

class MapMastery:
    def __init__(self, grid_size=300, resolution=0.1):
        self.size = grid_size; self.resolution = resolution
        self.visit_map   = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.coll_map    = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.success_map = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.decay = 0.9995

    def _to_grid(self, wx, wy):
        cx = self.size // 2
        return (np.clip(int(cx + wx / self.resolution), 0, self.size-1),
                np.clip(int(cx + wy / self.resolution), 0, self.size-1))

    def record_visit(self, wx, wy):     gx,gy=self._to_grid(wx,wy); self.visit_map[gx,gy]  += 1.0
    def record_collision(self, wx, wy): gx,gy=self._to_grid(wx,wy); self.coll_map[gx,gy]   += 1.0
    def record_success(self, wx, wy):   gx,gy=self._to_grid(wx,wy); self.success_map[gx,gy]+= 1.0

    def apply_decay(self):
        self.visit_map *= self.decay; self.coll_map *= self.decay; self.success_map *= self.decay

    def mastery_score(self):
        visited  = np.sum(self.visit_map > 0.5); total = self.size ** 2
        success  = np.sum(self.success_map > 0.5)
        return 0.6 * (visited / total) + 0.4 * (success / max(visited, 1))

    def get_stats(self):
        return {'mastery': self.mastery_score(),
                'visited': int(np.sum(self.visit_map > 0.5)),
                'collisions': int(self.coll_map.sum()),
                'successes': int(self.success_map.sum())}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — REWARD SHAPING
# ═════════════════════════════════════════════════════════════════════════════

class RewardCalculator:
    GOAL_REWARD    =  50.0
    COLLISION_BASE = -10.0
    DANGER_DIST    =   0.5
    SMOOTH_BONUS   =   0.05

    def __init__(self, curriculum: CurriculumManager):
        self.curriculum    = curriculum
        self.prev_distance = None
        self.prev_action   = np.zeros(2, dtype=np.float32)

    def reset(self, dist):
        self.prev_distance = dist
        self.prev_action   = np.zeros(2, dtype=np.float32)

    def compute(self, dist_to_goal, obs_info, action,
                reached=False, new_cells=0, step=0):
        r   = 0.0
        cfg = self.curriculum.cfg
        if self.prev_distance is not None:
            r += (self.prev_distance - dist_to_goal) * 5.0
        self.prev_distance = dist_to_goal
        if reached: r += self.GOAL_REWARD
        min_obs = obs_info.get('min_all', 10.0)
        if   min_obs < self.DANGER_DIST: r += self.COLLISION_BASE * cfg['obs_penalty']
        elif min_obs < 1.0:              r -= (1.0 - min_obs) * 0.5 * cfg['obs_penalty']
        r -= cfg['step_penalty']
        r += new_cells * 0.1
        r -= float(np.abs(action - self.prev_action).mean()) * self.SMOOTH_BONUS
        self.prev_action = action.copy()
        return float(np.clip(r, -20.0, 60.0))


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — EXTRACTEUR D'ÉTAT
# ═════════════════════════════════════════════════════════════════════════════

class StateExtractor:
    N_SECTORS       = 36
    MAX_GOAL_DIST   = 30.0

    def __init__(self, lidar_max_range=10.0):
        self.MAX_LIDAR_RANGE = lidar_max_range
        self.state_dim       = self.N_SECTORS + 6

    def extract(self, lidar_ranges, robot_x, robot_y, robot_yaw,
                goal_x, goal_y, v_lin, v_ang, occupancy_grid):
        state = np.zeros(self.state_dim, dtype=np.float32)
        n = len(lidar_ranges)
        if n > 0:
            step = max(1, n // self.N_SECTORS)
            for s in range(self.N_SECTORS):
                sector = lidar_ranges[s*step : min((s+1)*step, n)]
                clean  = [r for r in sector if not (math.isinf(r) or math.isnan(r))]
                raw    = min(min(clean) if clean else self.MAX_LIDAR_RANGE, self.MAX_LIDAR_RANGE)
                state[s] = math.log1p(raw) / math.log1p(self.MAX_LIDAR_RANGE)
        dx   = goal_x - robot_x; dy = goal_y - robot_y
        dist = math.sqrt(dx*dx + dy*dy)
        angle_to_goal = math.atan2(dy, dx) - robot_yaw
        while angle_to_goal >  math.pi: angle_to_goal -= 2*math.pi
        while angle_to_goal < -math.pi: angle_to_goal += 2*math.pi
        state[36] = min(dist / self.MAX_GOAL_DIST, 1.0)
        state[37] = math.sin(angle_to_goal)
        state[38] = math.cos(angle_to_goal)
        state[39] = np.clip(v_lin / 1.5,  -1.0, 1.0)
        state[40] = np.clip(v_ang / 2.0,  -1.0, 1.0)
        gx, gy = occupancy_grid.world_to_grid(robot_x, robot_y)
        radius = 10
        x0, x1 = max(0, gx-radius), min(occupancy_grid.size, gx+radius)
        y0, y1 = max(0, gy-radius), min(occupancy_grid.size, gy+radius)
        free_count = sum(
            1 for px in range(x0, x1) for py in range(y0, y1)
            if not occupancy_grid.is_occupied(px, py)
        )
        total_c = max((x1-x0)*(y1-y0), 1)
        state[41] = free_count / total_c
        return state


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — PLANIFICATEUR A*
# ═════════════════════════════════════════════════════════════════════════════

class AStarPlanner:
    def __init__(self, occupancy_grid, inflation=2):
        self.grid       = occupancy_grid
        self.resolution = occupancy_grid.resolution
        self.inflation  = inflation

    def plan_path(self, start_world, goal_world):
        sg = self.grid.world_to_grid(*start_world)
        gg = self.grid.world_to_grid(*goal_world)
        if not self.grid.is_valid(*gg): return None
        if self._is_inflated(*gg):
            gg = self._find_free_neighbor(gg) or gg
        open_set = []; heapq.heappush(open_set, (0.0, sg))
        came_from = {}; g_score = {sg: 0.0}
        while open_set:
            _, cur = heapq.heappop(open_set)
            if self._h(cur, gg) < 2:
                return self._reconstruct(came_from, cur, sg)
            for dx, dy in [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                nb = (cur[0]+dx, cur[1]+dy)
                if not self.grid.is_valid(*nb) or self._is_inflated(*nb): continue
                tg = g_score.get(cur, 0.0) + math.sqrt(dx*dx + dy*dy)
                if tg < g_score.get(nb, float('inf')):
                    came_from[nb] = cur; g_score[nb] = tg
                    heapq.heappush(open_set, (tg + self._h(nb, gg), nb))
        return None

    def _is_inflated(self, gx, gy):
        for dx in range(-self.inflation, self.inflation+1):
            for dy in range(-self.inflation, self.inflation+1):
                nx, ny = gx+dx, gy+dy
                if self.grid.is_valid(nx, ny) and self.grid.is_occupied(nx, ny): return True
        return False

    def _find_free_neighbor(self, gc, radius=8):
        for r in range(1, radius+1):
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    nx, ny = gc[0]+dx, gc[1]+dy
                    if self.grid.is_valid(nx, ny) and not self._is_inflated(nx, ny): return (nx, ny)
        return None

    def _h(self, a, b): return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    def _reconstruct(self, came_from, cur, start):
        path = [cur]
        while cur in came_from: cur = came_from[cur]; path.append(cur)
        path.reverse()
        # Décimer les waypoints : garder 1 sur 3 + dernier
        decimated = path[::3]
        if path[-1] not in decimated: decimated.append(path[-1])
        return [self.grid.grid_to_world(*p) for p in decimated]


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 9 — NAVIGATEUR HYBRIDE STABLE (RL + A*)
# ═════════════════════════════════════════════════════════════════════════════

class HybridNavigator:
    """
    Navigateur hybride corrigé – récupération intelligente.
    """

    ANGLE_DEADZONE = 0.04

    def __init__(self, ppo_agent: PPOAgent, astar: AStarPlanner,
                 max_lin=0.9, max_ang=1.2,
                 wheel_radius=0.1, wheel_base=0.5):
        self.ppo     = ppo_agent
        self.astar   = astar
        self.max_lin = max_lin
        self.max_ang = max_ang
        self.wr      = wheel_radius
        self.wb      = wheel_base
        self.motor_max_vel = 6.0

        self.current_path   = []
        self.path_index     = 0
        self.last_replan    = 0
        self.goal_pos       = None

        self._stuck_counter = 0
        self._last_pos      = None
        self._recovery_mode = False
        self._recovery_steps = 0
        self._recovery_dir   = 1.0
        self._recovery_attempts = 0          # ← nouveau

        self.rl_confidence = 0.0

        # Filtre EMA
        self._vel_alpha = 0.25
        self._ol_filt = 0.0
        self._or_filt = 0.0

        self.replan_delay     = 80
        self.stuck_threshold  = 40            # ← augmenté (35 → 40)
        self.move_threshold   = 0.02          # ← seuil de mouvement relevé

    def set_motor_max_vel(self, motor):
        self.motor_max_vel = motor.getMaxVelocity()

    def ik(self, v_lin, v_ang):
        v_lin = max(0.0, v_lin)
        ol  = (v_lin - v_ang * self.wb / 2.0) / self.wr
        or_ = (v_lin + v_ang * self.wb / 2.0) / self.wr
        max_abs = max(abs(ol), abs(or_), 1e-6)
        if max_abs > self.motor_max_vel:
            scale = self.motor_max_vel / max_abs
            ol  *= scale
            or_ *= scale
        return float(ol), float(or_)

    def update_confidence(self):
        n = self.ppo.update_count
        self.rl_confidence = 1.0 / (1.0 + math.exp(-(n - 20) / 10.0))

    def navigate(self, state, x, y, yaw, goal_x, goal_y,
                 obs_info, step_count, motors):
        self.update_confidence()
        dist = math.hypot(goal_x - x, goal_y - y)

        # Détection de blocage
        if self._last_pos is not None:
            moved = math.hypot(x - self._last_pos[0], y - self._last_pos[1])
            self._stuck_counter = self._stuck_counter + 1 if moved < self.move_threshold else 0
        self._last_pos = (x, y)

        # Cible atteinte
        if dist < 0.35:
            self._apply_filter(0.0, 0.0)
            return self._ol_filt, self._or_filt, np.zeros(2), 0.0, 0.0, True

        # Mode récupération (blocage)
        if self._stuck_counter >= self.stuck_threshold:
            return self._recovery(x, y, yaw, obs_info, step_count)

        # Action RL
        action, log_prob, value = self.ppo.act(state)
        v_lin_rl = ((float(action[0]) + 1.0) / 2.0) * self.max_lin
        v_ang_rl =  float(action[1]) * self.max_ang

        front_blocked = obs_info.get('front', 10.0) < 0.6
        use_rl = (self.rl_confidence >= 0.6 and not front_blocked)

        if use_rl:
            v_lin, v_ang = self._apply_rl_obstacle(v_lin_rl, v_ang_rl, obs_info)
        else:
            v_lin, v_ang = self._astar_control(x, y, yaw, goal_x, goal_y, obs_info,
                                                step_count, v_lin_rl, v_ang_rl)

        ol_raw, or_raw = self.ik(v_lin, v_ang)
        self._apply_filter(ol_raw, or_raw)
        return self._ol_filt, self._or_filt, action, log_prob, value, False

    def _apply_rl_obstacle(self, v_lin, v_ang, obs):
        min_dist = obs.get('min_all', 10.0)
        front    = obs.get('front',  10.0)

        if front < 0.6:
            v_lin = 0.0
            v_ang = self._choose_turn_dir(obs) * self.max_ang
        elif min_dist < 1.0:
            factor = min_dist / 1.0
            v_lin  = v_lin * (0.3 + 0.7 * factor)

        return max(0.0, v_lin), v_ang

    def _astar_control(self, x, y, yaw, goal_x, goal_y, obs, step_count,
                       v_lin_rl, v_ang_rl):
        need_replan = (
            self.goal_pos != (goal_x, goal_y) or
            not self.current_path or
            (step_count - self.last_replan) > self.replan_delay
        )
        if need_replan:
            self.goal_pos    = (goal_x, goal_y)
            self.last_replan = step_count
            new_path = self.astar.plan_path((x, y), (goal_x, goal_y))
            if new_path and len(new_path) > 1:
                self.current_path = new_path
                self.path_index   = 0
            else:
                return self._apply_rl_obstacle(v_lin_rl, v_ang_rl, obs)

        if not self.current_path:
            return self._apply_rl_obstacle(v_lin_rl, v_ang_rl, obs)

        return self._follow_path(x, y, yaw, obs)

    def _follow_path(self, x, y, yaw, obs):
        LOOKAHEAD_MIN = 0.4
        LOOKAHEAD_MAX = 1.2

        if not self.current_path or self.path_index >= len(self.current_path):
            return 0.05, 0.0

        while self.path_index < len(self.current_path) - 1:
            tx, ty = self.current_path[self.path_index]
            if math.hypot(tx - x, ty - y) > 0.25:
                break
            self.path_index += 1

        lookahead_dist = min(LOOKAHEAD_MIN + self.rl_confidence * LOOKAHEAD_MAX, LOOKAHEAD_MAX)
        target_idx = self.path_index
        for i in range(self.path_index, len(self.current_path)):
            d = math.hypot(self.current_path[i][0] - x, self.current_path[i][1] - y)
            if d >= lookahead_dist:
                target_idx = i
                break
        else:
            target_idx = len(self.current_path) - 1

        tx, ty = self.current_path[target_idx]
        dx, dy = tx - x, ty - y
        d = math.hypot(dx, dy)

        desired = math.atan2(dy, dx)
        err = desired - yaw
        err = (err + math.pi) % (2*math.pi) - math.pi

        if abs(err) < self.ANGLE_DEADZONE:
            v_ang = 0.0
        else:
            v_ang = np.clip(err * 1.0, -self.max_ang, self.max_ang)

        angle_factor = max(0.0, 1.0 - abs(err) / math.pi)
        dist_factor  = min(1.0, d / 1.5)
        v_lin = self.max_lin * angle_factor * dist_factor

        min_obs = obs.get('min_all', 10.0)
        front   = obs.get('front',  10.0)
        if front < 0.6:
            v_lin = 0.0
            v_ang = self._choose_turn_dir(obs) * self.max_ang
        elif min_obs < 1.0:
            v_lin *= (min_obs / 1.0)

        return max(0.0, v_lin), v_ang

    # ── NOUVEAU : récupération intelligente ─────────────────────────────
    def _recovery(self, x, y, yaw, obs, step_count):
        """
        Rotation jusqu'à ce que le devant soit dégagé, puis avance.
        Limite le nombre de tentatives pour éviter les boucles.
        """
        front = obs.get('front', 10.0)

        # Si on est déjà en mode récupération
        if not self._recovery_mode:
            # Éviter trop de tentatives infructueuses
            if self._recovery_attempts >= 5:
                print("⚠️  Trop de tentatives de récupération – abandon et attente.")
                self._recovery_attempts = 0
                self._stuck_counter = 0
                # Replanification forcée
                self.last_replan = step_count - self.replan_delay
                # Retourne une vitesse nulle pour attendre
                return 0.0, 0.0, np.zeros(2), 0.0, 0.0, False

            self._recovery_mode = True
            self._recovery_steps = 0
            self._recovery_dir = self._choose_turn_dir(obs)
            # Augmenter le compteur de tentatives
            self._recovery_attempts += 1
            print(f"⚠️  Récupération #{self._recovery_attempts} — rotation vers {'gauche' if self._recovery_dir > 0 else 'droite'}")

        # Vérifier si la voie est dégagée
        if front > 0.8:
            # Sortie de la récupération
            self._recovery_mode = False
            self._stuck_counter = 0
            self._recovery_attempts = 0
            # Forcer replanification
            self.last_replan = step_count - self.replan_delay
            print("✅  Récupération terminée – voie libre")
            # Avancer doucement
            ol, or_ = self.ik(0.3, 0.0)
            self._apply_filter(ol, or_)
            return self._ol_filt, self._or_filt, np.zeros(2), 0.0, 0.0, False

        # Sinon, continuer à tourner (max 30 pas)
        self._recovery_steps += 1
        if self._recovery_steps >= 30:
            # Temps écoulé sans dégagement : abandonner la récupération
            print("⚠️  Récupération interrompue – pas de dégagement après 30 pas")
            self._recovery_mode = False
            self._stuck_counter = 0
            self.last_replan = step_count - self.replan_delay
            # Ne pas avancer
            ol, or_ = self.ik(0.0, 0.0)
            self._apply_filter(ol, or_)
            return self._ol_filt, self._or_filt, np.zeros(2), 0.0, 0.0, False

        v_ang = self._recovery_dir * self.max_ang * 0.8
        ol_raw, or_raw = self.ik(0.0, v_ang)
        self._apply_filter(ol_raw, or_raw)
        dummy_action = np.array([0.0, float(self._recovery_dir)], dtype=np.float32)
        return self._ol_filt, self._or_filt, dummy_action, 0.0, 0.0, False

    @staticmethod
    def _choose_turn_dir(obs):
        left  = obs.get('left',  10.0)
        right = obs.get('right', 10.0)
        return 1.0 if left >= right else -1.0

    def _apply_filter(self, ol, or_):
        alpha = self._vel_alpha
        self._ol_filt = alpha * ol + (1 - alpha) * self._ol_filt
        self._or_filt = alpha * or_ + (1 - alpha) * self._or_filt


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 10 — INITIALISATION WEBOTS
# ═════════════════════════════════════════════════════════════════════════════

robot    = Robot()
timestep = int(robot.getBasicTimeStep())

gps   = robot.getDevice("gps"); gps.enable(timestep)
imu   = robot.getDevice("imu"); imu.enable(timestep)
lidar = robot.getDevice("lidar"); lidar.enable(timestep); lidar.enablePointCloud()

lidar_fov  = lidar.getFov()
lidar_max  = lidar.getMaxRange()
lidar_hres = lidar.getHorizontalResolution()
lidar_ainc = lidar_fov / lidar_hres if lidar_hres > 0 else 0.01

motors = []
for name in ["front_left_wheel_motor", "front_right_wheel_motor",
             "rear_left_wheel_motor",  "rear_right_wheel_motor"]:
    m = robot.getDevice(name)
    m.setPosition(float("inf")); m.setVelocity(0.0)
    motors.append(m)

def apply_velocities(ol, or_):
    motors[0].setVelocity(ol); motors[2].setVelocity(ol)
    motors[1].setVelocity(or_); motors[3].setVelocity(or_)

def analyze_obstacles():
    ranges = lidar.getRangeImage()
    if not ranges or len(ranges) < 10:
        return {'front':10.,'left':10.,'right':10.,'min_all':10.,
                'obstacle_detected':False,'front_clear':True,
                'left_clear':True,'right_clear':True}
    clean = [r if not (math.isinf(r) or math.isnan(r)) else 10.0 for r in ranges]
    n = len(clean)
    s = max(1, n // 8)
    front = clean[max(0, n//2-s) : min(n, n//2+s)] or [10.]
    left  = clean[:n//3] or [10.]
    right = clean[2*n//3:] or [10.]
    mf, ml, mr = min(front), min(left), min(right)
    ma = min(mf, ml, mr)
    return {
        'front': mf, 'left': ml, 'right': mr, 'min_all': ma,
        'obstacle_detected': ma < 0.8,
        'front_clear': mf > 1.0, 'left_clear': ml > 1.0, 'right_clear': mr > 1.0
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 11 — SLAM
# ═════════════════════════════════════════════════════════════════════════════

MAP_SIZE   = 1000
ctrl_dir   = os.path.dirname(os.path.abspath(__file__))
map_file   = os.path.join(ctrl_dir, "map.pkl")
model_file = os.path.join(ctrl_dir, "rl_model.pkl")
metrics_file = os.path.join(ctrl_dir, "rl_metrics.pkl")
command_file = os.path.join(ctrl_dir, "command.txt")
log_file     = os.path.join(ctrl_dir, "rl_navigation.log")
viz_state_file = os.path.join(ctrl_dir, "viz_state.json")   # ← pour le visualisateur live

if os.path.exists(map_file):
    try:
        with open(map_file, 'rb') as f: occupancy_grid = pickle.load(f)
        if not isinstance(occupancy_grid, OccupancyGrid) or occupancy_grid.size != MAP_SIZE:
            print("⚠️ Carte incompatible ou taille incorrecte — recréation.")
            occupancy_grid = OccupancyGrid(resolution=0.1, size=MAP_SIZE)
        else:
            print(f"🗺️  Carte SLAM chargée ({map_file})")
    except Exception as e:
        # Fichier corrompu (ex: "Ran out of input") → supprimer et recréer
        print(f"⚠️  Carte corrompue ({e}) — suppression et recréation.")
        try:
            os.remove(map_file)
        except OSError:
            pass
        occupancy_grid = OccupancyGrid(resolution=0.1, size=MAP_SIZE)
        print("📍 Nouvelle carte SLAM créée")
else:
    occupancy_grid = OccupancyGrid(resolution=0.1, size=MAP_SIZE)
    print("📍 Nouvelle carte SLAM créée")

def update_slam(rx, ry, ryaw):
    ranges = lidar.getRangeImage()
    if not ranges: return 0
    now   = time.time(); new_c = 0
    for i, r in enumerate(ranges):
        if r >= lidar_max * 0.99 or math.isinf(r) or math.isnan(r): continue
        angle  = ryaw - lidar_fov/2 + i * lidar_ainc
        ox, oy = rx + r * math.cos(angle), ry + r * math.sin(angle)
        gx, gy = occupancy_grid.world_to_grid(ox, oy)
        occupancy_grid.update_cell(gx, gy, True, now)
        steps = min(int(r / occupancy_grid.resolution), 30)
        for s in range(max(1, steps)):
            t  = s / max(steps, 1)
            fx, fy = rx + t*r*math.cos(angle), ry + t*r*math.sin(angle)
            fgx, fgy = occupancy_grid.world_to_grid(fx, fy)
            prev = occupancy_grid.grid[fgx][fgy].visited if occupancy_grid.is_valid(fgx, fgy) else True
            occupancy_grid.update_cell(fgx, fgy, False, now)
            if not prev: new_c += 1
    return new_c

def save_all():
    """Sauvegarde atomique : écrit dans .tmp puis renomme (évite la corruption sur crash)."""
    tmp = map_file + ".tmp"
    try:
        with open(tmp, 'wb') as f:
            pickle.dump(occupancy_grid, f)
        os.replace(tmp, map_file)
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde carte : {e}")
        try: os.remove(tmp)
        except OSError: pass

def log(msg):
    with open(log_file, 'a') as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def write_viz_state(rx, ry, ryaw, tgt, path, obs_data, stats):
    """Écrit un JSON minimal pour le visualisateur live (non bloquant)."""
    try:
        state = {
            'robot': {'x': float(rx), 'y': float(ry), 'yaw': float(ryaw)},
            'target': {'x': float(tgt[0]), 'y': float(tgt[1])} if tgt else None,
            'path': [[float(p[0]), float(p[1])] for p in path[:50]],  # max 50 pts
            'obs': {k: float(v) for k, v in obs_data.items() if isinstance(v, (int, float))},
            'stats': stats,
            'ts': time.time(),
        }
        # Écriture atomique via fichier temporaire
        tmp = viz_state_file + ".tmp"
        with open(tmp, 'w') as f: json.dump(state, f)
        os.replace(tmp, viz_state_file)
    except Exception:
        pass   # La visualisation ne doit jamais planter le contrôleur


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 12 — ASSEMBLAGE FINAL
# ═════════════════════════════════════════════════════════════════════════════

STATE_DIM  = 42; ACTION_DIM = 2

ppo        = PPOAgent(STATE_DIM, ACTION_DIM)
curriculum = CurriculumManager()
mastery    = MapMastery(grid_size=MAP_SIZE, resolution=0.1)
extractor  = StateExtractor(lidar_max_range=lidar_max)
normalizer = RunningNormalization(STATE_DIM)
reward_fn  = RewardCalculator(curriculum)

astar     = AStarPlanner(occupancy_grid, inflation=2)
navigator = HybridNavigator(ppo, astar,
                             max_lin=0.9, max_ang=1.2,
                             wheel_radius=0.1, wheel_base=0.5)
navigator.set_motor_max_vel(motors[0])

if os.path.exists(model_file):
    try:
        ppo.network.load(model_file)
        print("🧠 Modèle RL chargé — reprise de l'apprentissage")
    except Exception as e:
        print(f"⚠️  Impossible de charger le modèle : {e}")

target           = None
last_command     = ""
last_cmd_mtime   = 0.0   # heure de dernière lecture de command.txt (évite re-exécution)
step_count       = 0
episode_steps    = 0
episode_max      = 1200
current_v_lin    = 0.0
current_v_ang    = 0.0
update_interval  = 256

# Vider le fichier de commande au démarrage pour repartir proprement
try:
    with open(command_file, 'w') as _f: pass
except Exception:
    pass

print("\n" + "═"*60)
print("  🚀 NAVIGATION PAR DEEP REINFORCEMENT LEARNING v2")
print("  Algorithme : PPO (Proximal Policy Optimization)")
print(f"  Réseau     : {STATE_DIM} → 256 → 256 → {ACTION_DIM}")
print(f"  Curriculum : {curriculum.cfg['name']}")
print(f"  FIX        : v_lin ≥ 0 | EMA filtre | basculement déterministe")
print("═"*60)
log("Système RL v2 démarré")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 13 — BOUCLE PRINCIPALE
# ═════════════════════════════════════════════════════════════════════════════

while robot.step(timestep) != -1:
    step_count    += 1
    episode_steps += 1

    pos = gps.getValues()
    x, y = float(pos[0]), float(pos[1])
    yaw  = float(imu.getRollPitchYaw()[2])

    new_cells = 0
    if step_count % 5 == 0:
        new_cells = update_slam(x, y, yaw)
        mastery.record_visit(x, y)

    if step_count % 500 == 0:
        mastery.apply_decay()

    # ── Lecture de commande (mtime-based, exécution unique par écriture) ────
    if step_count % 3 == 0:   # vérifier toutes les 3 frames pour ne pas saturer l'IO
        try:
            if os.path.exists(command_file):
                mtime = os.path.getmtime(command_file)
                if mtime > last_cmd_mtime:
                    last_cmd_mtime = mtime
                    with open(command_file, 'r') as f:
                        cmd = f.read().strip()
                    # Vider immédiatement le fichier pour permettre la répétition
                    with open(command_file, 'w') as f:
                        pass
                    if cmd:
                        last_command = cmd
                        print(f"\n📥 Commande reçue : '{cmd}'")
                        if cmd == "explore":
                            target = None
                            print("🔍 Mode exploration activé")

                        elif cmd == "stats":
                            s = mastery.get_stats()
                            print(f"\n📊 STATISTIQUES ──────────────────────────")
                            print(f"   Updates PPO    : {ppo.update_count}")
                            print(f"   Steps totaux   : {ppo.total_steps}")
                            print(f"   Maîtrise carte : {s['mastery']*100:.1f}%")
                            print(f"   Cellules vis.  : {s['visited']}")
                            print(f"   Collisions     : {s['collisions']}")
                            print(f"   Curriculum     : {curriculum}")
                            if ppo.recent_losses:
                                print(f"   Loss récente   : {np.mean(ppo.recent_losses[-5:]):.4f}")
                            print(f"   Confiance RL   : {navigator.rl_confidence*100:.1f}%")
                            print(f"   Position robot : ({x:.2f}, {y:.2f})")
                            print(f"──────────────────────────────────────────")

                        elif cmd == "reset_model":
                            ppo.network = ActorCriticNetwork(STATE_DIM, ACTION_DIM)
                            ppo.update_count = 0; ppo.total_steps = 0
                            navigator.rl_confidence = 0.0
                            print("🔄 Modèle RL réinitialisé")

                        elif cmd == "stop":
                            target = None
                            navigator.current_path = []
                            apply_velocities(0.0, 0.0)
                            print("🛑 Robot arrêté")

                        elif cmd == "pos":
                            print(f"📍 Position actuelle : ({x:.3f}, {y:.3f})  yaw={math.degrees(yaw):.1f}°")

                        else:
                            # Interprétation comme coordonnée "x,y"
                            try:
                                parts = cmd.replace(';', ',').split(',')
                                if len(parts) >= 2:
                                    tx = float(parts[0].strip())
                                    ty = float(parts[1].strip())
                                    target = (tx, ty)
                                    reward_fn.reset(math.hypot(tx - x, ty - y))
                                    episode_steps = 0
                                    navigator.current_path = []
                                    navigator.goal_pos     = None
                                    navigator._stuck_counter   = 0
                                    navigator._recovery_mode   = False
                                    dist_cmd = math.hypot(tx - x, ty - y)
                                    print(f"🎯 Cible : ({tx:.2f}, {ty:.2f})  — distance : {dist_cmd:.2f} m")
                                    log(f"Cible: ({tx:.2f},{ty:.2f})  dist={dist_cmd:.2f}m")
                                else:
                                    print(f"❌ Format invalide (attendu 'x,y'): '{cmd}'")
                            except ValueError as ve:
                                print(f"❌ Commande non reconnue : '{cmd}'  ({ve})")
        except Exception as e:
            print(f"⚠️  Erreur lecture command.txt : {e}")

    # ── Mode exploration (frontier) ─────────────────────────────────────────
    if target is None:
        sz   = occupancy_grid.size; step_g = max(1, sz // 30)
        cands = []
        for gx in range(0, sz, step_g):
            for gy in range(0, sz, step_g):
                if not occupancy_grid.grid[gx][gy].visited:
                    for ndx, ndy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx, ny = gx+ndx, gy+ndy
                        if occupancy_grid.is_valid(nx, ny) and occupancy_grid.grid[nx][ny].visited:
                            wx, wy = occupancy_grid.grid_to_world(gx, gy)
                            cands.append((math.hypot(wx-x, wy-y), (wx, wy))); break
        if cands:
            cands.sort(); target = cands[0][1]
            reward_fn.reset(math.hypot(target[0]-x, target[1]-y))
            navigator.current_path = []; navigator.goal_pos = None

    if target is None:
        apply_velocities(0.0, 0.0)
        continue

    # ── Construction de l'état ──────────────────────────────────────────────
    lidar_ranges = lidar.getRangeImage() or []
    state_raw  = extractor.extract(lidar_ranges, x, y, yaw,
                                   target[0], target[1],
                                   current_v_lin, current_v_ang,
                                   occupancy_grid)
    state_norm = normalizer.update_and_normalize(state_raw)

    obs = analyze_obstacles()

    # ── Navigation ──────────────────────────────────────────────────────────
    result = navigator.navigate(state_norm, x, y, yaw,
                                target[0], target[1],
                                obs, step_count, motors)

    # Dépacker le résultat (la récupération renvoie 7 éléments)
    if len(result) == 7:
        ol, or_, action, log_prob, value, reached, _ = result
    else:
        ol, or_, action, log_prob, value, reached = result

    apply_velocities(ol, or_)

    # Estimation des vitesses courantes (pour le state suivant)
    v_lin_est   = (ol + or_) * 0.5 * navigator.wr
    v_ang_est   = (or_ - ol) * navigator.wr / navigator.wb
    current_v_lin = v_lin_est; current_v_ang = v_ang_est

    # ── Récompense ───────────────────────────────────────────────────────────
    dist_to_goal = math.hypot(target[0]-x, target[1]-y)
    reward = reward_fn.compute(dist_to_goal, obs, action,
                               reached=reached, new_cells=new_cells,
                               step=episode_steps)

    if obs.get('min_all', 10.0) < 0.4:
        mastery.record_collision(x, y)

    # ── Fin d'épisode ────────────────────────────────────────────────────────
    done = reached or (episode_steps >= episode_max)

    if reached:
        mastery.record_success(x, y); curriculum.on_success()
        print(f"✅ CIBLE ATTEINTE en {episode_steps} pas")
        log(f"Succès en {episode_steps} pas")
        target = None; episode_steps = 0
    elif done:
        curriculum.on_failure()
        print(f"⏱️  Timeout ({episode_steps} pas) | Dist restante : {dist_to_goal:.2f}m")
        episode_steps = 0

    # ── Buffer RL ────────────────────────────────────────────────────────────
    ppo.remember(state_norm, action, reward, value, log_prob, float(done))

    # ── Update PPO ───────────────────────────────────────────────────────────
    if step_count % update_interval == 0 and len(ppo.buffer) >= ppo.batch_size:
        _, last_val = ppo.network.forward_both(state_norm.reshape(1,-1).astype(np.float32))
        loss = ppo.update(last_value=float(np.atleast_1d(last_val).squeeze()))
        if loss is not None:
            print(f"🧠 Update #{ppo.update_count:04d} | Loss : {loss:.5f} "
                  f"| RL conf : {navigator.rl_confidence*100:.1f}% "
                  f"| Niveau : {curriculum.cfg['name']}")

    # ── Affichage périodique ─────────────────────────────────────────────────
    if step_count % 200 == 0 and target is not None:
        s = mastery.get_stats()
        print(f"📍 ({x:.2f},{y:.2f}) | Dist: {dist_to_goal:.2f}m "
              f"| F/L/R: {obs['front']:.2f}/{obs['left']:.2f}/{obs['right']:.2f} "
              f"| Maîtrise: {s['mastery']*100:.1f}%")

    # ── Export état de visualisation (toutes les 10 frames) ─────────────────
    if step_count % 10 == 0:
        s = mastery.get_stats()
        write_viz_state(x, y, yaw, target,
                        navigator.current_path[navigator.path_index:],
                        obs, {
                            'updates': ppo.update_count,
                            'steps':   ppo.total_steps,
                            'mastery': float(s['mastery']),
                            'level':   curriculum.cfg['name'],
                            'rl_conf': float(navigator.rl_confidence),
                        })

    # ── Sauvegardes périodiques ──────────────────────────────────────────────
    if step_count % 500 == 0:
        save_all(); ppo.network.save(model_file)
        with open(metrics_file, 'wb') as f:
            pickle.dump({'update_count': ppo.update_count,
                         'total_steps':  ppo.total_steps,
                         'recent_losses': ppo.recent_losses,
                         'curriculum_level': curriculum.level,
                         'mastery_stats': mastery.get_stats()}, f)

# ── Arrêt propre ─────────────────────────────────────────────────────────────
apply_velocities(0.0, 0.0)
save_all(); ppo.network.save(model_file)
print("\n🛑 Arrêt — carte et modèle sauvegardés.")
log("Système arrêté proprement")