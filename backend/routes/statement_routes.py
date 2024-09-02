from models.models import FinancialStatement, Customer
from fastapi import APIRouter, Request, Form, HTTPException,Depends
from fastapi.templating import Jinja2Templates
from models.models import Customer
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine

from customer_financial_statement import FsApp



router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/statements/new")
async def new_statement(request: Request, db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return templates.TemplateResponse("statements/new.html", {"request": request, "customers": customers})

@router.post("/statements/new")
async def create_statement(request: Request, db: Session = Depends(get_db), customer_id: int = Form(...)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    fs_app = FsApp(db)
    statement = fs_app.create_statement_data_for_customer(customer.cif_number)
    
    return templates.TemplateResponse("statements/created.html", {"request": request, "statement": statement})

@router.get("/statements/{statement_id}")
async def view_statement(request: Request, statement_id: int, db: Session = Depends(get_db)):
    statement = db.query(FinancialStatement).filter(FinancialStatement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    line_items = db.query(LineItemValue).filter(LineItemValue.financial_statement_id == statement_id).all()
    data = [[item.line_item_meta.name, item.value] for item in line_items]
    
    return templates.TemplateResponse("statements/view.html", {"request": request, "statement": statement, "data": data})

@router.post("/statements/{statement_id}/update")
async def update_statement(request: Request, statement_id: int, db: Session = Depends(get_db), field_name: str = Form(...), new_value: float = Form(...)):
    fs_app = FsApp(db)
    updated_values = fs_app.update_field_and_derived_values(statement_id, field_name, new_value)
    
    return {"success": True, "updated_values": updated_values}