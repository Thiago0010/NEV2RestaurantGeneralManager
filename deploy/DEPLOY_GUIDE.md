# 🚀 Guia de Deploy — Oracle Cloud Always Free

> **Sistema**: [NEV]2 Restaurant Management System
> **Plataforma**: Oracle Cloud Always Free Tier (2 VMs ARM, 1GB RAM cada, **100% grátis pra sempre**)
> **Tempo estimado**: 1-2 horas (primeira vez)

---

## 📋 Pré-requisitos

Antes de começar, tenha em mãos:

- ✅ Conta de email válida (pra criar conta Oracle)
- ✅ Cartão de crédito internacional (Oracle pede pra validar, mas **NÃO COBRA** se ficar no Always Free)
- ✅ Esse repositório commitado no GitHub (vou te mostrar como no passo 1)
- ✅ Um cliente SSH (no Windows: PowerShell com `ssh` nativo, ou Putty)

---

## 🗺️ Sumário

1. [Subir código pro GitHub](#1-subir-código-pro-github)
2. [Criar conta Oracle Cloud](#2-criar-conta-oracle-cloud)
3. [Criar a VM Always Free](#3-criar-a-vm-always-free)
4. [Liberar portas no painel Oracle](#4-liberar-portas-no-painel-oracle)
5. [Configurar a VM (SSH)](#5-configurar-a-vm-via-ssh)
6. [Configurar domínio grátis (DuckDNS)](#6-configurar-domínio-grátis-duckdns)
7. [Configurar .env.production](#7-configurar-envproduction)
8. [Rodar o deploy](#8-rodar-o-deploy)
9. [Configurar HTTPS (SSL grátis)](#9-configurar-https-ssl-grátis)
10. [Manutenção e atualizações](#10-manutenção-e-atualizações)

---

## 1. Subir código pro GitHub

### 1.1. Criar repositório
1. Vá em https://github.com/new
2. Nome: `Restaurant-NEV2-MANAGER` (ou o que preferir)
3. **Privado** (recomendado)
4. **NÃO** marque "Initialize with README"
5. Clique "Create repository"

### 1.2. Subir o código (do seu Windows)
```powershell
cd C:\Users\Thiago\OneDrive\Desktop\Restaurant-NEV2-MANAGER

git init
git add .
git commit -m "feat: prepara sistema pra deploy em Oracle Cloud"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/Restaurant-NEV2-MANAGER.git
git push -u origin main
```

> 💡 **Dica**: Adicione `.env.production` no `.gitignore` pra não subir senhas:
> ```powershell
> Add-Content .gitignore "`n.env.production`nbackend/.env"
> git add .gitignore
> git commit -m "chore: ignora .env.production"
> git push
> ```

---

## 2. Criar conta Oracle Cloud

1. Acesse https://cloud.oracle.com/
2. Clique em **"Start for Free"**
3. Preencha email, nome, país
4. Confirme email (recebe código)
5. Escolha senha
6. **Home Region** — escolha com cuidado (define onde seus recursos vão ficar PRA SEMPRE):
   - 🇧🇷 **São Paulo** (se disponível)
   - 🇺🇸 **US East (Ashburn)** como fallback
7. Coloque o cartão de crédito (validação, **não cobra nada no Always Free**)
8. Aguarde aprovação (geralmente instantâneo)

---

## 3. Criar a VM Always Free

1. No console Oracle, vá em **Compute → Instances → Create Instance**
2. **Name**: `nev2-server` (ou o que preferir)
3. **Placement**: deixa na sua home region
4. **Image and shape**:
   - Clique em **"Edit"** → **"Change Shape"**
   - Selecione **"Ampere"** (ARM)
   - Shape: **VM.Standard.A1.Flex**
   - **OCPU: 1**, **RAM: 1 GB** (deixa assim pra economizar)
5. **Networking**: deixa padrão (cria VCN nova)
6. **SSH Keys**:
   - Selecione **"Generate a key pair"** e **"Save private key"**
   - ⚠️ **MUITO IMPORTANTE**: salve o arquivo `.key` em local seguro! Você vai usar pra conectar.
   - No Windows, salve em `C:\Users\Thiago\.ssh\nev2-server.key`
7. **Boot volume**: 100 GB (Always Free, deixa padrão)
8. Clique **"Create"**
9. Aguarde uns 2-3 min até ficar **Running**
10. **Copie o IP público** (algo como `132.145.xx.xx`)

---

## 4. Liberar portas no painel Oracle

A Oracle bloqueia TODAS as portas por padrão. Você precisa liberar 80 e 443:

1. Vá em **Networking → Virtual Cloud Networks**
2. Clique na VCN que foi criada (geralmente com o mesmo nome da instance)
3. Clique na **Subnet** (link azul)
4. Clique em **"Default Security List"** (link azul)
5. Clique em **"Add Ingress Rules"**
6. Adicione **2 regras**:

   **Regra 1 — HTTP:**
   - Source CIDR: `0.0.0.0/0`
   - Protocol: TCP
   - Destination Port: `80`

   **Regra 2 — HTTPS:**
   - Source CIDR: `0.0.0.0/0`
   - Protocol: TCP
   - Destination Port: `443`

7. Clique **"Add Ingress Rules"**

> 💡 A porta 22 (SSH) já vem liberada por padrão.

---

## 5. Configurar a VM via SSH

### 5.1. Conectar via SSH (do Windows PowerShell)
```powershell
# Definir permissão da chave (só primeira vez)
icacls "C:\Users\Thiago\.ssh\nev2-server.key" /inheritance:r /grant:r "$($env:USERNAME):(R)"

# Conectar
ssh -i C:\Users\Thiago\.ssh\nev2-server.key ubuntu@SEU_IP_PUBLICO
```

### 5.2. Rodar setup da VM
Já logado na VM:
```bash
# Sobe o setup completo (Docker, firewall, swap, usuário deploy)
sudo bash deploy/oracle-setup.sh
```

> O script vai pedir confirmação algumas vezes. Responde `y` pra tudo.

### 5.3. Liberar portas no iptables (extra)
```bash
sudo bash deploy/oracle-ports.sh
```

### 5.4. Trocar pro usuário deploy
```bash
su - deploy
```

### 5.5. Clonar o repositório
```bash
mkdir -p ~/app && cd ~/app
git clone https://github.com/SEU_USUARIO/Restaurant-NEV2-MANAGER.git .
# Se for repo privado, vai pedir usuário e senha/token do GitHub
#   -> No GitHub: Settings → Developer settings → Personal access tokens → Generate new token
#   -> Dê permissão de "repo" e use o token como senha
```

---

## 6. Configurar domínio grátis (DuckDNS)

Você precisa de um domínio pra usar HTTPS. Vamos usar **DuckDNS** (grátis, sem cartão):

### 6.1. Criar domínio DuckDNS
1. Vá em https://www.duckdns.org
2. Logue com Google/GitHub
3. No campo, digite um nome (ex: `nev2restaurante`) e clique add
4. Vai aparecer: `nev2restaurante.duckdns.org`
5. **Copie o TOKEN** que aparece no topo da página

### 6.2. Configurar na VM
```bash
sudo bash deploy/setup-duckdns.sh nev2restaurante SEU_TOKEN_AQUI
```

Pronto! Seu domínio `nev2restaurante.duckdns.org` já aponta pro IP da VM.

---

## 7. Configurar .env.production

Na VM, dentro da pasta do projeto:
```bash
cd ~/app
cp .env.production.example .env.production
nano .env.production
```

Preencha as variáveis:

```bash
# ------- Domínio (use o DuckDNS que você criou) -------
BASE_URL=http://nev2restaurante.duckdns.org
FRONTEND_URL=http://nev2restaurante.duckdns.org
VITE_API_URL=/api/v1
VITE_WS_URL=/ws
CORS_ORIGINS=["http://nev2restaurante.duckdns.org"]

# ------- Banco -------
POSTGRES_DB=restaurant_nev2
POSTGRES_USER=nev2_admin
# Gere uma senha forte:
POSTGRES_PASSWORD=$(openssl rand -base64 24)

# ------- Segurança -------
# Gere a SECRET_KEY:
SECRET_KEY=$(openssl rand -base64 48)
```

**Copie esses valores gerados** (eles aparecem no terminal) e cole no `.env.production` na linha correspondente.

> 🔐 **Dica**: Salve essas senhas num local seguro (gerenciador de senhas). Se perder, vai ter que resetar tudo.

Salvar e sair: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 8. Rodar o deploy

```bash
bash deploy/deploy.sh
```

Esse script vai:
1. ✅ Validar o `.env.production`
2. ✅ Construir as imagens Docker
3. ✅ Subir Postgres + Redis + Backend + Frontend
4. ✅ Rodar migrations do banco
5. ✅ Verificar se tá tudo no ar

**Demorou uns 5-10 min na primeira vez** (download de imagens). Nos próximos deploys é bem mais rápido.

### Testar
Abra no navegador:
- Frontend: `http://nev2restaurante.duckdns.org`
- API: `http://nev2restaurante.duckdns.org/api/v1/docs`

---

## 9. Configurar HTTPS (SSL grátis)

Sem HTTPS o navegador vai mostrar "não seguro". Vamos colocar de graça com Let's Encrypt:

```bash
# Dentro da VM, com o domínio já apontando pra cá
sudo bash deploy/setup-ssl.sh nev2restaurante.duckdns.org seu-email@exemplo.com
```

Esse script gera o certificado. Depois disso:

### 9.1. Atualizar nginx pra usar HTTPS
```bash
docker exec -u root nev2-frontend apk add --no-cache certbot
docker exec -u root nev2-frontend sh -c '
  cat > /etc/nginx/conf.d/default.conf <<NGINX
server {
    listen 80;
    server_name nev2restaurante.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nev2restaurante.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/nev2restaurante.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nev2restaurante.duckdns.org/privkey.pem;

    root /usr/share/nginx/html;
    index index.html;

    # ... (resto igual ao nginx.prod.conf)
}
NGINX
nginx -s reload
'
```

> 💡 Versão completa do nginx com HTTPS vai ser automatizada em versão futura. Por enquanto copie manualmente do `nginx.prod.conf`.

### 9.2. Atualizar .env.production
Mude as URLs pra `https://`:
```bash
BASE_URL=https://nev2restaurante.duckdns.org
FRONTEND_URL=https://nev2restaurante.duckdns.org
CORS_ORIGINS=["https://nev2restaurante.duckdns.org"]
```

Reinicie:
```bash
bash deploy/deploy.sh --update
```

### 9.3. Auto-renovação do certificado
```bash
# Adiciona no crontab pra renovar todo dia 1 às 3h da manhã
( crontab -l 2>/dev/null; \
  echo "0 3 1 * * docker exec -u root nev2-frontend certbot renew --quiet && docker exec nev2-frontend nginx -s reload" ) | crontab -
```

---

## 10. Manutenção e atualizações

### 📜 Ver logs em tempo real
```bash
docker compose -f docker-compose.prod.yml logs -f
# ou só de um serviço:
docker logs -f nev2-backend
```

### 🔄 Atualizar o sistema (depois de git push)
```bash
cd ~/app
git pull
bash deploy/deploy.sh --update
```

### 🛑 Parar o sistema
```bash
docker compose -f docker-compose.prod.yml down
```

### ▶️ Subir de novo
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 💾 Backup do banco
```bash
docker exec nev2-postgres pg_dump -U nev2_admin restaurant_nev2 | gzip > backup-$(date +%Y%m%d).sql.gz
```

### 🔁 Restaurar backup
```bash
gunzip < backup-20260101.sql.gz | docker exec -i nev2-postgres psql -U nev2_admin restaurant_nev2
```

### 📊 Status dos containers
```bash
docker compose -f docker-compose.prod.yml ps
docker stats
```

### 🆘 Em caso de problemas

**1. VM tá lenta / travando:**
```bash
# Mata processos que podem ter vazado
docker system prune -a
```

**2. Postgres não sobe:**
```bash
docker logs nev2-postgres
docker volume inspect restaurantnev2manager_postgres_data
```

**3. Backend com erro:**
```bash
docker logs nev2-backend --tail 100
```

**4. Resetar tudo (PERIGOSO - apaga banco):**
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

---

## 💰 Custos

**Tudo isso é 100% grátis**. Não vai ter cobrança nenhuma se:
- ❌ Não criar instâncias pagas (só Allow Always Free)
- ❌ Não passar de 200GB de tráfego/mês de saída
- ❌ Não criar mais de 2 VMs

Pra conferir seu uso:
- Oracle Console → **Billing → Cost Analysis**

---

## 🔒 Segurança — Checklist

- [ ] SECRET_KEY gerada com `openssl rand` (não use a do .env.example!)
- [ ] POSTGRES_PASSWORD gerada com `openssl rand` (não use "postgres")
- [ ] `.env.production` adicionado no `.gitignore`
- [ ] Portas 5432/6379/8000 NÃO expostas no firewall (só 22/80/443)
- [ ] HTTPS configurado (depois do passo 9)
- [ ] Backup do banco programado (cron)

---

## 📞 Links úteis

- **Oracle Cloud Console**: https://cloud.oracle.com/
- **DuckDNS**: https://www.duckdns.org
- **Let's Encrypt**: https://letsencrypt.org/
- **Documentação Docker**: https://docs.docker.com/

---

## 🆘 Precisa de ajuda?

Se travar em algum passo, me chama! Boa sorte! 🚀
