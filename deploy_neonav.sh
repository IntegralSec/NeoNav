#!/bin/bash

set -e

# --- CONFIGURATION ---
REPO_URL="https://github.com/IntegralSec/NeoNav.git"
APP_DIR="/opt/NeoNav"
SERVICE_NAME="neonav"
USER_NAME="neonav"
PYTHON_BIN="python3"

echo "=== Creating user $USER_NAME (if needed) ==="
if ! id "$USER_NAME" &>/dev/null; then
    sudo useradd -r -s /bin/false "$USER_NAME"
    echo "User $USER_NAME created."
else
    echo "User $USER_NAME already exists."
fi

echo "=== Adding $USER_NAME to dialout and video groups ==="
sudo usermod -aG dialout,video "$USER_NAME"

echo "=== Installing Flask via apt ==="
sudo apt update
sudo apt install -y python3-flask

echo "=== Cloning repository ==="
if [ -d "$APP_DIR" ]; then
    sudo rm -rf "$APP_DIR"
fi
sudo git clone "$REPO_URL" "$APP_DIR"
sudo chown -R "$USER_NAME":"$USER_NAME" "$APP_DIR"

echo "=== Creating systemd service ==="
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=NeoNav Flask App (direct Python run)
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_BIN main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "=== Reloading systemd ==="
sudo systemctl daemon-reload

echo "=== Enabling and starting $SERVICE_NAME ==="
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "=== Checking service status ==="
sudo systemctl status "$SERVICE_NAME" --no-pager

echo "✅ Deployment complete!"
echo "⚠️ Please reboot the system to apply group changes:"
echo "   sudo reboot"
