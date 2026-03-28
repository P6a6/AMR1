"""
AMR1 LIDAR Visualizer — radar line style
Each angle bin has a radial line whose length = measured distance.
Lines fade over ~1.5 s then disappear. Sweep line shows current sensor position.

Install:  pip install pyserial matplotlib numpy
Run:      python lidar_visualizer.py
"""

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import threading
import math
import time
import sys

# ── Settings ────────────────────────────────────────────────────────
COM_PORT   = 'COM15'  # ← change to your port
BAUD_RATE  = 115200
MAX_RANGE  = 1000     # mm  (set to 4000 for room-scale)
ANGLE_BINS = 180      # 2° per bin
FADE_TIME  = 1.5      # seconds until a line fully fades (≈ 2–3 revolutions)

# ── Per-bin data ─────────────────────────────────────────────────────
_bin_dist    = np.zeros(ANGLE_BINS)
_bin_time    = np.full(ANGLE_BINS, -999.0)
_sweep_angle = [0.0]
_status      = ['waiting for motor...']
_lock        = threading.Lock()


def _angle_to_bin(angle_rad):
    return int(math.degrees(angle_rad) % 360 * ANGLE_BINS / 360) % ANGLE_BINS


def _serial_thread():
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1.0)
        print(f"[serial] Connected to {COM_PORT}")
    except serial.SerialException as e:
        print(f"[serial] Cannot open {COM_PORT}: {e}")
        print("         Check Device Manager for the correct port.")
        sys.exit(1)

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            if line.startswith('#'):
                with _lock:
                    _status[0] = line[2:].strip()
            elif ',' in line:
                parts     = line.split(',', 1)
                angle_rad = math.radians(float(parts[0]))
                dist_mm   = float(parts[1])
                if 10 < dist_mm < MAX_RANGE:
                    idx = _angle_to_bin(angle_rad)
                    with _lock:
                        _bin_dist[idx]   = dist_mm
                        _bin_time[idx]   = time.time()
                        _sweep_angle[0]  = angle_rad
        except Exception:
            pass


# ── Plot ─────────────────────────────────────────────────────────────
plt.style.use('dark_background')
fig = plt.figure(figsize=(8, 8), facecolor='#000000')
ax  = fig.add_subplot(111, projection='polar')
ax.set_facecolor('#000000')

ax.set_theta_zero_location('N')
ax.set_theta_direction(1)           # anticlockwise — matches physical motor rotation
ax.set_rlim(0, MAX_RANGE)

ax.set_rticks([250, 500, 750, 1000])
ax.set_yticklabels(['25 cm', '50 cm', '75 cm', '1 m'], color='#1a4a1a', size=8)
ax.xaxis.set_tick_params(labelcolor='#1a4a1a', labelsize=9)
ax.grid(color='#091509', linewidth=0.8)
ax.spines['polar'].set_color('#0d2b0d')

# "FRONT" label at 0° (top)
ax.text(0, MAX_RANGE * 1.13, 'FRONT', color='#00ff55',
        ha='center', va='center', fontsize=9, fontweight='bold')

# Dim reference line pointing forward (always visible)
ax.plot([0, 0], [0, MAX_RANGE], color='#00ff44', lw=0.5, alpha=0.12, zorder=2)

# Robot centre dot
ax.scatter([0], [0], s=55, c='#00ff44', zorder=6)

# Rotating sweep line — shows where the sensor is pointing right now
sweep_line, = ax.plot([], [], color='#aaffcc', lw=1.8, alpha=0.65, zorder=5)

# Pre-create one line object per angle bin — just update data each frame
bin_angles = np.linspace(0, 2 * np.pi, ANGLE_BINS, endpoint=False)
radar_lines = [ax.plot([], [], lw=1.8, solid_capstyle='round', zorder=4)[0]
               for _ in range(ANGLE_BINS)]

title_obj = ax.set_title('AMR1 LIDAR  |  waiting...',
                          color='#2a6a2a', pad=20, fontsize=11)


def _update(_frame):
    with _lock:
        dists = _bin_dist.copy()
        times = _bin_time.copy()
        sweep = _sweep_angle[0]
        s     = _status[0]

    now = time.time()

    # Move sweep line to current sensor angle
    sweep_line.set_data([sweep, sweep], [0, MAX_RANGE])

    for i, line in enumerate(radar_lines):
        d   = dists[i]
        age = now - times[i]

        if d <= 0 or age > FADE_TIME:
            line.set_data([], [])
            continue

        alpha = 1.0 - (age / FADE_TIME)          # 1.0 = just measured, 0.0 = faded

        # Bright lime-green when close and fresh → darker when far or old
        closeness = 1.0 - (d / MAX_RANGE)         # 1 = very close, 0 = at max range
        brightness = closeness * 0.5 + alpha * 0.5
        g = 0.25 + 0.75 * brightness
        r = closeness * 0.15 * alpha               # faint yellow tint for very close hits

        line.set_data([bin_angles[i], bin_angles[i]], [0, d])
        line.set_alpha(max(0.06, alpha))
        line.set_color((r, g, 0.08))

    title_obj.set_text(f'AMR1 LIDAR  |  {s}')
    return radar_lines + [sweep_line, title_obj]


# ── Start ─────────────────────────────────────────────────────────────
threading.Thread(target=_serial_thread, daemon=True).start()

ani = animation.FuncAnimation(fig, _update, interval=80,
                               blit=False, cache_frame_data=False)
plt.tight_layout()
plt.show()
