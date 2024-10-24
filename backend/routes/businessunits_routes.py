# routes/business_unit_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.models import BusinessUnit,Customer
from dependencies import get_db, auth_handler
from uuid import UUID

router = APIRouter(prefix="/business-units")

templates = Jinja2Templates(directory="../frontend/templates")

@router.get("")
async def list_business_units(
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    business_units = db.query(BusinessUnit).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "business_units/partials/list.html" 
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "business_units": business_units,
            "user": current_user,
"is_htmx":is_htmx
        }
    )

@router.get("/new")
async def create_business_unit_form(
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper)
):
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "business_units/partials/create_form.html" 
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "user": current_user,
            "is_htmx": is_htmx  
        }
    )

@router.post("/new")
async def create_business_unit(
    request: Request,
    name: str = Form(...),
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    business_unit = BusinessUnit(name=name)
    try:
        db.add(business_unit)
        db.commit()
        db.refresh(business_unit)
        return RedirectResponse(
            url="/business-units",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{business_unit_id}")
async def business_unit_detail(
    business_unit_id: UUID,
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business Unit not found")
        
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "business_units/partials/detail_content.html" if is_htmx else "business_units/detail.html"
    
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "business_unit": business_unit,
            "user": current_user,
"is_htmx":is_htmx
        }
    )

@router.get("/{business_unit_id}/edit")
async def edit_business_unit_form(
    business_unit_id: UUID,
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business Unit not found")
        
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "business_units/partials/edit_form.html" if is_htmx else "business_units/edit.html"
    
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "business_unit": business_unit,
            "user": current_user
        }
    )

@router.post("/{business_unit_id}/edit")
async def update_business_unit(
    business_unit_id: UUID,
    request: Request,
    name: str = Form(...),
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business Unit not found")
    
    try:
        business_unit.name = name
        db.commit()
        return RedirectResponse(
            url="/business-units",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

        
@router.delete("/{business_unit_id}")
async def delete_business_unit(
    business_unit_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()
        if not business_unit:
            raise HTTPException(status_code=404, detail="Business Unit not found")
            
        # Check if business unit is being used by any customers
        if db.query(Customer).filter(Customer.business_unit_id == business_unit_id).first():
            raise HTTPException(
                status_code=400,
                detail="Cannot delete business unit that is associated with customers"
            )
        
        db.delete(business_unit)
        db.commit()
        
        if request.headers.get("HX-Request") == "true":
            business_units = db.query(BusinessUnit).all()
            return templates.TemplateResponse(
                "business_units/partials/list.html",
                {
                    "request": request,
                    "business_units": business_units,
                    "user": {"name": "Test User"},
                    "is_htmx": True
                }
            )
        
        return JSONResponse(content={"message": "Business Unit deleted successfully"})
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
