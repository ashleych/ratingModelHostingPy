from models.models import FinancialStatement, Customer,LineItemValue
from fastapi import APIRouter, Request, Form, HTTPException,Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.models import Customer
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from schema import schema
from customer_financial_statement import FsApp

from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel
from typing import List
from schema import schema
from schema.schema import User
from dependencies import get_db,auth_handler
class UpdateStatementRequest(BaseModel):
    customer_id:str
    multi_statement_ids:List[str]
    line_items: List[schema.UpdatedValue]
router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")

router = APIRouter()

@router.get("/statements/new")
async def new_statement(request: Request, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return templates.TemplateResponse("statements/new.html", {"request": request,'user':current_user, "customers": customers})

@router.post("/statements/new")
async def create_statement(request: Request, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db), customer_id: int = Form(...)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    fs_app = FsApp(db)
    statement = fs_app.create_statement_data_for_customer(customer.cif_number)
    
    return templates.TemplateResponse("statements/created.html", {"request": request,'user':current_user, "statement": statement})



@router.get("/statements/{customer_id}")
async def view_statement(request:Request,customer_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    # try:
    fs_app = FsApp(db)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer_id).all()
    statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]
    statement_data= fs_app.get_statement_data(statement_ids=statement_ids)
    
    return templates.TemplateResponse("statements/partials/view.html", {
            "request": request,'user':current_user,
            "customer":customer,
            "data": jsonable_encoder(statement_data["data"]),
            "statement_type": statement_data["statement_type"],
            "dates_in_statement": statement_data["dates_in_statement"]
        })


    
# @router.post("/statements/{statement_id}/update")
# async def update_statement_old(request: Request, statement_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db), field_name: str = Form(...), new_value: float = Form(...)):
#     fs_app = FsApp(db)
#     print("field name is :",field_name)
#     print("field name is :",new_value)

#     try:
#         fs_app = FsApp(db)
#         print("field name is:", field_name)
#         print("new value is:", new_value)
#         updated_values = fs_app.update_field_and_derived_values(statement_id, field_name, new_value)
#         return {"success": True, "updated_values": updated_values}
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
#     return {"success": True, "updated_values": updated_values}

@router.post("statements/update_statement")
async def update_statement(request: UpdateStatementRequest, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    fs_app = FsApp(db)
    
        # Group updates by statement_id
    updates_by_statement = {}
    for item in request.line_items:
        if item.statement_id not in updates_by_statement:
            updates_by_statement[item.statement_id] = []
        updates_by_statement[item.statement_id].append(item)

    # Process updates for each statement
    all_updated_data = []
    for statement_id, updates in updates_by_statement.items():
        fs_app.update_statement(statement_id, updates)
    updated_data = fs_app.get_statement_data(request.multi_statement_ids)
    return RedirectResponse(url=f"/statements/{request.customer_id}", status_code=303)
