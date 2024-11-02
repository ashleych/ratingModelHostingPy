from models.models import FinancialStatement, Customer, LineItemValue
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
from models.models import FinancialStatement
import logging
logger = logging.getLogger(__name__)

class UpdateStatementRequest(BaseModel):
    customer_id: str
    multi_statement_ids: List[str]
    line_items: List[schema.UpdatedValue]


router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")

router = APIRouter()


@router.get("/statements/new/{customer_id}")
async def new_statement(request: Request, customer_id: str, current_user: User = Depends(auth_handler.auth_wrapper), db: Session = Depends(get_db)):

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    return templates.TemplateResponse("statements/partials/new.html", {"request": request, 'user': current_user, "customer": customer})


class StatementValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


@router.post("/statements/create_new")
async def create_statement(
    request: Request,
    current_user: User = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
    customer_id: str = Form(...),
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

        # Rule 1: If audited, cannot be projected
        # if audit_type == 'Audited' and projections:
        #     raise StatementValidationError(
        #         "Audited statements cannot be projections")

        # # Rule 2: If projected, cannot be actuals
        # if projections and actuals:
        #     raise StatementValidationError(
        #         "Statement cannot be both projections and actuals")

        # # Rule 2.1: Must be either actuals or projections
        # if not projections and not actuals:
        #     raise StatementValidationError(
        #         "Statement must be either actuals or projections")

        # # Rule 3: Must be either standalone or consolidated, not both
        # if standalone and consolidated:
        #     raise StatementValidationError(
        #         "Statement must be either standalone or consolidated, not both")

        # if not standalone and not consolidated:
        #     raise StatementValidationError(
        #         "Please select either standalone or consolidated")

        # Validate date
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
            db.commit()
            db.refresh(statement)

            # Return success response
            return RedirectResponse(
                url=f"/statements/{statement.id}",
                status_code=303  # See Other - appropriate for POST-to-GET redirect
            )

        except:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while creating statement"
            )

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


@router.get("/statements/{customer_id}")
async def view_statement(request: Request, customer_id: str, current_user: User = Depends(auth_handler.auth_wrapper), db: Session = Depends(get_db)):
    # try:
    fs_app = FsApp(db)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    statements = db.query(FinancialStatement).filter(
        FinancialStatement.customer_id == customer_id).all()
    statement_ids = [schema.FinancialStatement.model_validate(
        statement).id for statement in statements]
    statement_data = fs_app.get_statement_data(statement_ids=statement_ids)

    return templates.TemplateResponse("statements/partials/view.html", {
        "request": request, 'user': current_user,
        "customer": customer,
        "data": jsonable_encoder(statement_data["data"]),
        "statement_type": statement_data["statement_type"],
        "dates_in_statement": statement_data["dates_in_statement"]
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
