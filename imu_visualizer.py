"""
AMR1 IMU Visualizer — heading only
Compass needle + rolling heading & gyro-Z plots.

Install:  pip install pyserial matplotlib numpy
Run:      python imu_visualizer.py
"""

import serial, threading, time, sys, math, collections
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

COM_PORT  = 'COM15'
BAUD_RATE = 115200
HISTORY_S = 15
RATE_HZ   = 20
HISTORY_N = HISTORY_S * RATE_HZ

# ── Shared state ──────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_hdg     = [0.0]
_gz      = [0.0]
_status  = ['waiting for calibration...']
_hdg_buf = collections.deque([0.0] * HISTORY_N, maxlen=HISTORY_N)
_gz_buf  = collections.deque([0.0] * HISTORY_N, maxlen=HISTORY_N)
_t_buf   = collections.deque([-HISTORY_S + i / RATE_HZ
                               for i in range(HISTORY_N)], maxlen=HISTORY_N)
_t0 = time.time()

def _serial_thread():
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1.0)
        print(f"[serial] Connected to {COM_PORT}")
    except serial.SerialException as e:
        print(f"[serial] Cannot open {COM_PORT}: {e}")
        sys.exit(1)
    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            if line.startswith('#'):
                with _lock:
                    _status[0] = line[2:].strip()
                print(f"[status] {line[2:].strip()}")
                continue
            parts = line.split(',')
            if len(parts) < 7:
                continue
            gz  = float(parts[5])
            hdg = float(parts[6])
            t   = time.time() - _t0
            with _lock:
                _hdg[0] = hdg
                _gz[0]  = gz
                _hdg_buf.append(hdg)
                _gz_buf.append(gz)
                _t_buf.append(t)
        except Exception:
            pass

# ── Layout ────────────────────────────────────────────────────────────────────
plt.style.use('dark_background')
fig = plt.figure(figsize=(11, 7), facecolor='#080808')

ax_c  = fig.add_axes([0.03, 0.06, 0.50, 0.88])   # compass (left)
ax_h  = fig.add_axes([0.58, 0.55, 0.40, 0.36])   # heading history (top right)
ax_g  = fig.add_axes([0.58, 0.10, 0.40, 0.30])   # gyro Z history (bottom right)

for a in [ax_c, ax_h, ax_g]:
    a.set_facecolor('#080808')

# ── Compass — static ──────────────────────────────────────────────────────────
ax_c.set_xlim(-1.4, 1.4)
ax_c.set_ylim(-1.4, 1.4)
ax_c.set_aspect('equal')
ax_c.axis('off')

# Outer ring
ax_c.add_patch(plt.Circle((0, 0), 1.05, color='#001a00', fill=True, zorder=1))
ax_c.add_patch(plt.Circle((0, 0), 1.05, color='#00aa44', fill=False, lw=1.5, zorder=3))
ax_c.add_patch(plt.Circle((0, 0), 0.04, color='#00ff88', fill=True, zorder=7))

# Degree ticks and labels
for a in range(0, 360, 10):
    r   = math.radians(a)
    s, c = math.sin(r), math.cos(r)
    inner = 0.88 if a % 30 == 0 else 0.93
    ax_c.plot([s * inner, s * 1.05], [c * inner, c * 1.05],
              color='#00aa44' if a % 90 == 0 else '#004422',
              lw=1.5 if a % 90 == 0 else 0.6, zorder=2)
    if a % 30 == 0:
        label = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.get(a, f'{a}°')
        ax_c.text(s * 1.21, c * 1.21, label,
                  color='#00ff88' if a % 90 == 0 else '#00aa55',
                  ha='center', va='center',
                  fontsize=13 if a % 90 == 0 else 8,
                  fontweight='bold' if a % 90 == 0 else 'normal', zorder=5)

# Fixed forward reference line
ax_c.plot([0, 0], [0, 0.5], color='#00ff88', lw=0.8, alpha=0.2, zorder=2)

compass_title = ax_c.text(0, -1.32, 'Heading: --.-°', color='#00ff88',
                           ha='center', va='center', fontsize=14, fontweight='bold')

needle_fwd,  = ax_c.plot([], [], color='#00ff88', lw=5, solid_capstyle='round', zorder=6)
needle_back, = ax_c.plot([], [], color='#cc2222', lw=3, solid_capstyle='round', zorder=6)
hdg_val_text = ax_c.text(0, 0.55, '', color='#00ffaa',
                          ha='center', va='center', fontsize=11, zorder=8)

# ── Rolling plots — static ────────────────────────────────────────────────────
for a, ylabel, ylim, color in [
    (ax_h, 'Heading (°)', (-185, 185), '#00ff88'),
    (ax_g, 'Gyro Z (°/s)', (-80, 80),  '#88ff44'),
]:
    a.set_ylabel(ylabel, color=color, fontsize=9)
    a.set_ylim(*ylim)
    a.axhline(0, color='#1a3a1a', lw=0.8)
    a.tick_params(colors='#336633', labelsize=7)
    a.grid(color='#0d200d', lw=0.5)
    for sp in a.spines.values():
        sp.set_color('#1a3a1a')

ax_h.set_title('Heading history', color='#336633', fontsize=8, pad=3)
ax_g.set_title('Gyro Z (yaw rate)', color='#336633', fontsize=8, pad=3)
ax_g.set_xlabel('seconds ago', color='#336633', fontsize=8)

hdg_line, = ax_h.plot([], [], color='#00ff88', lw=1.3)
gz_line,  = ax_g.plot([], [], color='#88ff44', lw=1.0)
gz_zero   = ax_g.axhline(0, color='#333333', lw=0.5)

status_txt = fig.text(0.57, 0.97, '', color='#336633', fontsize=8, va='top')
drift_txt  = fig.text(0.57, 0.50, '', color='#555555', fontsize=8, va='top')

# ── Update ────────────────────────────────────────────────────────────────────
def _update(_frame):
    with _lock:
        hdg = _hdg[0]
        hb  = list(_hdg_buf)
        gb  = list(_gz_buf)
        tb  = list(_t_buf)
        st  = _status[0]

    # Compass needle
    r  = math.radians(hdg)
    nx, ny = math.sin(r), math.cos(r)
    needle_fwd.set_data( [0,  nx * 0.82], [0,  ny * 0.82])
    needle_back.set_data([0, -nx * 0.30], [0, -ny * 0.30])
    compass_title.set_text(f'Heading:  {hdg:+.1f}°')
    hdg_val_text.set_text(f'{hdg:+.1f}°')

    # Drift estimate from last 3 seconds of gz history
    recent_gz = list(_gz_buf)[-RATE_HZ * 3:]
    drift_rate = np.mean(recent_gz) if recent_gz else 0.0
    drift_txt.set_text(f'Drift est: {drift_rate:+.3f} °/s\n({drift_rate*60:.2f} °/min)')

    # Rolling plots
    t_arr = np.array(tb) - tb[-1]   # relative to now
    ax_h.set_xlim(t_arr[0], 0)
    ax_g.set_xlim(t_arr[0], 0)
    hdg_line.set_data(t_arr, hb)
    gz_line.set_data(t_arr, gb)

    status_txt.set_text(st)

    return [needle_fwd, needle_back, hdg_line, gz_line,
            compass_title, hdg_val_text, drift_txt, status_txt]

# ── Start ─────────────────────────────────────────────────────────────────────
threading.Thread(target=_serial_thread, daemon=True).start()
ani = animation.FuncAnimation(fig, _update, interval=80,
                               blit=False, cache_frame_data=False)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.show()
