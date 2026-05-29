# Customer CRUD

API REST simples para cadastro de clientes (nome, email, telefone). Construída com **FastAPI** e **PostgreSQL**, empacotada com Docker Compose. Serve para testar rapidamente um CRUD completo via Swagger UI.

## Stack

- Python 3.12 + FastAPI + SQLAlchemy 2
- PostgreSQL 16 (container)
- Pydantic v2 (validação, com `EmailStr`)

## Como rodar

A partir desta pasta:

```bash
docker compose up --build
```

Quando aparecer `Application startup complete`, abra:

- Swagger UI: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health

Para parar:

```bash
docker compose down          # mantém os dados no volume pgdata
docker compose down -v       # apaga também o volume (limpa o banco)
```

## Endpoints

| Método | Rota                    | Descrição                          |
| ------ | ----------------------- | ---------------------------------- |
| GET    | `/health`               | Healthcheck                        |
| POST   | `/customers`            | Cria cliente (201)                 |
| GET    | `/customers`            | Lista (`?skip=0&limit=100`)        |
| GET    | `/customers/{id}`       | Detalha (404 se não existe)        |
| PUT    | `/customers/{id}`       | Atualiza parcial (campos opcionais)|
| DELETE | `/customers/{id}`       | Remove (204)                       |

Email duplicado retorna **409 Conflict**.

## Roteiro de smoke test (no Swagger)

1. **POST `/customers`**
   ```json
   {"name": "Teste", "email": "t@x.com", "phone": "+55 11 99999-0000"}
   ```
   → 201 com `id`, `created_at`.

2. **POST** o mesmo email novamente → 409.

3. **GET `/customers`** → lista com 1 item.

4. **GET `/customers/{id}`** com id válido → 200; com id inválido → 404.

5. **PUT `/customers/{id}`** alterando só `phone`:
   ```json
   {"phone": "+55 11 88888-1111"}
   ```
   → 200 com `updated_at` preenchido.

6. **DELETE `/customers/{id}`** → 204; novo GET no mesmo id → 404.

## Estrutura

```
apps/customer-crud/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI app + rotas
│   ├── database.py    # engine, SessionLocal, get_db, init_db
│   ├── models.py      # Customer (SQLAlchemy)
│   ├── schemas.py     # CustomerCreate / Update / Out (Pydantic)
│   └── crud.py        # operações de banco
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

O schema do banco é criado no startup via `Base.metadata.create_all` — sem Alembic, suficiente para testes locais.

## Rodar sem Docker (opcional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/customers
uvicorn app.main:app --reload
```

Requer um Postgres acessível em `localhost:5432` com o banco `customers`.
