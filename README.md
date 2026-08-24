# [NEV]2 Restaurant Management System

Sistema completo de gerenciamento para restaurantes com backend Python (FastAPI) e frontend React.

## Arquitetura

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy 2.0 + PostgreSQL + Redis
- **Frontend**: React 18 + Vite + Tailwind CSS + Radix UI
- **Real-time**: WebSockets para atualizações em tempo real (pedidos, mesas, chamados)
- **Autenticação**: JWT com refresh tokens
- **QR Codes**: Geração automática para mesas

## Pré-requisitos

- Docker e Docker Compose
- Node.js 20+ (para desenvolvimento local do frontend)
- Python 3.11+ (para desenvolvimento local do backend)

## Início Rápido com Docker Compose

```bash
# Clone o repositório
cd Restaurant-NEV2-MANAGER

# Copie os arquivos de ambiente
cp backend/.env.example backend/.env
cp .env.example .env

# Edite o SECRET_KEY no backend/.env para produção!

# Suba todos os serviços
docker-compose up -d
```

Acesse:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Docs da API: http://localhost:8000/docs

## Desenvolvimento Local

### Backend

```bash
cd backend

# Crie um virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Configure o banco (precisa do PostgreSQL rodando)
cp .env.example .env
# Edite .env com suas credenciais

# Rode as migrações
alembic upgrade head

# Inicie o servidor
uvicorn app.main:app --reload
```

### Frontend

```bash
# Na raiz do projeto
npm install
npm run dev
```

## Estrutura do Projeto

```
Restaurant-NEV2-MANAGER/
├── backend/                 # Backend Python/FastAPI
│   ├── app/
│   │   ├── api/v1/         # Endpoints da API
│   │   ├── core/           # Config, database, security
│   │   ├── models/         # Models SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilitários
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── src/                     # Frontend React
│   ├── api/                # API client
│   ├── components/         # Componentes UI
│   ├── pages/              # Páginas
│   ├── lib/                # Contextos, utils
│   └── hooks/
├── docker-compose.yml
└── README.md
```

## Entidades Principais

- **Restaurant**: Estabelecimento (multi-tenant)
- **User**: Usuários (owner, manager, waiter, kitchen)
- **Category/Produto**: Cardápio
- **Table**: Mesas com QR Codes
- **Order/OrderItem**: Pedidos e itens
- **Employee**: Funcionários
- **ServiceCall**: Chamados de garçom/conta/ajuda

## Funcionalidades

✅ Autenticação JWT (login, registro, staff)
✅ Multi-tenant (isolamento por restaurante)
✅ Gerenciamento de mesas com QR Codes
✅ Cardápio (categorias, produtos, destaque)
✅ Pedidos em tempo real (WebSocket)
✅ Cozinha (status: recebido → preparando → pronto → entregue)
✅ Garçom (abrir mesa, adicionar itens, fechar conta)
✅ Cliente (cardápio via QR, acompanhar pedido, chamar garçom)
✅ Relatórios de vendas
✅ Configurações do estabelecimento

## API Endpoints Principais

