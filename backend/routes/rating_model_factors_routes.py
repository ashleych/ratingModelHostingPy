from fastapi import APIRouter, Request, Form, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.rating_model_model import RatingFactor
from models.rating_model_model import RatingModel
from dependencies import get_db
from uuid import UUID
import re
from typing import Dict, Set, Optional

router = APIRouter(prefix="/rating-models")
templates = Jinja2Templates(directory="../frontend/templates")
# utils/breadcrumbs.py

def build_factor_breadcrumbs(rating_model_id: UUID, action: str = None, factor_id: UUID = None, db: Session = None):
    """
    Build breadcrumb navigation for rating factor pages.
    
    Args:
        rating_model_id: UUID of the rating model
        action: Optional action ('new', 'edit', 'detail', 'dependencies')
        factor_id: Optional UUID of the factor for edit/detail views
        db: Database session
    """
    breadcrumbs = [
        {
            "name": "Rating Models",
            "url": "/rating-models",
            "htmx_url": "/rating-models"
        }
    ]
    
    if db and rating_model_id:
        rating_model = db.query(RatingModel).get(rating_model_id)
        if rating_model:
            breadcrumbs.append({
                "name": rating_model.name,
                "url": f"/rating-models/{rating_model_id}/factors",
                "htmx_url": f"/rating-models/{rating_model_id}/factors"
            })
            
            if action == 'new':
                breadcrumbs.append({
                    "name": "New Factor",
                    "url": None,
                    "htmx_url": None
                })
            elif action in ['edit', 'detail'] and factor_id and db:
                factor = db.query(RatingFactor).get(factor_id)
                if factor:
                    if action == 'detail':
                        breadcrumbs.append({
                            "name": factor.name,
                            "url": None,
                            "htmx_url": None
                        })
                    else:
                        breadcrumbs.append({
                            "name": factor.name,
                            "url": f"/rating-models/{rating_model_id}/factors/{factor_id}",
                            "htmx_url": f"/rating-models/{rating_model_id}/factors/{factor_id}"
                        })
                        breadcrumbs.append({
                            "name": "Edit",
                            "url": None,
                            "htmx_url": None
                        })
            elif action == 'dependencies':
                breadcrumbs.append({
                    "name": "Dependencies",
                    "url": None,
                    "htmx_url": None
                })
    
    return breadcrumbs

# utils/formula_validation.py
import re
from typing import Set, Tuple, Dict, List

