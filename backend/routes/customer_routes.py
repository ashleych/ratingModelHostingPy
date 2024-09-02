from fastapi import APIRouter, Request, Form, HTTPException,Depends
from fastapi.responses import RedirectResponse


from fastapi.templating import Jinja2Templates
from models.models import Customer,FinancialStatement,BusinessUnit
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine

router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse(url="/customers", status_code=303)

@router.get("/customers")
async def list_customers(request: Request, db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return templates.TemplateResponse("customers/partials/list.html", {"request": request, "customers": customers})


@router.get("/customers/{customer_id}")
async def customer_detail(request: Request, customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer_id).all()
    
    return templates.TemplateResponse("customers/partials/detail.html", {
        "request": request, 
        "customer": customer,
        "statements": statements
    })

@router.get("/customers/new")
async def new_customer(request: Request):
    return templates.TemplateResponse("customers/partials/new.html", {"request": request})


@router.delete("/customers/{customer_id}")
async def delete_customer(request: Request, customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    
    return {"success": True, "message": "Customer deleted successfully"}

@router.post("/customers/new")
async def create_customer(
    request: Request,
    db: Session = Depends(get_db),
    cif_number: str = Form(...),
    customer_name: str = Form(...),
    group_name: str = Form(...),
    business_unit: int = Form(...),
    relationship_type: str = Form(...),
    internal_risk_rating: str = Form(...)
):
    business_unit_obj = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit).first()
    if not business_unit_obj:
        raise HTTPException(status_code=400, detail="Invalid business unit")
    
    customer = Customer(
        cif_number=cif_number,
        customer_name=customer_name,
        group_name=group_name,
        business_unit=business_unit_obj,
        relationship_type=relationship_type,
        internal_risk_rating=internal_risk_rating
    )
    db.add(customer)
    db.commit()
    return templates.TemplateResponse("customers/partials/created.html", {"request": request, "customer": customer})

@router.get("/customers/{customer_id}/edit")
async def edit_customer(request: Request, customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    business_units = db.query(BusinessUnit).all()
    return templates.TemplateResponse("customers/partials/edit.html", {"request": request, "customer": customer, "business_units": business_units})

@router.post("/customers/{customer_id}/edit")
async def update_customer(
    request: Request,
    customer_id: str,
    db: Session = Depends(get_db),
    cif_number: str = Form(...),
    customer_name: str = Form(...),
    group_name: str = Form(...),
    business_unit: str = Form(...),
    relationship_type: str = Form(...),
    internal_risk_rating: str = Form(...)
):
    # Fetch the customer from the database
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Fetch the business unit from the database
    business_unit_obj = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit).first()
    if not business_unit_obj:
        raise HTTPException(status_code=400, detail=f"Invalid business unit -{business_unit}")
    
    # Update customer fields
    customer.cif_number = cif_number
    customer.customer_name = customer_name
    customer.group_name = group_name
    customer.business_unit = business_unit_obj
    customer.relationship_type = relationship_type
    customer.internal_risk_rating = internal_risk_rating
    
    try:
        # Commit the changes to the database
        db.commit()
    except Exception as e:
        # If there's an error, rollback the changes and raise an HTTP exception
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while updating the customer: {str(e)}")
    
    # Fetch all business units to pass to the template
    business_units = db.query(BusinessUnit).all()
    
    # Render the updated.html template with the updated customer information
    return templates.TemplateResponse(
        "customers/partials/updated.html",
        {
            "request": request,
            "customer": customer,
            "business_units": business_units
        }
    )