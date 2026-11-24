#Camada de schemas, para organização dos dados em estrutura lógica

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"  #validação de formato de emails

class Saida(BaseModel): #Saída a partir dos dados do banco de dados
    model_config = {"from_attributes": True}

#Classes de dados de usuários
class RegistroIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL, max_length=160)
    senha: str = Field(min_length=8, max_length=72)
    aceiteTermos: bool
    consentimentoFidelidade: bool = False

class LoginIn(BaseModel):
    email: str
    senha: str

class TokenOut(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"

class UsuarioOut(Saida): #Não retorna senha
    id: int
    nome: str
    email: str
    perfil: str
    pontos: int

class ConsentimentoIn(BaseModel):
    fidelidade: bool

#Clasess de dados de unidades, produtos e estoques
class UnidadeIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    cidade: str = Field(min_length=2, max_length=80)

class UnidadeOut(Saida):
    id: int
    nome: str
    cidade: str

class ProdutoIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    preco: float = Field(gt=0)
    unidadeId: int
    sazonal: bool = False

class ProdutoOut(Saida):
    id: int
    nome: str
    preco: float
    estoque: int
    sazonal: bool
    unidadeId: int

class ProdutoPagina(BaseModel):
    items: List[ProdutoOut]
    page: int
    limit: int
    total: int

class MovimentoEstoqueIn(BaseModel):
    produtoId: int
    tipo: Literal["ENTRADA", "SAIDA"]
    quantidade: int = Field(gt=0)

class EstoqueOut(Saida):
    id: int
    nome: str
    estoque: int

