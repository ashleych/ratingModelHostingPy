
import string
from pydantic import ConfigDict, BaseModel
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Column, DateTime, UUID, null

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON,UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from sqlalchemy import Enum as SQLAlchemyEnum
from .base import Base
from typing import List
from sqlalchemy.orm import Session

from schema.schema import WorkflowStatus


class FinancialStatement(Base):

    actuals = Column(Boolean)
    projections = Column(Boolean)
    audit_type = Column(String)  # Audited, Unaudited
    standalone = Column(Boolean)
    consolidated = Column(Boolean)
    financials_period_year = Column(Integer)
    financials_period_month = Column( Integer)
    financials_period_date = Column( Integer)
    customer_id = Column(UUID, ForeignKey('customer.id'),nullable=False)
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)
    # workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'), nullable=False)
    # workflow_action_type = Column(String, default=WorkflowActionType.DRAFT.value)
    is_dirty = Column(Boolean, default=True)
    preferred_statement = Column(Boolean)
    source_of_lag_variables = Column(Integer)
    preceding_statement_id=Column(UUID)

    customer = relationship("Customer")
    template = relationship("Template")


class LineItemMeta(Base):
    __table_args__ = (
        UniqueConstraint('template_id', 'name', name='uix_template_name'),
    )
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)
    template = relationship("Template")
    fin_statement_type = Column(String)
    header = Column(Boolean)
    formula = Column(String)
    type = Column(String)
    label = Column(String)
    name = Column(String,nullable=False)
    lag_months = Column(Integer)
    display = Column(Boolean)
    order_no = Column(Integer)
    display_order_no = Column(Integer)


class LineItemValue(Base):

    financial_statement_id = Column(UUID, ForeignKey('financialstatement.id'),nullable=False)
    line_item_meta_id = Column(UUID, ForeignKey('lineitemmeta.id'),nullable=False)
    value = Column(Float, nullable=True)
    financial_statement = relationship("FinancialStatement")
    line_item_meta = relationship("LineItemMeta")
    __table_args__ = ( UniqueConstraint('financial_statement_id', 'line_item_meta_id', name='uix_financial_statement_line_item'), )

    def __repr__(self):
        return f"<LineItemValue(financial_statement_id={self.financial_statement_id}, line_item_meta_id='{self.line_item_meta_id}', value={self.value})>"


class FinancialsPeriod(Base):
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    date = Column(Integer, nullable=False)
    type = Column(String, nullable=False)


class Template(Base):
    name = Column(String, nullable=False)
    description = Column(String)
    template_source_csv_id = Column(UUID, ForeignKey('templatesourcecsv.id'))
    template_source_csv = relationship("TemplateSourceCSV")
