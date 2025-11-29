<?php
// Enable full error reporting (development only)
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// ---- DB connection ----
$connectionString = "host=127.0.0.1 dbname=meshtastic user=webapp password=hydro";
$dbconn = pg_connect($connectionString);

if (!$dbconn) {
    die("Database connection failed. Check the Apache/PHP error log for details.");
}

// Meshtastic CLI configuration
$meshtasticCmd = '/home/pi/meshtastic/bin/meshtastic';
$meshtasticPort = '/dev/ttyUSB0';

// --- HANDLE LED FORM SUBMIT (Meshtastic stubbed for now) ------------------
$lastPacketSafe = null;
$lastOutputSafe = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['send_leds'])) {
    $led1 = isset($_POST['led1']);
    $led2 = isset($_POST['led2']);

    $packet = json_encode([
        "led1" => $led1,
        "led2" => $led2
    ]);

    // Invoke Meshtastic CLI to send the JSON packet
    $command = $meshtasticCmd
        . ' --port ' . escapeshellarg($meshtasticPort)
        . ' --sendtext ' . escapeshellarg($packet)
        . ' 2>&1';

    $output = shell_exec($command);

    if ($output === null) {
        $output = 'Meshtastic CLI did not return any output. If this persists, check the Apache error log.';
    }

    $lastPacketSafe = htmlspecialchars($packet, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $lastOutputSafe = htmlspecialchars($output ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// --- LOAD DATA FOR TABLE & CHART -----------------------------------------
$query = "
    SELECT
        time,
        sender,
        recipient,
        portnum,
        temperature,
        humidity,
        led1,
        led2
    FROM messages_temp_humidity_led
    ORDER BY time ASC;
";

$result = pg_query($dbconn, $query);

if (!$result) {
    $queryError = pg_last_error($dbconn);
    die("Query failed: " . htmlspecialchars($queryError, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'));
}

$tableRows = [];
$chartData = [];
$latestRow = null;

while ($row = pg_fetch_assoc($result)) {
    $tableRows[] = $row;
    $latestRow = $row;

    $chartData[] = [
        "time"        => $row["time"],
        "temperature" => is_null($row["temperature"]) ? null : (float)$row["temperature"],
        "humidity"    => is_null($row["humidity"]) ? null : (float)$row["humidity"],
        "led1"        => is_null($row["led1"]) ? null : (($row["led1"] === 't' || $row["led1"] === 'true' || $row["led1"] === 1 || $row["led1"] === '1') ? 1 : 0),
        "led2"        => is_null($row["led2"]) ? null : (($row["led2"] === 't' || $row["led2"] === 'true' || $row["led2"] === 1 || $row["led2"] === '1') ? 1 : 0)
    ];
}

pg_close($dbconn);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meshtastic Temperature / Humidity Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            height: 100%;
            margin: 0;
            font-family: sans-serif;
            background: #f5f5f5; /* Match other pages */
            color: #000;
            overflow: hidden; /* No page scrollbars */
            font-size: 14px; /* tuned for 7" screen at arm's length */
        }

        .page {
            height: 100vh;
            max-height: 100vh;
            display: flex;
            flex-direction: column;
            padding: 8px 12px;
            gap: 6px;
        }

        .header {
            flex: 0 0 auto;
        }

        .header h1 {
            margin: 0;
            font-size: 1rem;
        }

        .main {
            flex: 1 1 auto;
            min-height: 0;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .top-panel,
        .table-panel,
        .controls-panel {
            background: #ffffff;
            border-radius: 6px;
            border: 1px solid #dddddd;
            padding: 6px;
        }

        /* Give the chart more vertical space */
        .top-panel {
            flex: 0 0 45%;
            min-height: 0;
            display: flex;
            flex-direction: column;
        }

        .panel-title {
            font-size: 0.78rem;
            margin-bottom: 4px;
        }

        .chart-container {
            position: relative;
            flex: 1 1 auto;
            min-height: 0;
            overflow-x: auto; /* horizontal scroll for chart */
        }

        .chart-container canvas {
            width: 100%;
            min-width: 1200px; /* force scroll on smaller screens */
            height: 100% !important;
        }

        .bottom-row {
            flex: 1 1 55%;
            min-height: 0;
            display: flex;
            gap: 6px;
        }

        .table-panel {
            flex: 2.8;
            display: flex;
            flex-direction: column;
            min-height: 0;
            min-width: 0; /* allow shrink inside flex */
        }

        /* Shrink LED control area horizontally (about half previous) */
        .controls-panel {
            flex: 0.5;
            min-height: 0;
            min-width: 140px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .table-wrapper {
            flex: 1 1 auto;
            min-height: 0;
            overflow-y: auto;  /* vertical scroll inside table */
            overflow-x: auto;  /* allow horizontal scroll if needed */
            border: 1px solid #dddddd;
            border-radius: 4px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            table-layout: auto; /* let columns size to content/header */
            font-size: 0.75rem;
        }

        thead {
            position: sticky;
            top: 0;
            background: #eeeeee;
            z-index: 1;
        }

        th, td {
            padding: 3px 4px;
            border-bottom: 1px solid #eeeeee;
            text-align: left;
            white-space: nowrap; /* keep columns compact and sized by content */
        }

        tbody tr:nth-child(even) {
            background: #fafafa;
        }

        tbody tr:hover {
            background: #f0f0f0;
        }

        .controls-panel h2 {
            font-size: 0.9rem;
            margin-top: 0;
        }

        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 6px 0;
        }

        .toggle-row span {
            font-size: 0.78rem;
        }

        /* Toggle switch styling */
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 22px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background-color: #bbbbbb;
            transition: .3s;
            border-radius: 22px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 2px;
            bottom: 2px;
            background-color: #ffffff;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: #0a84ff;
        }

        input:checked + .slider:before {
            transform: translateX(22px);
        }

        .send-button {
            width: 100%;
            padding: 8px;
            margin-top: 8px;
            border: none;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: bold;
            cursor: pointer;
            background: linear-gradient(135deg, #0a84ff, #34d1ff);
            color: #fff;
        }

        .send-button:hover {
            filter: brightness(1.05);
        }

        .status-box {
            margin-top: 6px;
            font-size: 0.75rem;
            background: #fafafa;
            border-radius: 4px;
            padding: 6px;
            border: 1px solid #dddddd;
            max-height: 120px;
            overflow-y: auto;
        }

        .status-box pre {
            max-height: 80px;
            overflow-y: auto;
            background: #f0f0f0;
            padding: 4px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
<div class="page">
    <div class="header">
        <h1>Meshtastic Temperature / Humidity Dashboard</h1>
    </div>

    <div class="main">
        <!-- TOP: DUAL-AXIS CHART -->
        <div class="top-panel">
            <div class="panel-title">Temperature &amp; Humidity Over Time</div>
            <div class="chart-container">
                <canvas id="tempHumidityChart"></canvas>
            </div>
        </div>

        <!-- BOTTOM: TABLE + LED CONTROLS -->
        <div class="bottom-row">
            <!-- TABLE PANEL -->
            <div class="table-panel">
                <div class="panel-title">messages_temp_humidity_led</div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                        <tr>
                            <th>Time</th>
                            <th>From</th>
                            <th>To</th>
                            <th>Port</th>
                            <th>Temperature</th>
                            <th>Humidity</th>
                            <th>LED 1</th>
                            <th>LED 2</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php if (!empty($tableRows)): ?>
                            <?php foreach ($tableRows as $row): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($row["time"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php echo htmlspecialchars($row["sender"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php echo htmlspecialchars($row["recipient"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php echo htmlspecialchars($row["portnum"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php echo htmlspecialchars($row["temperature"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php echo htmlspecialchars($row["humidity"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></td>
                                    <td><?php
                                        if ($row["led1"] === 't') {
                                            echo 'On';
                                        } elseif ($row["led1"] === 'f') {
                                            echo 'Off';
                                        } else {
                                            echo '';
                                        }
                                    ?></td>
                                    <td><?php
                                        if ($row["led2"] === 't') {
                                            echo 'On';
                                        } elseif ($row["led2"] === 'f') {
                                            echo 'Off';
                                        } else {
                                            echo '';
                                        }
                                    ?></td>
                                </tr>
                            <?php endforeach; ?>
                        <?php else: ?>
                            <tr>
                                <td colspan="8">No data available.</td>
                            </tr>
                        <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- LED CONTROLS PANEL -->
            <div class="controls-panel">
                <div>
                    <h2>LED Control</h2>

                    <form method="post">
                        <div class="toggle-row">
                            <span>LED 1</span>
                            <label class="switch">
                                <input type="checkbox" name="led1" value="1">
                                <span class="slider"></span>
                            </label>
                        </div>

                        <div class="toggle-row">
                            <span>LED 2</span>
                            <label class="switch">
                                <input type="checkbox" name="led2" value="1">
                                <span class="slider"></span>
                            </label>
                        </div>

                        <button class="send-button" type="submit" name="send_leds">SEND</button>
                    </form>

                    <?php if ($lastPacketSafe !== null): ?>
                        <div class="status-box">
                            <strong>Last packet:</strong><br>
                            <code><?php echo $lastPacketSafe; ?></code>
                            <br><br>
                            <strong>Meshtastic status:</strong>
                            <pre><?php echo $lastOutputSafe; ?></pre>
                        </div>
                    <?php endif; ?>

                    <?php if ($latestRow !== null): ?>
                        <div class="status-box">
                            <strong>Latest received telemetry:</strong><br>
                            <span>
                                <strong>Time:</strong>
                                <?php echo htmlspecialchars($latestRow["time"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?>
                            </span><br>
                            <span>
                                <strong>Temperature:</strong>
                                <?php echo htmlspecialchars($latestRow["temperature"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?> &deg;C
                            </span><br>
                            <span>
                                <strong>Humidity:</strong>
                                <?php echo htmlspecialchars($latestRow["humidity"] ?? "", ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?> %
                            </span><br>
                            <span>
                                <strong>LED 1:</strong>
                                <?php
                                    if ($latestRow["led1"] === 't') {
                                        echo 'On';
                                    } elseif ($latestRow["led1"] === 'f') {
                                        echo 'Off';
                                    } else {
                                        echo '';
                                    }
                                ?>
                            </span><br>
                            <span>
                                <strong>LED 2:</strong>
                                <?php
                                    if ($latestRow["led2"] === 't') {
                                        echo 'On';
                                    } elseif ($latestRow["led2"] === 'f') {
                                        echo 'Off';
                                    } else {
                                        echo '';
                                    }
                                ?>
                            </span>
                        </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// --- JS: BUILD DUAL-AXIS CHART FROM PHP DATA ------------------------------
const phpChartData = <?php echo json_encode($chartData); ?>;

const labels = phpChartData.map(d => d.time);
const tempData = phpChartData.map(d => d.temperature);
const humData  = phpChartData.map(d => d.humidity);

const ctx = document.getElementById('tempHumidityChart').getContext('2d');

if (labels.length > 0) {
    const led1Data = phpChartData.map(d => d.led1);
    const led2Data = phpChartData.map(d => d.led2);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: tempData,
                    yAxisID: 'yTemp',
                    borderWidth: 4,
                    borderColor: 'red',
                    pointRadius: 3,
                    pointHoverRadius: 4
                },
                {
                    label: 'Humidity (%)',
                    data: humData,
                    yAxisID: 'yHum',
                    borderWidth: 4,
                    borderColor: 'green',
                    pointRadius: 3,
                    pointHoverRadius: 4
                },
                {
                    label: 'LED 1',
                    data: led1Data,
                    yAxisID: 'yLed1',
                    borderWidth: 4,
                    borderColor: 'blue',
                    pointRadius: 3,
                    pointHoverRadius: 4,
                    stepped: true
                },
                {
                    label: 'LED 2',
                    data: led2Data,
                    yAxisID: 'yLed2',
                    borderWidth: 4,
                    borderColor: 'magenta',
                    pointRadius: 3,
                    pointHoverRadius: 4,
                    stepped: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                yTemp: {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    }
                },
                yHum: {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Humidity (%)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                yLed1: {
                    type: 'linear',
                    position: 'right',
                    min: 0,
                    max: 1,
                    title: {
                        display: true,
                        text: 'LED 1 (0/1)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                yLed2: {
                    type: 'linear',
                    position: 'right',
                    min: 0,
                    max: 1,
                    title: {
                        display: true,
                        text: 'LED 2 (0/1)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
}
</script>
</body>
</html>
