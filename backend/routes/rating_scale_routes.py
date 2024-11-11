# routes/rating_scale_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.rating_model_model import MasterRatingScale
from dependencies import get_db, auth_handler

router = APIRouter(prefix="/rating-scales")

templates = Jinja2Templates(directory="../frontend/templates")

@router.get("")
async def list_rating_scales(
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    rating_scales = db.query(MasterRatingScale).all()
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "rating_scales/partials/list.html" 
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "rating_scales": rating_scales,
            "user": current_user,

"is_htmx":is_htmx
        }
    )

@router.get("/new")
async def create_rating_scale_form(
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper)
):
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "rating_scales/partials/create_form.html" if is_htmx else "rating_scales/create.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "user": current_user,
            "is_htmx":is_htmx
        }
    )

@router.post("/new")
async def create_rating_scale(
    request: Request,
    rating_grade: str = Form(...),
    pd: float = Form(...),
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    rating_scale = MasterRatingScale(rating_grade=rating_grade, pd=pd)
    try:
        db.add(rating_scale)
        db.commit()
        db.refresh(rating_scale)
        return RedirectResponse(
            url="/rating-scales",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rating_scale_id}")
async def rating_scale_detail(
    rating_scale_id: str,
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    rating_scale = db.query(MasterRatingScale).filter(MasterRatingScale.id == rating_scale_id).first()
    if not rating_scale:
        raise HTTPException(status_code=404, detail="Rating Scale not found")
        
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "rating_scales/partials/detail.html"
    
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "rating_scale": rating_scale,
            "user": current_user,
            "is_htmx":is_htmx
        }
    )

@router.get("/{rating_scale_id}/edit")
async def edit_rating_scale_form(
    rating_scale_id: str,
    request: Request,
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    rating_scale = db.query(MasterRatingScale).filter(MasterRatingScale.id == rating_scale_id).first()
    if not rating_scale:
        raise HTTPException(status_code=404, detail="Rating Scale not found")
        
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "rating_scales/partials/edit_form.html" 
    
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "rating_scale": rating_scale,
            "user": current_user,

            "is_htmx":is_htmx
        }
    )

@router.post("/{rating_scale_id}/edit")
async def update_rating_scale(
    rating_scale_id: str,
    request: Request,
    rating_grade: str = Form(...),
    pd: float = Form(...),
    current_user: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db)
):
    rating_scale = db.query(MasterRatingScale).filter(MasterRatingScale.id == rating_scale_id).first()
    if not rating_scale:
        raise HTTPException(status_code=404, detail="Rating Scale not found")
    
    try:
        rating_scale.rating_grade = rating_grade
        rating_scale.pd = pd
        db.commit()
        return RedirectResponse(
            url="/rating-scales",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))



@router.delete("/{rating_scale_id}")
async def delete_rating_scale(
    rating_scale_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        rating_scale = db.query(MasterRatingScale).filter(MasterRatingScale.id == rating_scale_id).first()
        if not rating_scale:
            raise HTTPException(status_code=404, detail="Rating Scale not found")
        
        db.delete(rating_scale)
        db.commit()
        
        # If it's an HTMX request, return the updated list
        if request.headers.get("HX-Request") == "true":
            rating_scales = db.query(MasterRatingScale).all()
            return templates.TemplateResponse(
                "rating_scales/partials/list.html",
                {
                    "request": request,
                    "rating_scales": rating_scales,
                    "user": {"name": "Test User"},  # Mock user while auth is disabled
                    "is_htmx": True
                }
            )
        
        return JSONResponse(content={"message": "Rating Scale deleted successfully"})
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))