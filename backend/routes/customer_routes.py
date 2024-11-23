from db.database import SessionLocal, engine
from dependencies import auth_handler, get_db
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from enums_and_constants import WorkflowStage
from models.models import BusinessUnit, Customer
from models.rating_instance_model import RatingFactorScore, RatingInstance
from models.rating_model_model import RatingFactor, RatingModel
from models.statement_models import FinancialStatement
from models.workflow_model import WorkflowAction
from schema.schema import User
from sqlalchemy.orm import Session, joinedload

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

from uuid import UUID

from typing import List, Dict, Union
from uuid import UUID

def organise_workflow_actions(workflow_action_ids: List[Union[UUID, str]], db: Session) -> Dict[UUID, UUID]:
    """
    Organizes workflow actions by financial statement ID.
    Prioritizes APPROVED stage actions, falls back to head=True actions if no APPROVED found.
    
    Args:
        workflow_action_ids: List of workflow action IDs to organize
        db: SQLAlchemy database session
        
    Returns:
        Dict mapping financial statement IDs to their most relevant workflow action IDs
    """
    # Query workflow actions with their related rating instances
    wf_actions = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.id.in_(workflow_action_ids))
        .join(WorkflowAction.rating_instance)
        .all()
    )
    
    # Group by financial statement ID
    actions_by_statement: Dict[UUID, List[WorkflowAction]] = {}
    for action in wf_actions:
        if not action.rating_instance:
            continue
            
        fin_stmt_id = action.rating_instance.financial_statement_id
        if fin_stmt_id not in actions_by_statement:
            actions_by_statement[fin_stmt_id] = []
        actions_by_statement[fin_stmt_id].append(action)
    
    result: Dict[UUID, UUID] = {}
    
    # Process each financial statement's workflow actions
    for fin_stmt_id, actions in actions_by_statement.items():
        # First look for APPROVED stage actions
        approved_actions = [
            action for action in actions 
            if action.workflow_stage == WorkflowStage.APPROVED
        ]
        
        if approved_actions:
            # Take the latest approved action
            latest_approved = max(
                approved_actions,
                key=lambda x: x.created_at
            )
            result[fin_stmt_id] = latest_approved.id
            continue
            
        # If no approved actions, look for head=True actions
        head_actions = [
            action for action in actions 
            if action.head == True and not action.is_stale
        ]
        
        if head_actions:
            # Take the latest head action
            latest_head = max(
                head_actions,
                key=lambda x: x.created_at
            )
            result[fin_stmt_id] = latest_head.id
    
    return result

@router.get("/customers/{customer_id}")
async def customer_detail(request: Request, customer_id: str, current_user:User = Depends(auth_handler.auth_wrapper),db: Session = Depends(get_db)):
    customer = (db.query(Customer)
                .options(
                    joinedload(Customer.business_unit)
                    .joinedload(BusinessUnit.template)
                )
                .filter(Customer.id == customer_id)
                .first())
    business_unit_obj = db.query(BusinessUnit).filter(BusinessUnit.id == customer.business_unit_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer_id).all()
    
    # Fetch rating instances for all statements
    statement_ids = [statement.id for statement in statements]
    # rating_instances = db.query(RatingInstance).filter(RatingInstance.financial_statement_id.in_(statement_ids)).all()
        # Fetch rating instances with rating model info for all statements
    statement_ids = [statement.id for statement in statements]
    workflow_actions = db.query(WorkflowAction).filter(WorkflowAction.head==True).all()
    workflow_action_ids = [wf.id for wf in workflow_actions]

    statement_wise_workflow_actions= organise_workflow_actions(workflow_action_ids=workflow_action_ids,db=db)
    
    def get_rating_instance_from_workflow_action_id(wf_id: str| UUID,db:Session):
        return db.query(WorkflowAction).filter(WorkflowAction.id==wf_id).first().rating_instance_id


        
    rating_instance_ids= [get_rating_instance_from_workflow_action_id(wf_id,db) for stmt_id,wf_id in  statement_wise_workflow_actions.items()  ]

    # rating_instances = (db.query(RatingInstance, RatingModel)
    #     .join(RatingModel, RatingInstance.rating_model_id == RatingModel.id)
    #     .filter(RatingInstance.id.in_(rating_instance_ids))
    #     .all())
    rating_instances = (
        db.query(RatingInstance, RatingModel, WorkflowAction)
        .join(RatingModel, RatingInstance.rating_model_id == RatingModel.id)
        .join(WorkflowAction, RatingInstance.id == WorkflowAction.rating_instance_id)
        .filter(WorkflowAction.id.in_(list(statement_wise_workflow_actions.values())))
        .all()
    )
    # rating_instances = db.query(RatingInstance).filter(RatingInstance.id.in_(rating_instance_ids)).all()
    # Create a dictionary mapping financial statement IDs to rating instances
    # rating_map = {ri.financial_statement_id: ri for ri in rating_instances}
    # rating_map = {ri.financial_statement_id: ri[0] for ri in rating_instances}

    # # Attach rating instances to statements
    # for statement in statements:
    #     statement.rating_instance = rating_map.get(statement.id)
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse("customers/partials/detail.html", {
        "request": request,'user':current_user, 
        "customer": customer,
        "rating_instances": rating_instances, 
        "statements": statements,
        "business_unit":business_unit_obj,
        "is_htmx":is_htmx,
        'statement_wise_workflow_actions':statement_wise_workflow_actions


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