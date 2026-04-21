// ── Battery Voltage Monitor ───────────────────────────────────────────────────
// Voltage divider: 100kΩ (top) + 27kΩ (bottom) → GPIO 10
// 3S Li-ion: 12.6V full, 9.0V empty

#include <Arduino.h>

#define BAT_PIN     10
#define R_TOP    100.0f   // kΩ
#define R_BOT     27.0f   // kΩ
#define V_FULL    12.6f
#define V_EMPTY    9.0f
#define CAL       1.044f  // calibrated: 12.0V supply reads ~12.0V (was 11.375 raw, 12.13 at 1.055)

void setup() {
    Serial.begin(115200);
    analogSetAttenuation(ADC_11db);   // enables 0–3.3V range on all ADC pins
    delay(300);
    Serial.println("# Battery monitor — readings every 1s");
    Serial.println("# Voltage | Percent");
}

void loop() {
    // Average 16 samples to reduce ADC noise
    long sum = 0;
    for (int i = 0; i < 16; i++) {
        sum += analogRead(BAT_PIN);
        delay(2);
    }
    float raw  = sum / 16.0f;
    float Vadc = raw * 3.3f / 4095.0f;
    float Vbat = Vadc * (R_TOP + R_BOT) / R_BOT * CAL;
    int   pct  = constrain((int)((Vbat - V_EMPTY) / (V_FULL - V_EMPTY) * 100.0f), 0, 100);

    Serial.printf("%.2f V  |  %d%%\n", Vbat, pct);
    delay(1000);
}
