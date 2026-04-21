# AMR Robot - Project Context
> Keep this file in the root of your PlatformIO project folder.
> Update it as the project progresses.

---

## Project Overview
Custom autonomous mobile robot (AMR) for a care home navigation scenario.
- Starts at Room A
- Operator sends command → robot navigates to Room C via Room B (unknown obstacles)
- Avoids obstacles autonomously
- Gripper picks up/drops off a small object at Room C
- Second command → robot returns to Room A
- Commands sent wirelessly (no physical buttons)

---

## Microcontroller
- **Main board:** ESP32-S3 DevKitC-1
- **Camera board:** ESP32-CAM (separate, communicates via UART)
- **IDE:** PlatformIO in VS Code
- **Framework:** Arduino (ESP32 Arduino **2.x** — use `ledcSetup/ledcAttachPin/ledcWrite`, NOT `ledcAttach`)
- **Flash method:** USB (OTA to be added later)

---

## Parts List

| Part | Model | Notes |
|---|---|---|
| Main MCU | ESP32-S3 DevKitC-1 | 240MHz dual-core, 520KB SRAM |
| Drive motors | NEMA 17 stepper x2 | Salvaged from 3D printer, 1.8°/step, 200 steps/rev |
| Motor drivers | TMC2209 x2 | Custom soldered perf board, shared EN pin |
| LIDAR sensor | VL53L1X TOF400C | 4m range, I2C, address 0x29 |
| LIDAR rotation motor | Small DC motor | 12V direct, PWM speed control via transistor |
| LIDAR angle encoder | AS5600 magnetic encoder | 12-bit absolute position, I2C address 0x36, mounted on rotating platform |
| LIDAR bearing | 6005-2RS | 25mm ID x 47mm OD x 12mm, deep groove ball bearing |
| LIDAR slip ring | 6-wire slip ring | 24mm max diameter, 4 wires used (VCC/GND/SDA/SCL for VL53L1X only) |
| IMU | MPU6050 GY-521 | I2C, address 0x68, gyro + accelerometer |
| Gripper servo | SG90 (or similar) | 5V, PWM control |
| Gripper IR sensor | IR obstacle sensor module | Detects object in front of gripper |
| LIDAR homing sensor | IR obstacle sensor module | Startup homing only — angle tracking now handled by AS5600 |
| Camera | ESP32-CAM | Streams footage to phone, receives LIDAR data via UART |
| Battery | 12V LiPo/Li-ion pack | Powers everything |
| Buck converter | 12V → 5V | Powers ESP32-S3, servos |
| Chassis | Custom 3D printed | Tracked tank-style, 150mm inner width, 164mm track contact length |

---

## Full Pin Assignment - ESP32-S3

### Drive Motors
| Component | Signal | GPIO |
|---|---|---|
| Left NEMA 17 | EN (active LOW) | 4 |
| Left NEMA 17 | DIR | 5 |
| Left NEMA 17 | STEP | 6 |
| Right NEMA 17 | EN (shared) | 4 |
| Right NEMA 17 | DIR | 1 |
| Right NEMA 17 | STEP | 2 |

> MS1 and MS2 grounded on both TMC2209s = 1/8 microstepping = 1600 steps/rev

### LIDAR Assembly
| Component | Signal | GPIO |
|---|---|---|
| DC motor (transistor gate) | PWM | 38 |
| LIDAR homing IR sensor | Data | 48 |
| VL53L1X TOF sensor | SDA | 8 (through slip ring) |
| VL53L1X TOF sensor | SCL | 9 (through slip ring) |
| AS5600 encoder | SDA | 8 (direct — encoder IC is stationary) |
| AS5600 encoder | SCL | 9 (direct — encoder IC is stationary) |

> GPIO 39, 40, 41 are free (previously used by 28BYJ-48 stepper, which was replaced).
> DC motor runs on 12V direct from battery. Transistor gate driven by GPIO 38 PWM.
> Use `ledcSetup(0, 25000, 8)` + `ledcAttachPin(38, 0)` — 25kHz is above hearing range.
> IR sensor (GPIO 48): only used for startup homing. Use INPUT_PULLUP — floats without it.
>
> **AS5600 placement:** IC is fixed (stationary), mounted above the rotating LIDAR dome on its own bracket.
> The diametrically magnetized disc magnet is embedded in the centre of the rotating dome/axis top.
> AS5600 wires directly to ESP32-S3 (no slip ring). Only VL53L1X goes through the slip ring.
> Both devices still share GPIO 8/9 I2C bus — no address conflict (0x36 vs 0x29).
> Magnet gap: design for **1.0–1.5mm** between magnet top surface and AS5600 IC face (Z-axis fixed at print time).
> Wire.setClock(100000) — 100kHz required for slip ring reliability (400kHz causes I2C errors).

