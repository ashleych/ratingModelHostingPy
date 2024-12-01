from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean

from enums_and_constants import WorkflowStage
from schema.schema import Role, User



class ApprovalTracking(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True,extra='allow')

    required_maker_approvers:int
    required_checker_approvers:int
    required_approver_approvers:int
    allowed_maker_approvers:List[Role] 
    allowed_checker_approvers:List[Role] 
    allowed_approver_approvers:List[Role] 

    acutal_maker_approvers:Optional[List[User]]=None
    actual_checker_approvers:Optional[List[User]]=None
    actual_approver_approvers:Optional[List[User]]=None

    maker_stage_approved:Optional[bool]=False
    checker_stage_approved:Optional[bool]=False
    approver_stage_approved:Optional[bool]=False

    def update_approval_status(self):
            if self.required_maker_approvers==len(self.acutal_maker_approvers):
                self.maker_stage_approved = True
            if self.required_checker_approvers==len(self.actual_checker_approvers):
                self.checker_stage_approved = True
            if self.required_approver_approvers==len(self.actual_approver_approvers):
                self.approver_stage_approved = True

            

    def get_stage_level_approval_status(self,stage:WorkflowStage) -> bool|None:
        if stage==WorkflowStage.MAKER:
             return self.maker_stage_approved
        if stage==WorkflowStage.CHECKER:
             return self.checker_stage_approved
        if stage==WorkflowStage.APPROVER:
             return self.approver_stage_approved
        return None