#!/usr/bin/env bash
# =============================================================
# oracle-setup.sh
# Script pra rodar DENTRO da VM da Oracle Cloud (Ubuntu 22.04)
# Prepara o servidor: instala Docker, configura firewall, swap.
# Rodar como root:  sudo bash oracle-setup.sh
# =============================================================
set -euo pipefail

echo "==> [1/6] Atualizando sistema..."
apt-get update -y
apt-get upgrade -y
apt-get install -y curl wget git ufw ca-certificates gnupg lsb-release

echo "==> [2/6] Criando swap de 2GB (essencial em VM de 1GB RAM)..."
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "   Swap criado e ativado."
else
  echo "   Swap já existe, pulando."
fi

echo "==> [3/6] Instalando Docker..."
if ! command -v docker &> /dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  echo "   Docker instalado."
else
  echo "   Docker já instalado."
fi

echo "==> [4/6] Configurando firewall (UFW)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
# SSH
ufw allow 22/tcp
# HTTP / HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
# IMPORTANTE: NÃO abre 5432, 6379, 8000 pro mundo (só nginx fala com backend)
ufw --force enable
echo "   Firewall configurado."

echo "==> [5/6] Criando usuário 'deploy' pra gerenciar o app..."
if ! id -u deploy &> /dev/null; then
  useradd -m -s /bin/bash deploy
  usermod -aG docker deploy
  echo "   Usuário deploy criado e adicionado ao grupo docker."
else
  echo "   Usuário deploy já existe."
fi

echo "==> [6/6] Ajustes finais do SO..."
# Otimização de memória pro Postgres
echo "vm.swappiness=10" >> /etc/sysctl.conf
sysctl -p
echo "   Pronto!"

cat <<EOF

=============================================================
  ✅  VM da Oracle Cloud pronta pra deploy!
=============================================================
Próximos passos:

  1. Logue como deploy:        su - deploy
  2. Vá pra pasta do app:     mkdir -p ~/app && cd ~/app
  3. Copie/clone seu projeto pra lá
  4. Copie o .env.production.example pra .env.production
        cp .env.production.example .env.production
        nano .env.production
     (preencha SECRET_KEY e POSTGRES_PASSWORD com senhas fortes)
  5. Rode o deploy.sh:
        bash deploy.sh

  IMPORTANTE: libere a porta 80/443 na Oracle Cloud Console:
     Networking → Virtual Cloud Networks → sua VCN →
     Subnet → Security Lists → Add Ingress Rules:
       - 0.0.0.0/0  TCP  80
       - 0.0.0.0/0  TCP  443
     (a porta 22 já vem liberada por padrão)

EOF
