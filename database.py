from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Usaremos SQLite para desarrollo rápido. Luego puedes migrar a PostgreSQL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./expedientes.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()