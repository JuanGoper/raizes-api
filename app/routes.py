#Camada de rotas da API (endpoints), validação de dados, conferência de perfil e início nos serviços

from typing import List, Optional
import jwt
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app import infra, schemas, services
from app.domain import VALOR_PONTO, Produto, Unidade, Usuario

#Autenticação por token JWT
bearer = HTTPBearer(auto_error=False)

def usuario_logado(credenciais=Depends(bearer), db: Session = Depends(infra.get_db)):
    if credenciais is None:
        raise services.erro(401, "Token de acesso não informado.")
    try:
        dados = infra.ler_token(credenciais.credentials)
    except jwt.PyJWTError:
        raise services.erro(401, "Token inválido ou expirado.")
    usuario = db.get(Usuario, int(dados["sub"]))
    if usuario is None or not usuario.ativo:
        raise services.erro(401, "Usuário inexistente ou inativo.")
    return usuario

def checar_perfil(usuario, *perfis):
    if usuario.perfil not in perfis:
        raise services.erro(403, "Seu perfil não tem permissão para esta operação.")

#Regras de paginação das listagens
def pagina(page: int = Query(1, ge=1)):
    return page

def tamanho(limit: int = Query(10, ge=1, le=100)):
    return limit

#/auth
auth = APIRouter(prefix="/auth", tags=["Auth"])

@auth.post("/registro", response_model=schemas.UsuarioOut, status_code=201, summary="Cadastra um CLIENTE (exige aceite dos termos)")
def registro(dados: schemas.RegistroIn, db: Session = Depends(infra.get_db)):
    return services.criar_usuario(db, dados)

@auth.post("/login", response_model=schemas.TokenOut, summary="Faz login e devolve o token JWT")
def login(dados: schemas.LoginIn, db: Session = Depends(infra.get_db)):
    return {"accessToken": services.fazer_login(db, dados), "tokenType": "Bearer"}

#/usuarios
usuarios = APIRouter(prefix="/usuarios", tags=["Usuários"])

@usuarios.get("/me", response_model=schemas.UsuarioOut, summary="Dados do usuário logado")
def meus_dados(usuario=Depends(usuario_logado)):
    return usuario


#/unidades
unidades = APIRouter(prefix="/unidades", tags=["Unidades"])

@unidades.get("", response_model=List[schemas.UnidadeOut], summary="Lista as unidades (público)")
def listar_unidades(db: Session = Depends(infra.get_db)):
    return db.query(Unidade).order_by(Unidade.id).all()

@unidades.post("", response_model=schemas.UnidadeOut, status_code=201, summary="Cadastra unidade (ADMIN)")
def criar_unidade(dados: schemas.UnidadeIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN")
    return services.criar_unidade(db, usuario, dados)

@unidades.get("/{unidade_id}/cardapio", response_model=List[schemas.ProdutoOut], summary="Cardápio da unidade (público)")
def cardapio(unidade_id: int, db: Session = Depends(infra.get_db)):
    return services.cardapio_da_unidade(db, unidade_id)

#/produtos
produtos = APIRouter(prefix="/produtos", tags=["Produtos"])

@produtos.get("", response_model=schemas.ProdutoPagina, summary="Lista produtos ativos (paginado)")
def listar_produtos(page: int = Depends(pagina), limit: int = Depends(tamanho),
                    usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    consulta = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.id)
    return services.paginar(consulta, page, limit)

@produtos.get("/{produto_id}", response_model=schemas.ProdutoOut, summary="Consulta um produto")
def obter_produto(produto_id: int, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    return services.buscar_produto(db, produto_id)

@produtos.post("", response_model=schemas.ProdutoOut, status_code=201, summary="Cria produto (ADMIN ou GERENTE)")
def criar_produto(dados: schemas.ProdutoIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN", "GERENTE")
    return services.criar_produto(db, usuario, dados)

@produtos.put("/{produto_id}", response_model=schemas.ProdutoOut, summary="Atualiza produto (ADMIN ou GERENTE)")
def atualizar_produto(produto_id: int, dados: schemas.ProdutoIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN", "GERENTE")
    return services.atualizar_produto(db, usuario, produto_id, dados)

@produtos.delete("/{produto_id}", status_code=204, summary="Inativa produto (exclusão lógica)")
def inativar_produto(produto_id: int, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN", "GERENTE")
    services.inativar_produto(db, usuario, produto_id)

#/estoque
estoque = APIRouter(prefix="/estoque", tags=["Estoque"])

@estoque.post("/movimentos", response_model=schemas.EstoqueOut, status_code=201, summary="Entrada ou saída de estoque (ADMIN ou GERENTE)")
def movimentar(dados: schemas.MovimentoEstoqueIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN", "GERENTE")
    return services.movimentar_estoque(db, usuario, dados)

@estoque.get("", response_model=List[schemas.EstoqueOut], summary="Saldo de estoque de uma unidade (ADMIN ou GERENTE)")
def consultar_estoque(unidadeId: int, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "ADMIN", "GERENTE")
    return db.query(Produto).filter(Produto.unidadeId == unidadeId, Produto.ativo == True).order_by(Produto.id).all()

#/pedidos
pedidos = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@pedidos.post("", response_model=schemas.PedidoOut, status_code=201, summary="Cria pedido (canalPedido é obrigatório)")
def criar_pedido(dados: schemas.PedidoIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    return services.criar_pedido(db, usuario, dados)

@pedidos.get("", response_model=schemas.PedidoPagina, summary="Lista pedidos (filtros: canalPedido, status, unidadeId)")
def listar_pedidos(canalPedido: Optional[schemas.Canal] = None, status: Optional[schemas.Status] = None,
                   unidadeId: Optional[int] = None, page: int = Depends(pagina), limit: int = Depends(tamanho),
                   usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    return services.listar_pedidos(db, usuario, canalPedido, status, unidadeId, page, limit)

@pedidos.get("/{pedido_id}", response_model=schemas.PedidoOut, summary="Consulta um pedido")
def obter_pedido(pedido_id: int, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    return services.buscar_pedido(db, usuario, pedido_id)

@pedidos.patch("/{pedido_id}/status", response_model=schemas.PedidoOut, summary="Atualiza o status: em preparo, pronto, entregue (equipe)")
def atualizar_status(pedido_id: int, dados: schemas.StatusIn, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    checar_perfil(usuario, "COZINHA", "ATENDENTE", "GERENTE", "ADMIN")
    return services.mudar_status(db, usuario, pedido_id, dados.status)

@pedidos.post("/{pedido_id}/cancelar", response_model=schemas.PedidoOut, summary="Cancela o pedido, devolve o estoque e os pontos")
def cancelar(pedido_id: int, usuario=Depends(usuario_logado), db: Session = Depends(infra.get_db)):
    return services.cancelar_pedido(db, usuario, pedido_id)



TODAS = [auth, usuarios, unidades, produtos, estoque, pedidos, pagamentos, fidelidade, auditoria]