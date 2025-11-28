/******************************************************************************
 *  Author:  Alexander Pagaduan
 *  Date:    November 27, 2025
 *
 *  Project: Senior Design – Smart Aquaponics Sensor/Actuator System
 *
 *  Intellectual Property Notice:
 *  ---------------------------------------------------------------------------
 *  This file contains original work authored by Alexander Pagaduan, including:
 *    - SensorActuator module design and implementation
 *    - Custom JSON command/feedback protocol
 *    - LED control logic
 *    - Sensor integration logic (DHT, ultrasonic, LUX)
 *    - Routing/packet-handling modifications
 *    - Hardware/software architecture decisions
 *
 *  COPYRIGHT & OWNERSHIP:
 *  All rights to this work are owned exclusively by the author,
 *  Alexander Pagaduan. This work is protected under U.S. Copyright Law.
 *
 *  PERMISSION REQUIRED:
 *  This work may NOT be used, copied, modified, shared, or integrated into any
 *  project, assignment, research effort, or hardware/software system without my
 *  explicit written permission.
 *
 *  LIMITED LICENSE — SENIOR DESIGN ONLY:
 *  If permission is explicitly granted in writing, it applies ONLY to the
 *  SSU Senior Design project:
 *
 *        “Smart Aquaponics Monitoring & Actuation System”
 *
 *      Team Members: Huy Nguyen, Marcus Serrano
 *      Advisor:      Dr. Farid Farahmand
 *
 *  ***TERMINATION CLAUSE***
 *  ---------------------------------------------------------------------------
 *  If I am removed from the senior design team or no longer participating in
 *  the project for any reason, all permissions granted to teammates, advisors,
 *  or any other individual are immediately revoked. From that point forward,
 *  none of my code, designs, diagrams, or contributions may be used, shared,
 *  submitted, or integrated into the project.
 *
 *  UNIVERSITY RESTRICTIONS:
 *  Sonoma State University may *evaluate* this work for grading purposes ONLY.
 *  No rights are granted to reuse, redistribute, store, or repurpose this work
 *  for future academic or instructional use without my explicit written consent.
 *
 *  CREDIT REQUIREMENT:
 *  If permission is granted for project use, I must be credited as the original
 *  author in all submissions, presentations, documentation, and demonstrations.
 *
 *  NO REDISTRIBUTION:
 *  This file (and derivative work) may NOT be:
 *    - reused in other SSU or external projects
 *    - included in teaching materials or archives
 *    - redistributed or modified without permission
 *    - presented as another individual's work
 *    - used outside the approved Senior Design scope
 *
 *  All rights reserved.
 *  © 2025 Alexander Pagaduan
 ******************************************************************************/



#include "SensorActuatorModule.h"
#include "MeshService.h"
#include "MeshRadio.h"
#include "Router.h"
#include "NodeDB.h"
#include "configuration.h"
#include "Channels.h"

// ==================== External core objects ====================
extern MeshService *service;
extern Router *router;
extern NodeDB *nodeDB;
extern const RegionInfo *myRegion;
extern Channels channels;

// ==================== Pin assignments ====================
#define DHTPIN   6
#define LUXPIN   7
#define TRIGPIN  5
#define ECHOPIN  4

// VALID OUTPUT PINS
#define LED1_PIN 48
#define LED2_PIN 47

// ===========================================================
// radioReady()
// ===========================================================
bool SensorActuatorModule::radioReady()
{
    if (!router || !nodeDB) return false;

    meshtastic_QueueStatus qs = router->getQueueStatus();
    if (nodeDB->getNodeNum() == 0) return false;
    if (qs.maxlen == 0) return false;

    return true;
}

// ===========================================================
// Constructor
// ===========================================================
SensorActuatorModule::SensorActuatorModule()
    : dht(DHTPIN), lastSend(0)
{
    led1State = false;
    led2State = false;
}

// ===========================================================
// SETUP
// ===========================================================
void SensorActuatorModule::setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("[SensorActuator] setup()");

    // Sensors
    dht.begin();
    pinMode(TRIGPIN, OUTPUT);
    pinMode(ECHOPIN, INPUT);

    // LEDs
    pinMode(LED1_PIN, OUTPUT);
    pinMode(LED2_PIN, OUTPUT);
    digitalWrite(LED1_PIN, LOW);
    digitalWrite(LED2_PIN, LOW);

    Serial.println("[SensorActuator] Node ready (JSON mode).");
}

