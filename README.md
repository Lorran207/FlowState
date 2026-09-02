# FlowState

Sistema de produtividade e aprendizado para desenvolvedores — Kanban + Pomodoro + Journal + GitHub Integration.

> "Não rastreie o que você estudou. Rastreie o que você consegue construir."

## Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Zustand + TanStack Query
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
- **Auth**: JWT (access + refresh tokens) + OAuth2 GitHub
- **Jobs**: APScheduler (sync de commits em background)
- **Deploy**: Docker Compose (local) → Render (backend) + Vercel (frontend)

## Estrutura

```
flowstate/
├── backend/
│   └── app/
│       ├── api/routes/      # endpoints
│       ├── schemas/         # Pydantic DTOs
│       ├── services/        # regras de negócio
│       ├── repositories/    # acesso a dados
│       ├── models/          # SQLAlchemy models
│       └── core/            # config, auth, database
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── pages/
│       └── types/
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Roadmap V0.1 (MVP - Loop Fechado)

- [x] Cadastro/login (email + senha, JWT)
- [x] Kanban (Backlog / Hoje / Fazendo / Feito) com drag-and-drop
- [x] Pomodoro 100% frontend (timer roda mesmo trocando de aba)
- [x] Modal pós-Pomodoro: "O que você aprendeu?" (~280 chars)
- [x] XP + Streak (simples)
- [x] Dashboard mínimo
- [x] Docker Compose + CI + deploy

## Roadmap V0.2 (GitHub Integration)

- [x] OAuth2 GitHub (login/cadastro com GitHub + vincular conta existente)
- [x] Sync de commits via GitHub Events API (`httpx`)
- [x] Background job com APScheduler (intervalo configurável, default 30 min)
- [x] Sincronização manual sob demanda (`POST /github/sync`)
- [x] Feed de atividades unificado (pomodoros + journals + commits)
- [x] Heatmap estilo GitHub Contributions (dias com ≥50 min de foco ganham destaque)
- [x] Persistência de commits deduplicados por SHA

## Como rodar localmente

### Pré-requisitos

- Docker e Docker Compose
- Node.js 20+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recomendado para o backend) ou `pip` + `venv`

### Configuração inicial (primeira vez)

```bash
cd FlowState
cp .env.example .env

cd frontend && npm install && cd ..
cd backend && uv sync && cd ..
```

### Permissão do Docker (Linux)

Se `docker compose` falhar com `permission denied` no socket do Docker, adicione seu usuário ao grupo `docker` e faça logout/login:

```bash
sudo usermod -aG docker $USER
```

Alternativa temporária: prefixe os comandos Docker com `sudo`.

---

### Opção A — Tudo com Docker (mais simples)

Sobe Postgres, backend e frontend de uma vez:

```bash
cd FlowState
docker compose up -d
```

Aguarde alguns segundos e acesse:

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Docs da API | http://localhost:8000/docs |

Para ver os logs ou parar:

```bash
docker compose logs -f      # acompanhar logs
docker compose down         # parar tudo
```

---

### Opção B — Desenvolvimento manual (3 terminais)

Útil quando você quer hot-reload no backend e frontend, mas ainda usa Docker só para o banco.

#### Terminal 1 — Banco de dados

```bash
cd FlowState
docker compose up -d postgres
```

> O serviço no `docker-compose.yml` se chama **`postgres`** (não `db`).
> Aguarde ~5 segundos para o Postgres ficar pronto.

#### Terminal 2 — Backend

```bash
cd FlowState/backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Docs da API: http://localhost:8000/docs

#### Terminal 3 — Frontend

```bash
cd FlowState/frontend
npm run dev
```

App: http://localhost:5173

---

### Opção C — Só o banco no Docker, backend com pip

Se preferir não usar `uv`:

```bash
cd FlowState
docker compose up -d postgres

cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

### Fluxo para testar (screenshots / demo)

1. **Cadastro** → http://localhost:5173/register
2. **Login** → http://localhost:5173/login
3. **Dashboard** → http://localhost:5173/
4. **Kanban** → http://localhost:5173/kanban
   - Crie uma tarefa
   - Mova entre colunas clicando nos botões
   - Clique em **Focar** para abrir o Pomodoro
   - Conclua o timer e escreva no diário
5. **Dashboard** novamente → verifique XP e streak atualizados

---

### Problemas comuns

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `permission denied` no Docker | Usuário fora do grupo `docker` | `sudo usermod -aG docker $USER` e relogar |
| `no such service: db` | Nome do serviço incorreto | Use `postgres`: `docker compose up -d postgres` |
| `Connection refused` no backend | Postgres não está rodando | Suba o banco antes: `docker compose up -d postgres` |
| `No 'script_location' key found` (Alembic) | `alembic.ini` incompleto | Já corrigido no repositório; faça `git pull` |
| Frontend abre mas API falha | Backend parado ou porta 8000 ocupada | Confira `curl http://localhost:8000/health` |

