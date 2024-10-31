# routes/rating_model_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.models import RatingModel, Template
from dependencies import get_db, auth_handler
from uuid import UUID

router = APIRouter(prefix="/rating-models")
templates = Jinja2Templates(directory="../frontend/templates")

@router.get("")
async def list_rating_models(
    request: Request,
    db: Session = Depends(get_db)
):
    rating_models = db.query(RatingModel).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "ratingModel/partials/list.html",
        {
            "request": request,
            "rating_models": rating_models,
            "is_htmx": is_htmx
        }
    )

@router.get("/new")
async def create_rating_model_form(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get available templates for dropdown
    templates_list = db.query(Template).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "ratingModel/partials/create.html",
        {
            "request": request,
            "templates": templates_list,
            "is_htmx": is_htmx
        }
    )

@router.post("/new")
async def create_rating_model(
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    template_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Check if name is unique
        existing = db.query(RatingModel).filter(RatingModel.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Rating model with this name already exists")

        rating_model = RatingModel(
            name=name,
            label=label,
            template_id=template_id
        )
        db.add(rating_model)
        db.commit()
        db.refresh(rating_model)
        return RedirectResponse(
            url="/rating-models",
            status_code=303
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rating_model_id}")
async def get_rating_model(
    rating_model_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")
    
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "ratingModel/partials/detail.html",
        {
            "request": request,
            "rating_model": rating_model,
            "is_htmx": is_htmx
        }
    )

@router.get("/{rating_model_id}/edit")
async def edit_rating_model_form(
    rating_model_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")
    
    templates_list = db.query(Template).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    
    return templates.TemplateResponse(
        "ratingModel/partials/edit.html",
        {
            "request": request,
            "rating_model": rating_model,
            "templates": templates_list,
            "is_htmx": is_htmx
        }
    )

@router.post("/{rating_model_id}/edit")
async def update_rating_model(
    rating_model_id: UUID,
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    template_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")
    
    try:
        # Check if name is unique (excluding current model)
        existing = db.query(RatingModel)\
            .filter(RatingModel.name == name, RatingModel.id != rating_model_id)\
            .first()
        if existing:
            raise HTTPException(status_code=400, detail="Rating model with this name already exists")

        rating_model.name = name
        rating_model.label = label
        rating_model.template_id = template_id
        db.commit()
        return RedirectResponse(
            url="/rating-models",
            status_code=303
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{rating_model_id}")
async def delete_rating_model(
    rating_model_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")
    
    try:
        db.delete(rating_model)
        db.commit()
        
        if request.headers.get("HX-Request") == "true":
            rating_models = db.query(RatingModel).all()
            return templates.TemplateResponse(
                "ratingModel/partials/list.html",
                {
                    "request": request,
                    "rating_models": rating_models,
                    "is_htmx": True
                }
            )
        
        return {"message": "Rating model deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))