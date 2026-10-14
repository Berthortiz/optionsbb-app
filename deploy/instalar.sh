#!/usr/bin/env bash
# Uso (en el servidor Ubuntu, como usuario normal con sudo):  bash instalar.sh
set -e
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip unzip debian-keyring debian-archive-keyring apt-transport-https curl gpg
# Caddy (HTTPS automático)
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -y && sudo apt-get install -y caddy
# Usuario y carpetas
id optionsbb >/dev/null 2>&1 || sudo useradd -r -m -s /usr/sbin/nologin optionsbb
sudo mkdir -p /opt/optionsbb /var/lib/optionsbb
sudo unzip -o ~/optionsbb_v3.0.zip -d /opt/optionsbb >/dev/null
# si el zip trae una carpeta interna, subirla un nivel
if [ -d /opt/optionsbb/optionsbb ]; then sudo cp -a /opt/optionsbb/optionsbb/. /opt/optionsbb/ && sudo rm -rf /opt/optionsbb/optionsbb; fi
sudo pip3 install --break-system-packages openpyxl tzdata || true
sudo cp /opt/optionsbb/deploy/optionsbb.env.example /etc/optionsbb.env
sudo chmod 600 /etc/optionsbb.env
sudo cp /opt/optionsbb/deploy/optionsbb.service /etc/systemd/system/
sudo cp /opt/optionsbb/deploy/Caddyfile /etc/caddy/Caddyfile
sudo chown -R optionsbb:optionsbb /opt/optionsbb /var/lib/optionsbb
sudo systemctl daemon-reload
sudo systemctl enable --now optionsbb
sudo systemctl restart caddy
echo "LISTO. Crea el administrador con:"
echo "  sudo -u optionsbb bash -c 'set -a; . /etc/optionsbb.env; python3 /opt/optionsbb/server.py create-admin'"