def validate_syntax(formula: str, valid_names: Set[str], current_factor_name: str = None) -> Tuple[bool, str]:
    """
    Validate the syntax of a rating factor formula.
    
    Args:
        formula: The formula string to validate
        valid_names: Set of valid factor names that can be used in formulas
        current_factor_name: Name of the current factor (to prevent self-reference)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not formula:
        return True, ""

    # Remove all whitespace for easier parsing
    formula = formula.replace(" ", "")
    
    # Basic syntax check
    try:
        # Check balanced parentheses
        parentheses_count = 0
        for char in formula:
            if char == '(':
                parentheses_count += 1
            elif char == ')':
                parentheses_count -= 1
            if parentheses_count < 0:
                return False, "Unmatched closing parenthesis"
        if parentheses_count > 0:
            return False, "Unmatched opening parenthesis"

        # Extract all variable names
        variables = set(re.findall(r'[a-zA-Z]\w*', formula))
        
        # Check for self-reference
        if current_factor_name and current_factor_name in variables:
            return False, f"Formula cannot reference itself: {current_factor_name}"
        
        # Check for undefined variables
        undefined = variables - valid_names - {'abs', 'min', 'max', 'sum', 'avg'}  # Built-in functions
        if undefined:
            return False, f"Undefined factors in formula: {', '.join(undefined)}"
        
        # Check operators
        operators = set(re.findall(r'[\+\-\*\/\(\)]', formula))
        invalid_operators = operators - {'+', '-', '*', '/', '(', ')'}
        if invalid_operators:
            return False, f"Invalid operators in formula: {', '.join(invalid_operators)}"
        
        return True, ""
    except Exception as e:
        return False, f"Syntax error: {str(e)}"

def check_circular_reference(
    formulas: Dict[str, str],
    factor_name: str,
    formula: str,
    visited: Set[str] = None,
    path: List[str] = None
) -> Tuple[bool, List[str]]:
    """
    Check for circular dependencies in rating factor formulas.
    
    Args:
        formulas: Dictionary of factor_name -> formula
        factor_name: Name of the current factor
        formula: Formula to check
        visited: Set of visited factor names
        path: Current dependency path
        
    Returns:
        Tuple of (is_valid, circular_path)
    """
    if visited is None:
        visited = set()
    if path is None:
        path = []
        
    if factor_name in visited:
        return False, path + [factor_name]
    
    if not formula:
        return True, []
    
    visited.add(factor_name)
    path.append(factor_name)
    
    # Extract dependencies from formula
    dependencies = set(re.findall(r'[a-zA-Z]\w*', formula))
    dependencies = {dep for dep in dependencies if dep in formulas}
    
    for dep in dependencies:
        is_valid, circular_path = check_circular_reference(
            formulas,
            dep,
            formulas.get(dep, ''),
            visited.copy(),
            path.copy()
        )
        if not is_valid:
            return False, circular_path
            
    return True, []

# routes/formula_validation.py
@router.post("/rating-models/{rating_model_id}/factors/validate-formula")
async def validate_factor_formula(
    rating_model_id: UUID,
    request: Request,
    formula: str = Form(...),
    factor_name: str = Form(None),
    factor_id: UUID = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Get all factor names for the current rating model
        factors = db.query(RatingFactor).filter(
            RatingFactor.rating_model_id == rating_model_id
        ).all()
        
        # Create map of names to formulas for dependency checking
        formulas = {
            factor.name: factor.formula
            for factor in factors
            if factor.id != factor_id  # Exclude current factor if editing
        }
        
        # Add the current formula being validated
        if factor_name:
            formulas[factor_name] = formula
            
        valid_names = set(formulas.keys())
        
        # Validate syntax
        syntax_valid, syntax_error = validate_syntax(
            formula,
            valid_names,
            current_factor_name=factor_name
        )
        
        if not syntax_valid:
            return JSONResponse(
                status_code=400,
                content={
                    'valid': False,
                    'error': syntax_error
                }
            )
        
        # Check for circular dependencies
        if factor_name:
            is_valid, circular_path = check_circular_reference(
                formulas,
                factor_name,
                formula
            )
            
            if not is_valid:
                return JSONResponse(
                    status_code=400,
                    content={
                        'valid': False,
                        'error': f"Circular dependency detected: {' → '.join(circular_path)}"
                    }
                )
        
        return JSONResponse(content={'valid': True})
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                'valid': False,
                'error': f"Validation error: {str(e)}"
            }
        )
@router.get("/{rating_model_id}/factors")
async def list_rating_factors(
    rating_model_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")

    factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_model_id
    ).order_by(RatingFactor.module_order, RatingFactor.order_no).all()

    # Clean up formulas
    for factor in factors:
        if factor.formula:
            factor.formula = factor.formula.strip()

    is_htmx = request.headers.get("HX-Request") == "true"
    breadcrumbs = build_factor_breadcrumbs(rating_model_id, db=db)

    return templates.TemplateResponse(
        "ratingModel/factors/list.html",
        {
            "request": request,
            "rating_model": rating_model,
            "factors": factors,
            "is_htmx": is_htmx,
            "breadcrumbs": breadcrumbs
        }
    )

@router.get("/{rating_model_id}/factors/new")
async def create_factor_form(
    rating_model_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    rating_model = db.query(RatingModel).filter(RatingModel.id == rating_model_id).first()
    if not rating_model:
        raise HTTPException(status_code=404, detail="Rating model not found")

    # Get max order numbers to suggest next numbers
    max_order = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_model_id
    ).with_entities(
        RatingFactor.module_order,
        RatingFactor.order_no
    ).order_by(
        RatingFactor.module_order.desc(),
        RatingFactor.order_no.desc()
    ).first()

    next_module_order = (max_order[0] if max_order else 0) + 1
    next_order = (max_order[1] if max_order else 0) + 1

    is_htmx = request.headers.get("HX-Request") == "true"
    breadcrumbs = build_factor_breadcrumbs(rating_model_id, 'new', db=db)

    return templates.TemplateResponse(
        "ratingModel/factors/create.html",
        {
            "request": request,
            "rating_model": rating_model,
            "next_module_order": next_module_order,
            "next_order": next_order,
            "is_htmx": is_htmx,
            "breadcrumbs": breadcrumbs
        }
    )

@router.post("/{rating_model_id}/factors/new")
async def create_factor(
    rating_model_id: UUID,
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    factor_type: str = Form(...),
    input_source: Optional[str] = Form(None),
    parent_factor_name: Optional[str] = Form(None),
    weightage: Optional[float] = Form(None),
    module_name: str = Form(...),
    module_order: int = Form(...),
    order_no: int = Form(...),
    formula: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        factor = RatingFactor(
            rating_model_id=rating_model_id,
            name=name,
            label=label,
            factor_type=factor_type,
            input_source=input_source,
            parent_factor_name=parent_factor_name,
            weightage=weightage,
            module_name=module_name,
            module_order=module_order,
            order_no=order_no,
            formula=formula
        )

        db.add(factor)
        db.commit()
        db.refresh(factor)

        return RedirectResponse(
            url=f"/rating-models/{rating_model_id}/factors",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rating_model_id}/factors/{factor_id}/edit")
async def edit_factor_form(
    rating_model_id: UUID,
    factor_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    factor = db.query(RatingFactor).filter(
        RatingFactor.id == factor_id,
        RatingFactor.rating_model_id == rating_model_id
    ).first()

    if not factor:
        raise HTTPException(status_code=404, detail="Rating factor not found")

    # Get available parent factors
    available_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_model_id,
        RatingFactor.id != factor_id  # Exclude current factor
    ).order_by(RatingFactor.module_order, RatingFactor.order_no).all()

    breadcrumbs = build_factor_breadcrumbs(rating_model_id, 'edit', factor_id, db=db)
    is_htmx = request.headers.get("HX-Request") == "true"

    return templates.TemplateResponse(
        "ratingModel/factors/edit.html",
        {
            "request": request,
            "factor": factor,
            "is_htmx": is_htmx,
            "available_factors": available_factors,
            "breadcrumbs": breadcrumbs
        }
    )

@router.post("/{rating_model_id}/factors/{factor_id}/edit")
async def update_factor(
    rating_model_id: UUID,
    factor_id: UUID,
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    factor_type: str = Form(...),
    input_source: Optional[str] = Form(None),
    parent_factor_name: Optional[str] = Form(None),
    weightage: Optional[float] = Form(None),
    module_name: str = Form(...),
    module_order: int = Form(...),
    order_no: int = Form(...),
    formula: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    factor = db.query(RatingFactor).filter(
        RatingFactor.id == factor_id,
        RatingFactor.rating_model_id == rating_model_id
    ).first()

    if not factor:
        raise HTTPException(status_code=404, detail="Rating factor not found")

    try:
        factor.name = name
        factor.label = label
        factor.factor_type = factor_type
        factor.input_source = input_source
        factor.parent_factor_name = parent_factor_name
        factor.weightage = weightage
        factor.module_name = module_name
        factor.module_order = module_order
        factor.order_no = order_no
        factor.formula = formula

        db.commit()
        return RedirectResponse(
            url=f"/rating-models/{rating_model_id}/factors",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{rating_model_id}/factors/{factor_id}")
async def delete_factor(
    rating_model_id: UUID,
    factor_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    factor = db.query(RatingFactor).filter(
        RatingFactor.id == factor_id,
        RatingFactor.rating_model_id == rating_model_id
    ).first()

    if not factor:
        raise HTTPException(status_code=404, detail="Rating factor not found")

    try:
        db.delete(factor)
        db.commit()

        if request.headers.get("HX-Request") == "true":
            factors = db.query(RatingFactor).filter(
                RatingFactor.rating_model_id == rating_model_id
            ).order_by(RatingFactor.module_order, RatingFactor.order_no).all()

            return templates.TemplateResponse(
                "ratingModel/factors/list.html",
                {
                    "request": request,
                    "rating_model_id": rating_model_id,
                    "factors": factors,
                    "is_htmx": True
                }
            )

        return {"message": "Rating factor deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

def get_factor_dependency_chart(factor: RatingFactor, all_formulas: Dict[str, Dict], depth: int = 2) -> str:
    """
    Generate a Mermaid flowchart showing dependencies for a single rating factor.
    all_formulas should be a dict with name -> {id: UUID, formula: str}
    """
    def extract_dependencies(formula: str) -> Set[str]:
        if not formula:
            return set()
        return set(re.findall(r'[a-zA-Z]\w*', formula))

    def get_all_dependencies(factor_name: str, depth: int = 2, visited=None) -> Set[str]:
        if visited is None:
            visited = set()
        if depth == 0 or factor_name in visited:
            return set()
            
        visited.add(factor_name)
        related = set()
        
        # Get direct dependencies
        formula = all_formulas.get(factor_name, {}).get('formula', '')
        deps = extract_dependencies(formula)
        related.update(deps)
        
        # Get factors that depend on this
        dependents = {name for name, info in all_formulas.items() 
                     if factor_name in extract_dependencies(info.get('formula', ''))}
        related.update(dependents)
        
        # Recursive lookup
        for rel_factor in deps.union(dependents):
            if rel_factor not in visited:
                related.update(get_all_dependencies(rel_factor, depth - 1, visited))
                
        return related

    # Get related factors
    related_factors = get_all_dependencies(factor.name, depth=depth)
    related_factors.add(factor.name)
    
    mermaid_lines = [
        "%%{init: {'flowchart': {'curve': 'basis', 'rankSpacing': 50, 'nodeSpacing': 50}}}%%",
        "flowchart TD"
    ]
    
    # Add nodes with clickable links
    rating_model_id = factor.rating_model_id
    for factor_name in related_factors:
        clean_name = factor_name.replace(" ", "_").replace("-", "_")
        factor_info = all_formulas.get(factor_name, {})
        factor_id = factor_info.get('id')
        
        if factor_name == factor.name:
            mermaid_lines.append(f'    {clean_name}["{factor_name}"]:::focus')
        else:
            mermaid_lines.append(f'    {clean_name}["{factor_name}"]')
            
        if factor_id:
            mermaid_lines.append(
                f'    click {clean_name} "/rating-models/{rating_model_id}/factors/{factor_id}"'
            )
    
    # Add connections
    for factor_name in related_factors:
        clean_name = factor_name.replace(" ", "_").replace("-", "_")
        formula = all_formulas.get(factor_name, {}).get('formula', '')
        deps = extract_dependencies(formula)
        
        for dep in deps:
            if dep in related_factors:
                clean_dep = dep.replace(" ", "_").replace("-", "_")
                mermaid_lines.append(f"    {clean_dep} --> {clean_name}")
    
    mermaid_lines.append("classDef focus fill:#f9f,stroke:#333,stroke-width:2px;")
    
    return "\n".join(mermaid_lines)

@router.get("/{rating_model_id}/factors/{factor_id}")
async def get_factor_detail(
    request: Request,
    rating_model_id: UUID,
    factor_id: UUID,
    depth: int = Query(2),
    db: Session = Depends(get_db)
):
    factor = db.query(RatingFactor).filter(
        RatingFactor.id == factor_id,
        RatingFactor.rating_model_id == rating_model_id
    ).first()
    
    if not factor:
        raise HTTPException(status_code=404, detail="Rating factor not found")
    
    # Get all formulas with their IDs
    factors = db.query(RatingFactor.name, RatingFactor.id, RatingFactor.formula)\
        .filter(RatingFactor.rating_model_id == rating_model_id)\
        .all()
    
    # Convert to dictionary with additional info
    formulas = {
        factor.name: {'id': factor.id, 'formula': factor.formula}
        for factor in factors
    }
    
    mermaid_chart = get_factor_dependency_chart(factor, formulas, depth)
    breadcrumbs = build_factor_breadcrumbs(rating_model_id, 'detail', factor_id, db=db)
    
    return templates.TemplateResponse(
        "ratingModel/factors/detail.html",
        {
            "request": request,
            "factor": factor,
            "rating_model_id": rating_model_id,
            "mermaid_chart": mermaid_chart,
            "depth": depth,
            "breadcrumbs": breadcrumbs,
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )