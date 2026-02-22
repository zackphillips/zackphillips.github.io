[Unit]
Description={{DESCRIPTION}}
After=network.target

[Service]
Type=simple
User={{USER}}
WorkingDirectory={{WORKING_DIRECTORY}}
Environment=GIT_BRANCH={{GIT_BRANCH}}
Environment=GIT_REMOTE={{GIT_REMOTE}}
Environment=GIT_AMEND={{GIT_AMEND}}
Environment=GIT_FORCE_PUSH={{GIT_FORCE_PUSH}}
Environment=SIGNALK_URL={{SIGNALK_URL}}
Environment=OUTPUT_FILE={{OUTPUT_FILE}}
ExecStart={{EXEC_START}}
Restart={{RESTART_POLICY}}
RestartSec={{RESTART_SEC}}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
