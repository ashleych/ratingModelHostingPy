from models.statement_models import Template
from models.statement_models import FinancialStatement, LineItemMeta, LineItemValue
from models.models import Customer
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.models import Customer
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from schema import schema
from customer_financial_statement import FsApp

from fastapi.encoders import jsonable_encoder
from typing import Optional
from pydantic import BaseModel
from typing import List
from schema import schema
from schema.schema import User
from dependencies import get_db, auth_handler

from datetime import datetime
from models.statement_models import FinancialStatement
import logging
from models.statement_models import LineItemValue
logger = logging.getLogger(__name__)

class UpdateStatementRequest(BaseModel):
    customer_id: str
    multi_statement_ids: List[str]
    line_items: List[schema.UpdatedValue]
from models import models

router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")

router = APIRouter()

from uuid import UUID

from models.models import BusinessUnit
from models.statement_models import Template
from sqlalchemy.orm import joinedload
@router.get("/statements/new/{customer_id}")
async def new_statement(
    request: Request,
    customer_id: UUID,
    current_user: User = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    customer = (db.query(Customer)
                .options(
                    joinedload(Customer.business_unit)
                    .joinedload(BusinessUnit.template)
                )
                .filter(Customer.id == customer_id)
                .first())
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get template from customer's business unit
    template = None
    if customer.business_unit and customer.business_unit.template:
        template = customer.business_unit.template

    # Create a default statement date (current date or None)
    statement_date = None  # or datetime.now() if you want to filter by current date
    
    fs_app = FsApp(db)
    # Get all available statements with recommendation flags
    available_statements = fs_app.get_available_preceding_statements(
        customer_id=customer_id,
        statement_date=statement_date
    )
    
    # Get the recommended statement (if any)
    recommended_statement = next(
        (item for item in available_statements if item['is_recommended']), 
        None
    )

    return templates.TemplateResponse(
        "statements/partials/new.html",
        {
            "request": request,
            "customer": customer,
            "template": template,
            "user": current_user,
            "best_preceding_statement": recommended_statement if recommended_statement else None,
            "available_statements": available_statements,
                        "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )
class StatementValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)
# Add this function at the module level

def initiate_line_item_values(db: Session, statement: FinancialStatement, template_id: str|UUID):
    """
    Initialize LineItemValue entries for all LineItemMeta records associated with the template
    """
    try:
        # Get all LineItemMeta records for this template
        line_item_metas = db.query(LineItemMeta).filter(
            LineItemMeta.template_id == template_id
        ).all()

        # Create LineItemValue entries for each LineItemMeta
        line_item_values = []
        for meta in line_item_metas:
            line_item_value = LineItemValue(
                financial_statement_id=statement.id,
                line_item_meta_id=meta.id,
                value=None  # Initially set to None
            )
            line_item_values.append(line_item_value)

        # Bulk insert all LineItemValues
        if line_item_values:
            db.bulk_save_objects(line_item_values)
 
        return True
    except Exception as e:
        logger.error(f"Error initializing line item values: {str(e)}")
        return False

@router.post("/statements/create_new")
async def create_statement(
    request: Request,
    current_user: User = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
    customer_id: str = Form(...),
    template_id:str | UUID=Form(...),
    audit_type: str = Form(...),
    financials_period_year: int = Form(...),
    financials_period_month: int = Form(...),
    financials_period_date: int = Form(...),
    statement_type: str = Form(...),
    statement_scope: str = Form(...),
    preferred_statement: Optional[bool] = Form(False)
):
    try:
        # Validate customer exists
        customer = db.query(Customer).filter(
            Customer.id == customer_id).first()
        if not customer:
            raise StatementValidationError("Customer not found")

        # Business rule validations
        if audit_type not in ['Audited', 'Unaudited']:
            raise StatementValidationError("Invalid audit type")


        try:
            statement_date = datetime(
                year=financials_period_year,
                month=financials_period_month,
                day=financials_period_date
            )

            # Optional: Add validation for dates not in the future
            if statement_date > datetime.now():
                raise StatementValidationError(
                    "Statement date cannot be in the future")

        except ValueError:
            raise StatementValidationError("Invalid date combination")
        # Create statement object
        statement = FinancialStatement(
            customer_id=customer_id,
            template_id=template_id,  # You'll need to get this from somewhere
            audit_type=audit_type,
            financials_period_year=financials_period_year,
            financials_period_month=financials_period_month,
            financials_period_date=financials_period_date,
            actuals=(statement_type == 'actuals'),
            projections=(statement_type == 'projections'),
            standalone=(statement_scope == 'standalone'),
            consolidated=(statement_scope == 'consolidated'),
            preferred_statement=preferred_statement,
            is_dirty=True,
        )
        # Create statement object
        # Save to database
        try:
            db.add(statement)
            db.flush()  # Flush to get the statement ID but don't commit yet

            # Initialize line item values
            success = initiate_line_item_values(db, statement, template_id)
            
            if not success:
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize line item values"
                )

            # If everything is successful, commit the transaction
            db.commit()
            db.refresh(statement)

            return RedirectResponse(
                url=f"/statements/{customer_id}",
                status_code=303
            )


        except:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while creating statement"
            )
    # make blank entries in the database in LineITemValue table for each LineItemMeta
    
    #write a function initiate_lineItem values 
    except StatementValidationError as validation_error:
        # Render the form again with error messages
        return templates.TemplateResponse(
            "statements/partials/new.html",
            {
                "request": request,
                "user": current_user,
                "customer": customer,
                "error": validation_error.detail,
                "form_data": {
                    "audit_type": audit_type,
                    "financials_period_year": financials_period_year,
                    "financials_period_month": financials_period_month,
                    "financials_period_date": financials_period_date,
                    "actuals": actuals,
                    "projections": projections,
                    "standalone": standalone,
                    "consolidated": consolidated,
                    "preferred_statement": preferred_statement
                }
            },
            status_code=400
        )
    except Exception as e:
        # Log the unexpected error
        logger.error(f"Unexpected error creating statement: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )

@router.get("/statements/view/{statement_id}")
async def view_statement(
    request: Request, 
    statement_id: str, 
    current_user: User = Depends(auth_handler.auth_wrapper), 
    db: Session = Depends(get_db)
):
    fs_app = FsApp(db)
    
    # Get the initial statement
    current_statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id
    ).first()
    
    if not current_statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    # Get the customer for this statement
    customer = db.query(Customer).filter(
        Customer.id == current_statement.customer_id
    ).first()
    
    # Build sequence of statements by traversing backwards through preceding_statement_id
    statement_sequence = []
    stmt = current_statement
    
    while stmt:
        statement_sequence.insert(0, stmt.id)  # Insert at beginning to maintain chronological order
        if stmt.preceding_statement_id:
            stmt = db.query(FinancialStatement).filter(
                FinancialStatement.id == stmt.preceding_statement_id
            ).first()
        else:
            stmt = None
    
    # Get statement data using the ordered sequence
    statement_data = fs_app.get_statement_data(statement_ids=statement_sequence)
    
    return templates.TemplateResponse("statements/partials/view.html", {
        "request": request,
        "user": current_user,
        "customer": customer,
        "data": jsonable_encoder(statement_data["data"]),
        "statement_type": statement_data["statement_type"],
        "dates_in_statement": statement_data["dates_in_statement"],
                    "is_htmx": request.headers.get("HX-Request") == "true"
    })
@router.post("statements/update_statement")
async def update_statement(request: UpdateStatementRequest, current_user: User = Depends(auth_handler.auth_wrapper), db: Session = Depends(get_db)):
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

@router.delete("/statements/{statement_id}")
async def delete_statement(
    request: Request,
    statement_id: str|UUID, 
    current_user: User = Depends(auth_handler.auth_wrapper), 
    db: Session = Depends(get_db)
):
    try:
        # Query the statement
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.id == statement_id
        ).first()
        customer_id=statement.customer_id
        
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")
            
        # Delete associated LineItemValues first (due to foreign key constraint)
        db.query(LineItemValue).filter(
            LineItemValue.financial_statement_id == statement_id
        ).delete()
        
        # Delete the statement
        db.delete(statement)
        db.commit()
        return RedirectResponse(
            url=f"/customers/{customer_id}",
            headers={
                "HX-Redirect": f"/customers/{customer_id}",

            },
                status_code=303
        )
        # Return success response
        return {"message": "Statement deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting statement: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting statement")