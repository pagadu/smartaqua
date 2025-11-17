<?php
// Connect to PostgreSQL – same creds you used in index.php
$conn = pg_connect("host=localhost dbname=meshtastic user=webapp password=hydro");
if (!$conn) {
    die("Error: Unable to connect to database.");
}

// Query the view we just made
$sql = "
    SELECT
        ts,
        time,
        sender,
        recipient,
        portnum,
        temperature,
        humidity
    FROM messages_temp_humidity
    ORDER BY time DESC;
";
$result = pg_query($conn, $sql);
if (!$result) {
    die("Error running query: " . pg_last_error($conn));
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meshtastic – Temperature & Humidity</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #111;
            color: #eee;
            margin: 0;
            padding: 0;
        }

        h1 {
            text-align: center;
            padding: 20px 0;
            margin: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto 40px auto;
            padding: 0 10px 40px 10px;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 10px;
        }

        th, td {
            border: 1px solid #444;
            padding: 6px 10px;
            text-align: left;
            font-size: 0.9rem;
        }

        th {
            background-color: #222;
        }

        tr:nth-child(even) {
            background-color: #1a1a1a;
        }

        tr:nth-child(odd) {
            background-color: #151515;
        }

        .subtitle {
            text-align: center;
            margin-top: -10px;
            margin-bottom: 10px;
            color: #aaa;
            font-size: 0.9rem;
        }

        a {
            color: #7fb9ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>Meshtastic – Temperature &amp; Humidity</h1>
    <div class="subtitle">
        Parsed from JSON inside the <code>message</code> field (non-JSON messages show NULL).
        &nbsp;|&nbsp; <a href="index.php">Back to main view</a>
    </div>

    <div class="container">
        <table>
            <thead>
                <tr>
                    <th>ts (DB)</th>
                    <th>time (packet)</th>
                    <th>sender</th>
                    <th>recipient</th>
                    <th>portnum</th>
                    <th>temperature</th>
                    <th>humidity</th>
                </tr>
            </thead>
            <tbody>
                <?php while ($row = pg_fetch_assoc($result)): ?>
                    <tr>
                        <td><?php echo htmlspecialchars($row['ts']); ?></td>
                        <td><?php echo htmlspecialchars($row['time']); ?></td>
                        <td><?php echo htmlspecialchars($row['sender']); ?></td>
                        <td><?php echo htmlspecialchars($row['recipient']); ?></td>
                        <td><?php echo htmlspecialchars($row['portnum']); ?></td>
                        <td><?php echo htmlspecialchars($row['temperature']); ?></td>
                        <td><?php echo htmlspecialchars($row['humidity']); ?></td>
                    </tr>
                <?php endwhile; ?>
            </tbody>
        </table>
    </div>
</body>
</html>
<?php
pg_free_result($result);
pg_close($conn);
?>
