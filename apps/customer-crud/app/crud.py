from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


def create_customer(db: Session, payload: schemas.CustomerCreate) -> models.Customer:
    customer = models.Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> models.Customer | None:
    return db.get(models.Customer, customer_id)


def list_customers(db: Session, skip: int = 0, limit: int = 100) -> list[models.Customer]:
    stmt = select(models.Customer).order_by(models.Customer.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update_customer(
    db: Session, customer_id: int, payload: schemas.CustomerUpdate
) -> models.Customer | None:
    customer = db.get(models.Customer, customer_id)
    if customer is None:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> bool:
    customer = db.get(models.Customer, customer_id)
    if customer is None:
        return False
    db.delete(customer)
    db.commit()
    return True
