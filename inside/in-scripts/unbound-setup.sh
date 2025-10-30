setup_unbound() {
  cat <<'EOF' >/etc/systemd/system/roothints.service
[Unit]
Description=Update root hints for unbound
After=network.target

[Service]
ExecStart=/usr/bin/curl -o /etc/unbound/root.hints https://www.internic.net/domain/named.cache
EOF

  cat <<'EOF' >/etc/systemd/system/roothints.timer
[Unit]
Description=Run root.hints monthly

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
EOF
}
