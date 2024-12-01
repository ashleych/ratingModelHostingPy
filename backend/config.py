from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker



def create_engine_and_session(db_path):
    SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:postgres@localhost/{db_path}"

    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, Session()


# class WorkflowActionType(Enum):
#     DRAFT = "draft"

DB_NAME = "rating_model_py_app"

