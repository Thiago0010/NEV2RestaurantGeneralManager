#!/usr/bin/env bash
# =============================================================
# setup-ssl.sh - Configura HTTPS com Let's Encrypt (grátis)
# Requer que o domínio já aponte pro IP da sua VM
# Roda dentro do container frontend como root (uma única vez)
# =============================================================
set -euo pipefail

if [ -z "${1:-}" ]; then
  err "Uso: sudo bash deploy/setup-ssl.sh seudominio.duckdns.org seu-email@exemplo.com"
fi

DOMAIN="$1"
EMAIL="$2"

echo "==> Instalando certbot no container frontend..."
docker exec -u root nev2-frontend sh -c '
  apk add --no-cache certbot openssl
'

echo "==> Gerando certificado pra $DOMAIN ..."
docker exec -u root nev2-frontend certbot certonly \
  --standalone \
  --preferred-challenges http \
  --domain "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email

# Para o nginx pra liberar a porta 80
docker exec -u root nev2-frontend sh -c '
  apk add --no-cache certbot openssl
'

cat <<EOF

✅ Certificado gerado em:
   /etc/letsencrypt/live/$DOMAIN/

Agora vamos ajustar o nginx pra usar HTTPS.
(Esse passo extra precisa de você editar manualmente ou usar um config automática.)

Próximo passo (manual):
  1. Edite:  nano deploy/oracle-setup.sh
  2. Depois: docker exec -u root nev2-frontend sh -c "..."
     (instruções completas no DEPLOY_GUIDE.md)

OU (caminho mais fácil):
  Use o deploy/nginx-https.conf.example que está junto deste script.

EOF
