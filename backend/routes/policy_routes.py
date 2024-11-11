from fastapi.encoders import jsonable_encoder
from models.policy_rules_model import PolicyRule, WorkflowStageConfig
from models.statement_models import LineItemMeta, LineItemValue
from models.models import Role
from services.policy_service import PolicyRulesService
import json
import logging
from fastapi import APIRouter, Request, Form, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from typing import Any, Optional
from enums_and_constants import ActionRight
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
from dependencies import get_db, auth_handler

from schema.schema import PolicyRulesCreate, PolicyRulesResponse, User
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from enums_and_constants import WorkflowStage
from models.models import User, BusinessUnit
from schema.schema import (
    PolicyRuleCreate,
    PolicyRuleUpdate,
    PolicyRuleResponse,
    WorkflowStageConfigCreate
)
from enums_and_constants import RejectionFlow
from sqlalchemy.orm import joinedload

templates = Jinja2Templates(directory="../frontend/templates")

router = APIRouter(prefix="/policy-rules")




# @router.get("/{business_unit_id}", response_model=PolicyRulesResponse)
# async def get_policy_rules(
#     business_unit_id: UUID,
#     db: Session = Depends(get_db)
# ):
#     service = PolicyRulesService(db)
#     policy = service.get_workflow_configuration(business_unit_id)
#     if not policy:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No active policy found for business unit"
#         )
#     return policy



