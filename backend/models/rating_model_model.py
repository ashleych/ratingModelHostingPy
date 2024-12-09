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



class RatingFactor(Base):
    __tablename__ = 'ratingfactor'

    name = Column(String, nullable=False)
    label = Column(String)
    input_source = Column(String)
    order_no = Column(Integer)
    factor_type = Column(String)
    parent_factor_name = Column(String)
    weightage = Column(Float)
    module_name = Column(String)
    module_order = Column(Integer)  # New field for module order
    formula = Column(String)
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'), nullable=False)

    rating_model = relationship("RatingModel")
    __table_args__ = (UniqueConstraint('rating_model_id', 'name', name='uix_rating_model_factorname'),)

    def get_factors_attributes(self, db: Session) -> List["RatingFactorAttribute"]:
        """
        Get the attributes of a rating factor.
        """
        return db.query(RatingFactorAttribute).filter_by(rating_factor_id=self.id).order_by(RatingFactorAttribute.score).all()

class RatingModel(Base):

    name = Column(String, unique=True)
    label = Column(String)
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)

    template = relationship("Template")

    def get_factor_by_name(self, name: str,db:Session) -> "RatingFactor|None":
        """
        Get the ID of a rating factor by its name.
        """
        factor = db.query(RatingFactor).filter_by(name=name).filter(RatingModel.id==self.id).first()
        if factor:
            return factor
        return None


class RatingModelApplicabilityRules(Base):
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'),nullable=False)
    business_unit_id = Column(UUID, ForeignKey('businessunit.id'))

    rating_model = relationship("RatingModel")
    business_unit = relationship("BusinessUnit")

class RatingFactorAttribute(Base):

    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'),nullable=False)
    rating_factor_id = Column(UUID, ForeignKey('ratingfactor.id'),nullable=False)
    rating_factor_name = Column(String)
    name = Column(String)
    label = Column(String)
    attribute_type = Column(String)
    bin_start = Column(Float)
    bin_end = Column(Float)
    score = Column(Float)

    rating_factor = relationship("RatingFactor")
    rating_model = relationship("RatingModel")


class FactorInputSource(enum.Enum):


    USER_INPUT = "user_input"
    FINANCIAL_STATEMENT = "financial_statement"
    DERIVED = "derived"


class FactorType(enum.Enum):
    QUALITATIVE = "qualitative"
    OVERALLSCORE = "overallScore"
    QUANTITATIVE = "quantitative"
    OVERALL="overall"


class AttributeType(enum.Enum):
    BIN = "bin"
    LOOKUP = "lookup"


class ScoreToGradeMapping(Base):
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'),nullable=False)
    bin_start=Column(Float)
    bin_end=Column(Float)
    grade=Column(String)

    rating_model = relationship("RatingModel")


class TemplateSourceCSV(Base):
    source_path = Column(String)


class MasterRatingScale(Base):
    rating_grade = Column(String, unique=True, nullable=False)
    pd = Column(Float, nullable=False)