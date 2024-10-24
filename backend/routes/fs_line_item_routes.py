# routes/line_item_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from models.models import LineItemMeta, Template
from dependencies import get_db
from uuid import UUID

router = APIRouter()
templates = Jinja2Templates(directory="../frontend/templates")

@router.get("/templates/{template_id}/lineitems")
async def list_line_items(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    line_items = db.query(LineItemMeta).filter(
        LineItemMeta.template_id == template_id
    ).order_by(LineItemMeta.order_no).all()
        # Clean up formulas
    for item in line_items:
        if item.formula:
            item.formula = item.formula.strip()
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/list.html",
        {
            "request": request,
            "template": template,
            "line_items": line_items,
            "is_htmx": is_htmx
        }
    )

@router.get("/templates/{template_id}/lineitems/new")
async def create_line_item_form(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get max order_no to suggest next number
    max_order = db.query(LineItemMeta).filter(
        LineItemMeta.template_id == template_id
    ).with_entities(LineItemMeta.order_no).order_by(LineItemMeta.order_no.desc()).first()
    
    next_order = (max_order[0] + 1) if max_order else 1
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/create.html",
        {
            "request": request,
            "template": template,
            "next_order": next_order,
            "is_htmx": is_htmx
        }
    )

@router.post("/templates/{template_id}/lineitems/new")
async def create_line_item(
    template_id: UUID,
    request: Request,
    fin_statement_type: str = Form(...),
    header: bool = Form(False),
    formula: Optional[str] = Form(None),
    type: str = Form(...),
    label: str = Form(...),
    name: str = Form(...),
    lag_months: Optional[int] = Form(0),
    display: bool = Form(True),
    order_no: int = Form(...),
    display_order_no: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        line_item = LineItemMeta(
            template_id=template_id,
            fin_statement_type=fin_statement_type,
            header=header,
            formula=formula,
            type=type,
            label=label,
            name=name,
            lag_months=lag_months,
            display=display,
            order_no=order_no,
            display_order_no=display_order_no or order_no
        )
        
        db.add(line_item)
        db.commit()
        db.refresh(line_item)
        
        return RedirectResponse(
            url=f"/templates/{template_id}/lineitems",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/templates/{template_id}/lineitems/{item_id}/edit")
async def edit_line_item_form(
    template_id: UUID,
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    line_item = db.query(LineItemMeta).filter(
        LineItemMeta.id == item_id,
        LineItemMeta.template_id == template_id
    ).first()
    
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/edit.html",
        {
            "request": request,
            "line_item": line_item,
            "is_htmx": is_htmx
        }
    )

@router.post("/templates/{template_id}/lineitems/{item_id}/edit")
async def update_line_item(
    template_id: UUID,
    item_id: UUID,
    request: Request,
    fin_statement_type: str = Form(...),
    header: bool = Form(False),
    formula: Optional[str] = Form(None),
    type: str = Form(...),
    label: str = Form(...),
    name: str = Form(...),
    lag_months: Optional[int] = Form(0),
    display: bool = Form(True),
    order_no: int = Form(...),
    display_order_no: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    line_item = db.query(LineItemMeta).filter(
        LineItemMeta.id == item_id,
        LineItemMeta.template_id == template_id
    ).first()
    
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    try:
        line_item.fin_statement_type = fin_statement_type
        line_item.header = header
        line_item.formula = formula
        line_item.type = type
        line_item.label = label
        line_item.name = name
        line_item.lag_months = lag_months
        line_item.display = display
        line_item.order_no = order_no
        line_item.display_order_no = display_order_no or order_no
        
        db.commit()
        return RedirectResponse(
            url=f"/templates/{template_id}/lineitems",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/templates/{template_id}/lineitems/{item_id}")
async def delete_line_item(
    template_id: UUID,
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    line_item = db.query(LineItemMeta).filter(
        LineItemMeta.id == item_id,
        LineItemMeta.template_id == template_id
    ).first()
    
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    try:
        db.delete(line_item)
        db.commit()
        
        if request.headers.get("HX-Request") == "true":
            line_items = db.query(LineItemMeta).filter(
                LineItemMeta.template_id == template_id
            ).order_by(LineItemMeta.order_no).all()
            
            return templates.TemplateResponse(
                "lineitems/partials/list.html",
                {
                    "request": request,
                    "template_id": template_id,
                    "line_items": line_items,
                    "is_htmx": True
                }
            )
        
        return {"message": "Line item deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}/lineitems/{item_id}")
async def get_line_item_detail(
    template_id: UUID,
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    # Get line item with related template
    line_item = db.query(LineItemMeta).filter(
        LineItemMeta.id == item_id,
        LineItemMeta.template_id == template_id
    ).join(Template).first()
    
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/detail.html",
        {
            "request": request,
            "line_item": line_item,
            "is_htmx": is_htmx
        }
    )