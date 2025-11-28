/******************************************************************************
 *  Author:  Alexander Pagaduan
 *  Date:    November 27, 2025
 *
 *  Project: Senior Design – Smart Aquaponics Sensor/Actuator System
 *
 *  Intellectual Property Notice:
 *  ---------------------------------------------------------------------------
 *  This file contains original software and design contributions developed by
 *  Alexander Pagaduan, including:
 *    - SensorActuator module architecture
 *    - JSON command/feedback protocol
 *    - LED control logic
 *    - Sensor integration (DHT, ultrasonic, LUX)
 *    - Packet-handling and routing behavior
 *    - Hardware/software coordination logic
 *
 *  COPYRIGHT & OWNERSHIP:
 *  This work is protected under U.S. Copyright Law.
 *  All rights are retained by the author, Alexander Pagaduan.
 *
 *  PERMISSION REQUIRED:
 *  This work may NOT be used, copied, modified, shared, or integrated into any
 *  project without my explicit written permission.
 *
 *  LIMITED LICENSE — SSU SENIOR DESIGN ONLY:
 *  If permission is granted in writing, it applies exclusively to the:
 *
 *        “Smart Aquaponics Monitoring & Actuation System”
 *        Team Members: Huy Nguyen, Marcus Serrano
 *        Faculty Advisor: Dr. Farid Farahmand
 *
 *  CREDIT REQUIREMENT:
 *  If permission is granted to use or integrate this work, full authorship
 *  credit MUST be given to Alexander Pagaduan in all documentation, reports,
 *  presentations, and submitted materials.
 *
 *  PROJECT STATUS CLAUSE:
 *  Because this code is actively maintained by me, permission to use or
 *  modify it is tied to my participation on the project. If I am removed,
 *  excluded, or unable to continue in the team for any reason, all permissions are immediately revoked.
 *  The team may not continue using any portion of this work without renewed
 *  written permission.
 *
 *  UNIVERSITY USE:
 *  Sonoma State University may review this work for grading purposes only.
 *  No reuse in future classes, labs, or instructional materials is permitted
 *  without my explicit written consent.
 *
 *  GENERAL RESTRICTIONS:
 *    - Not to be reused in other SSU or external projects
 *    - Not for redistribution or adaptation without permission
 *    - Not to be presented as someone else’s work
 *    - Not for departmental or instructional reuse
 *
 *  All rights reserved.
 *  © 2025 Alexander Pagaduan
 ******************************************************************************/

#pragma once

#include "Arduino.h"
#include "MeshService.h"
#include "MeshRadio.h"
#include "Router.h"
#include "NodeDB.h"
#include "modules/SensorActuator/DHT11.h"

class SensorActuatorModule {
public:
    SensorActuatorModule();
    void setup();
    void loop();
    void sendSensorData();
    void handleIncomingPacket(meshtastic_MeshPacket *p);

    // ✨ ADD THIS FUNCTION — required by your .cpp
    void sendLedStateBack();

private:
    // ===== Sensors =====
    DHT11 dht;
    unsigned long lastSend;
    static constexpr unsigned long SEND_INTERVAL = 30000; // 30s

    // ===== LED State =====
    bool led1State = false;
    bool led2State = false;

    // ===== Helper Functions =====
    bool radioReady();
    void applyLedState();
    void parseJsonCommand(const String &msg);
    void sendLedFeedback();
    void sendJson(const String &payload);
};
