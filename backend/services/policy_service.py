# --- Service Layer ---

import json
import logging
from fastapi import APIRouter, Request, Form, HTTPException, Depends,Query,status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from typing import Any, Optional
from models.policy_rules_model import PolicyRule, WorkflowStageConfig
from models.statement_models import LineItemMeta, LineItemValue
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
from dependencies import get_db,auth_handler
from models.models import User, BusinessUnit
from schema.schema import (
    PolicyRuleCreate, 
    PolicyRuleUpdate, 
    PolicyRuleResponse,
    WorkflowStageConfigCreate
)
from enums_and_constants import WorkflowStage,ActionRight

class PolicyRulesService:

    def __init__(self, db: Session):
        self.db = db
    
    def create_policy_rules(self, data: PolicyRuleCreate) -> PolicyRule:
        # Create policy
        policy = PolicyRule(
            business_unit_id=data.business_unit_id,
            name=data.name,
            description=data.description
        )
        self.db.add(policy)
        self.db.flush()
        
        # Create workflow stages
        for stage_config in data.workflow_stages:
            workflow_stage = WorkflowStageConfig(
                policy_id=policy.id,
                stage=stage_config.stage,
                min_count=stage_config.min_count,
                allowed_roles=stage_config.allowed_roles,
                rights=stage_config.rights,
                order_in_stage=stage_config.order_in_stage,
                is_sequential=stage_config.is_sequential,
                rejection_flow=stage_config.rejection_flow
            )
            self.db.add(workflow_stage)
        
        self.db.commit()
        return policy
    
    def get_workflow_configuration(self, business_unit_id: UUID) -> Optional[PolicyRule]:
        return self.db.query(PolicyRule).filter(
            PolicyRule.business_unit_id == business_unit_id,
            PolicyRule.is_active == True
        ).first()
    
    def validate_user_stage_access(
        self,
        user_role: str,
        business_unit_id: UUID,
        stage: WorkflowStage
    ) -> Dict[str, Set[ActionRight]]:
        policy = self.get_workflow_configuration(business_unit_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active policy found for business unit"
            )
        
        stage_config = next(
            (s for s in policy.workflow_stages if s.stage == stage),
            None
        )
        
        if not stage_config or user_role not in stage_config.allowed_roles:
            return {"allowed": False, "rights": set()}
        
        return {
            "allowed": True,
            "rights": set(stage_config.rights)
        }

