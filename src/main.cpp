// ── AS5600 Magnet Alignment Helper ───────────────────────────────────────
//
// Flash this to align the AS5600 magnetic encoder before final assembly.
// Continuously prints STATUS and MAGNITUDE to Serial at 115200.
//
// STATUS bits:
//   MD = 1, MH = 0, ML = 0  →  magnet detected, field strength OK
//   MH = 1                  →  magnet too strong / too close — move it further
//   ML = 1                  →  magnet too weak  / too far   — move it closer
//
// MAGNITUDE (0–4095):
//   Maximize this value while keeping MD=1, MH=0, ML=0.
//   Peak = sensor centered under the magnet's rotation axis.
//
// Angle (0–4095 = 0°–360°):
//   Should sweep smoothly as you rotate the assembly by hand.
//   Verify no jumps or reversals before committing to assembly.
//
// Pins: AS5600 SDA → 8   SCL → 9   (same I2C bus as VL53L1X)
// AS5600 I2C address: 0x36

#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN  8
#define SCL_PIN  9

#define AS5600_ADDR   0x36
#define REG_STATUS    0x0B
#define REG_MAGNITUDE 0x1B   // high byte 0x1B, low byte 0x1C (12-bit)
#define REG_ANGLE     0x0E   // high byte 0x0E, low byte 0x0F (12-bit)

// Read a 12-bit value from two consecutive registers (big-endian)
uint16_t readWord(uint8_t reg) {
    Wire.beginTransmission(AS5600_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(AS5600_ADDR, (uint8_t)2);
    if (Wire.available() < 2) return 0xFFFF;
    uint16_t hi = Wire.read();
    uint16_t lo = Wire.read();
    return ((hi << 8) | lo) & 0x0FFF;
}

uint8_t readByte(uint8_t reg) {
    Wire.beginTransmission(AS5600_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(AS5600_ADDR, (uint8_t)1);
    if (!Wire.available()) return 0xFF;
    return Wire.read();
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("# AS5600 Magnet Alignment Helper");
    Serial.println("# --------------------------------");
    Serial.println("# MD=1 MH=0 ML=0  →  field strength OK");
    Serial.println("# MH=1            →  magnet too close, move it away");
    Serial.println("# ML=1            →  magnet too far,   move it closer");
    Serial.println("# Maximize MAGNITUDE while keeping field OK");
    Serial.println("# Rotate assembly by hand — ANGLE should sweep 0–4095 smoothly");
    Serial.println("# --------------------------------");

    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(100000);

    // Verify device is present
    Wire.beginTransmission(AS5600_ADDR);
    if (Wire.endTransmission() != 0) {
        Serial.println("# ERROR: AS5600 not found at 0x36 — check wiring");
        while (1) delay(100);
    }
    Serial.println("# AS5600 found — starting alignment readout...");
    Serial.println();
    Serial.println("STATUS (MD MH ML) | MAGNITUDE (0-4095) | ANGLE (0-4095 = 0-360°)");
}

void loop() {
    uint8_t  status = readByte(REG_STATUS);
    uint16_t mag    = readWord(REG_MAGNITUDE);
    uint16_t raw    = readWord(REG_ANGLE);

    bool md = (status >> 5) & 1;   // magnet detected
    bool ml = (status >> 4) & 1;   // too weak
    bool mh = (status >> 3) & 1;   // too strong

    float angle_deg = raw * 360.0f / 4096.0f;

    // Build a compact status string
    char statusStr[32];
    if (!md) {
        snprintf(statusStr, sizeof(statusStr), "NO MAGNET");
    } else if (mh) {
        snprintf(statusStr, sizeof(statusStr), "TOO STRONG (move away)");
    } else if (ml) {
        snprintf(statusStr, sizeof(statusStr), "TOO WEAK   (move closer)");
    } else {
        snprintf(statusStr, sizeof(statusStr), "OK");
    }

    Serial.printf("%-24s | MAG: %4u | ANGLE: %6.1f deg (raw %4u)\n",
                  statusStr, mag, angle_deg, raw);

    delay(100);  // 10 Hz — fast enough to see changes while adjusting
}
