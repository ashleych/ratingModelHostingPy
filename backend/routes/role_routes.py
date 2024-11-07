# routes/template_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.models import Role
from dependencies import get_db, auth_handler
from uuid import UUID

router = APIRouter(prefix="/roles")
templates = Jinja2Templates(directory="../frontend/templates")

@router.get("")
async def list_templates(
    request: Request,
    db: Session = Depends(get_db)
):
    list = db.query(Role).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    htmltemplate = "roles/partials/list.html"
    return templates.TemplateResponse(
        htmltemplate,
        {
            "request": request,
            "roles": list,
            "is_htmx": is_htmx
        }
    )

@router.get("/new")
async def create_template_form(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get available template source CSVs for dropdown
    is_htmx = request.headers.get("HX-Request") == "true"
    htmltemplate = "roles/partials/new.html"
    return templates.TemplateResponse(
        htmltemplate,
        {
            "request": request,
            "is_htmx": is_htmx
        }
    )

@router.post("/new")
async def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        role = Role(
            name=name,
            description=description
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return RedirectResponse(
            url="/roles",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{role_id}")
async def get_template(
    role_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "roles/partials/detail.html",
        {
            "request": request,
            "role": role,
            "is_htmx": is_htmx
        }
    )

@router.get("/{role_id}/edit")
async def edit_role_form(
    role_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    
    return templates.TemplateResponse(
        "roles/partials/edit.html",
        {
            "request": request,
            "role": role,
            "is_htmx": is_htmx
        }
    )

@router.post("/{role_id}/edit")
async def update_template(
    role_id: UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    try:
        role.name = name
        role.description = description
        db.commit()
        return RedirectResponse(
            url="/roles",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{role_id}")
async def delete_template(
    role_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    try:
        db.delete(role)
        db.commit()
        
        # If it's an HTMX request, return updated list
        # if request.headers.get("HX-Request") == "true":
        #     list = db.query(Role).all()
        #     return templates.TemplateResponse(
        #         "roles/partials/list.html",
        #         {
        #             "request": request,
        #             "templates": list,
        #             "is_htmx": True
        #         }
        #     )
        return RedirectResponse(url="/roles", status_code=303)
        # return {"message": "Role deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))