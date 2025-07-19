# Setup

## Set up systemd timer (preferred over cron for robustness):
Unit file: `/etc/systemd/system/signalk-gitpush.service`

```
[Unit]
Description=Push SignalK JSON snapshot to git

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /path/to/push_signalk_blob.py
WorkingDirectory=/path/to/git/repo
```

Timer file: `/etc/systemd/system/signalk-gitpush.timer`

```ini
[Unit]
Description=Run SignalK git push every 1 min

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=10s

[Install]
WantedBy=timers.target
```

## Enable + Start

```bash
sudo systemctl daemon-reexec
sudo systemctl enable --now signalk-gitpush.timer
```

## Check systemd timer + service status
```bash
systemctl list-timers --all | grep signalk-gitpush
``
This shows next/last run times.

To see if it ran successfully:

```bash
journalctl -u signalk-gitpush.service --since "10 minutes ago"
```