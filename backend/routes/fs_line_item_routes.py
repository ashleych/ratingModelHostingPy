# routes/line_item_routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Any, Optional
from models.models import LineItemMeta, Template
from dependencies import get_db
from uuid import UUID
from models.models import LineItemMeta, LineItemValue, Template
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
    try:
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

    except Exception as e:
        return HTMLResponse(f"""
        <div class="text-red-600 dark:text-red-400">
            Error validating formula: {str(e)}
        </div>
        """)


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

def get_item_dependency_chart(line_item: LineItemMeta, all_formulas: Dict[str, str]) -> str:
    """
    Generate a Mermaid flowchart showing dependencies for a single line item.
    Shows both upstream and downstream dependencies.
    """
    def extract_dependencies(formula: str) -> Set[str]:
        """Extract line item names used in a formula"""
        if not formula:
            return set()
        return set(re.findall(r'[a-zA-Z]\w*', formula))

    def get_all_dependencies(item_name: str, depth: int = 2, visited=None) -> Set[str]:
        """Get all related items within specified depth - both up and downstream"""
        if visited is None:
            visited = set()
        if depth == 0 or item_name in visited:
            return set()
            
        visited.add(item_name)
        related = set()
        
        # Get items this depends on (upstream)
        formula = all_formulas.get(item_name, '')
        deps = extract_dependencies(formula)
        related.update(deps)
        
        # Get items that depend on this (downstream)
        dependents = set()
        for name, formula in all_formulas.items():
            if item_name in extract_dependencies(formula):
                dependents.add(name)
        related.update(dependents)
        
        # Recursively get related items
        for rel_item in deps.union(dependents):
            if rel_item not in visited:
                related.update(get_all_dependencies(rel_item, depth - 1, visited))
                
        return related

    # Get related items
    related_items = get_all_dependencies(line_item.name)
    related_items.add(line_item.name)
    
    # Generate Mermaid chart
    mermaid_lines = [
        "%%{init: {'flowchart': {'curve': 'basis', 'rankSpacing': 50, 'nodeSpacing': 50}}}%%",
        "flowchart TD"
    ]
    
    # Add nodes
    for item_name in related_items:
        clean_name = item_name.replace(" ", "_").replace("-", "_")
        if item_name == line_item.name:
            mermaid_lines.append(f'    {clean_name}["{item_name}"]:::focus')
        else:
            mermaid_lines.append(f'    {clean_name}["{item_name}"]')
    
    # Add connections
    added_connections = set()
    for item_name in related_items:
        clean_name = item_name.replace(" ", "_").replace("-", "_")
        formula = all_formulas.get(item_name, '')
        deps = extract_dependencies(formula)
        
        for dep in deps:
            if dep in related_items:  # Only show connections between related items
                clean_dep = dep.replace(" ", "_").replace("-", "_")
                connection = f"{clean_dep} --> {clean_name}"
                if connection not in added_connections:
                    mermaid_lines.append(f"    {connection}")
                    added_connections.add(connection)
    
    # Add class definitions
    mermaid_lines.append("classDef focus fill:#f9f,stroke:#333,stroke-width:2px;")
    
    return "\n".join(mermaid_lines)

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
    breadcrumbs = build_line_item_breadcrumbs(
        template_id, 'detail', item_id, db=db)
    formulas = dict(db.query(LineItemMeta.name, LineItemMeta.formula)
                    .filter(LineItemMeta.template_id == template_id)
                    .all())

    mermaid_chart = get_item_dependency_chart(line_item, formulas)
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        "lineitems/partials/detail.html",
        {
            "request": request,
            "line_item": line_item,
            "is_htmx": is_htmx,
            "formulas": formulas,
            "mermaid_chart": mermaid_chart,
            "breadcrumbs": breadcrumbs
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