@router.get("/")
async def list_policy_rules(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper),
    is_htmx: bool = False
):
    """List all policy rules."""
    policy_rules = db.query(PolicyRule).all()

    if is_htmx:
        return templates.TemplateResponse(
            "policy_rules/partials/list.html",
            {
                "request": request,
                "policy_rules": policy_rules,
                "is_htmx": request.headers.get("HX-Request") == "true"
            }
        )

    return templates.TemplateResponse(
        "policy_rules/partials/list.html",
        {
            "request": request,
            "policies": jsonable_encoder(policy_rules),
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )


@router.get("/new")
async def new_policy_rule(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Show new policy rule form."""
    business_units = db.query(BusinessUnit).all()
    roles = db.query(Role).all()

    return templates.TemplateResponse(
        "policy_rules/partials/new.html",
        {
            "request": request,
            "business_units": business_units,
            "roles": roles,
            "action_rights": ActionRight,
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )

@router.post("/", response_model=PolicyRuleResponse)
async def create_policy_rule(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Create a new policy rule."""
    form_data = await request.form()

    # Create main policy rule
    policy_rule = PolicyRule(
        name=form_data.get("name"),
        business_unit_id=form_data.get("business_unit"),
        description=form_data.get("description"),
        is_active=True,
    )
    db.add(policy_rule)
    db.flush()

    # Create workflow stages
    stages = [
        {
            "stage": WorkflowStage.MAKER,
            "roles": form_data.getlist("maker_roles"),
            "rights": form_data.getlist("maker_rights"),
            "min_count": 1
        },
        {
            "stage": WorkflowStage.CHECKER,
            "roles": form_data.getlist("checker_roles"),
            "rights": form_data.getlist("checker_rights"),
            "min_count": int(form_data.get("min_checkers", 1))
        },
        {
            "stage": WorkflowStage.APPROVER,
            "roles": form_data.getlist("approver_roles"),
            "rights": form_data.getlist("approver_rights"),
            "min_count": int(form_data.get("min_approvers", 1)),
            "sequential_approval": form_data.get("sequential_approval") == "on",
            "rejection_flow": RejectionFlow.from_string(form_data.get("rejection_flow"))
        }
    ]

    for stage_config in stages:

        workflow_stage = WorkflowStageConfig(
            policy_id=policy_rule.id,
            stage=stage_config["stage"],
            allowed_roles=stage_config["roles"],
            rights=stage_config["rights"],
            min_count=stage_config["min_count"],


        )
        if stage_config['stage'] == WorkflowStage.APPROVER:
            workflow_stage.is_sequential = stage_config["sequential_approval"]
            workflow_stage.rejection_flow = stage_config["rejection_flow"]

        db.add(workflow_stage)

    db.commit()

    return templates.TemplateResponse(
        "policy_rules/partials/detail.html",
        {
            "request": request,
            "policy": policy_rule,
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )


@router.get("/view/{policy_id}", response_model=PolicyRuleResponse)
async def view_policy_rule(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Get policy rule details."""
    policy = (
        db.query(PolicyRule)
        .options(
            joinedload(PolicyRule.business_unit),
            joinedload(PolicyRule.workflow_stages)
        )
        .filter(PolicyRule.id == policy_id)
        .first()
    )
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    
    roles = db.query(Role).all()

    # Group workflow stages by type for easier template access
    workflow_config = {
        WorkflowStage.MAKER: None,
        WorkflowStage.CHECKER: None,
        WorkflowStage.APPROVER: None
    }
    
    for stage in policy.workflow_stages:
        workflow_config[stage.stage] = stage

    return templates.TemplateResponse(
        "policy_rules/partials/detail.html",
        {
            "request": request,
            "policy": policy,
            "roles": jsonable_encoder(roles),
            "action_rights": ActionRight,
            "workflow_config": workflow_config,
            "WorkflowStage": WorkflowStage,
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )

@router.get("/{policy_id}/edit")
async def edit_policy_rule(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Show edit policy rule form."""
    policy = (
        db.query(PolicyRule)
        .options(
            joinedload(PolicyRule.business_unit),
            joinedload(PolicyRule.workflow_stages)
        )
        .filter(PolicyRule.id == policy_id)
        .first()
    )
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    
    business_units = db.query(BusinessUnit).all()
    roles = db.query(Role).all()

    # Group workflow stages by type for easier template access
    workflow_config = {
        WorkflowStage.MAKER: None,
        WorkflowStage.CHECKER: None,
        WorkflowStage.APPROVER: None
    }
    
    for stage in policy.workflow_stages:
        workflow_config[stage.stage] = stage

    return templates.TemplateResponse(
        "policy_rules/partials/edit.html",
        {
            "request": request,
            "policy": policy,
            "business_units": business_units,
            "roles": jsonable_encoder(roles),
            "action_rights": ActionRight,
            "workflow_config": workflow_config,
            "WorkflowStage": WorkflowStage,  
            "is_htmx": request.headers.get("HX-Request") == "true"
        }
    )

@router.post("/{policy_id}")
async def update_policy_rule(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Update an existing policy rule."""
    form_data = await request.form()
    
    policy = db.query(PolicyRule).filter(PolicyRule.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy rule not found")

    # Update main policy rule
    policy.name = form_data.get("name")
    policy.business_unit_id = form_data.get("business_unit")
    policy.description = form_data.get("description")

    # Delete existing workflow stages
    db.query(WorkflowStageConfig).filter(
        WorkflowStageConfig.policy_id == policy_id
    ).delete()
    
    # Create new workflow stages
    stages = [
        {
            "stage": WorkflowStage.MAKER,
            "roles": form_data.getlist("maker_roles"),
            "rights": form_data.getlist("maker_rights"),
            "min_count": 1
        },
        {
            "stage": WorkflowStage.CHECKER,
            "roles": form_data.getlist("checker_roles"),
            "rights": form_data.getlist("checker_rights"),
            "min_count": int(form_data.get("min_checkers", 1))
        },
        {
            "stage": WorkflowStage.APPROVER,
            "roles": form_data.getlist("approver_roles"),
            "rights": form_data.getlist("approver_rights"),
            "min_count": int(form_data.get("min_approvers", 1)),
            "sequential_approval": form_data.get("sequential_approval") == "on",
            "rejection_flow": RejectionFlow.from_string(form_data.get("rejection_flow"))
        }
    ]

    for stage_config in stages:
        workflow_stage = WorkflowStageConfig(
            policy_id=policy.id,
            stage=stage_config["stage"],
            allowed_roles=stage_config["roles"],
            rights=stage_config["rights"],
            min_count=stage_config["min_count"]
        )
        
        if stage_config['stage'] == WorkflowStage.APPROVER:
            workflow_stage.is_sequential = stage_config["sequential_approval"]
            workflow_stage.rejection_flow = stage_config["rejection_flow"]

        db.add(workflow_stage)

    db.commit()
    db.refresh(policy)

    # Redirect to detail view
    return RedirectResponse(
        url=request.url_for('view_policy_rule', policy_id=policy.id),
        status_code=303
    )

# @router.get("/{policy_id}/edit")
# async def edit_policy_rule(
#     policy_id: UUID,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(auth_handler.auth_wrapper)
# ):
#     """Show edit policy rule form."""
#     policy_rule = db.query(PolicyRules).filter(
#         PolicyRules.id == policy_id).first()
#     if not policy_rule:
#         raise HTTPException(status_code=404, detail="Policy rule not found")

#     business_units = db.query(BusinessUnit).all()
#     roles = db.query(Role).all()

#     return templates.TemplateResponse(
#         "policy_rules/partials/edit.html",
#         {
#             "request": request,
#             "policy": policy_rule,
#             "business_units": business_units,
#             "roles": roles,
#             "action_rights": ActionRight,
#             "is_htmx": True
#         }
#     )


# @router.post("/{policy_id}")
# async def update_policy_rule(
#     policy_id: UUID,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(auth_handler.auth_wrapper)
# ):
#     """Update a policy rule."""
#     policy_rule = db.query(PolicyRules).filter(
#         PolicyRules.id == policy_id).first()
#     if not policy_rule:
#         raise HTTPException(status_code=404, detail="Policy rule not found")

#     form_data = await request.form()

#     # Update main policy rule
#     policy_rule.name = form_data.get("name")
#     policy_rule.business_unit_id = form_data.get("business_unit")
#     policy_rule.description = form_data.get("description")
#     policy_rule.sequential_approval = form_data.get(
#         "sequential_approval") == "on"
#     policy_rule.rejection_flow = RejectionFlow(form_data.get("rejection_flow"))
#     policy_rule.updated_at = datetime.utcnow()

#     # Update workflow stages
#     stages = [
#         {
#             "stage": WorkflowStage.MAKER,
#             "roles": form_data.getlist("maker_roles"),
#             "rights": form_data.getlist("maker_rights"),
#             "min_count": 1
#         },
#         {
#             "stage": WorkflowStage.CHECKER,
#             "roles": form_data.getlist("checker_roles"),
#             "rights": form_data.getlist("checker_rights"),
#             "min_count": int(form_data.get("min_checkers", 1))
#         },
#         {
#             "stage": WorkflowStage.APPROVER,
#             "roles": form_data.getlist("approver_roles"),
#             "rights": form_data.getlist("approver_rights"),
#             "min_count": int(form_data.get("min_approvers", 1))
#         }
#     ]

#     # Delete existing stages
#     db.query(WorkflowStageConfig).filter(
#         WorkflowStageConfig.policy_id == policy_id
#     ).delete()

#     # Create new stages
#     for stage_config in stages:
#         workflow_stage = WorkflowStageConfig(
#             policy_id=policy_rule.id,
#             stage=stage_config["stage"],
#             allowed_roles=stage_config["roles"],
#             rights=stage_config["rights"],
#             min_count=stage_config["min_count"]
#         )
#         db.add(workflow_stage)

#     db.commit()

#     return templates.TemplateResponse(
#         "policy_rules/partials/detail.html",
#         {
#             "request": request,
#             "policy": policy_rule,
#             "is_htmx": True
#         }
#     )


@router.delete("/{policy_id}")
async def delete_policy_rule(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_handler.auth_wrapper)
):
    """Delete a policy rule."""
    policy_rule = db.query(PolicyRule).filter(
        PolicyRule.id == policy_id).first()
    if not policy_rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")

    # Delete workflow stages first due to foreign key constraint
    db.query(WorkflowStageConfig).filter(
        WorkflowStageConfig.policy_id == policy_id
    ).delete()

    db.delete(policy_rule)
    db.commit()

    return {"message": "Policy rule deleted successfully"}


# @router.post("/{policy_id}/activate")
# async def activate_policy_rule(
#     policy_id: UUID,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(auth_handler.auth_wrapper)
# ):
#     """Activate a policy rule."""
#     policy_rule = db.query(PolicyRules).filter(
#         PolicyRules.id == policy_id).first()
#     if not policy_rule:
#         raise HTTPException(status_code=404, detail="Policy rule not found")

#     policy_rule.is_active = True
#     policy_rule.updated_at = datetime.utcnow()
#     db.commit()

#     return templates.TemplateResponse(
#         "policy_rules/partials/detail.html",
#         {
#             "request": request,
#             "policy": policy_rule,
#             "is_htmx": True
#         }
#     )


# @router.post("/{policy_id}/deactivate")
# async def deactivate_policy_rule(
#     policy_id: UUID,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(auth_handler.auth_wrapper)
# ):
#     """Deactivate a policy rule."""
#     policy_rule = db.query(PolicyRules).filter(
#         PolicyRules.id == policy_id).first()
#     if not policy_rule:
#         raise HTTPException(status_code=404, detail="Policy rule not found")

#     policy_rule.is_active = False
#     policy_rule.updated_at = datetime.utcnow()
#     db.commit()

#     return templates.TemplateResponse(
#         "policy_rules/partials/detail.html",
#         {
#             "request": request,
#             "policy": policy_rule,
#             "is_htmx": True
#         }
#     )
