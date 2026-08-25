# 🚀 Guia de Deploy — Render + Supabase + UptimeRobot

> **Sistema**: [NEV]2 Restaurant Management System
> **Stack**: Render.com (free) + Supabase Postgres (free) + UptimeRobot (free)
> **Custo**: R$ 0,00/mês (sem cartão de crédito!)
> **Sistema**: 24/7 online, sem sleep

---

## 📋 O que você vai ter no final

- ✅ **Frontend React** rodando em `https://nev2-frontend.onrender.com`
- ✅ **Backend FastAPI** rodando em `https://nev2-backend.onrender.com`
- ✅ **Banco Postgres** no Supabase (500MB grátis pra sempre)
- ✅ **Redis** gerenciado pelo Render
- ✅ **UptimeRobot** pingando a cada 5min (Render nunca dorme)
- ✅ **HTTPS** automático (Render cuida)
- ✅ **Sem cartão de crédito** em lugar nenhum

---

## 🗺️ Sumário (tempo total: ~30 min)

1. [Subir código pro GitHub](#1-subir-código-pro-github)
2. [Criar projeto no Supabase](#2-criar-projeto-no-supabase-postgres)
3. [Criar conta no Render](#3-criar-conta-no-render)
4. [Deploy via Blueprint](#4-deploy-via-blueprint)
5. [Configurar DATABASE_URL](#5-configurar-database_url-do-supabase)
6. [Configurar UptimeRobot](#6-configurar-uptimerobot-keep-alive)
7. [Atualizar URLs reais](#7-atualizar-urls-reais-depois-do-primeiro-deploy)
8. [Manutenção](#8-manutenção-e-atualizações)

---

## 1. Subir código pro GitHub

### 1.1. Criar repositório
1. Vá em https://github.com/new
2. Nome: `Restaurant-NEV2-MANAGER`
3. **Privado**
4. NÃO marque "Initialize with README"
5. Clique **Create repository**

### 1.2. Subir código (do seu Windows PowerShell)
```powershell
cd C:\Users\Thiago\OneDrive\Desktop\Restaurant-NEV2-MANAGER

git add .
git commit -m "feat: adiciona config de deploy no Render"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/Restaurant-NEV2-MANAGER.git
git push -u origin main
```

---

## 2. Criar projeto no Supabase (Postgres)

1. Vá em https://supabase.com (cria conta com GitHub, **sem cartão**)
2. **New Project**
3. Preencha:
   - **Name**: `nev2-restaurant`
   - **Database Password**: gera uma senha forte (anota ela!)
   - **Region**: `South America (São Paulo)` se disponível, senão `US East`
4. Clique **Create new project** (demora ~2 min)
5. Quando terminar, vá em **Settings → Database → Connection string → URI**
6. Copie a string — vai ser algo tipo:
   ```
   postgresql://postgres.xxxx:SENHA@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
7. **⚠️ IMPORTANTE**: Use a porta **6543** (Transaction Mode / Pooler) — não a 5432
8. Adicione `?pgbouncer=true` no final se ainda não tiver
9. **Anote essa URL** — vamos usar no passo 5

---

## 3. Criar conta no Render

1. Vá em https://render.com
2. **Get Started for Free**
3. Cria conta com **GitHub** (mais fácil, conecta direto)
4. **Sem cartão de crédito** — Render free não pede!

---

## 4. Deploy via Blueprint

1. No dashboard Render, clique **New** → **Blueprint**
2. Conecta o repositório `Restaurant-NEV2-MANAGER`
3. Render vai detectar o `render.yaml` automaticamente
4. Clique **Apply**
5. Render vai criar 3 serviços:
   - `nev2-backend` (Web Service)
   - `nev2-redis` (Redis)
   - `nev2-frontend` (Static Site)
6. **Aguarda o primeiro deploy** (5-10 min pra buildar tudo)
7. ⚠️ **Vai falhar o backend** porque falta a DATABASE_URL — sem pânico, é o próximo passo!

---

## 5. Configurar DATABASE_URL do Supabase

1. No Render Dashboard, clique em **nev2-backend**
2. Vá em **Environment**
3. Na variável **DATABASE_URL**, clica em **Edit**
4. Cola a connection string do Supabase que você copiou no passo 2
5. Clica **Save Changes**
6. Render vai **re-deployar automaticamente** (3-5 min)
7. Acompanhe em **Logs** — quando aparecer "Application startup complete", tá no ar!

### 5.1. Rodar migrations do banco
Quando o backend subir:
1. Vai em **Shell** (no menu do nev2-backend no Render)
2. Roda:
   ```bash
   alembic upgrade head
   ```
3. Aguarda completar — deve criar todas as tabelas

---

## 6. Configurar UptimeRobot (keep-alive)

Esse é o **passo chave** pra Render nunca dormir:

1. Vá em https://uptimerobot.com (cria conta com email, **sem cartão**)
2. Clica **+ Add New Monitor**
3. Preenche:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `NEV2 Backend`
   - **URL**: `https://nev2-backend.onrender.com/api/v1/health`
   - **Monitoring Interval**: **5 minutes** ⬅️ importante!
4. Clica **Create Monitor**

### 6.1. Adiciona também o frontend (opcional, mas recomendado)
- Clica **+ Add New Monitor** de novo
- **Friendly Name**: `NEV2 Frontend`
- **URL**: `https://nev2-frontend.onrender.com/`
- **Interval**: 5 minutes

Pronto! Agora o Render **nunca mais vai dormir** porque tem alguém pingando a cada 5 min. 🎉

---

## 7. Atualizar URLs reais (depois do primeiro deploy)

Depois que tudo subiu, o Render te deu URLs reais. Vamos atualizar as configs:

### 7.1. Pega as URLs reais
- Backend: vai estar tipo `https://nev2-backend-abc123.onrender.com`
- Frontend: vai estar tipo `https://nev2-frontend-xyz789.onrender.com`

### 7.2. Atualiza variáveis do Backend
Em **nev2-backend → Environment**, edita:

| Variável | Valor |
|---|---|
| `CORS_ORIGINS` | `["https://nev2-frontend-xyz789.onrender.com"]` |
| `BASE_URL` | `https://nev2-frontend-xyz789.onrender.com` |
| `FRONTEND_URL` | `https://nev2-frontend-xyz789.onrender.com` |

### 7.3. Atualiza variáveis do Frontend
Em **nev2-frontend → Environment**, edita:

| Variável | Valor |
|---|---|
| `VITE_API_URL` | `https://nev2-backend-abc123.onrender.com/api/v1` |
| `VITE_WS_URL` | `wss://nev2-backend-abc123.onrender.com/ws` |

### 7.4. Atualiza rotas do Frontend (no render.yaml ou no painel)
Em **nev2-frontend → Redirects/Rewrites**, edita as rotas pra apontar pro backend real:

```
/api/* → https://nev2-backend-abc123.onrender.com/api/*
/ws/*  → https://nev2-backend-abc123.onrender.com/ws/*
/*     → /index.html
```

### 7.5. Trigger re-deploy
- Backend: clica **Manual Deploy → Deploy latest commit**
- Frontend: clica **Manual Deploy → Deploy latest commit**

Aguarda uns 3-5 min e testa!

---

## 8. Manutenção e atualizações

### 📝 Atualizar código
1. Faz commit e push pro GitHub:
   ```powershell
   git add .
   git commit -m "feat: minha mudança"
   git push
   ```
2. Render detecta e faz deploy automático!

### 📊 Ver logs
- Render Dashboard → seu serviço → **Logs**
- Stream em tempo real

### 💾 Backup do banco
```bash
# No seu Windows (com psql instalado) ou no Shell do Render
pg_dump "postgresql://postgres.xxxx:SENHA@aws-0-us-east-1.pooler.supabase.com:6543/postgres" > backup.sql
```

Ou usa a interface do Supabase:
- **Database → Backups** (faz backup automático diário no plano free)

### 🔄 Resetar banco (CUIDADO - apaga tudo)
No Supabase:
- **Settings → Database → Reset Database**

### 📈 Ver uso
- **Render Dashboard** mostra uso de CPU/RAM/tempo
- **Supabase Dashboard** mostra uso de storage/bandas

---

## ⚠️ Limitações do Plano Free (honestidade total)

| Limite | Valor | Você vai estourar? |
|---|---|---|
| Render backend | 512MB RAM, dorme sem uso | ❌ Não (com UptimeRobot) |
| Render banda | 100GB/mês | ❌ Não |
| Render build time | 500h/mês | ❌ Não |
| Supabase storage | 500MB | ⚠️ Em ~6-12 meses |
| Supabase bandas | 2GB/mês | ⚠️ Se tiver MUITO tráfego |
| UptimeRobot | 50 monitores, 5min | ❌ Não |

### Quando você começar a crescer:
- Supabase storage lotar → upgrade pra Pro ($25/mês) ou move pro Neon (outro free)
- Render limits → upgrade plano ($7/mês)
- Mas pra começar, **o free aguenta tranquilo**.

---

## 🆘 Problemas comuns

### "Application startup complete" não aparece
- Vai em **Logs**
- Procura por **Traceback** (erro Python)
- Geralmente é DATABASE_URL errada — confere se copiou certinho

### Frontend carrega mas API dá erro
- CORS bloqueando → confere `CORS_ORIGINS` no backend
- URL errada → confere `VITE_API_URL` no frontend
- Esqueceu de re-deployar depois de mudar env vars

### Backend dormiu mesmo com UptimeRobot
- Espera 1-2 min — primeiro request após acordar demora
- Se persistir, UptimeRobot pode estar com interval errado (coloca 5min)

### Migrations não rodaram
- Vai em **Shell** do backend no Render
- Roda: `alembic upgrade head`
- Se der erro de conexão, testa a DATABASE_URL direto:
  ```bash
  python -c "from sqlalchemy.ext.asyncio import create_async_engine; import asyncio; asyncio.run(create_async_engine('$DATABASE_URL').connect())"
  ```

---

## 💰 Custos finais

**R$ 0,00/mês**. Garantido.

Sem cartão, sem teste grátis que acaba, sem cobrança surpresa.

---

## 🎉 Próximos passos depois do deploy

1. ✅ **Custom domain** (domínio próprio tipo `restaurantenev.com.br` — R$50/ano)
2. ✅ **Monitoring** no UptimeRobot já tá feito
3. ✅ **Alertas por email** se cair (UptimeRobot manda)
4. ⏳ Quando crescer, upgrade Supabase ($25/mês)

---

**Bora fazer? Me chama quando tiver subido no GitHub que eu te ajudo nos próximos passos!** 🚀
