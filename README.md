# FlowState

Sistema de produtividade e aprendizado para desenvolvedores — Kanban + Pomodoro + Journal + GitHub Integration.

## Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Zustand + TanStack Query
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
- **Auth**: JWT (access + refresh tokens)
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

## Como rodar localmente

### Pré-requisitos
- Docker e Docker Compose
- Node.js 20+ (para desenvolvimento frontend)
- Python 3.12+ (para desenvolvimento backend)

### Com Docker (recomendado)

```bash
# Copie as variáveis de ambiente
cp .env.example .env

# Suba os containers
docker compose up -d

# Acesse:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# Docs da API: http://localhost:8000/docs
```

### Desenvolvimento Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# ou com uv: uv sync --frozen

# Rode as migrations
alembic upgrade head

# Inicie o servidor
uvicorn app.main:app --reload
```

### Desenvolvimento Frontend

```bash
cd frontend
npm install
npm run dev
```

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

## Modelo de Dados

```sql
users          (id, email, name, password_hash, created_at)
tasks          (id, user_id, title, description, status, position, created_at, completed_at)
study_sessions (id, user_id, task_id?, started_at, ended_at, duration_min, completed)
journal_entries(id, user_id, session_id, content, created_at)
xp_events      (id, user_id, amount, source[task|pomodoro|journal], created_at)
user_stats     (user_id, xp_total, level, streak, longest_streak, last_active_date)
```

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

## Próximas Versões

- **V0.2**: OAuth2 GitHub + Sync de commits + Heatmap
- **V0.3**: Skills + Flashcards (SM-2) + Badges
- **V0.4**: Redis + Testes + README + Artigo técnico