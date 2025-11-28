#pragma once
#include "Arduino.h"

class DHT11 {
private:
    uint8_t pin;
public:
    DHT11(uint8_t p) { pin = p; }
    void begin() { pinMode(pin, INPUT_PULLUP); }

    bool read(float &humidity, float &temperature) {
        uint8_t data[5] = {0};
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
        delay(18);
        digitalWrite(pin, HIGH);
        delayMicroseconds(40);
        pinMode(pin, INPUT_PULLUP);

        unsigned long start = micros();
        while (digitalRead(pin) == HIGH)
            if (micros() - start > 80) return false;

        for (int i = 0; i < 40; i++) {
            while (digitalRead(pin) == LOW)
                if (micros() - start > 10000) return false;
            unsigned long h = micros();
            while (digitalRead(pin) == HIGH)
                if (micros() - start > 10000) return false;
            if ((micros() - h) > 50)
                data[i / 8] |= (1 << (7 - (i % 8)));
        }

        humidity = data[0];
        temperature = data[2];
        return true;
    }
};
