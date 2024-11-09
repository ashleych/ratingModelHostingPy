# routes/line_item_routes.py
import json
import logging
from fastapi import APIRouter, Request, Form, HTTPException, Depends,Query
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from typing import Any, Optional
from models.statement_models import LineItemMeta, LineItemValue
from models.statement_models import Template
from dependencies import get_db
from uuid import UUID
from models.statement_models import Template
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Dict
from typing import Dict, Set, List
from collections import defaultdict
import re
from typing import Tuple
from dependencies import get_db
router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")

# Enhanced breadcrumb builder with sections


def build_breadcrumbs(template_id=None, section=None, line_item_id=None):
    """
    Build breadcrumb navigation data with optional section

    Args:
        template_id: Optional template ID
        section: Optional section name (e.g., 'settings', 'formulas')
        line_item_id: Optional line item ID
    """
    breadcrumbs = [
        {
            'name': 'Templates',
            'url': url_for('fs_routes.list_templates')
        }
    ]

    if template_id:
        template = Template.query.get(template_id)
        if template:
            breadcrumbs.append({
                'name': template.name,
                'url': url_for('fs_routes.view_template', template_id=template_id)
            })

            if section:
                section_names = {
                    'settings': 'Template Settings',
                    'formulas': 'Formula Editor',
                    'layout': 'Layout Editor'
                }
                breadcrumbs.append({
                    'name': section_names.get(section, section.title()),
                    'url': url_for(f'fs_routes.template_{section}', template_id=template_id)
                })

            if line_item_id:
                line_item = LineItem.query.get(line_item_id)
                if line_item:
                    breadcrumbs.append({
                        'name': line_item.name,
                        'url': '#'
                    })

    return breadcrumbs


def build_line_item_breadcrumbs(
    template_id: UUID,
    section: str = None,
    line_item_id: UUID = None,
    db: Session = None
) -> List[Dict[str, str]]:
    """Build breadcrumb navigation data for line item routes"""
    breadcrumbs = [
        {
            'name': 'Templates',
            'url': '/templates'
        }
    ]

    # Add template
    template = db.query(Template).filter(Template.id == template_id).first()
    if template:
        breadcrumbs.append({
            'name': template.name,
            'url': f'/templates/{template_id}'
        })

        # Add Line Items section
        breadcrumbs.append({
            'name': 'Line Items',
            'url': f'/templates/{template_id}/lineitems'
        })

        # Add action-specific breadcrumb
        if section:
            if section == 'new':
                breadcrumbs.append({
                    'name': 'New Line Item',
                    'url': '#'
                })
            elif section == 'edit' and line_item_id:
                line_item = db.query(LineItemMeta).filter(
                    LineItemMeta.id == line_item_id).first()
                if line_item:
                    breadcrumbs.append({
                        'name': f'Edit {line_item.name}',
                        'url': '#'
                    })
            elif section == 'detail' and line_item_id:
                line_item = db.query(LineItemMeta).filter(
                    LineItemMeta.id == line_item_id).first()
                if line_item:
                    breadcrumbs.append({
                        'name': line_item.name,
                        'url': '#'
                    })

    return breadcrumbs


