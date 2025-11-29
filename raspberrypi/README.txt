Meshtastic + PostgreSQL + Dashboard Cheat Sheet
==============================================

GENERAL PATHS
-------------
Meshtastic project dir:  /home/pi/meshtastic
JSONL log file:         /home/pi/meshtastic/messages.jsonl
Main DB:                meshtastic
Main Linux user:        pi

-----------------------------------
1) MESHTASTIC VENV & CLI COMMANDS
-----------------------------------

# Activate Meshtastic virtual environment
cd ~/meshtastic
source bin/activate

# Deactivate virtual environment
deactivate

# Meshtastic CLI examples (run with venv active)
meshtastic --info           # Radio info
meshtastic --nodes          # Known nodes
meshtastic --ch             # Channel settings

# If you ever get "Permission denied" on the CLI binary:
# (Only if needed)
chmod +x ~/meshtastic/bin/meshtastic


--------------------------
2) POSTGRESQL QUICK START
--------------------------

# Log into meshtastic DB as postgres superuser
sudo -u postgres psql -d meshtastic

# Log into meshtastic DB as pi (peer auth, recommended for scripts)
sudo -u pi psql -d meshtastic
# or, when logged in as pi:
psql -d meshtastic

# Inside psql:
\l                          -- list databases
\dt                         -- list tables
\dv                         -- list views
\d+ messages_raw            -- describe a table/view
\d+ messages_temp_humidity_led
                            -- schema of main sensor/LED view
SELECT * FROM messages_temp_humidity_led
ORDER BY time DESC LIMIT 20;
                            -- see latest sensor/LED data

\q                          -- quit psql

# Re-run view definitions from a SQL file (e.g., views.sql)
psql -d meshtastic -f /home/pi/meshtastic/views.sql


------------------------------
3) PYTHON SCRIPTS & USE CASES
------------------------------

All scripts assume:
- Linux user: pi
- DB name: meshtastic
- Run from:  ~/meshtastic
- Usually with venv active:  source ~/meshtastic/bin/activate

A) messageLogger.py
   -----------------
   Location:
     /home/pi/meshtastic/messageLogger.py

   Purpose:
   - Connects to Meshtastic radio via SerialInterface
   - Listens for incoming packets in real time
   - For each packet:
       * Appends one JSON object per line to messages.jsonl
       * Inserts the same JSON into PostgreSQL table messages_raw (if DB reachable)

   How to run:
     cd ~/meshtastic
     source bin/activate
     python3 messageLogger.py

   Behavior:
   - Keeps running and printing messages until you press Ctrl+C
   - If DB connection fails, it continues logging to messages.jsonl only


B) import_jsonl_to_db.py
   ----------------------
   Location:
     /home/pi/meshtastic/import_jsonl_to_db.py

   Purpose:
   - OFFLINE sync tool to "flash" the DB
   - Completely overwrites messages_raw with the contents of messages.jsonl
   - Reads each line from /home/pi/meshtastic/messages.jsonl (one JSON object per line)
   - TRUNCATES messages_raw first, then inserts each JSON object into messages_raw.data (jsonb)

   How to run (as pi, locally):
     cd ~/meshtastic
     source bin/activate
     python3 import_jsonl_to_db.py

   IMPORTANT:
   - This WILL wipe messages_raw before reloading from messages.jsonl.
   - Use when you want the DB to exactly match the current JSONL file.


----------------------------------
4) DATABASE TABLES / VIEWS SUMMARY
----------------------------------

Base table:
-----------
messages_raw
- Columns:
    id (serial / primary key)
    ts (timestamp of insertion)
    data (jsonb)  -- Raw message as JSON

- Populated by:
    * messageLogger.py (live logging)
    * import_jsonl_to_db.py (offline reload)


Convenience views:
------------------

messages_clean
- Fields:
    id
    ts
    time       -- data->>'time'
    sender     -- data->>'from'
    recipient  -- data->>'to'
    portnum    -- data->>'portnum'
    raw_message -- data->>'message'
- Use case:
    "Human readable" view of raw messages (no sensor parsing).


messages_temp_humidity
- Fields:
    ts
    time
    sender / recipient / portnum
    temperature (numeric)
    humidity    (numeric)
- Use case:
    Older format where message JSON has:
      { "Temperature": "...", "Humidity": "..." }
    Good for simple temp/humidity history.


messages_temp_humidity_led
- Fields:
    ts
    time
    sender / recipient / portnum
    temperature (numeric)
    humidity    (numeric)
    led1        (boolean)
    led2        (boolean)

- Behavior:
    * Supports BOTH old and new JSON formats:
        Old: { "Temperature": "...", "Humidity": "..." }
        New: {
          "temperature": 23.5,
          "humidity": 45,
          "led1": true,
          "led2": false
        }
    * Temperature & humidity are taken from either the new lowercase keys
      or the old capitalized keys.
    * led1 / led2 only exist in the new format.

- Typical query:
    SELECT time, temperature, humidity, led1, led2
    FROM messages_temp_humidity_led
    ORDER BY time DESC
    LIMIT 50;

- Use case:
    Main view for dashboards/graphs that show both sensor data and LED states.


-----------------------------------
5) QUICK WORKFLOWS / METHODS OF USE
-----------------------------------

A) Normal live operation
   ----------------------
   1) Start Meshtastic venv:
        cd ~/meshtastic
        source bin/activate
   2) Start live logger:
        python3 messageLogger.py
   3) Web dashboards (Apache/PHP) read from views like:
        messages_clean
        messages_temp_humidity_led

B) Recover / rebuild DB from JSONL
   --------------------------------
   1) Ensure messages.jsonl has the data you want
   2) (Optional) stop any running logger first
   3) Rebuild DB:
        cd ~/meshtastic
        source bin/activate
        python3 import_jsonl_to_db.py
   4) Verify in psql:
        sudo -u pi psql -d meshtastic
        SELECT COUNT(*) FROM messages_raw;
        SELECT * FROM messages_temp_humidity_led ORDER BY time DESC LIMIT 10;

C) Quick DB check
   ---------------
   # As postgres:
   sudo -u postgres psql -d meshtastic

   # Or as pi:
   sudo -u pi psql -d meshtastic

   Then:
   \dt
   \dv
   SELECT * FROM messages_clean ORDER BY time DESC LIMIT 5;
   SELECT * FROM messages_temp_humidity_led ORDER BY time DESC LIMIT 5;

   \q
