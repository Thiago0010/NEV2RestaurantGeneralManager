#!/usr/bin/env bash
# =============================================================
# deploy.sh - Sobe/atualiza o sistema na VM Oracle Cloud
# Rodar como usuário 'deploy' de dentro da pasta do projeto
#   bash deploy.sh            -> primeiro deploy
#   bash deploy.sh --update   -> atualizar código
# =============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# Cores pro terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[X]${NC} $1"; exit 1; }

# ---------------- Validações iniciais ----------------
[ -f .env.production ] || err ".env.production não encontrado. Copie de .env.production.example e preencha."

# Checa se SECRET_KEY ainda é o default
if grep -q "TROQUE_POR" .env.production; then
  err "Você esqueceu de trocar variáveis no .env.production (procura por TROQUE_POR)."
fi

# Garante que existe .env.production no backend também (lido pelo backend se preciso)
if [ ! -f backend/.env ]; then
  log "Criando backend/.env a partir do .env.production..."
  cp .env.production backend/.env
fi

# ---------------- Carga das variáveis ----------------
set -a
# shellcheck disable=SC1091
source .env.production
set +a

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

MODE="${1:-first}"

if [ "$MODE" = "--update" ]; then
  log "==> Modo UPDATE: baixando código novo..."
  git pull origin main || warn "git pull falhou (talvez não seja um repo git, tudo bem)"
fi

log "==> [1/4] Limpando containers/parados..."
docker compose -f docker-compose.prod.yml down --remove-orphans || true

log "==> [2/4] Construindo imagens (pode demorar uns minutos)..."
docker compose -f docker-compose.prod.yml build --no-cache

log "==> [3/4] Subindo os serviços..."
docker compose -f docker-compose.prod.yml up -d

log "==> [4/4] Aguardando Postgres ficar saudável..."
for i in {1..30}; do
  if docker exec nev2-postgres pg_isready -U "${POSTGRES_USER:-nev2_admin}" >/dev/null 2>&1; then
    log "   Postgres OK."
    break
  fi
  echo "   esperando... ($i/30)"
  sleep 2
done

log "==> Rodando migrations do Alembic..."
docker exec nev2-backend alembic upgrade head || warn "Migrations falharam (verifique logs)"

log "==> Verificando se backend está respondendo..."
sleep 5
if docker exec nev2-backend curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1 || \
   docker exec nev2-backend curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
  log "   Backend OK!"
else
  warn "   Backend ainda inicializando. Verifique: docker logs nev2-backend"
fi

cat <<EOF

=============================================================
  ✅  Deploy concluído!
=============================================================
Serviços rodando:
EOF
docker compose -f docker-compose.prod.yml ps

cat <<EOF

URLs:
  Frontend: ${BASE_URL}/
  API:      ${BASE_URL}/api/v1/
  Docs:     ${BASE_URL}/api/v1/docs

Comandos úteis:
  Ver logs:        docker compose -f docker-compose.prod.yml logs -f
  Reiniciar:       docker compose -f docker-compose.prod.yml restart
  Parar tudo:      docker compose -f docker-compose.prod.yml down
  Atualizar:       bash deploy/deploy.sh --update

=============================================================
EOF