```
POST   /api/v1/auth/register          # Registrar owner + restaurante
POST   /api/v1/auth/login             # Login
GET    /api/v1/auth/me                # Usuário atual
PUT    /api/v1/auth/me                # Atualizar perfil (restaurant_id, role)

GET    /api/v1/restaurant/me          # Meu restaurante
PUT    /api/v1/restaurant/me          # Atualizar restaurante
GET    /api/v1/restaurant/public/{slug}  # Público (para QR)

GET    /api/v1/categories             # Listar categorias
POST   /api/v1/categories             # Criar categoria
PUT    /api/v1/categories/{id}        # Atualizar
DELETE /api/v1/categories/{id}        # Deletar

GET    /api/v1/products               # Listar produtos
POST   /api/v1/products               # Criar produto
PATCH  /api/v1/products/{id}/toggle/available  # Toggle disponível

GET    /api/v1/tables                 # Listar mesas
POST   /api/v1/tables                 # Criar mesa(s)
GET    /api/v1/tables/{id}/qr         # QR Code da mesa

GET    /api/v1/orders                 # Listar pedidos
POST   /api/v1/orders                 # Criar pedido
PUT    /api/v1/orders/{id}            # Atualizar status
POST   /api/v1/orders/{id}/items      # Adicionar itens

GET    /api/v1/employees              # Listar funcionários
POST   /api/v1/employees              # Criar funcionário

GET    /api/v1/service-calls          # Listar chamados
POST   /api/v1/service-calls          # Criar chamado
PUT    /api/v1/service-calls/{id}     # Atualizar status

# Públicos (sem auth)
GET    /api/v1/public/restaurant/{slug}
GET    /api/v1/public/restaurant/qr/{token}
GET    /api/v1/public/restaurant/{id}/categories
GET    /api/v1/public/restaurant/{id}/products
POST   /api/v1/public/restaurant/{id}/orders
POST   /api/v1/public/restaurant/{id}/service-calls

# WebSockets
WS     /api/v1/ws/restaurant/{id}?token=...          # Autenticado
WS     /api/v1/ws/public/restaurant/{id}/table/{id}  # Público
```

## Variáveis de Ambiente

### Backend (.env)

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_nev2
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-min-32-chars
BASE_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
DEBUG=true
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Produção

1. Use um `SECRET_KEY` forte (32+ caracteres)
2. Configure `DEBUG=false`
3. Use PostgreSQL e Redis gerenciados
4. Configure HTTPS e CORS adequados
5. Use um proxy reverso (nginx) na frente
6. Configure backups automáticos do PostgreSQL


## Histórico de Bugs Resolvidos

### ✅ Bug 1+3 — `GET /api/v1/orders?status=[object Object]` retornando **400 Bad Request**

**Causa:** o `URLSearchParams(params).toString()` no cliente chamava `toString()` em cada valor, então quando `status` era um array (ou caía um objeto) virava literalmente `[object+Object]` na URL, e o backend rejeitava com 400.

**Correção (`src/api/client.js`):** substituído por um helper `buildQuery(params)` que serializa arrays via `URLSearchParams.append(key, value)` (gerando `status=received&status=preparing`), ignora `null`/`undefined` e pula objetos aninhados em vez de convertê-los via `toString()`.

---

### ✅ Bug 2 — `GET /api/v1/products?page_size=1000` retornando **422 Unprocessable Entity**

**Causa:** os endpoints validavam `page_size: int = Query(..., le=500)`. O frontend envia `page_size=1000`, gerando 422 antes de chegar no service.

**Correção (`backend/app/api/v1/endpoints/*.py`):** aumentado o limite de `page_size` para `le=1000` em **products**, **orders**, **categories**, **service_calls** e **tables**. Agora o frontend pode puxar a lista completa sem erro de validação.

---

### ✅ Bug 4 — `PUT /api/v1/restaurant/me` quebrando com `MissingGreenlet: greenlet_spawn has not been called`

**Causa:** o `Restaurant` (e outros modelos) tem `updated_at = Column(..., server_default=func.now(), onupdate=func.now())`. Após `db.flush()`, o SQLAlchemy ainda não havia materializado o novo `updated_at` no objeto — e quando o Pydantic (`from_attributes=True`) tentou serializar, disparou lazy-load fora do greenlet async, levantando `MissingGreenlet`.

**Correção (`backend/app/services/crud.py` + `backend/app/api/v1/endpoints/restaurant.py`):**
- Adicionado `await db.refresh(obj)` após `db.flush()` em todos os `create`/`update` dos services (`Restaurant`, `Category`, `Product`, `Table`, `Order`, `Employee`, `ServiceCall`).
- Idem em `create_restaurant_onboarding` no endpoint.
- Isso garante que colunas gerenciadas pelo servidor (`created_at`, `updated_at`, `closed_at`) sejam carregadas no contexto async **antes** da serialização Pydantic, eliminando o `MissingGreenlet`.

## Licença

Proprietário - [NEV]2 Restaurant Management System
