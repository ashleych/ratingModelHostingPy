# FastAPI endpoint example
# routes/template_routes.py

from models.statement_models import Template
from models.statement_models import FinancialStatement, LineItemMeta, LineItemValue
from models.models import Customer
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.models import Customer
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from rating_workflow_processing import create_workflow_for_customer
from schema import schema
from customer_financial_statement import FsApp

from fastapi.encoders import jsonable_encoder
from typing import Optional
from pydantic import BaseModel
from typing import List
from schema import schema
from schema.schema import ErrorResponse, User, WorkflowError
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


@router.post("/workflow/create/{cif_number}")
async def create_workflow(
    cif_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper),
):
    try:
        customer=db.query(Customer).filter(Customer.cif_number==cif_number).first()
        workflow = create_workflow_for_customer(db, cif_number, current_user,customer)
        return {"success": True, "workflow_id": str(workflow.id)}
    except WorkflowError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                code=e.code.value,
                message=e.message,
                details=e.details
            ).dict()
        )
