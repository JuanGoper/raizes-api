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
SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-somente-para-desenvolvimento")
TOKEN_EXPIRA_MINUTOS = int(os.getenv("TOKEN_EXPIRA_MINUTOS", "60"))

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

#Regras de segurança e senhas
def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def senha_confere(senha, senha_hash):
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())

def criar_token(usuario_id):
    validade = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRA_MINUTOS)
    return jwt.encode({"sub": str(usuario_id), "exp": validade}, SECRET_KEY, algorithm="HS256")

def ler_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