// ===========================================================
// LOOP
// ===========================================================
void SensorActuatorModule::loop() {
    static bool pskReady = false;

    if (!pskReady && radioReady()) {
        channels.setActiveByIndex(0);
        Serial.println("[SensorActuator] PSK ready.");
        pskReady = true;
    }

    if (pskReady && (millis() - lastSend >= SEND_INTERVAL)) {
        lastSend = millis();
        sendSensorData();
    }
}

// ===========================================================
// SEND SENSOR PAYLOAD
// ===========================================================
void SensorActuatorModule::sendSensorData() {
    if (!radioReady()) return;

    float h = 0, t = 0;
    int lux = analogRead(LUXPIN);

    dht.read(h, t);

    digitalWrite(TRIGPIN, LOW);
    delayMicroseconds(3);
    digitalWrite(TRIGPIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGPIN, LOW);

    long duration = pulseIn(ECHOPIN, HIGH, 30000);
    float distance = duration ? duration * 0.034f / 2.0f : NAN;

    String json = "{";
    json += "\"temp\":" + String(t,1) + ",";
    json += "\"hum\":"  + String(h,1) + ",";
    json += "\"lux\":"  + String(lux) + ",";
    json += "\"dist\":" + String(distance,1);
    json += "}";

    Serial.println("[SensorActuator] Sending sensor data → " + json);

    meshtastic_MeshPacket *p = router->allocForSending();
    if (!p) return;

    strlcpy((char *)p->decoded.payload.bytes, json.c_str(),
            sizeof(p->decoded.payload.bytes));
    p->decoded.payload.size = strlen((char *)p->decoded.payload.bytes);
    p->decoded.portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
    p->to = 0xFFFFFFFF;
    p->channel = 0;

    router->sendLocal(p, RX_SRC_LOCAL);
}

// ===========================================================
// HANDLE INCOMING LED COMMANDS
// ===========================================================
void SensorActuatorModule::handleIncomingPacket(meshtastic_MeshPacket *p) {
    if (!MeshService::isTextPayload(p)) return;

    String msg = String((char *)p->decoded.payload.bytes);
    Serial.println("[SensorActuator] Received: " + msg);
    Serial.println("[SensorActuator] LED handler running...");

    // Reject non-JSON
    if (!(msg.startsWith("{") && msg.endsWith("}"))) {
        Serial.println("[SensorActuator] Ignored non-JSON");
        return;
    }

    // Lowercase for matching
    String lowerMsg = msg;
    lowerMsg.toLowerCase();

    // Avoid loops
    if (lowerMsg.indexOf("feedbackled1") != -1 ||
        lowerMsg.indexOf("feedbackled2") != -1) {
        Serial.println("[SensorActuator] Ignored feedback JSON");
        return;
    }

    bool hasLed1 = lowerMsg.indexOf("\"led1\"") != -1;
    bool hasLed2 = lowerMsg.indexOf("\"led2\"") != -1;

    if (!hasLed1 && !hasLed2) {
        Serial.println("[SensorActuator] Ignored non-LED JSON");
        return;
    }

    // LED1
    if (hasLed1) {
        int pos = lowerMsg.indexOf("\"led1\"");
        led1State = (lowerMsg.indexOf("true", pos) != -1);
        digitalWrite(LED1_PIN, led1State ? HIGH : LOW);
    }

    // LED2
    if (hasLed2) {
        int pos = lowerMsg.indexOf("\"led2\"");
        led2State = (lowerMsg.indexOf("true", pos) != -1);
        digitalWrite(LED2_PIN, led2State ? HIGH : LOW);
    }

    Serial.printf("[SensorActuator] LED1=%d LED2=%d\n", led1State, led2State);

    sendLedStateBack();
}

// ===========================================================
// SEND LED STATE BACK
// ===========================================================
void SensorActuatorModule::sendLedStateBack() {
    if (!radioReady()) return;

    String json = "{";
    json += "\"feedbackled1\":"; json += (led1State ? "true" : "false"); json += ",";
    json += "\"feedbackled2\":"; json += (led2State ? "true" : "false");
    json += "}";

    Serial.println("[SensorActuator] Sending LED feedback → " + json);

    meshtastic_MeshPacket *p = router->allocForSending();
    if (!p) return;

    strlcpy((char *)p->decoded.payload.bytes, json.c_str(),
            sizeof(p->decoded.payload.bytes));
    p->decoded.payload.size = strlen((char *)p->decoded.payload.bytes);
    p->decoded.portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
    p->to = 0xFFFFFFFF;
    p->channel = 0;

    router->sendLocal(p, RX_SRC_LOCAL);
}
