<?php
// Simple viewer for the messages_temp_humidity view

// ---- DB connection ----
$connectionString = "host=127.0.0.1 dbname=meshtastic user=webapp password=hydro";
$dbconn = pg_connect($connectionString);

if (!$dbconn) {
    die("Database connection failed: " . pg_last_error());
}

// Get latest rows from the view
$query = "SELECT * FROM messages_temp_humidity ORDER BY ts DESC LIMIT 200;";
$result = pg_query($dbconn, $query);

if (!$result) {
    die("Query failed: " . pg_last_error($dbconn));
}

// ---- Output HTML ----
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meshtastic Temperature &amp; Humidity</title>
    <style>
        body {
            font-family: sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        h1 {
            margin-bottom: 10px;
        }
        p {
            margin-top: 0;
            margin-bottom: 15px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            background: #fff;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 4px 8px;
            font-size: 0.9rem;
        }
        th {
            background: #eee;
        }
        tr:nth-child(even) {
            background: #f9f9f9;
        }
        .timestamp-col {
            white-space: nowrap;
        }
        a {
            color: #0077cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>messages_temp_humidity</h1>
    <p>
        Showing latest 200 rows from the view (Temperature &amp; Humidity parsed from the
        <code>message</code> field).
        &nbsp;|&nbsp;
        <a href="index.php">Back to messages_clean</a>
    </p>

    <table>
        <thead>
            <tr>
                <?php
                $numFields = pg_num_fields($result);
                for ($i = 0; $i < $numFields; $i++) {
                    $fieldName = pg_field_name($result, $i);
                    echo "<th>" . htmlspecialchars($fieldName) . "</th>";
                }
                ?>
            </tr>
        </thead>
        <tbody>
            <?php
            while ($row = pg_fetch_assoc($result)) {
                echo "<tr>";
                foreach ($row as $colName => $value) {
                    $class = ($colName === 'ts' || $colName === 'received_at') ? 'timestamp-col' : '';
                    echo "<td class=\"{$class}\">" . htmlspecialchars((string)$value) . "</td>";
                }
                echo "</tr>";
            }
            ?>
        </tbody>
    </table>
</body>
</html>
<?php
pg_free_result($result);
pg_close($dbconn);
