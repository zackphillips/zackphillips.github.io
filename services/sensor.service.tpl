[Unit]
Description={{DESCRIPTION}}
After=network.target

[Service]
Type=simple
User={{USER}}
WorkingDirectory={{WORKING_DIRECTORY}}
ExecStart={{EXEC_START}}
Restart={{RESTART_POLICY}}
RestartSec={{RESTART_SEC}}
Environment=SENSOR_HOST={{SENSOR_HOST}}
Environment=SENSOR_PORT={{SENSOR_PORT}}

[Install]
WantedBy=multi-user.target
