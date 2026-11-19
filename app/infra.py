#Camada de infraestrutura, com funções para banco de dados, segurança, senha e pagamento simulado

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import bcrypt
import jwt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.domain import Base

load_dotenv()  #Caso utilizar o .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./raizes.db")

#Regras do banco de dados sem necessidade de instalação
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def criar_tabelas():
    Base.metadata.create_all(bind=engine)

def get_db(): #Sessões a cada requisição
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

