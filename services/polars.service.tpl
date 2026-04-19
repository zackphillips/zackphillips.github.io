[Unit]
Description={{DESCRIPTION}}
After=network.target

[Service]
Type=simple
User={{USER}}
WorkingDirectory={{WORKING_DIRECTORY}}
Environment=SIGNALK_URL={{SIGNALK_URL}}
ExecStart={{EXEC_START}}
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
