"""
Train Track Health Simulation
================================
Simulates a train making repeated passes over a multi-segment track of
configurable health states. Each pass executes a full OODA loop per segment:

  Observe  – sample real accelerometer data from the dataset for that
             segment's true health state (realistic sensor noise included)
  Orient   – run Kalman filter + position-aligned feature extraction +
             trained Random Forest classifier -> soft class probabilities
  Decide   – Bayesian update of segment health belief;
             MPC computes safe speed for the next segment
  Act      – train moves to next segment at the MPC-commanded speed

Components
----------
  DataPool            : holds preloaded run feature vectors grouped by class
  BayesianSegmentTracker : maintains P(Healthy|obs), P(Degraded|obs),
                           P(Damaged|obs) per segment via sequential
                           Bayesian filtering
  MPCSpeedController  : N-step look-ahead receding-horizon speed planner
  Simulation          : orchestrates the full loop, saves dashboard plots
"""


labeled_data_example = {
'Healthy': [sample1, sample2, sample3]
'Degraded': []
}
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Import shared helpers from the classifier module
import sys
sys.path.insert(0, str(Path(__file__).parent))
from track_health_classifier import (
    TRACK_LABELS, CLASS_NAMES, BASE_DIR,
    KalmanFilter1D, load_and_align, extract_run_features, feature_names,
    N_SEGMENTS,
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Simulation parameters (edit these to change the scenario) ─────────────────
TRACK_CONFIG = [0, 0, 1, 2, 1, 0]   # true health states: 0=Healthy 1=Degraded 2=Damaged
N_PASSES     = 15                    # number of train passes to simulate
V_MAX_FPS    = 3.0                   # normal cruise speed (fps)
V_MIN_FPS    = 0.5                   # minimum allowable speed (fps)
MPC_HORIZON  = 3                     # look-ahead segments for MPC
RANDOM_SEED  = 42

# Speed penalty weights per health state (0=none, higher=slower)
SPEED_PENALTY = {0: 0.0, 1: 0.45, 2: 0.80}

# ── Class colour map ───────────────────────────────────────────────────────────
STATE_COLORS = {0: "#2ca02c", 1: "#ff7f0e", 2: "#d62728"}   # green / orange / red
STATE_ALPHA  = {0: 1.0,       1: 0.8,       2: 0.8}


# ══════════════════════════════════════════════════════════════════════════════
# 1.  DataPool  – one feature vector per real run, indexed by class
# ══════════════════════════════════════════════════════════════════════════════

class DataPool:
    """
    Preloads feature vectors from all dataset runs so the simulation can draw
    a random sample for each segment observation without re-reading CSV files.
    """

    def __init__(self):
        kf = KalmanFilter1D()
        self._pool: dict[int, list[np.ndarray]] = {0: [], 1: [], 2: []}

        print("Loading dataset into DataPool...")
        for track_type, (label, state_name) in TRACK_LABELS.items():
            track_dir = BASE_DIR / track_type
            for cond_dir in sorted(track_dir.iterdir()):
                for run_dir in sorted(cond_dir.iterdir()):
                    data = load_and_align(run_dir)
                    if data is None:
                        continue
                    fv = extract_run_features(data, kf)
                    if fv is None:
                        continue
                    self._pool[label].append(fv)

        for label, name in enumerate(CLASS_NAMES):
            print(f"  {name}: {len(self._pool[label])} runs loaded")

    def sample(self, true_state: int, rng: random.Random) -> np.ndarray:
        """Return a random feature vector from real runs of this health state."""
        return rng.choice(self._pool[true_state])

    def all_features_and_labels(self):
        X, y = [], []
        for label, fvecs in self._pool.items():
            for fv in fvecs:
                X.append(fv)
                y.append(label)
        return np.vstack(X).astype(np.float32), np.array(y, dtype=np.int32)


# ══════════════════════════════════════════════════════════════════════════════
# 2.  BayesianSegmentTracker
# ══════════════════════════════════════════════════════════════════════════════

class BayesianSegmentTracker:
    """
    Maintains a posterior distribution over health states for one track segment.

    Update rule (sequential Bayesian filter):
      posterior[i]  ∝  likelihood[i]  *  prior[i]

    The 'likelihood' is the soft probability vector output by the Random Forest
    classifier, which approximates P(observation | state=i).  Treating each
    classifier call as an independent observation, we multiply likelihoods
    across passes (equivalent to running the HMM forward algorithm with a
    stationary transition matrix).

    A small floor (MIN_BELIEF) prevents any state from being completely ruled
    out, preserving the ability to correct errors once a human provides
    updated information.
    """

    MIN_BELIEF = 0.02   # prevent zero-probability states

    def __init__(self, n_classes: int = 3):
        self.n = n_classes
        self.belief = np.ones(n_classes, dtype=np.float64) / n_classes  # uniform prior

    def update(self, likelihood: np.ndarray) -> None:
        """Multiply current belief by likelihood vector and renormalise."""
        self.belief = self.belief * likelihood
        self.belief = np.clip(self.belief, self.MIN_BELIEF, None)
        self.belief /= self.belief.sum()

    def map_state(self) -> int:
        """Maximum a-posteriori state estimate."""
        return int(np.argmax(self.belief))

    def entropy(self) -> float:
        """Shannon entropy of the current belief — low = confident."""
        p = self.belief
        return float(-np.sum(p * np.log(p + 1e-30)))

    def reset(self) -> None:
        self.belief = np.ones(self.n, dtype=np.float64) / self.n

    def human_correction(self, true_state: int) -> None:
        """
        Human-in-the-loop: operator verifies or corrects the segment state.
        Collapses the belief to a near-certain distribution centred on the
        confirmed state.
        """
        self.belief = np.full(self.n, self.MIN_BELIEF)
        self.belief[true_state] = 1.0 - (self.n - 1) * self.MIN_BELIEF
        self.belief /= self.belief.sum()


# ══════════════════════════════════════════════════════════════════════════════
# 3.  MPC Speed Controller
# ══════════════════════════════════════════════════════════════════════════════

class MPCSpeedController:
    """
    Receding-horizon speed controller.

    At each segment the MPC looks ahead MPC_HORIZON segments, computes a
    risk score for each using the current Bayesian beliefs, then selects the
    commanded speed for the *current* segment that minimises cumulative risk
    while respecting acceleration constraints.

    Risk model:
        risk(belief) = sum_i  belief[i] * SPEED_PENALTY[i]
        speed = V_MAX * (1 - risk)  clamped to [V_MIN, V_MAX]

    This is a linear, single-state MPC; replacing it with a Pyomo-based QP
    is straightforward for the full project.
    """

    def __init__(self, v_max: float, v_min: float, horizon: int):
        self.v_max   = v_max
        self.v_min   = v_min
        self.horizon = horizon

    def _risk(self, belief: np.ndarray) -> float:
        return float(sum(belief[i] * SPEED_PENALTY[i] for i in range(len(belief))))

    def compute_speed(
        self,
        trackers: list[BayesianSegmentTracker],
        current_seg: int,
    ) -> tuple[float, str]:
        """
        Returns (commanded_speed_fps, alert_string).
        Looks ahead `horizon` segments from current_seg.
        """
        n_segs  = len(trackers)
        look_ahead_risk = 0.0
        worst_seg_risk  = 0.0

        for h in range(self.horizon):
            idx  = (current_seg + h) % n_segs
            risk = self._risk(trackers[idx].belief)
            look_ahead_risk += risk * (0.8 ** h)   # discount future segments
            worst_seg_risk   = max(worst_seg_risk, risk)

        # Speed based on worst segment in horizon (conservative safety policy)
        speed = self.v_max * (1.0 - worst_seg_risk)
        speed = max(self.v_min, min(self.v_max, speed))

        # Alert logic
        map_state = trackers[current_seg].map_state()
        if map_state == 2:
            alert = "DANGER  – Damaged track detected. Speed reduced. Whistle!"
        elif map_state == 1:
            alert = "WARNING – Degraded track. Proceed with caution."
        else:
            alert = "CLEAR"

        return round(speed, 3), alert


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Simulation
# ══════════════════════════════════════════════════════════════════════════════

class Simulation:

    def __init__(
        self,
        track_config: list[int],
        n_passes: int,
        seed: int = RANDOM_SEED,
    ):
        self.track_config = track_config
        self.n_segments   = len(track_config)
        self.n_passes     = n_passes
        self.rng          = random.Random(seed)

        # Load data and train classifier
        self.pool = DataPool()
        self._train_classifier()

        # Initialise per-segment Bayesian trackers
        self.trackers = [BayesianSegmentTracker() for _ in range(self.n_segments)]

        # MPC controller
        self.mpc = MPCSpeedController(V_MAX_FPS, V_MIN_FPS, MPC_HORIZON)

        # History for plotting
        # belief_history[pass][segment] = belief array
        self.belief_history: list[list[np.ndarray]] = []
        self.speed_history:  list[list[float]]       = []   # [pass][segment]
        self.pred_history:   list[list[int]]          = []  # MAP predictions

    # ── Model training ─────────────────────────────────────────────────────────

    def _train_classifier(self) -> None:
        print("\nTraining Random Forest classifier on full dataset...")
        X, y = self.pool.all_features_and_labels()
        self.scaler = StandardScaler()
        X_s = self.scaler.fit_transform(X)
        self.clf = RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        self.clf.fit(X_s, y)
        train_acc = (self.clf.predict(X_s) == y).mean()
        print(f"  Training accuracy: {train_acc:.3f}  |  "
              f"{X.shape[0]} runs  x  {X.shape[1]} features")

    # ── OODA loop for one pass ─────────────────────────────────────────────────

    def run_pass(self, pass_num: int) -> None:
        pass_beliefs = []
        pass_speeds  = []
        pass_preds   = []

        print(f"\n{'='*70}")
        print(f"PASS {pass_num+1:02d}/{self.n_passes}  "
              f"({'  '.join(CLASS_NAMES[s] for s in self.track_config)})")
        print(f"{'='*70}")
        print(f"  {'Seg':>3}  {'True':>8}  {'MAP':>8}  "
              f"{'P(H)':>6}  {'P(D)':>6}  {'P(X)':>6}  "
              f"{'Speed':>6}  Alert")
        print(f"  {'-'*3}  {'-'*8}  {'-'*8}  "
              f"{'-'*6}  {'-'*6}  {'-'*6}  "
              f"{'-'*6}  -----")

        for seg_idx, true_state in enumerate(self.track_config):

            # ── OBSERVE ──────────────────────────────────────────────────────
            # Sample a real run from the dataset matching this segment's state
            feat_vec = self.pool.sample(true_state, self.rng)

            # ── ORIENT ───────────────────────────────────────────────────────
            # Run classifier to get soft class probabilities
            feat_scaled = self.scaler.transform(feat_vec.reshape(1, -1))
            proba = self.clf.predict_proba(feat_scaled)[0]   # shape (3,)

            # ── DECIDE ───────────────────────────────────────────────────────
            # Bayesian update
            self.trackers[seg_idx].update(proba)
            belief   = self.trackers[seg_idx].belief.copy()
            map_pred = self.trackers[seg_idx].map_state()

            # MPC computes safe speed for this segment
            speed, alert = self.mpc.compute_speed(self.trackers, seg_idx)

            # ── ACT ──────────────────────────────────────────────────────────
            # (In a real system the train would actually change speed here)

            pass_beliefs.append(belief)
            pass_speeds.append(speed)
            pass_preds.append(map_pred)

            correct = "OK" if map_pred == true_state else "ERR"
            print(f"  {seg_idx:>3}  "
                  f"{CLASS_NAMES[true_state]:>8}  "
                  f"{CLASS_NAMES[map_pred]:>8}  "
                  f"{belief[0]:>6.3f}  {belief[1]:>6.3f}  {belief[2]:>6.3f}  "
                  f"{speed:>6.2f}  {alert}  [{correct}]")

        self.belief_history.append(pass_beliefs)
        self.speed_history.append(pass_speeds)
        self.pred_history.append(pass_preds)

    # ── Human-in-the-loop correction (mid-simulation) ────────────────────────

    def human_correction(self, seg_idx: int, pass_after: int = None) -> None:
        """
        Simulate a human operator verifying the true state of a segment.
        Applied automatically after `pass_after` passes if specified.
        """
        true_state = self.track_config[seg_idx]
        self.trackers[seg_idx].human_correction(true_state)
        print(f"\n  [HITL] Segment {seg_idx} state verified by operator: "
              f"{CLASS_NAMES[true_state]}. Belief updated.")

    # ── Run full simulation ────────────────────────────────────────────────────

    def run(self, hitl_at_pass: int = None, hitl_segments: list[int] = None) -> None:
        print("\n" + "="*70)
        print("TRACK HEALTH SIMULATION")
        print("="*70)
        print(f"Track layout ({self.n_segments} segments):")
        for i, s in enumerate(self.track_config):
            print(f"  Segment {i}: {CLASS_NAMES[s]}")
        print(f"\nPasses: {self.n_passes}  |  V_max: {V_MAX_FPS} fps  "
              f"|  MPC horizon: {MPC_HORIZON} segments")

        for p in range(self.n_passes):
            self.run_pass(p)

            # Human-in-the-loop correction at specified pass
            if hitl_at_pass is not None and p + 1 == hitl_at_pass:
                for seg in (hitl_segments or []):
                    self.human_correction(seg)

        self._print_final_summary()
        self._save_plots()

    # ── Summary ────────────────────────────────────────────────────────────────

    def _print_final_summary(self) -> None:
        print("\n" + "="*70)
        print("FINAL SEGMENT BELIEFS  (after all passes)")
        print("="*70)
        print(f"  {'Seg':>3}  {'True':>8}  {'MAP':>8}  "
              f"{'P(H)':>7}  {'P(D)':>7}  {'P(X)':>7}  {'Entropy':>7}")
        n_correct = 0
        for i, true_s in enumerate(self.track_config):
            t   = self.trackers[i]
            map_s = t.map_state()
            if map_s == true_s:
                n_correct += 1
            print(f"  {i:>3}  {CLASS_NAMES[true_s]:>8}  "
                  f"{CLASS_NAMES[map_s]:>8}  "
                  f"{t.belief[0]:>7.4f}  {t.belief[1]:>7.4f}  "
                  f"{t.belief[2]:>7.4f}  {t.entropy():>7.4f}")
        print(f"\n  Final MAP accuracy: {n_correct}/{self.n_segments} segments correct")

    # ── Plots ──────────────────────────────────────────────────────────────────

    def _save_plots(self) -> None:
        self._plot_belief_evolution()
        self._plot_speed_profile()
        self._plot_track_dashboard()

    def _plot_belief_evolution(self) -> None:
        """Per-segment belief P(true state) over passes."""
        n_seg = self.n_segments
        fig, axes = plt.subplots(1, n_seg, figsize=(3 * n_seg, 4), sharey=True)
        passes = np.arange(1, self.n_passes + 1)

        for seg_idx, ax in enumerate(axes):
            true_s = self.track_config[seg_idx]
            for state_idx, state_name in enumerate(CLASS_NAMES):
                beliefs = [self.belief_history[p][seg_idx][state_idx]
                           for p in range(self.n_passes)]
                lw  = 2.5 if state_idx == true_s else 1.0
                ls  = "-"  if state_idx == true_s else "--"
                ax.plot(passes, beliefs, color=STATE_COLORS[state_idx],
                        linewidth=lw, linestyle=ls, label=state_name)

            ax.set_title(f"Seg {seg_idx}\n(True: {CLASS_NAMES[true_s]})",
                         fontsize=9)
            ax.set_xlabel("Pass #")
            ax.set_ylim(0, 1)
            ax.grid(True, alpha=0.3)
            if seg_idx == 0:
                ax.set_ylabel("Belief")
                ax.legend(fontsize=7)

        fig.suptitle("Bayesian Belief Evolution per Track Segment", fontsize=11)
        plt.tight_layout()
        p = OUTPUT_DIR / "sim_belief_evolution.png"
        fig.savefig(p, dpi=150)
        print(f"\nBelief evolution plot saved -> {p}")
        plt.close(fig)

    def _plot_speed_profile(self) -> None:
        """Heat-map of commanded speed: passes x segments."""
        speed_mat = np.array(self.speed_history)  # (n_passes, n_segs)

        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(speed_mat, aspect="auto", cmap="RdYlGn",
                       vmin=V_MIN_FPS, vmax=V_MAX_FPS, origin="upper")
        plt.colorbar(im, ax=ax, label="Commanded Speed (fps)")

        ax.set_xlabel("Track Segment")
        ax.set_ylabel("Pass Number")
        ax.set_xticks(range(self.n_segments))
        ax.set_xticklabels([
            f"Seg {i}\n({CLASS_NAMES[self.track_config[i]][0]})"
            for i in range(self.n_segments)
        ], fontsize=8)
        ax.set_yticks(range(self.n_passes))
        ax.set_yticklabels([f"Pass {p+1}" for p in range(self.n_passes)], fontsize=7)
        ax.set_title("MPC-Commanded Speed per Segment per Pass\n"
                     "(Green=fast/healthy, Red=slow/damaged)")

        plt.tight_layout()
        p = OUTPUT_DIR / "sim_speed_profile.png"
        fig.savefig(p, dpi=150)
        print(f"Speed profile plot saved    -> {p}")
        plt.close(fig)

    def _plot_track_dashboard(self) -> None:
        """Final-pass track map + per-class accuracy over passes."""
        fig, (ax_track, ax_acc) = plt.subplots(1, 2, figsize=(13, 4))

        # ── Left: track map with final belief bars ────────────────────────────
        bar_w = 0.8
        for seg_idx in range(self.n_segments):
            true_s   = self.track_config[seg_idx]
            belief   = self.trackers[seg_idx].belief
            map_s    = self.trackers[seg_idx].map_state()
            # Stacked bar: green / orange / red shares
            bottom = 0.0
            for state_idx in range(3):
                ax_track.bar(
                    seg_idx, belief[state_idx],
                    bottom=bottom, width=bar_w,
                    color=STATE_COLORS[state_idx],
                    alpha=0.85,
                    edgecolor="white", linewidth=0.5,
                )
                bottom += belief[state_idx]
            # Border colour = true state
            rect = plt.Rectangle(
                (seg_idx - bar_w / 2, 0), bar_w, 1.0,
                fill=False,
                edgecolor=STATE_COLORS[true_s],
                linewidth=3,
            )
            ax_track.add_patch(rect)
            correct = map_s == true_s
            ax_track.text(seg_idx, 1.03,
                          "OK" if correct else "ERR",
                          ha="center", va="bottom", fontsize=8,
                          color="black" if correct else "red",
                          fontweight="bold")

        ax_track.set_xlim(-0.6, self.n_segments - 0.4)
        ax_track.set_ylim(0, 1.15)
        ax_track.set_xticks(range(self.n_segments))
        ax_track.set_xticklabels([f"Seg {i}" for i in range(self.n_segments)])
        ax_track.set_ylabel("Belief Probability")
        ax_track.set_title("Track Segment Health Beliefs\n"
                            "(border = true state, stacked = belief)")
        legend_patches = [
            mpatches.Patch(color=STATE_COLORS[i], label=CLASS_NAMES[i])
            for i in range(3)
        ]
        ax_track.legend(handles=legend_patches, loc="upper right", fontsize=8)

        # ── Right: MAP accuracy over passes ──────────────────────────────────
        accs = []
        for p in range(self.n_passes):
            n_correct = sum(
                1 for seg_idx in range(self.n_segments)
                if self.pred_history[p][seg_idx] == self.track_config[seg_idx]
            )
            accs.append(n_correct / self.n_segments)

        ax_acc.plot(range(1, self.n_passes + 1), accs,
                    marker="o", color="steelblue", linewidth=2)
        ax_acc.axhline(1.0, color="green", linestyle="--", alpha=0.5,
                       label="Perfect classification")
        ax_acc.set_xlabel("Pass Number")
        ax_acc.set_ylabel("Fraction of Segments Correctly Classified")
        ax_acc.set_ylim(0, 1.1)
        ax_acc.set_title("MAP Classification Accuracy Over Passes")
        ax_acc.grid(True, alpha=0.3)
        ax_acc.legend(fontsize=8)

        fig.suptitle(
            f"Track Health Simulation — {self.n_passes} Passes  "
            f"|  Track: {[CLASS_NAMES[s][0] for s in self.track_config]}",
            fontsize=10,
        )
        plt.tight_layout()
        p = OUTPUT_DIR / "sim_dashboard.png"
        fig.savefig(p, dpi=150)
        print(f"Dashboard plot saved        -> {p}")
        plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sim = Simulation(
        track_config=TRACK_CONFIG,
        n_passes=N_PASSES,
        seed=RANDOM_SEED,
    )
    # Run the simulation; apply a HITL correction at pass 8 on segment 2
    # (simulates an operator verifying a flagged damaged segment)
    sim.run(
        hitl_at_pass=8,
        hitl_segments=[2],
    )
