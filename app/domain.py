#Arquivo com a camada de domínio, entidades, regras básicas, tabelas do banco de dados

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def agora(): #Função para registro de operações
    return datetime.now(timezone.utc).replace(tzinfo=None)

#Definição das tabelas do banco de dados
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    email = Column(String, unique=True)
    senhaHash = Column(String)  #armazena apenas o hash, não a senha
    perfil = Column(String)
    ativo = Column(Boolean, default=True)
    pontos = Column(Integer, default=0)
    aceitouTermos = Column(Boolean, default=False)  #Termos de aceite e consentimento para atendimento a LGPD
    dataAceite = Column(DateTime)
    consentimentoFidelidade = Column(Boolean, default=False)
    dataConsentimento = Column(DateTime)

class Unidade(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    cidade = Column(String)

class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    preco = Column(Float)
    estoque = Column(Integer, default=0)
    sazonal = Column(Boolean, default=False)  #Para itens não permanentes no cardápio
    ativo = Column(Boolean, default=True) #Para possibilitar exibir produtos fora de estoque
    unidadeId = Column(Integer, ForeignKey("unidades.id"))  #Para identificação de produtos exclusivos de determinada unidade

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True)
    usuarioId = Column(Integer)
    acao = Column(String)
    entidade = Column(String)
    entidadeId = Column(Integer)
    detalhes = Column(Text)
    criadoEm = Column(DateTime, default=agora)