### IMU
| Component | Signal | GPIO |
|---|---|---|
| MPU6050 | SDA | 8 (shared I2C bus) |
| MPU6050 | SCL | 9 (shared I2C bus) |

### Gripper
| Component | Signal | GPIO |
|---|---|---|
| Gripper servo | PWM signal | 42 |
| Gripper IR sensor | Data | 7 |

### Power Monitoring
| Component | Signal | GPIO |
|---|---|---|
| Battery voltage divider | Analog in | 10 |

> Voltage divider: 100kΩ (top) + 27kΩ (bottom) between battery+ and GND. Middle point → GPIO 10.
> Scales: 12.6V→2.68V, 10.8V→2.30V, 9.0V→1.91V — within ESP32-S3 ADC range (use ADC_11db attenuation).
> 3S Li-ion: full=12.6V, empty=9.0V. Percent = (Vbat-9.0)/(12.6-9.0)×100, clamped 0–100.
> Calibration factor CAL=1.044 (accounts for resistor tolerance + ADC Vref error). Verified against bench supply.
> ADC: average 16 samples to reduce noise. analogSetAttenuation(ADC_11db) required.
> Note: readings slightly compressed above 12.4V (ADC near saturation) — acceptable, battery drops below 12.4V quickly after use.
> Do NOT use 33kΩ — gives 3.13V at full charge, damages ADC accuracy.

### ESP32-CAM UART
| Signal | ESP32-S3 GPIO | ESP32-CAM GPIO |
|---|---|---|
| TX (S3 → CAM) | 17 | 13 (RX) |
| RX (CAM → S3) | 18 | 12 (TX) |

> GPIO 12/13 on CAM avoids conflict with CAM programming pins (0/1/3)

---

## Power Architecture
```
12V Battery
├── Direct → TMC2209 VM pins (NEMA 17 motor power)
├── Direct → DC LIDAR motor (via transistor, PWM from GPIO 38)
└── Buck converter (12V → 5V)
        ├── ESP32-S3 (5V pin)
        ├── ESP32-CAM (5V pin)
        └── Gripper servo (SG90)

ESP32-S3 onboard 3.3V LDO
        ├── VL53L1X (via slip ring VCC line — rotating)
        ├── AS5600 (direct 3.3V — stationary, no slip ring)
        ├── MPU6050 GY-521
        ├── Gripper IR sensor
        └── LIDAR homing IR sensor
```

---

## I2C Bus
- SDA → GPIO 8, SCL → GPIO 9
- Wire.setClock(100000) — **100kHz required** (slip ring is unreliable at 400kHz)
- VL53L1X address: 0x29 (on rotating platform, via slip ring)
- AS5600 address:  0x36 (stationary, direct connection — no slip ring)
- MPU6050 address: 0x68 (on main board, direct connection)
- No address conflicts between any devices

---

## IMU — Implementation Notes

### MPU6050 Heading (Gyro Z integration)
- Calibration: `mpu.CalibrateAccel(6)` + `mpu.CalibrateGyro(15)` at boot — robot must be flat and still for ~5s
- Heading integration: `headingDeg -= fgz * dtSec` (**negative** — turning right = increasing heading)
- Residual drift after calibration: ~±0.03°/s (~2°/min) — acceptable for short navigation runs
- Long-term drift correction will come from LIDAR scan matching in sensor fusion
- For final robot: calibrate at boot, use motor startup chimes to signal when calibration is complete and robot can be moved
- Accel X/Y (tilt) not used for navigation — robot stays flat at all times

---

## Navigation Architecture
Three-layer sensor fusion:
1. **Stepper odometry** — straight-line distance tracking (step counting)
2. **MPU6050 gyroscope** — turn angle measurement during skid-steer turns
3. **VL53L1X spinning LIDAR** — 360° obstacle detection + long-term drift correction

**LIDAR angle measurement:** AS5600 absolute magnetic encoder mounted on the rotating platform reads the true angle directly (0–4095 = 0°–360°, 12-bit). This replaces the previous time-interpolation method (IR pulse period ÷ elapsed time), which had ±22–25° error due to motor speed variation and 20ms TOF integration blur.

**LIDAR startup homing:** On boot, DC motor spins until IR sensor (GPIO 48) triggers → establishes a known reference point. After that, AS5600 provides continuous absolute angle — IR sensor no longer needed for ongoing tracking.

