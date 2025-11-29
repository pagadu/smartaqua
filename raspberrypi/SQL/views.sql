CREATE OR REPLACE VIEW messages_clean AS
SELECT
    id,
    ts,
    data->>'time'      AS time,
    data->>'from'      AS sender,
    data->>'to'        AS recipient,
    data->>'portnum'   AS portnum,
    data->>'message'   AS raw_message
FROM messages_raw;

CREATE VIEW messages_temp_humidity AS
SELECT
    ts,
    (data->>'time')::timestamptz AS time,
    data->>'from'                 AS sender,
    data->>'to'                   AS recipient,
    data->>'portnum'              AS portnum,

    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
        THEN ((data->>'message')::jsonb ->> 'Temperature')::numeric
        ELSE NULL
    END AS temperature,

    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
        THEN ((data->>'message')::jsonb ->> 'Humidity')::numeric
        ELSE NULL
    END AS humidity

FROM messages_raw;

CREATE OR REPLACE VIEW messages_temp_humidity_led AS
SELECT
    ts,
    (data->>'time')::timestamptz AS time,
    data->>'from'                 AS sender,
    data->>'to'                   AS recipient,
    data->>'portnum'              AS portnum,

    -- Temperature: supports both new `temperature` and old `Temperature`
    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
        THEN COALESCE(
                 ((data->>'message')::jsonb ->> 'temperature')::numeric,
                 ((data->>'message')::jsonb ->> 'Temperature')::numeric
             )
        ELSE NULL
    END AS temperature,

    -- Humidity: supports both new `humidity` and old `Humidity`
    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
        THEN COALESCE(
                 ((data->>'message')::jsonb ->> 'humidity')::numeric,
                 ((data->>'message')::jsonb ->> 'Humidity')::numeric
             )
        ELSE NULL
    END AS humidity,

    -- LED1 (only present in the new format)
    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
             AND ((data->>'message')::jsonb ? 'led1')
        THEN ((data->>'message')::jsonb ->> 'led1')::boolean
        ELSE NULL
    END AS led1,

    -- LED2 (only present in the new format)
    CASE
        WHEN data->>'message' IS NOT NULL
             AND data->>'message' ~ '^\s*\{.*\}\s*$'
             AND ((data->>'message')::jsonb ? 'led2')
        THEN ((data->>'message')::jsonb ->> 'led2')::boolean
        ELSE NULL
    END AS led2

FROM messages_raw;
