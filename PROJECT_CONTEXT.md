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
| LIDAR bearing | 6005-2RS | 25mm ID x 47mm OD x 12mm, deep groove ball bearing |
| LIDAR slip ring | 6-wire slip ring | 24mm max diameter, 4 wires used (VCC/GND/SDA/SCL) |
| IMU | MPU6050 GY-521 | I2C, address 0x68, gyro + accelerometer |
| Gripper servo | SG90 (or similar) | 5V, PWM control |
| Gripper IR sensor | IR obstacle sensor module | Detects object in front of gripper |
| LIDAR homing sensor | IR obstacle sensor module | Detects home position of rotating LIDAR platform |
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
| VL53L1X TOF sensor | SDA | 8 |
| VL53L1X TOF sensor | SCL | 9 |

> GPIO 39, 40, 41 are now free (previously used by 28BYJ-48 stepper, which was replaced).
> DC motor runs on 12V direct from battery. Transistor gate driven by GPIO 38 PWM.
> IR sensor (GPIO 48) also used for RPM measurement — triggers once per revolution.
> Use INPUT_PULLUP on GPIO 48 — sensor output floats without it, causing false triggers.

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

> Voltage divider: 100kΩ + 33kΩ between 12V and GND. Middle point → GPIO 10. Scales 12V to ~3V.

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
        ├── VL53L1X
        ├── MPU6050 GY-521
        ├── Gripper IR sensor
        └── LIDAR homing IR sensor
```

---

## I2C Bus
- SDA → GPIO 8, SCL → GPIO 9
- VL53L1X address: 0x29
- MPU6050 address: 0x68
- No address conflict

---

## Navigation Architecture
Three-layer sensor fusion:
1. **Stepper odometry** — straight-line distance tracking (step counting)
2. **MPU6050 gyroscope** — turn angle measurement during skid-steer turns
3. **VL53L1X spinning LIDAR** — 360° obstacle detection + long-term drift correction

LIDAR homing: On boot, DC motor spins until IR sensor triggers → platform pointing dead forward → timestamp reset → continuous rotation begins. Angle is time-interpolated between IR pulses (recalibrates every revolution).

---

## Chassis Dimensions
- Inner body width: 150mm
- Outer width: ~199mm
- Track contact length (ground): 164mm
- Track-to-track spacing (centre): ~132mm
- L/W ratio: 1.24 (good for skid steering)

---

## ESP32-CAM Role
- Streams MJPEG video to phone via WiFi access point
- Receives LIDAR scan data + battery % + heading from S3 via UART
- Serves web interface: switch between live camera view and LIDAR radar display
- Phone connects to CAM's WiFi access point to view everything

---

## Testing Order (Current Phase)
- [ ] 1. VL53L1X TOF sensor — distance reading to serial monitor
- [ ] 2. DC LIDAR motor — RPM measurement via IR sensor, PWM speed tuning
- [ ] 3. LIDAR scanning — motor + VL53L1X, live polar map via lidar_visualizer.py
- [ ] 4. MPU6050 IMU — heading/gyro output to serial monitor
- [ ] 5. NEMA 17 drive motors — basic movement test (forward/back/turn)
- [ ] 6. Gripper servo — open/close test
- [ ] 7. Gripper IR sensor — object detection test
- [ ] 8. Full sensor fusion — combined odometry + IMU + LIDAR
- [ ] 9. Autonomous navigation
- [ ] 10. ESP32-CAM integration (low priority, do last)

---

## Libraries Required (PlatformIO)
```ini
lib_deps =
    waspinator/AccelStepper@^1.64.0
    pololu/VL53L1X@^1.3.1
    electroniccats/MPU6050@^1.3.0
```