---

## LIDAR Scanner — Implementation Notes

### AS5600 Encoder
- Register 0x0B (STATUS): MD bit (bit 5) = magnet detected, MH (bit 3) = too strong, ML (bit 4) = too weak
- Register 0x1B–0x1C (MAGNITUDE): 12-bit field strength, used for physical alignment
- Register 0x0E–0x0F (ANGLE): 12-bit raw angle, 0–4095 = 0°–360°
- Alignment procedure: maximize MAGNITUDE value while STATUS shows MD=1, MH=0, ML=0
- Well-aligned sensor at 1–2mm gap typically reads MAGNITUDE 2000–3500

### VL53L1X TOF Sensor
- Mode: Short (1.3m range), timing budget 20ms → ~46 readings/rev at 65 RPM (~7.8° resolution)
- Minimum timing budget is 20ms — limited by SPAD photon counting statistics, cannot be reduced
- At 65 RPM: one revolution = 923ms → 46 samples per revolution
- Long mode (4m) requires 33ms minimum budget → fewer samples per rev
- `sensor.startContinuous(20)` + `sensor.read()` (blocking) — blocks ~20ms until new measurement ready

### DC Rotation Motor (Closed-Loop PI) — TUNED & WORKING
- Target RPM: 65 (60 RPM is stiction zone — avoid)
- Steady-state PWM: ~58–59
- PWM: LEDC channel 0, 25kHz (above hearing range), 8-bit resolution
- Soft-start: ramp to PWM=62 (must be near steady-state — too low risks stiction stall on startup)
- Homing speed: PWM=42 (slow enough to stop cleanly at IR trigger)
- PI gains: KP=0.2, KI=0.06, integral clamp ±10 RPM, rate limiter ±3 PWM/rev
- PI updated once per full revolution (revolution period measured via AS5600 accumulated angle)
- RPM EMA: alpha=0.3 (3-rev time constant for smooth estimate)
- Warmup: discard first 3 revolutions before scanning
- Stall detection: time-based — if no full revolution in 2500ms → stall
- Stall recovery: ramp +2 PWM/sample toward PWM=72, reset integral on recovery
- Remaining ±3–5 RPM variation is mechanical (motor load/drag), not fixable in software

### Angle Calculation (AS5600 — current implementation)
- Read raw angle BEFORE and AFTER `sensor.read()` (which blocks ~20ms)
- Signed delta with rollover: `d = to - from; if d > 2048: d -= 4096; if d < -2048: d += 4096`
- Midpoint angle = rawBefore + delta/2 → apply home offset → output angle
- Home offset set at startup when IR sensor triggers: `homeOffsetDeg = rawToDeg(readRawAngle())`
- Corrected angle: `(rawDeg - homeOffsetDeg + 360) % 360` → 0° = front (IR position)
- Revolution completion tracked by accumulating delta; when accumulated ≥ 360° → one rev done
- Residual angular jitter ~2–3° per revolution — inherent to 20ms integration window at 65 RPM, not fixable

### Python Visualizer (lidar_visualizer.py)
- COM port: **COM15**, baud 115200
- Polar plot, anticlockwise rotation, 0° = North (front of robot)
- 180 bins (2° per bin), age-based fading (1.5s fade), lime-green sweep line
- Lines starting with `#` are status messages, ignored by plot

---

## Chassis Dimensions
- Inner body width: 150mm
- Outer width: ~199mm
- Track contact length (ground): 164mm
- Track-to-track spacing (centre): ~132mm
- L/W ratio: 1.24 (good for skid steering)

---

## Gripper — Implementation Notes
- Servo mounted inverted: 175° = closed, 5° = fully open, 70° = grip hold
- Normal resting state: closed (175°) — open on approach, close to grip
- IR sensor (GPIO 7, digital only, active LOW): used to confirm object is held and detect when object is released
- Autonomous grip sequence: open jaw → approach object (IR detects it) → close to GRIP_DEG (70°) → confirm IR still triggered → navigate → release at destination
- No force sensing — grip angle is fixed at 70°, tuned for the specific object used

---

## ESP32-CAM Role
- WiFi AP: SSID "AMR1", password "amr1robot" — supervisor connects phone/laptop
- Supervisor opens http://192.168.4.1 — two-tab web interface:
  - Tab 1: live MJPEG camera stream (/stream endpoint)
  - Tab 2: LIDAR radar canvas + RPM / battery % / heading
- WebSocket on port 81 pushes live data to browser
- PlatformIO project: c:\Users\parsa\Documents\PlatformIO\Projects\ESpcam
- Board: esp32cam (AI Thinker), lib: links2004/WebSockets

