"""
3D Track Health Simulation Visualizer
======================================
Renders an animated GIF of the train traveling over the multi-segment track.

Visual encoding
---------------
  Track segments  : color blended from belief vector
                    green  = Healthy belief
                    orange = Degraded belief
                    red    = Damaged belief
                    gray   = unobserved (uniform prior)

  Train           : white box; moves faster over green, slower over red
                    whistle spike rendered when Damaged segment detected

  Belief bars     : stacked vertical bars above each segment, updating
                    after each observation

  Speed needle    : horizontal bar above train, length proportional to speed
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401  (registers 3D projection)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
import random, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from track_health_classifier import CLASS_NAMES
from simulation import (
    DataPool, BayesianSegmentTracker, MPCSpeedController,
    TRACK_CONFIG, V_MAX_FPS, V_MIN_FPS, MPC_HORIZON,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Vis parameters ─────────────────────────────────────────────────────────────
N_VIS_PASSES          = 5     # passes to animate (keep GIF manageable)
FRAMES_PER_SEG_VMAX   = 14   # frames to cross one segment at V_MAX
MAX_FRAMES_PER_SEG    = 42   # cap on slow-segment frames
ANIMATION_INTERVAL_MS = 60   # ms between frames (~16 FPS)
RANDOM_SEED           = 42

# ── Colour constants ───────────────────────────────────────────────────────────
C_HEALTHY  = np.array([0.20, 0.70, 0.20])   # green
C_DEGRADED = np.array([1.00, 0.55, 0.05])   # orange
C_DAMAGED  = np.array([0.85, 0.12, 0.12])   # red
C_UNKNOWN  = np.array([0.72, 0.72, 0.72])   # gray (no observation yet)
C_TRAIN    = (0.93, 0.93, 0.93)
C_WHEEL    = (0.25, 0.25, 0.25)
C_RAIL     = (0.55, 0.55, 0.55)
C_SPEED_OK = (0.20, 0.70, 0.20)
C_SPEED_WN = (1.00, 0.55, 0.05)
C_SPEED_DG = (0.85, 0.12, 0.12)


def belief_to_rgb(belief: np.ndarray) -> tuple:
    """Blend state colours weighted by current belief."""
    rgb = belief[0] * C_HEALTHY + belief[1] * C_DEGRADED + belief[2] * C_DAMAGED
    return tuple(np.clip(rgb, 0, 1))


# ══════════════════════════════════════════════════════════════════════════════
# Box / geometry helpers
# ══════════════════════════════════════════════════════════════════════════════

def _box_faces(x, y, z, dx, dy, dz):
    """Return the 6 faces of an axis-aligned box as a list of vertex quads."""
    verts = [
        # bottom
        [(x,    y,    z),    (x+dx, y,    z),    (x+dx, y+dy, z),    (x,    y+dy, z)],
        # top
        [(x,    y,    z+dz), (x+dx, y,    z+dz), (x+dx, y+dy, z+dz), (x,    y+dy, z+dz)],
        # front
        [(x,    y,    z),    (x+dx, y,    z),    (x+dx, y,    z+dz), (x,    y,    z+dz)],
        # back
        [(x,    y+dy, z),    (x+dx, y+dy, z),    (x+dx, y+dy, z+dz), (x,    y+dy, z+dz)],
        # left
        [(x,    y,    z),    (x,    y+dy, z),    (x,    y+dy, z+dz), (x,    y,    z+dz)],
        # right
        [(x+dx, y,    z),    (x+dx, y+dy, z),    (x+dx, y+dy, z+dz), (x+dx, y,    z+dz)],
    ]
    return verts


def draw_box(ax, x, y, z, dx, dy, dz, face_color, edge_color=(0.3,0.3,0.3), alpha=1.0, lw=0.4):
    faces = _box_faces(x, y, z, dx, dy, dz)
    poly  = Poly3DCollection(faces, alpha=alpha, linewidths=lw)
    poly.set_facecolor(face_color)
    poly.set_edgecolor(edge_color)
    ax.add_collection3d(poly)
    return poly


# ══════════════════════════════════════════════════════════════════════════════
# Pre-compute simulation data
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation(pool, clf, scaler, track_config, n_passes, seed):
    """
    Replay the OODA loop and record frame-level data for animation.

    Returns a list of dicts, one per segment-crossing:
        pass_num, seg_idx, speed, alert,
        beliefs_before, beliefs_after  (list of array per segment),
        frames_in_seg
    """
    n_seg    = len(track_config)
    rng      = random.Random(seed)
    trackers = [BayesianSegmentTracker() for _ in range(n_seg)]
    mpc      = MPCSpeedController(V_MAX_FPS, V_MIN_FPS, MPC_HORIZON)
    events   = []   # one event per segment crossing

    for p in range(n_passes):
        for seg_idx, true_state in enumerate(track_config):
            # ── Observe & Orient ──────────────────────────────────────────────
            fv          = pool.sample(true_state, rng)
            feat_scaled = scaler.transform(fv.reshape(1, -1))
            proba       = clf.predict_proba(feat_scaled)[0]

            beliefs_before = [t.belief.copy() for t in trackers]

            # ── Decide ────────────────────────────────────────────────────────
            trackers[seg_idx].update(proba)
            beliefs_after = [t.belief.copy() for t in trackers]
            speed, alert  = mpc.compute_speed(trackers, seg_idx)

            # Frames for this segment crossing (slower = more frames)
            raw_frames   = int(round(FRAMES_PER_SEG_VMAX * V_MAX_FPS / max(speed, 0.1)))
            n_frames_seg = min(raw_frames, MAX_FRAMES_PER_SEG)

            events.append(dict(
                pass_num       = p,
                seg_idx        = seg_idx,
                speed          = speed,
                alert          = alert,
                map_pred       = trackers[seg_idx].map_state(),
                true_state     = true_state,
                beliefs_before = beliefs_before,
                beliefs_after  = beliefs_after,
                n_frames       = n_frames_seg,
            ))

    return events, trackers


# ══════════════════════════════════════════════════════════════════════════════
# Expand events into per-frame data
# ══════════════════════════════════════════════════════════════════════════════

def build_frames(events, track_config):
    """
    Convert event list into a flat list of frame dicts for animation.
    Each frame has the train's exact X position and the current belief state.
    frame_idx is stored so the whistle wave phase can animate continuously.
    """
    frames = []

    seg_enter = lambda i: i - 0.45
    seg_exit  = lambda i: i + 0.45

    for ev in events:
        seg_idx = ev["seg_idx"]
        x_start = seg_enter(seg_idx)
        x_end   = seg_exit(seg_idx)
        n       = ev["n_frames"]

        for k in range(n):
            t       = k / max(n - 1, 1)
            tx      = x_start + t * (x_end - x_start)
            beliefs = ev["beliefs_before"] if t < 0.5 else ev["beliefs_after"]

            frames.append(dict(
                train_x   = tx,
                speed     = ev["speed"],
                pass_num  = ev["pass_num"],
                seg_idx   = seg_idx,
                alert     = ev["alert"],
                map_pred  = ev["map_pred"],
                true_state= ev["true_state"],
                beliefs   = beliefs,
                frame_idx = len(frames),   # absolute frame counter for wave phase
            ))

    return frames


# ══════════════════════════════════════════════════════════════════════════════
# Animator
# ══════════════════════════════════════════════════════════════════════════════

class TrackHealthVisualizer:

    # Layout constants
    SEG_W  = 0.92    # segment box width  (X)
    SEG_D  = 1.0     # segment box depth  (Y)
    SEG_H  = 0.07    # segment box height (Z)
    RAIL_H = 0.04    # raised rail strip height
    TRAIN_W = 0.42
    TRAIN_D = 0.60
    TRAIN_H = 0.30
    TRAIN_Z = SEG_H + RAIL_H
    BAR_X_OFF = 0.05   # offset of belief bars within segment
    BAR_W  = 0.25      # each belief bar width
    BAR_MAX_H = 1.0    # max height for P=1
    BAR_Z = SEG_H + 0.01
    SPEED_BAR_Z = TRAIN_Z + TRAIN_H + 0.10
    SPEED_BAR_MAX_W = 0.80

    def __init__(self, frames, track_config, n_passes):
        self.frames       = frames
        self.track_config = track_config
        self.n_seg        = len(track_config)
        self.n_passes     = n_passes

    # ── Static scene: rails, ties ─────────────────────────────────────────────

    def _draw_static(self, ax):
        """Rails and cross-ties — drawn once."""
        track_len = self.n_seg
        rail_y    = [0.15, 0.75]
        for ry in rail_y:
            ax.plot([-.5, track_len-.5], [ry, ry], [self.SEG_H, self.SEG_H],
                    color=C_RAIL, linewidth=3, zorder=2)
        # Cross-ties every 0.3 units
        for tx in np.arange(-.4, track_len-.4, 0.3):
            ax.plot([tx, tx], [0.05, 0.95], [self.SEG_H]*2,
                    color=(0.50, 0.35, 0.15), linewidth=2.5, zorder=1)

    # ── Draw one complete frame ───────────────────────────────────────────────

    def draw_frame(self, ax, fd):
        ax.cla()

        # ── Axes styling ──────────────────────────────────────────────────────
        ax.set_xlim(-0.55, self.n_seg - 0.45)
        ax.set_ylim(-0.10, 1.10)
        ax.set_zlim(0, 1.8)
        ax.set_box_aspect([self.n_seg * 0.9, 1.0, 1.4])
        ax.view_init(elev=22, azim=-55)
        ax.set_facecolor((0.10, 0.10, 0.12))
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.grid(False)
        ax.set_axis_off()

        beliefs = fd["beliefs"]

        # ── Track segment boxes ───────────────────────────────────────────────
        for i in range(self.n_seg):
            bel   = beliefs[i]
            color = belief_to_rgb(bel)
            sx    = i - self.SEG_W / 2
            draw_box(ax, sx, 0, 0,
                     self.SEG_W, self.SEG_D, self.SEG_H,
                     face_color=color, alpha=0.90, lw=0.5)

            # ── Belief stacked bars ───────────────────────────────────────────
            bar_x  = sx + self.BAR_X_OFF
            bz     = self.BAR_Z
            colors = [C_HEALTHY, C_DEGRADED, C_DAMAGED]
            for s_idx in range(3):
                h = float(bel[s_idx]) * self.BAR_MAX_H
                draw_box(ax,
                         bar_x + s_idx * (self.BAR_W + 0.02),
                         0.12, bz, self.BAR_W, 0.70, h,
                         face_color=tuple(colors[s_idx]), alpha=0.85, lw=0.3)
                bz_label = bz + float(bel[s_idx]) * self.BAR_MAX_H + 0.03
                ax.text(bar_x + s_idx * (self.BAR_W + 0.02) + self.BAR_W/2,
                        0.47, bz_label,
                        f"{bel[s_idx]:.2f}",
                        fontsize=5.5, ha="center", va="bottom", color="white",
                        zorder=10)

            # ── Segment label ─────────────────────────────────────────────────
            ax.text(i, 1.08, -0.02,
                    f"Seg {i}\n{CLASS_NAMES[self.track_config[i]][0]}",
                    fontsize=6.5, ha="center", va="top",
                    color="white", zorder=10)

        # ── Static rails & ties ───────────────────────────────────────────────
        self._draw_static(ax)

        # ── Train body ────────────────────────────────────────────────────────
        tx = fd["train_x"] - self.TRAIN_W / 2
        draw_box(ax, tx, 0.20, self.TRAIN_Z,
                 self.TRAIN_W, self.TRAIN_D, self.TRAIN_H,
                 face_color=C_TRAIN, alpha=0.95, lw=0.6)

        # Cab / front window highlight
        draw_box(ax, tx + self.TRAIN_W*0.55, 0.22, self.TRAIN_Z + self.TRAIN_H*0.35,
                 self.TRAIN_W*0.40, self.TRAIN_D*0.56, self.TRAIN_H*0.55,
                 face_color=(0.60, 0.80, 0.95), alpha=0.70, lw=0.3)

        # Wheels (flat boxes along each rail)
        for wy in [0.14, 0.70]:
                draw_box(ax,
                         tx + 0.04, wy, self.SEG_H,
                         self.TRAIN_W - 0.08, 0.12, self.RAIL_H + 0.01,
                         face_color=C_WHEEL, alpha=1.0, lw=0.2)

        # ── Whistle (Damaged alert) ───────────────────────────────────────────
        if fd["alert"].startswith("DANGER"):
            roof_z   = self.TRAIN_Z + self.TRAIN_H
            wx       = fd["train_x"] - 0.04   # whistle sits near front of roof
            wy_c     = 0.50                    # Y centre of train

            # Physical whistle tube on the roof
            draw_box(ax, wx - 0.04, wy_c - 0.06, roof_z,
                     0.08, 0.12, 0.18,
                     face_color=(0.85, 0.75, 0.10), alpha=1.0, lw=0.3)
            # Flare bell at top of tube
            draw_box(ax, wx - 0.07, wy_c - 0.09, roof_z + 0.16,
                     0.14, 0.18, 0.05,
                     face_color=(1.00, 0.90, 0.20), alpha=1.0, lw=0.3)

            # Expanding sound-wave arcs — 4 rings, phase driven by frame index
            phase = fd.get("frame_idx", 0) % 16   # cycles every 16 frames
            for ring in range(4):
                # each ring starts at a different phase offset so they stagger
                r = ((phase + ring * 4) % 16) / 15.0 * 0.55 + 0.05
                alpha_wave = max(0.0, 1.0 - r / 0.60)
                theta = np.linspace(-np.pi * 0.65, np.pi * 0.65, 40)
                wave_x = wx + r * np.cos(theta)
                wave_z = roof_z + 0.18 + r * np.abs(np.sin(theta))
                wave_y = np.full_like(theta, wy_c)
                ax.plot(wave_x, wave_y, wave_z,
                        color=(1.0, 0.95, 0.25),
                        linewidth=1.8, alpha=alpha_wave, zorder=20)

            # "WHISTLE!" label above the wave rings
            ax.text(wx, wy_c, roof_z + 0.85,
                    "WHISTLE!", fontsize=8.5,
                    color=(1.0, 0.95, 0.25),
                    ha="center", va="bottom",
                    fontweight="bold", zorder=21)

        # ── Speed bar (above train) ───────────────────────────────────────────
        speed_frac = fd["speed"] / V_MAX_FPS
        bar_len    = speed_frac * self.SPEED_BAR_MAX_W
        bar_color  = (C_SPEED_OK if speed_frac > 0.65
                      else C_SPEED_WN if speed_frac > 0.35
                      else C_SPEED_DG)
        bx = fd["train_x"] - self.SPEED_BAR_MAX_W / 2
        # Background bar (dim)
        ax.plot([bx, bx + self.SPEED_BAR_MAX_W],
                [0.50, 0.50],
                [self.SPEED_BAR_Z, self.SPEED_BAR_Z],
                color=(0.30, 0.30, 0.30), linewidth=6, solid_capstyle="butt")
        # Actual speed bar
        ax.plot([bx, bx + bar_len],
                [0.50, 0.50],
                [self.SPEED_BAR_Z, self.SPEED_BAR_Z],
                color=bar_color, linewidth=6, solid_capstyle="butt", zorder=10)
        ax.text(fd["train_x"], 0.50, self.SPEED_BAR_Z + 0.06,
                f"{fd['speed']:.2f} fps",
                fontsize=7.5, ha="center", va="bottom", color="white", zorder=11)

        # ── HUD (top-left overlay via ax.text at fixed 3D coords) ─────────────
        ax.text2D(0.02, 0.96,
                  f"Pass {fd['pass_num']+1}/{self.n_passes}   "
                  f"Seg {fd['seg_idx']}",
                  transform=ax.transAxes,
                  fontsize=9, color="white", va="top",
                  bbox=dict(boxstyle="round,pad=0.3",
                            facecolor=(0.15,0.15,0.15), alpha=0.7))

        alert_color = ("white" if fd["alert"] == "CLEAR"
                       else "#ff9500" if fd["alert"].startswith("WARNING")
                       else "#ff3b3b")
        ax.text2D(0.02, 0.86,
                  fd["alert"],
                  transform=ax.transAxes,
                  fontsize=8, color=alert_color, va="top",
                  bbox=dict(boxstyle="round,pad=0.25",
                            facecolor=(0.10,0.10,0.10), alpha=0.7))

        # ── Legend ────────────────────────────────────────────────────────────
        legend_items = [
            mpatches.Patch(color=C_HEALTHY,  label="Healthy"),
            mpatches.Patch(color=C_DEGRADED, label="Degraded"),
            mpatches.Patch(color=C_DAMAGED,  label="Damaged"),
        ]
        ax.legend(handles=legend_items,
                  loc="upper right",
                  fontsize=7,
                  facecolor=(0.15, 0.15, 0.15),
                  labelcolor="white",
                  edgecolor="gray",
                  framealpha=0.8)

        ax.set_title(
            "Track Health Simulation — Bayesian Belief + MPC Speed Control",
            color="white", fontsize=9, pad=4,
        )

    # ── Run animation ─────────────────────────────────────────────────────────

    def animate(self, out_path: Path) -> None:
        fig = plt.figure(figsize=(11, 6), facecolor=(0.10, 0.10, 0.12))
        ax  = fig.add_subplot(111, projection="3d")

        total = len(self.frames)
        print(f"Rendering {total} frames  ({self.n_passes} passes × "
              f"{self.n_seg} segments) ...")

        def update(frame_idx):
            if frame_idx % 50 == 0:
                print(f"  frame {frame_idx}/{total}", end="\r")
            self.draw_frame(ax, self.frames[frame_idx])
            return []

        ani = FuncAnimation(
            fig, update,
            frames=total,
            interval=ANIMATION_INTERVAL_MS,
            blit=False,
        )

        writer = PillowWriter(fps=int(1000 / ANIMATION_INTERVAL_MS))
        ani.save(str(out_path), writer=writer)
        print(f"\nAnimation saved -> {out_path}")
        plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # ── Load data and train classifier ────────────────────────────────────────
    pool = DataPool()
    X, y = pool.all_features_and_labels()
    scaler = StandardScaler()
    X_s    = scaler.fit_transform(X)
    clf    = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    clf.fit(X_s, y)
    print(f"Classifier ready — training acc: {(clf.predict(X_s)==y).mean():.3f}")

    # ── Pre-compute simulation ────────────────────────────────────────────────
    print(f"\nRunning {N_VIS_PASSES}-pass simulation over track: "
          f"{[CLASS_NAMES[s] for s in TRACK_CONFIG]}")
    events, _ = run_simulation(
        pool, clf, scaler, TRACK_CONFIG, N_VIS_PASSES, RANDOM_SEED,
    )
    frames = build_frames(events, TRACK_CONFIG)
    print(f"Total animation frames: {len(frames)}")

    # ── Animate ────────────────────────────────────────────────────────────────
    viz = TrackHealthVisualizer(frames, TRACK_CONFIG, N_VIS_PASSES)
    viz.animate(OUTPUT_DIR / "track_simulation_3d.gif")


if __name__ == "__main__":
    main()
