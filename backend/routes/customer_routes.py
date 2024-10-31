from fastapi import APIRouter, Request, Form, HTTPException,Depends
from fastapi.responses import RedirectResponse


from fastapi.templating import Jinja2Templates
from models.models import Customer,FinancialStatement,BusinessUnit,RatingInstance,RatingFactor,RatingFactorScore
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from schema.schema import User
from dependencies import get_db,auth_handler
router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")
@router.get("/customers")
async def list_customers(request: Request,  current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
  # Check if it's an HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # Choose template based on request type
    return templates.TemplateResponse("customers/partials/list.html", {"request": request,'user':current_user, "customers": customers,"is_htmx":is_htmx})


@router.get("/customers/new")
async def new_customer(request: Request,  current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    business_units = db.query(BusinessUnit).all()

    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse("customers/partials/new.html", {"request": request,'user':current_user,"business_units": business_units,"is_htmx":is_htmx})



#     })


@router.get("/customers/{customer_id}")
async def customer_detail(request: Request, customer_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer_id).all()
    
    # Fetch rating instances for all statements
    statement_ids = [statement.id for statement in statements]
    rating_instances = db.query(RatingInstance).filter(RatingInstance.financial_statement_id.in_(statement_ids)).all()
    
    # Create a dictionary mapping financial statement IDs to rating instances
    rating_map = {ri.financial_statement_id: ri for ri in rating_instances}
    
    # Attach rating instances to statements
    for statement in statements:
        statement.rating_instance = rating_map.get(statement.id)
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse("customers/partials/detail.html", {
        "request": request,'user':current_user, 
        "customer": customer,
        "statements": statements,
        "is_htmx":is_htmx
    })

@router.delete("/customers/{customer_id}")
async def delete_customer(request: Request, customer_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    
    return {"success": True, "message": "Customer deleted successfully"}


    
@router.post("/customers/new")
async def create_customer(
    request: Request,
    current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db),
    customer_name: str = Form(...),
    group_name: str = Form(...),
    cif_number: str = Form(...),
    business_unit: str = Form(...),
    relationship_type: str = Form(...),
    internal_risk_rating: str = Form(...),
):
    # Validate business unit
    business_unit_obj = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit).first()
    if not business_unit_obj:
        raise HTTPException(status_code=400, detail="Invalid business unit")

    # Create new customer first
    new_customer = Customer(
        customer_name=customer_name,
        cif_number=cif_number,
        group_name=group_name,
        business_unit_id=business_unit,
        relationship_type=relationship_type,
        internal_risk_rating=internal_risk_rating,
        # workflow_action_type="Create"  # Set the initial workflow action type
    )
    db.add(new_customer)
    db.flush()  # This will assign an ID to the new customer

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the customer: {str(e)}")

    is_htmx = request.headers.get("HX-Request") == "true"
    return {"message": "Customer created successfully", "customer_id": new_customer.id,"is_htmx":is_htmx}
@router.get("/customers/{customer_id}/edit")
async def edit_customer(request: Request, customer_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    business_units = db.query(BusinessUnit).all()

    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse("customers/partials/edit.html", {"request": request,"is_htmx":is_htmx,'user':current_user, "customer": customer, "business_units": business_units})

@router.post("/customers/{customer_id}/edit")
async def update_customer(
    request: Request,
    customer_id: str,
    current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db),
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
    
    is_htmx = request.headers.get("HX-Request") == "true"
    # Render the updated.html template with the updated customer information
    return templates.TemplateResponse(
        "customers/partials/updated.html",
        {
            "request": request,'user':current_user,
            "customer": customer,
            "business_units": business_units,
            "is_htmx":is_htmx
        }
    )