# 🧪 Guia de Teste Local em Modo Produção

> **Objetivo**: Simular EXATAMENTE o ambiente de produção do Render, mas rodando 100% no seu Windows.
> **Por quê testar antes?**: Evita descobrir bugs DEPOIS de subir pro Render (que demora mais pra re-deployar).

---

## 🎯 O que esse modo simula

| Coisa | Render (real) | Teste local (esse modo) |
|---|---|---|
| Frontend | Build Vite + nginx servindo | Build Vite + nginx local OU direto pelo dist |
| Backend | Docker, sem reload, 1 worker | Python venv, sem reload, 1 worker |
| DEBUG | false | false |
| Postgres | Supabase (externo) | Docker local |
| Redis | Render Key-Value | Docker local |
| CORS | produção | produção |
| SECRET_KEY | forte | fraca (só teste!) |

---

## 🚀 Como rodar

### Opção A — Script automático (mais fácil)

**Um clique só**:
```
Duplo clique em start-test-prod.bat
```

Ele vai:
1. ✅ Verificar Docker
2. ✅ Subir Postgres + Redis em Docker
3. ✅ Aguardar Postgres ficar pronto
4. ✅ Buildar o frontend (modo prod → `dist/`)
5. ✅ Criar venv Python e instalar deps
6. ✅ Rodar migrations do banco
7. ✅ Subir o backend em modo produção (sem reload)

**Quando terminar de testar**:
```
Duplo clique em stop-test-prod.bat
```

---

### Opção B — Manual (didático, passo a passo)

Abra **3 janelas** do PowerShell:

**Janela 1 — Postgres + Redis**:
```powershell
cd C:\Users\Thiago\OneDrive\Desktop\Restaurant-NEV2-MANAGER
docker compose -f docker-compose.test.yml up
```

**Janela 2 — Backend em modo prod**:
```powershell
cd C:\Users\Thiago\OneDrive\Desktop\Restaurant-NEV2-MANAGER
$env:ENV_FILE = ".env.test"
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

**Janela 3 — Build + servir frontend**:
```powershell
cd C:\Users\Thiago\OneDrive\Desktop\Restaurant-NEV2-MANAGER
npm run build
npx serve dist -l 5173
```

---

## 🧪 O que testar

### 1. Acessar a aplicação
- Abra http://localhost:5173 (ou http://localhost se usar nginx)
- Deve carregar o frontend buildado (não é dev mode)

### 2. Criar conta de dono
- Tela de registro
- Verifique se cria restaurante + usuário
- ⚠️ Se der erro de CORS, é pq o `FRONTEND_URL` no .env.test não bate com a URL que você tá acessando

### 3. Login
- Faça login
- JWT deve ser gerado e armazenado

### 4. Criar categoria + produto
- Menu → Categorias → criar
- Produtos → criar
- Verifica se salvou no Postgres

### 5. Testar WebSocket (pedidos em tempo real)
- Abra 2 abas: uma como cozinha, outra como cliente
- Crie um pedido numa aba
- A outra deve atualizar **na hora** sem precisar dar F5
- ⚠️ Se não atualizar, é problema no WebSocket

### 6. Gerar QR Code de mesa
- Mesas → criar → gerar QR
- Escaneie com o celular (mesma rede Wi-Fi)
- Acesse `http://SEU_IP_LOCAL:5173/r/...` pelo celular
- Se abrir, tá tudo certo com a config de URL

### 7. Verificar logs
- O backend em modo prod **NÃO** mostra logs de cada request por padrão
- Pra ver logs estruturados, use:
  ```powershell
  # No Windows, abre direto: uvicorn já mostra os prints
  ```
- Em prod de verdade (Render), vai aparecer em **Logs** no painel

### 8. Derrubar e subir de novo (testa persistência)
```powershell
.\stop-test-prod.bat
.\start-test-prod.bat
```
- Seus dados devem continuar lá (Postgres é persistente)
- Mas os uploads/arquivos do usuário NÃO (pq não tá com volume persistente nesse modo de teste — em prod de verdade, vai tá)

---

## 🔍 Onde olhar se der erro

### Backend não sobe
- Veja a mensagem no terminal
- Geralmente é variável errada no `.env.test`
- Compara com o `.env.example` que tá no backend

### Frontend não carrega
- Clica F12 → Console
- Erros vermelhos vão dizer onde tá o problema
- Geralmente é URL errada da API

### CORS error
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:5173' has been blocked by CORS
```
- Adiciona a origem em `CORS_ORIGINS` no `.env.test`
- Reinicia o backend

### WebSocket não conecta
- Olha o Console do navegador
- Se aparecer "WebSocket connection failed", é pq:
  - A URL tá errada (deve ser `ws://localhost:8000/ws/...`)
  - O nginx não tá com proxy do `/ws/` configurado

### Postgres não conecta
- Verifica se o container tá rodando: `docker ps`
- Verifica a porta: `netstat -an | findstr 5432`
- Testa manual:
  ```powershell
  docker exec -it nev2-postgres-test psql -U nev2_test -d restaurant_nev2_test
  ```

---

## 🎯 Diferenças entre teste local e Render real

| Diferença | Por quê | Impacto |
|---|---|---|
| Render dorme sem uso | Limitação do free tier | UptimeRobot resolve |
| Render tem HTTPS automático | Render cuida | Em teste local usa HTTP |
| Render tem domínio `.onrender.com` | Render atribui | Em teste local usa localhost |
| Render não tem persistência de arquivo | Disco efêmero | Em teste local funciona normal |
| Render gera SECRET_KEY automático | Segurança | Em teste local tá fixa |

Nenhuma dessas diferenças impede o teste. Quando você subir pro Render, a única coisa que muda é o domínio e o HTTPS.

---

## ✅ Quando tá tudo OK

Você consegue:
- ✅ Logar e deslogar
- ✅ Criar restaurante, categoria, produto
- ✅ Criar mesa e gerar QR
- ✅ Cliente escaneia QR pelo celular e vê cardápio
- ✅ Cliente faz pedido
- ✅ Cozinha vê pedido em tempo real (sem F5)
- ✅ Pedido passa por: recebido → preparando → pronto → entregue
- ✅ Relatórios mostram vendas do dia

**Se tudo isso funciona, tá pronto pra subir pro Render!** 🚀

---

## 🆘 Problemas comuns

**"ModuleNotFoundError: No module named 'fastapi'"**
- Você não ativou o venv: `.\backend\.venv\Scripts\Activate.ps1`

**"alembic: command not found"**
- Mesmo problema do venv acima

**"Could not connect to server: Connection refused"**
- Postgres não tá rodando: `docker compose -f docker-compose.test.yml up -d`

**"permission denied for schema public"**
- Deletar volume e recriar:
  ```powershell
  docker compose -f docker-compose.test.yml down -v
  docker compose -f docker-compose.test.yml up -d
  ```

**Frontend em dev mode mesmo depois do build**
- Limpa o cache: `Remove-Item -Recurse -Force node_modules\.vite`
- Builda de novo: `npm run build`
- Serve com `npx serve dist` (não `npm run dev`)

---

## 🎯 Próximo passo

Depois que tudo funciona em teste:
1. ✅ Suba pro GitHub
2. ✅ Crie projeto no Supabase
3. ✅ Faça deploy no Render
4. ✅ Configure UptimeRobot
5. ✅ Tá no ar de graça! 🎉
