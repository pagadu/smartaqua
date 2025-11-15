//h
#pragma once

#include <Arduino.h>
#include "MeshService.h"
#include "MeshRadio.h"
#include "MeshRouter.h"
#include "NodeDB.h"
#include "DHT11.h"

//extra hs

#include "configuration.h"
#if !MESHTASTIC_EXCLUDE_GPS
#include "GPS.h"
#endif
#include "PowerFSM.h"
#include "PowerMon.h"
#include "ReliableRouter.h"
#include "airtime.h"
#include "buzz.h"

#include "FSCommon.h"
#include "Led.h"
#include "RTC.h"
#include "SPILock.h"
#include "Throttle.h"
#include "concurrency/OSThread.h"
#include "concurrency/Periodic.h"
#include "detect/ScanI2C.h"
#include "error.h"
#include "power.h"

#if !MESHTASTIC_EXCLUDE_I2C
#include "detect/ScanI2CConsumer.h"
#include "detect/ScanI2CTwoWire.h"
#include <Wire.h>
#endif
#include "detect/einkScan.h"
#include "graphics/RAKled.h"
#include "graphics/Screen.h"
#include "main.h"
#include "mesh/generated/meshtastic/config.pb.h"
#include "meshUtils.h"
#include "modules/Modules.h"
#include "sleep.h"
#include "target_specific.h"
#include <memory>
#include <utility>

// Main class that handles reading sensors (on the SENSOR node)
// and handling incoming packets + LED output (on the ACTUATOR node)
class SensorActuatorModule
{
public:
    SensorActuatorModule();
    void setup();
    void loop();

#if defined(SENSOR_NODE)
    // Sends JSON sensor data over LoRa/Mesh
    void sendSensorData();
#endif

#if defined(ACTUATOR_NODE)
    // Handles an incoming mesh packet and triggers LED blink
    void handleIncoming(meshtastic_MeshPacket *p);
#endif

private:
    DHT11 dht;                        // DHT11 sensor instance
    unsigned long lastSend;           // Timestamp of last sensor transmission
    static constexpr unsigned long SEND_INTERVAL = 30000; // 30 sec interval
};


//cpp


#include "SensorActuatorModule.h"
#include "Channels.h"
#include "configuration.h"

// External objects from firmware
extern MeshService *service;
extern Router *router;
extern NodeDB *nodeDB;
extern const RegionInfo *myRegion;
extern Channels channels;

#define DHTPIN   6
#define LUXPIN   7
#define TRIGPIN  5
#define ECHOPIN  4
#define LED_TEMP 7

static bool radioReady()
{
    if (!router || !nodeDB) return false;
    meshtastic_QueueStatus qs = router->getQueueStatus();
    return (nodeDB->getNodeNum() != 0 && qs.maxlen != 0);
}

SensorActuatorModule::SensorActuatorModule()
    : dht(DHTPIN), lastSend(0)
{
}

void SensorActuatorModule::setup()
{
    Serial.begin(115200);
    delay(1200);

#if defined(SENSOR_NODE)
    dht.begin();
    pinMode(TRIGPIN, OUTPUT);
    pinMode(ECHOPIN, INPUT);

#elif defined(ACTUATOR_NODE)
    pinMode(LED_TEMP, OUTPUT);
    digitalWrite(LED_TEMP, LOW);
#endif
}

void SensorActuatorModule::loop()
{
    static bool chReady = false;

    if (!chReady && radioReady()) {
        channels.setActiveByIndex(0);
        chReady = true;
    }

#if defined(SENSOR_NODE)
    if (millis() - lastSend >= SEND_INTERVAL) {
        lastSend = millis();
        sendSensorData();
    }
#endif
}

#if defined(SENSOR_NODE)
void SensorActuatorModule::sendSensorData()
{
    if (!radioReady()) return;

    float h = 0, t = 0;
    int lux = analogRead(LUXPIN);

    dht.read(h, t);

    digitalWrite(TRIGPIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGPIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGPIN, LOW);

    long dur = pulseIn(ECHOPIN, HIGH, 30000);
    float dist = (dur == 0 ? -1 : (dur * 0.034f / 2.0f));

    String json = "{";
    json += "\"temp\":\"" + String(t, 1) + "\",";
    json += "\"humidity\":\"" + String(h, 1) + "\",";
    json += "\"lux\":\"" + String(lux) + "\",";
    json += "\"distance\":\"" + String(dist, 1) + "\"";
    json += "}";

    Serial.println("[SensorActuator] Sending → " + json);

    meshtastic_MeshPacket *p = router->allocForSending();
    if (!p) return;

    strlcpy((char *)p->decoded.payload.bytes, json.c_str(),
            sizeof(p->decoded.payload.bytes));

    p->decoded.payload.size = strlen((char *)p->decoded.payload.data);
    p->decoded.portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
    p->to = 0xFFFFFFFF;
    p->channel = 0;
    p->pki_encrypted = false;
    p->want_ack = false;
    if (p->hop_limit == 0) p->hop_limit = 3;

    router->sendLocal(p, RX_SRC_LOCAL);
}
#endif

#if defined(ACTUATOR_NODE)
void SensorActuatorModule::handleIncoming(meshtastic_MeshPacket *p)
{
    if (!MeshService::isTextPayload(p)) return;

    String msg = String((char *)p->decoded.payload.data);
    Serial.println("[SensorActuator] Received → " + msg);

    bool isSensorMsg =
        msg.indexOf("\"temp\"")     != -1 ||
        msg.indexOf("\"humidity\"") != -1 ||
        msg.indexOf("\"lux\"")      != -1 ||
        msg.indexOf("\"distance\"") != -1;

    if (isSensorMsg) {
        digitalWrite(LED_TEMP, HIGH);
        delay(250);
        digitalWrite(LED_TEMP, LOW);
    }
}
#endif


