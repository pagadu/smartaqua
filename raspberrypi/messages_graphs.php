<?php
// Show PHP errors in browser
error_reporting(E_ALL);
ini_set('display_errors', 1);

// ----- DB CONNECTION (as user pi) -----
$conn = pg_connect("host=localhost port=5432 dbname=meshtastic user=pi password=hydro");

if (!$conn) {
    die("DB connection failed: " . pg_last_error());
}

// ----- QUERY THE VIEW -----
$sql = "SELECT time, temperature, humidity 
        FROM messages_temp_humidity 
        ORDER BY time ASC";

$result = pg_query($conn, $sql);

if (!$result) {
    die("Query failed: " . pg_last_error($conn));
}

$timestamps   = [];
$temperatures = [];
$humidities   = [];

while ($row = pg_fetch_assoc($result)) {
    $timestamps[]   = $row['time'];
    $temperatures[] = is_null($row['temperature']) ? null : (float)$row['temperature'];
    $humidities[]   = is_null($row['humidity']) ? null : (float)$row['humidity'];
}

pg_close($conn);
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Temperature & Humidity Graphs</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

<h2>Temperature Over Time</h2>
<canvas id="tempChart"></canvas>

<h2>Humidity Over Time</h2>
<canvas id="humidityChart"></canvas>

<script>
const timestamps   = <?php echo json_encode($timestamps); ?>;
const temperatures = <?php echo json_encode($temperatures); ?>;
const humidities   = <?php echo json_encode($humidities); ?>;

// Temperature graph
new Chart(document.getElementById('tempChart'), {
    type: 'line',
    data: {
        labels: timestamps,
        datasets: [{
            label: 'Temperature',
            data: temperatures,
            borderWidth: 2,
            fill: false
        }]
    }
});

// Humidity graph
new Chart(document.getElementById('humidityChart'), {
    type: 'line',
    data: {
        labels: timestamps,
        datasets: [{
            label: 'Humidity',
            data: humidities,
            borderWidth: 2,
            fill: false
        }]
    }
});
</script>

</body>
</html>