## API Endpoints

### Auth
- `POST /auth/register` - Registrar usuário
- `POST /auth/login` - Login
- `POST /auth/refresh` - Renovar access token
- `GET /auth/me` - Usuário atual

### Tasks (Kanban)
- `GET /tasks` - Listar tarefas
- `POST /tasks` - Criar tarefa
- `GET /tasks/{id}` - Obter tarefa
- `PATCH /tasks/{id}` - Atualizar tarefa
- `DELETE /tasks/{id}` - Deletar tarefa
- `POST /tasks/reorder/{status}` - Reordenar tarefas

### Sessions (Pomodoro)
- `GET /sessions` - Listar sessões
- `POST /sessions` - Iniciar sessão
- `POST /sessions/{id}/complete` - Concluir sessão

### Journal
- `POST /journal` - Criar entrada de journal

### Dashboard
- `GET /dashboard` - Dados do dashboard

### GitHub (OAuth + Sync)
- `GET /auth/github/authorize` - URL de autorização do GitHub (aceita `?t=<access_token>` para vincular à conta logada)
- `GET /auth/github/callback` - Callback do OAuth (redireciona para `{FRONTEND_URL}/auth/callback` com os tokens)
- `GET /github/status` - Status da conexão (username + nº de commits)
- `POST /github/sync` - Sincroniza commits agora (além do job em background)
- `DELETE /github/disconnect` - Desconecta o GitHub (exige senha definida)
- `GET /github/commits?limit=N` - Commits recentes importados

### Activity (Feed + Heatmap)
- `GET /activity/feed?days=14&limit=50` - Feed unificado: pomodoros, journals e commits
- `GET /activity/heatmap?days=365` - Atividade por dia (count + minutos) para o heatmap

## Modelo de Dados

```sql
users          (id, email, name, password_hash?, github_id?, github_username?,
                github_access_token?, created_at)
tasks          (id, user_id, title, description, status, position, created_at, completed_at)
study_sessions (id, user_id, task_id?, started_at, ended_at, duration_min, completed)
journal_entries(id, user_id, session_id, content, created_at)
xp_events      (id, user_id, amount, source[task|pomodoro|journal], created_at)
user_stats     (user_id, xp_total, level, streak, longest_streak, last_active_date)
commits        (id, user_id, sha, message, repo_name, url, committed_at, created_at)
               -- únicos por (user_id, sha); sincronizados do GitHub
```

> `password_hash` é opcional para contas criadas via OAuth (login apenas pelo GitHub).
> Nesses casos, `DELETE /github/disconnect` é bloqueado até o usuário definir uma senha.

## XP Values

| Ação | XP |
|------|-----|
| Completar tarefa | 10 |
| Completar Pomodoro | 15 |
| Escrever Journal | 5 |

Level = (XP Total // 100) + 1

## CI/CD

GitHub Actions roda em todo push:
- Backend: ruff (lint) + mypy (types) + pytest
- Frontend: eslint + tsc + build

## Configurar o GitHub OAuth (V0.2)

1. Crie um OAuth App em <https://github.com/settings/developers>:
   - **Application name**: FlowState (dev)
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
2. Preencha `GITHUB_CLIENT_ID` e `GITHUB_CLIENT_SECRET` no `.env`.
3. Rode a migration e suba os serviços:

```bash
cd backend && uv run alembic upgrade head && cd ..
docker compose up -d
```

O sync de commits roda em background via APScheduler a cada `GITHUB_SYNC_INTERVAL_MINUTES`
(default 30) e também pode ser disparado manualmente pelo botão **Sincronizar commits** no
dashboard. O fluxo usa a GitHub Events API (`/users/{username}/events` → `PushEvent`) e
importa commits deduplicados por SHA.

## Próximas Versões

- **V0.3**: Skills + Flashcards (SM-2) + Badges
- **V0.4**: Redis + Testes + README + Artigo técnico