def validate_syntax(formula: str, valid_names: Set[str], current_line_item_name: str = None) -> tuple[bool, str]:
    """Validate formula syntax and line item names"""
    if not formula.strip():
        return False, "Formula is empty. This line item will not be calculated."

    # Split formula into tokens
    tokens = re.findall(r'[\w_]+|[+\-*/()]', formula)
    tokens_stripped = [t.strip() for t in tokens]

    # Define valid operators
    valid_operators = {'+', '-', '*', '/', '(', ')'}

    # Check for single operator
    if len(tokens_stripped) == 1:
        if tokens_stripped[0] in valid_operators:
            return False, "Invalid formula: Cannot use a single operator alone. Formula must include line item names."
        if tokens_stripped[0] == current_line_item_name:
            return False, "Invalid formula: Cannot reference the line item itself in its formula."

    # Check if formula starts or ends with an operator
    if tokens_stripped[0] in {'+', '-', '*', '/'}:
        return False, "Invalid formula: Cannot start with an operator"
    if tokens_stripped[-1] in {'+', '-', '*', '/'}:
        return False, "Invalid formula: Cannot end with an operator"

    # Check parentheses matching
    parentheses_count = 0
    for token in tokens_stripped:
        if token == '(':
            parentheses_count += 1
        elif token == ')':
            parentheses_count -= 1
        if parentheses_count < 0:
            return False, "Invalid formula: Mismatched parentheses - unexpected closing parenthesis"

    if parentheses_count > 0:
        return False, "Invalid formula: Mismatched parentheses - missing closing parenthesis"

    # Check for consecutive operators
    for i in range(len(tokens_stripped) - 1):
        if (tokens_stripped[i] in {'+', '-', '*', '/'} and
                tokens_stripped[i + 1] in {'+', '-', '*', '/'}):
            return False, f"Invalid formula: Cannot have consecutive operators '{tokens_stripped[i]}{tokens_stripped[i + 1]}'"

    # Validate each token and check for self-reference
    for token in tokens_stripped:
        # Check if token is an operator
        if token in valid_operators:
            continue

        # Check if token is a valid variable name (alphanumeric with underscores)
        # Must start with letter, followed by letters/numbers/underscores
        if re.match(r'^[a-zA-Z]\w*$', token):
            if token == current_line_item_name:
                return False, "Invalid formula: Cannot reference the line item itself in its formula"
            if token not in valid_names:
                return False, f"Invalid line item name: '{token}'"
        else:
            return False, f"Invalid token: '{token}'. Line item names must start with a letter and can only contain letters, numbers, and underscores."

    return True, ""


