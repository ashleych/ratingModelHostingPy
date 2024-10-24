
from security import AuthHandler, RequiresLoginException
from db.database import SessionLocal 
from models.models import User
from typing import Optional
from passlib.context import CryptContext
from jose import jwt

from fastapi import FastAPI, Request, Response

from db.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


auth_handler = AuthHandler()