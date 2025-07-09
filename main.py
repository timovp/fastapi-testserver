# main.py
import os
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Field, SQLModel, create_engine, Session, select

#
# ─── API‐KEY SETUP ──────────────────────────────────────────────────────────────
#
API_KEY = os.getenv("MY_API_KEY", "secret123")
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
        headers={"WWW-Authenticate": "API key"},
    )


#
# ─── DATABASE MODEL & ENGINE ───────────────────────────────────────────────────
#
DATABASE_URL = "sqlite:///./items.db"
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False},
)


class AcceptedInvoiceNumber(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    accepted_invoice_number: str


def get_session():
    with Session(engine) as session:
        yield session


#
# ─── LIFESPAN ───────────────────────────────────────────────────────────────────
#
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    SQLModel.metadata.create_all(engine)
    yield
    # Shutdown: (nothing to do for SQLite, but you could close connections, etc.)


app = FastAPI(lifespan=lifespan)


#
# ─── CRUD ENDPOINTS ─────────────────────────────────────────────────────────────
#
@app.get(
    "/accepted_invoice_numbers",
    response_model=List[AcceptedInvoiceNumber],
    dependencies=[Depends(get_api_key)],
)
def read_items(session: Session = Depends(get_session)):
    return session.exec(select(AcceptedInvoiceNumber)).all()


@app.post(
    "/accepted_invoice_numbers",
    response_model=AcceptedInvoiceNumber,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
def create_item(item: AcceptedInvoiceNumber, session: Session = Depends(get_session)):
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.put(
    "/accepted_invoice_numbers/{invoice_id}",
    response_model=AcceptedInvoiceNumber,
    dependencies=[Depends(get_api_key)],
)
def update_invoice(
    invoice_id: int, invoice_number: str, session: Session = Depends(get_session)
):
    existing_invoice = session.get(AcceptedInvoiceNumber, invoice_id)
    if not existing_invoice:
        raise HTTPException(status_code=404, detail="Item not found")
    existing_invoice.accepted_invoice_number = invoice_number
    session.add(existing_invoice)
    session.commit()
    session.refresh(existing_invoice)
    return existing_invoice


@app.get("/healthz", include_in_schema=False)
async def health():
    return {"status": "ok"}
