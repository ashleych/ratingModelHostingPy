from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLALCHEMY_DATABASE_URL = getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./sql_app.db")
SQLALCHEMY_DATABASE_URL ="postgresql://postgres:postgres@localhost/rating_model_py_app"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL 
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()