def check_circular_reference(
    all_formulas: Dict[str, str],
    line_item_name: str,
    formula_to_check: str
) -> Tuple[bool, List[str]]:
    """
    Check for circular references in formula and return the circular path if found.

    Args:
        all_formulas: Dict of line_item_name -> formula
        line_item_name: The line item being checked
        formula_to_check: The formula being added/updated

    Returns:
        Tuple[bool, List[str]]: (is_valid, circular_path)
        - is_valid: True if no circular reference, False if there is
        - circular_path: Empty list if no circular reference, otherwise list of items in the circular path
    """
    def extract_dependencies(formula: str) -> Set[str]:
        """Extract line item names used in a formula"""
        if not formula:
            return set()
        return set(re.findall(r'[a-zA-Z]\w*', formula))

    def check_dependency_path(current_item: str, target: str, visited: Set[str], path: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if there's a path from current_item back to target through dependencies.
        Returns (True, path) if circular reference found, (False, []) otherwise.
        """
        path.append(current_item)

        if current_item == target:
            return True, path

        if current_item in visited:
            return False, []

        visited.add(current_item)

        # Get formula for current item
        current_formula = all_formulas.get(current_item)
        if not current_formula:
            path.pop()
            return False, []

        # Get dependencies of current formula
        deps = extract_dependencies(current_formula)

        # Check each dependency
        for dep in deps:
            found, circular_path = check_dependency_path(
                dep, target, visited, path.copy())
            if found:
                return True, circular_path

        path.pop()
        return False, []

    # Get dependencies in the formula being checked
    direct_deps = extract_dependencies(formula_to_check)

    # For each dependency, check if it leads back to the line item being checked
    for dep in direct_deps:
        found, path = check_dependency_path(dep, line_item_name, set(), [])
        if found:
            # The line_item_name is already in the path, no need to add it again
            return False, path

    return True, []


def format_circular_path(path: List[str]) -> str:
    """Format the circular path for display"""
    if not path:
        return ""
    return " → ".join(path)


@router.post("/templates/{template_id}/lineitems/validate-formula")
async def validate_formula_endpoint(
    template_id: UUID,
    formula: str = Form(...),
    line_item_name: str = Form(...),
    db: Session = Depends(get_db)
):
    # try:
        # Get all valid line item names and their formulas
        line_items = db.query(LineItemMeta)\
            .filter(LineItemMeta.template_id == template_id)\
            .all()

        valid_names = {item.name for item in line_items}
        current_formulas = {item.name: item.formula for item in line_items}

        # First check syntax
        syntax_valid, syntax_error = validate_syntax(formula, valid_names)
        if not syntax_valid:
            return HTMLResponse(f"""
            <div class="text-red-600 dark:text-red-400">
                {syntax_error}
            </div>
            """)

        # Then check for circular references
        is_valid, circular_path = check_circular_reference(
            current_formulas,
            line_item_name,
            formula
        )
        if not is_valid:
            circular_path_str = format_circular_path(circular_path)
            return HTMLResponse(f"""
            <div class="text-red-600 dark:text-red-400">
                Circular reference detected: {circular_path_str}
            </div>
            """)

        # If we got here, formula is valid
        return HTMLResponse("""
        <div class="text-green-600 dark:text-green-400">
            Formula is valid ✓
        </div>
        """)

    # except Exception as e:
    #     return HTMLResponse(f"""
    #     <div class="text-red-600 dark:text-red-400">
    #         Error validating formula: {str(e)}
    #     </div>
    #     """)


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
    breadcrumbs = build_line_item_breadcrumbs(template_id, db=db)

    return templates.TemplateResponse(
        "lineitems/partials/list.html",
        {
            "request": request,
            "template": template,
            "line_items": line_items,
            "is_htmx": is_htmx,
            "breadcrumbs": breadcrumbs
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
    breadcrumbs = build_line_item_breadcrumbs(template_id, 'new', db=db)
    return templates.TemplateResponse(
        "lineitems/partials/create.html",
        {
            "request": request,
            "template": template,
            "next_order": next_order,
            "is_htmx": is_htmx,
            "breadcrumbs": breadcrumbs
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

    template = db.query(Template).filter(Template.id == template_id).first()
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")

    available_items = db.query(LineItemMeta).filter(
        LineItemMeta.template_id == template_id,
        LineItemMeta.id != item_id  # Exclude current item
    ).order_by(LineItemMeta.order_no).all()
    breadcrumbs = build_line_item_breadcrumbs(
        template_id, 'edit', item_id, db=db)

    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/edit.html",
        {
            "request": request,
            "line_item": line_item,
            "is_htmx": is_htmx,
            "template": template,
            "available_items": available_items,
            "breadcrumbs": breadcrumbs
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


@router.get("/templates/dependencies/{template_id}")
async def view_dependencies(
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

    dependency_info = get_dependency_graph(line_items)

    # Generate flowchart for all items
    mermaid_chart = generate_mermaid_flowchart(line_items, dependency_info)

    # Generate individual charts for each item
    individual_charts = {}
    for item in line_items:
        # Get all related items (dependencies and dependents)
        related_items = []
        # Add direct dependencies
        deps = dependency_info['dependencies'].get(item.name, set())
        related_items.extend([li for li in line_items if li.name in deps])
        # Add direct dependents
        dependents = dependency_info['dependents'].get(item.name, set())
        related_items.extend(
            [li for li in line_items if li.name in dependents])
        # Add the item itself
        related_items.append(item)
        # Generate chart for this subset
        if deps or dependents:  # Only create chart if there are relationships
            individual_charts[item.name] = generate_mermaid_flowchart(
                related_items, dependency_info)

    breadcrumbs = build_line_item_breadcrumbs(
        template_id, 'dependencies', db=db)

    is_htmx = request.headers.get("HX-Request") == "true"
    template_name = (
        "lineitems/partials/dependencies.html" if is_htmx else "lineitems/dependencies.html"
    )

    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "template": template,
            "dependency_info": dependency_info,
            "line_items": line_items,
            "breadcrumbs": breadcrumbs,
            "is_htmx": is_htmx,
            "mermaid_chart": mermaid_chart,
            "individual_charts": individual_charts
        }
    )


def get_item_dependency_chart(line_item: LineItemMeta, all_formulas: Dict[str, Dict],depth:int=2) -> str:
    """
    Generate a Mermaid flowchart showing dependencies for a single line item.
    all_formulas should be a dict with name -> {id: UUID, formula: str}
    """
    def extract_dependencies(formula: str) -> Set[str]:
        if not formula:
            return set()
        return set(re.findall(r'[a-zA-Z]\w*', formula))

    def get_all_dependencies(item_name: str, depth: int = 2, visited=None) -> Set[str]:
        if visited is None:
            visited = set()
        if depth == 0 or item_name in visited:
            return set()
            
        visited.add(item_name)
        related = set()
        
        # Get direct dependencies
        formula = all_formulas.get(item_name, {}).get('formula', '')
        deps = extract_dependencies(formula)
        related.update(deps)
        
        # Get items that depend on this
        dependents = {name for name, info in all_formulas.items() 
                     if item_name in extract_dependencies(info.get('formula', ''))}
        related.update(dependents)
        
        # Recursive lookup
        for rel_item in deps.union(dependents):
            if rel_item not in visited:
                related.update(get_all_dependencies(rel_item, depth - 1, visited))
                
        return related

    # Get related items
    related_items = get_all_dependencies(line_item.name,depth=depth)
    related_items.add(line_item.name)
    
    mermaid_lines = [
        "%%{init: {'flowchart': {'curve': 'basis', 'rankSpacing': 50, 'nodeSpacing': 50}}}%%",
        "flowchart TD"
    ]
    
    # Add nodes with clickable links
    template_id = line_item.template_id
    for item_name in related_items:
        clean_name = item_name.replace(" ", "_").replace("-", "_")
        item_info = all_formulas.get(item_name, {})
        item_id = item_info.get('id')
        
        if item_name == line_item.name:
            mermaid_lines.append(f'    {clean_name}["{item_name}"]:::focus')
        else:
            mermaid_lines.append(f'    {clean_name}["{item_name}"]')
            
        if item_id:
            mermaid_lines.append(f'    click {clean_name} "/templates/{template_id}/lineitems/{item_id}"')
    
    # Add connections
    for item_name in related_items:
        clean_name = item_name.replace(" ", "_").replace("-", "_")
        formula = all_formulas.get(item_name, {}).get('formula', '')
        deps = extract_dependencies(formula)
        
        for dep in deps:
            if dep in related_items:
                clean_dep = dep.replace(" ", "_").replace("-", "_")
                mermaid_lines.append(f"    {clean_dep} --> {clean_name}")
    
    mermaid_lines.append("classDef focus fill:#f9f,stroke:#333,stroke-width:2px;")
    
    return "\n".join(mermaid_lines)


@router.get("/templates/{template_id}/lineitems/{item_id}")
async def get_line_item_detail(
    request: Request,
    template_id: UUID,
    item_id: UUID,
    depth: int = Query(2),
    db: Session = Depends(get_db)
):
    line_item = db.query(LineItemMeta).filter(
        LineItemMeta.id == item_id,
        LineItemMeta.template_id == template_id
    ).first()
    
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    # Get all formulas with their IDs
    items = db.query(LineItemMeta.name, LineItemMeta.id, LineItemMeta.formula)\
        .filter(LineItemMeta.template_id == template_id)\
        .all()
    
    # Convert to dictionary with additional info
    formulas = {
        item.name: {'id': item.id, 'formula': item.formula}
        for item in items
    }
    
    mermaid_chart = get_item_dependency_chart(line_item, formulas,depth)
    
    return templates.TemplateResponse(
        "lineitems/partials/detail.html",
        {
            "request": request,
            "line_item": line_item,
            "template_id":template_id,
            "mermaid_chart": mermaid_chart,
            "depth":depth,
            "is_htmx": request.headers.get("HX-Request") == "true"

        }
    )

def generate_mermaid_flowchart(line_items: List[LineItemMeta], dependency_info: Dict[str, Any]) -> str:
    """Generate a Mermaid flowchart string for line item dependencies"""
    mermaid_lines = ["flowchart TD"]

    # Add nodes
    for item in line_items:
        # Clean the name for Mermaid (replace spaces and special chars)
        node_id = f"id_{item.name}"
        mermaid_lines.append(f'    {node_id}["{item.name}"]')

    # Add connections
    for item in line_items:
        node_id = f"id_{item.name}"
        deps = dependency_info['dependencies'].get(item.name, set())
        for dep in deps:
            dep_id = f"id_{dep}"
            mermaid_lines.append(f'    {dep_id} --> {node_id}')

    return "\n".join(mermaid_lines)


def get_dependency_graph(line_items: List[LineItemMeta]) -> Dict[str, Any]:
    """
    Creates a dependency graph showing all relationships between line items

    Args:
        line_items: List of LineItemMeta objects

    Returns:
        Dict with:
        - dependencies: Dict[str, Set[str]] - Direct dependencies for each line item
        - dependents: Dict[str, Set[str]] - Items that depend on each line item
        - paths: Dict[str, List[str]] - Complete dependency path for each line item
    """
    # Helper function to extract dependencies from formula
    def extract_dependencies(formula: str) -> Set[str]:
        if not formula:
            return set()
        return set(re.findall(r'[a-zA-Z]\w*', formula))

    # Initialize result structures
    direct_dependencies = {}  # item -> set of items it depends on
    dependents = {}          # item -> set of items that depend on it
    all_paths = {}          # item -> list of all items in its dependency chain

    # First pass: Build direct dependencies and dependents
    for item in line_items:
        name = item.name
        deps = extract_dependencies(item.formula) if item.formula else set()

        # Store direct dependencies
        direct_dependencies[name] = deps

        # Initialize dependents sets if needed
        if name not in dependents:
            dependents[name] = set()
        for dep in deps:
            if dep not in dependents:
                dependents[dep] = set()
            dependents[dep].add(name)

    # Helper function to build complete dependency path
    def build_dependency_path(item: str, visited: Set[str] = None) -> List[str]:
        if visited is None:
            visited = set()

        if item in visited:
            return []  # Avoid circular references

        visited.add(item)
        path = [item]

        for dep in direct_dependencies.get(item, set()):
            sub_path = build_dependency_path(dep, visited.copy())
            if sub_path:
                path.extend(sub_path)

        return path

    # Build complete dependency paths for each item
    for item in direct_dependencies:
        all_paths[item] = build_dependency_path(item)

    return {
        'dependencies': direct_dependencies,
        'dependents': dependents,
        'paths': all_paths
    }

@router.get("/templates/{template_id}/bulk-create")
async def bulk_create_form(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/bulk_create.html",
        {
            "request": request,
            "template_id": template_id,
            "template": template,
            "is_htmx":is_htmx  
        }
    )


@router.post("/templates/{template_id}/bulk-create")
async def bulk_create_line_items(
    template_id: UUID,
    line_items: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        items_data = json.loads(line_items)
        
        # Create line items
        created_items = []
        for item in items_data:
            line_item = LineItemMeta(
                template_id=template_id,
                fin_statement_type=item['fin_statement_type'],
                header=item['header'],
                formula=item['formula'],
                type=item['type'],
                label=item['label'],
                name=item['name'],
                lag_months=item['lag_months'],
                display=item['display'],
                order_no=item['order_no'],
                display_order_no=item['display_order_no']
            )
            db.add(line_item)
            created_items.append(line_item)
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Delete any items that were created
            for item in created_items:
                db.delete(item)
            db.commit()
            raise HTTPException(status_code=400, detail="Database integrity error")
            
        return RedirectResponse(
            url=f"/templates/{template_id}/lineitems",
            status_code=303
        )
        
    except Exception as e:
        db.rollback()
        # Delete any items that were created
        for item in created_items:
            db.delete(item)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

import json
import logging
from uuid import UUID
from fastapi import Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Set

import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_file_size_mb: int = 10,
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure logging to both file and console with rotation.
    
    Args:
        log_dir: Directory where log files will be stored
        log_level: Logging level (default: INFO)
        max_file_size_mb: Maximum size of each log file in MB
        backup_count: Number of backup files to keep
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create and configure file handler with rotation
    log_file = os.path.join(
        log_dir,
        f'app_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup message
    logger.info(f"Logging configured - writing to {log_file}")
    
    return logger

# Usage in your FastAPI endpoint
logger = setup_logging()

@router.post("/templates/{template_id}/bulk-validate")
async def validate_line_items(
    template_id: UUID,
    line_items: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Log incoming request
        logger.info(f"Processing bulk validation request for template_id: {template_id}")
        
        # Parse JSON with error handling
        try:
            items_data = json.loads(line_items)
            if not isinstance(items_data, list):
                logger.error("Invalid data format: Expected a list of items")
                return JSONResponse(
                    status_code=400,
                    content={'error': 'Invalid data format: Expected a list of items'}
                )
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={'error': f'Invalid JSON format: {str(e)}'}
            )

        validation_errors = []
        
        # Validate basic structure of each item
        for idx, item in enumerate(items_data, 1):
            required_fields = {'name', 'formula'}
            if not all(field in item for field in required_fields):
                missing_fields = required_fields - set(item.keys())
                logger.error(f"Row {idx}: Missing required fields: {missing_fields}")
                return JSONResponse(
                    status_code=400,
                    content={'error': f'Row {idx}: Missing required fields: {missing_fields}'}
                )

        # Get existing line items for template
        try:
            existing_items = db.query(LineItemMeta)\
                .filter(LineItemMeta.template_id == template_id)\
                .all()
            existing_names = {item.name for item in existing_items}
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={'error': 'Database error while fetching existing items'}
            )

        # Get all formulas for circular dependency check
        current_formulas: Dict[str, str] = {
            item.name: item.formula 
            for item in existing_items 
            if item.formula
        }
        
        # Add new items to formula dict
        for item in items_data:
            current_formulas[item['name']] = item['formula']

        # Validate each line item
        for idx, item in enumerate(items_data, 1):
            row_errors = []
            
            # Log current item being processed
            logger.info(f"Validating row {idx}: {item['name']}")
            
            # Check name uniqueness against existing items
            if item['name'] in existing_names:
                error_msg = f"Line item name '{item['name']}' already exists"
                logger.error(f"Row {idx}: {error_msg}")
                row_errors.append(error_msg)
            
            # Check for duplicate names within the pasted data
            name_count = sum(1 for x in items_data if x['name'] == item['name'])
            if name_count > 1:
                error_msg = f"Duplicate line item name '{item['name']}' in the pasted data"
                logger.error(f"Row {idx}: {error_msg}")
                row_errors.append(error_msg)
            
            # Validate formula syntax
            if item['formula']:
                try:
                    valid_names = set(current_formulas.keys())
                    syntax_valid, syntax_error = validate_syntax(
                        item['formula'],
                        valid_names,
                        current_line_item_name=item['name']
                    )
                    if not syntax_valid:
                        error_msg = f"Formula syntax error: {syntax_error}"
                        logger.error(f"Row {idx}: {error_msg}")
                        row_errors.append(error_msg)
                except Exception as e:
                    logger.error(f"Formula validation error in row {idx}: {str(e)}")
                    row_errors.append(f"Formula validation error: {str(e)}")
            
            # Check for circular dependencies
            if item['formula']:
                try:
                    is_valid, circular_path = check_circular_reference(
                        current_formulas,
                        item['name'],
                        item['formula']
                    )
                    if not is_valid:
                        circular_path_str = " → ".join(circular_path)
                        error_msg = f"Circular dependency detected: {circular_path_str}"
                        logger.error(f"Row {idx}: {error_msg}")
                        row_errors.append(error_msg)
                except Exception as e:
                    logger.error(f"Circular dependency check error in row {idx}: {str(e)}")
                    row_errors.append(f"Circular dependency check error: {str(e)}")
            
            if row_errors:
                validation_errors.append({
                    'row': idx,
                    'errors': row_errors
                })
        
        if validation_errors:
            logger.info(f"Validation failed with {len(validation_errors)} errors")
            return JSONResponse(
                status_code=400,
                content={'validation_errors': validation_errors}
            )
        
        logger.info("Validation completed successfully")
        return JSONResponse(content={'status': 'valid'})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={'error': f'Internal server error: {str(e)}'}
        )