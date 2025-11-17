<?php
// messages_temp_humidity.php

// ---- SHOW ERRORS (for debugging) ----
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// ---- DB CONFIG ----
$host   = "localhost";
$dbname = "meshtastic";
$user   = "pi";
$pass   = "hydro";   // your DB password for user pi

$conn_str = "host=$host dbname=$dbname user=$user password=$pass";

$db = pg_connect($conn_str);
if (!$db) {
    die("Database connection error: " . pg_last_error());
}

// ---- QUERY ----
$query = "
    SELECT id, ts, time, sender, recipient, portnum, raw_message
    FROM messages_clean
    ORDER BY ts DESC
    LIMIT 500;
";

$result = pg_query($db, $query);
if (!$result) {
    die("Query error: " . pg_last_error($db));
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meshtastic Messages – Temp/Humidity View</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #111;
            color: #eee;
            margin: 0;
            padding: 0;
        }
        header {
            background: #222;
            padding: 16px;
            border-bottom: 1px solid #333;
        }
        header h1 {
            margin: 0;
            font-size: 24px;
        }
        header p {
            margin: 4px 0 0 0;
            font-size: 12px;
            color: #aaa;
        }
        main {
            padding: 16px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            font-size: 12px;
        }
        thead {
            background: #1c1c1c;
        }
        th, td {
            border: 1px solid #333;
            padding: 6px 8px;
            text-align: left;
            vertical-align: top;
        }
        tr:nth-child(even) {
            background: #181818;
        }
        tr:nth-child(odd) {
            background: #101010;
        }
        th {
            position: sticky;
            top: 0;
            z-index: 2;
        }
        .mono {
            font-family: "Courier New", monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
<header>
    <h1>Meshtastic Messages – Temp/Humidity</h1>
    <p>Showing latest rows from PostgreSQL view <code>messages_clean</code></p>
</header>
<main>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>DB Time (ts)</th>