### UART Protocol — S3 → CAM (S3 GPIO17→CAM GPIO13, S3 GPIO18←CAM GPIO15, 115200 baud)
> CAM GPIO12 avoided — it is a bootstrap strapping pin on ESP32. If HIGH during reset it sets 1.8V flash mode, causing "Failed to communicate with flash chip" upload errors.
> Always disconnect UART wires from CAM before flashing it.
S3 must send these line formats:
  "L:angle,dist\n"    — one LIDAR point (angle float degrees, dist int mm)
  "S:rpm,bat,hdg\n"   — status once/second (rpm int, bat int %, hdg float °)
Example: "L:127.4,843\n"  "S:65,87,34.1\n"

---

## Testing Progress

- [x] 1. VL53L1X TOF sensor — distance reading confirmed working
- [x] 2. DC LIDAR motor — stable 65 RPM closed-loop, ±3–5 RPM mechanical variation, silent (25kHz PWM)
- [x] 3. LIDAR scanning — VL53L1X + DC motor + AS5600 working, polar visualizer confirmed working
- [x] 4. AS5600 integration — magnet aligned (MAGNITUDE ~2080, OK status), encoder wired direct (no slip ring), homing + absolute angle tracking working. ~7.8° angular resolution at 65 RPM.
- [x] 5. MPU6050 IMU — calibrated, heading confirmed working, drift ~±0.03°/s residual
- [x] 6. NEMA 17 drive motors — forward/back confirmed working. Left motor STEP/DIR physically swapped on perfboard — constructor uses `AccelStepper(DRIVER, L_DIR, L_STEP)` to compensate.
- [x] 7. Gripper servo — angles confirmed: OPEN=5°, CLOSE=175°, GRIP=70°. Servo mounted inverted (higher angle = more closed).
- [x] 8. Gripper IR sensor — digital only (no AO pin). Active LOW. Potentiometer trimmed for ~few cm detection range in front of gripper.
- [x] 9. Battery voltage monitor — GPIO 10, 100kΩ+27kΩ divider, CAL=1.044, reads ±0.1V accurate
- [ ] 10. Full sensor fusion — combined odometry + IMU + LIDAR
- [ ] 11. Autonomous navigation
- [ ] 12. ESP32-CAM integration — firmware written (ESpcam project), ESP32-CAM unit broken, defer

---

## Libraries Required (PlatformIO)
```ini
lib_deps =
    pololu/VL53L1X@^1.3.1
    electroniccats/MPU6050@^1.3.0
```
> AccelStepper NOT in lib_deps currently — add back only when testing NEMA 17 drive motors.
> AccelStepper causes `sdkconfig.h` compile error on ESP32-S3 when not needed (see Gotchas).
> No external library needed for AS5600 — read via Wire directly.
> Use `platform = espressif32` (no version pin) — pinning a version causes incomplete SDK installs.

---

## Key Lessons / Gotchas

| Issue | Fix |
|---|---|
| `ledcAttach()` not found | ESP32 Arduino 2.x — use `ledcSetup(ch, freq, bits)` + `ledcAttachPin(pin, ch)` + `ledcWrite(ch, val)` |
| Motor PWM whine | analogWrite defaults to ~1kHz. Use LEDC at 25kHz (above hearing) |
| IR sensor false triggers | GPIO 48 needs INPUT_PULLUP — floats without it, triggers on touch |
| PI controller slams PWM to 0 on first reading | First closed-loop sample at ~157 RPM → huge error. Fix: feedforward + ±5 PWM/rev rate limiter |
| Motor oscillates at 60 RPM target | 60 RPM is in the motor's stiction zone. Use 65 RPM minimum |
| Soft-start PWM too low → stall on startup | Soft-start must ramp to near steady-state PWM (~62). Too low (48) risks stiction before PI takes over |
| I2C errors through slip ring | 400kHz unreliable. Use `Wire.setClock(100000)` (100kHz) |
| Visualizer rotation mirrored | Physical motor is anticlockwise. Set `ax.set_theta_direction(1)` in matplotlib |
| AccelStepper causes `sdkconfig.h` compile error | Known ESP32-S3 issue. Remove AccelStepper from lib_deps when not needed for drive motor tests |
| Pinning `platform = espressif32@x.x.x` breaks build | Pinned version downloads incomplete SDK. Use `platform = espressif32` (no version) |
| `pio` not found in PowerShell | Use PlatformIO sidebar in VS Code → esp32s3 → General → Clean/Upload. Not the system terminal. |
