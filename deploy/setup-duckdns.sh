#!/usr/bin/env bash
# =============================================================
# setup-duckdns.sh
# DuckDNS = DNS dinâmico GRÁTIS (https://www.duckdns.org)
# Pra domínio grátis tipo: seunome.duckdns.org
#
# Como usar:
#   1. Vá em https://www.duckdns.org e crie conta (com Google/GitHub)
#   2. Crie um subdomínio (ex: nev2restaurante) -> vira nev2restaurante.duckdns.org
#   3. Copie o TOKEN que aparece no painel
#   4. Rode:  sudo bash deploy/setup-duckdns.sh nev2restaurante SEU_TOKEN
#
# Esse script:
#   - Atualiza o IP do DuckDNS pra apontar pra esse servidor
#   - Instala um cron que atualiza a cada 5 minutos
# =============================================================
set -euo pipefail

if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  err "Uso: sudo bash deploy/setup-duckdns.sh SEU_SUBDOMINIO SEU_TOKEN"
fi

SUBDOMAIN="$1"
TOKEN="$2"
DOMAIN="${SUBDOMAIN}.duckdns.org"

echo "==> Atualizando DuckDNS: $DOMAIN -> $(curl -s ifconfig.me)"
curl -s "https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=" \
  | tee /tmp/duckdns-update.log

echo ""
echo "==> Instalando cron de auto-update a cada 5 minutos..."
SCRIPT_PATH="/usr/local/bin/duckdns-update.sh"

cat > "$SCRIPT_PATH" <<INNER
#!/usr/bin/env bash
curl -s "https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=" > /var/log/duckdns.log 2>&1
INNER
chmod +x "$SCRIPT_PATH"

# Adiciona no crontab (atualiza a cada 5 min)
( crontab -l 2>/dev/null | grep -v duckdns-update.sh ; \
  echo "*/5 * * * * $SCRIPT_PATH" ) | crontab -

cat <<EOF

✅ DuckDNS configurado!

Seu domínio: $DOMAIN
Ele aponta agora pro IP: $(curl -s ifconfig.me)

Teste:
  ping $DOMAIN
  curl -I http://$DOMAIN

Lembre-se: quando você rodar o deploy.sh, use:
  BASE_URL=http://$DOMAIN
  CORS_ORIGINS=["http://$DOMAIN"]

EOF
