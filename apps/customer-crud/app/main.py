from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Customer CRUD",
    version="0.1.0",
    description="API simples de cadastro de clientes (nome, email, telefone).",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/customers",
    response_model=schemas.CustomerOut,
    status_code=status.HTTP_201_CREATED,
    tags=["customers"],
)
def create_customer(
    payload: schemas.CustomerCreate, db: Session = Depends(get_db)
) -> schemas.CustomerOut:
    try:
        return crud.create_customer(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )


@app.get(
    "/customers",
    response_model=list[schemas.CustomerOut],
    tags=["customers"],
)
def list_customers(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[schemas.CustomerOut]:
    return crud.list_customers(db, skip=skip, limit=limit)


@app.get(
    "/customers/{customer_id}",
    response_model=schemas.CustomerOut,
    tags=["customers"],
)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> schemas.CustomerOut:
    customer = crud.get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return customer


@app.put(
    "/customers/{customer_id}",
    response_model=schemas.CustomerOut,
    tags=["customers"],
)
def update_customer(
    customer_id: int,
    payload: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
) -> schemas.CustomerOut:
    try:
        customer = crud.update_customer(db, customer_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return customer


@app.delete(
    "/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["customers"],
)
def delete_customer(customer_id: int, db: Session = Depends(get_db)) -> Response:
    if not crud.delete_customer(db, customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
