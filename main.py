# main.py
import os
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Field, SQLModel, create_engine, Session, select
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# serve files from ./static as root

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
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/items.db")
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False},
)


class AcceptedInvoiceNumber(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    accepted_invoice_number: str


class AcceptedVendorName(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    accepted_vendor_name: str


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


# serve UI assets under /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# serve index.html at root for SPA


@app.get("/")
async def get_index():
    return FileResponse("static/index.html")


#
# ─── CRUD ENDPOINTS ─────────────────────────────────────────────────────────────
#
@app.get(
    "/accepted_invoice_numbers",
    response_model=List[AcceptedInvoiceNumber],
    dependencies=[Depends(get_api_key)],
)
def read_invoice_numbers(session: Session = Depends(get_session)):
    return session.exec(select(AcceptedInvoiceNumber)).all()


@app.post(
    "/accepted_invoice_numbers",
    response_model=AcceptedInvoiceNumber,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
def create_invoice_numbers(
    invoice_number: AcceptedInvoiceNumber, session: Session = Depends(get_session)
):
    session.add(invoice_number)
    session.commit()
    session.refresh(invoice_number)
    return invoice_number


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


@app.get(
    "/accepted_vendor_names",
    response_model=List[AcceptedVendorName],
    dependencies=[Depends(get_api_key)],
)
def read_vendor_names(session: Session = Depends(get_session)):
    return session.exec(select(AcceptedVendorName)).all()


@app.post(
    "/accepted_vendor_names",
    response_model=AcceptedVendorName,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
def create_vendor_name(
    vendor_name: AcceptedVendorName, session: Session = Depends(get_session)
):
    session.add(vendor_name)
    session.commit()
    session.refresh(vendor_name)
    return vendor_name


@app.put(
    "/accepted_vendor_names/{vendor_id}",
    response_model=AcceptedVendorName,
    dependencies=[Depends(get_api_key)],
)
def update_vendor_name(
    vendor_id: int, vendor_name: str, session: Session = Depends(get_session)
):
    existing_vendor = session.get(AcceptedVendorName, vendor_id)
    if not existing_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    existing_vendor.accepted_vendor_name = vendor_name
    session.add(existing_vendor)
    session.commit()
    session.refresh(existing_vendor)
    return existing_vendor


@app.get("/healthz", include_in_schema=False)
async def health():
    return {"status": "ok"}
