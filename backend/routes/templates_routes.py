# routes/template_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.statement_models import Template
from models.rating_model_model import TemplateSourceCSV
from dependencies import get_db, auth_handler
from uuid import UUID

router = APIRouter(prefix="/templates")
templates = Jinja2Templates(directory="../frontend/templates")

@router.get("")
async def list_templates(
    request: Request,
    db: Session = Depends(get_db)
):
    template_list = db.query(Template).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "financialTemplate/partials/list.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "templates": template_list,
            "is_htmx": is_htmx
        }
    )

@router.get("/new")
async def create_template_form(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get available template source CSVs for dropdown
    source_csvs = db.query(TemplateSourceCSV).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "financialTemplate/partials/create.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "source_csvs": source_csvs,
            "is_htmx": is_htmx
        }
    )

@router.post("/new")
async def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    template_source_csv_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    try:
        template = Template(
            name=name,
            description=description,
            template_source_csv_id=template_source_csv_id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return RedirectResponse(
            url="/templates",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{template_id}")
async def get_template(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "financialTemplate/partials/detail.html",
        {
            "request": request,
            "template": template,
            "is_htmx": is_htmx
        }
    )

@router.get("/{template_id}/edit")
async def edit_template_form(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    source_csvs = db.query(TemplateSourceCSV).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    
    return templates.TemplateResponse(
        "financialTemplate/partials/edit.html",
        {
            "request": request,
            "template": template,
            "source_csvs": source_csvs,
            "is_htmx": is_htmx
        }
    )

@router.post("/{template_id}/edit")
async def update_template(
    template_id: UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    template_source_csv_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        template.name = name
        template.description = description
        template.template_source_csv_id = template_source_csv_id
        db.commit()
        return RedirectResponse(
            url="/templates",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        db.delete(template)
        db.commit()
        
        # If it's an HTMX request, return updated list
        if request.headers.get("HX-Request") == "true":
            templates_list = db.query(Template).all()
            return templates.TemplateResponse(
                "financialTemplate/partials/list.html",
                {
                    "request": request,
                    "templates": templates_list,
                    "is_htmx": True
                }
            )
        
        return {"message": "Template deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))