#Camada de aplicação, com as regras de cada oepração da API (dados, caminhos, comunicação com o banco, erros

import secrets
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import infra
from app.domain import (PODE_CANCELAR, PODE_PAGAR, TRANSICOES, VALOR_PONTO, ItemPedido, LogAuditoria,
                        Pagamento, Pedido, Produto, Unidade, Usuario, agora)

def erro(status, mensagem):
    return HTTPException(status_code=status, detail=mensagem)

def registrar_log(db, usuario_id, acao, entidade, entidade_id=None, detalhes=None): #Consulta para auditoria, sem retenção de dados pessoais
    db.add(LogAuditoria(usuarioId=usuario_id, acao=acao, entidade=entidade, entidadeId=entidade_id, detalhes=detalhes))

def paginar(consulta, page, limit): #Consulta por página específica dos resutlados
    total = consulta.count()
    itens = consulta.offset((page - 1) * limit).limit(limit).all()
    return {"items": itens, "page": page, "limit": limit, "total": total}

#FUnções de usuário com atendimento a LGPD
def criar_usuario(db: Session, dados):
    if not dados.aceiteTermos:
        raise erro(422, "É necessário aceitar os termos de uso e a política de privacidade (LGPD).")
    email = dados.email.strip().lower()
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise erro(409, "Já existe um usuário com este e-mail.")
    usuario = Usuario(nome=dados.nome.strip(), email=email, senhaHash=infra.gerar_hash(dados.senha),
                      perfil="CLIENTE",  # o cadastro público só cria CLIENTE; a equipe vem do seed
                      aceitouTermos=True, dataAceite=agora(),
                      consentimentoFidelidade=dados.consentimentoFidelidade, dataConsentimento=agora())
    db.add(usuario)
    db.flush()
    registrar_log(db, usuario.id, "USUARIO_CRIADO", "usuario", usuario.id)
    db.commit()
    return usuario

def fazer_login(db: Session, dados):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email.strip().lower()).first()
    if usuario is None or not usuario.ativo or not infra.senha_confere(dados.senha, usuario.senhaHash):
        raise erro(401, "E-mail ou senha inválidos.")
    registrar_log(db, usuario.id, "LOGIN", "usuario", usuario.id)
    db.commit()
    return infra.criar_token(usuario.id)



#Funções para unidades, produtos e estoques
def criar_unidade(db: Session, usuario, dados):
    unidade = Unidade(nome=dados.nome, cidade=dados.cidade)
    db.add(unidade)
    db.flush()
    registrar_log(db, usuario.id, "UNIDADE_CRIADA", "unidade", unidade.id)
    db.commit()
    return unidade

def buscar_produto(db: Session, produto_id):
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise erro(404, "Produto não encontrado.")
    return produto

def criar_produto(db: Session, usuario, dados):
    if db.get(Unidade, dados.unidadeId) is None:
        raise erro(404, "Unidade não encontrada.")
    produto = Produto(nome=dados.nome, preco=dados.preco, sazonal=dados.sazonal, unidadeId=dados.unidadeId, estoque=0)
    db.add(produto)
    db.flush()
    registrar_log(db, usuario.id, "PRODUTO_CRIADO", "produto", produto.id)
    db.commit()
    return produto

def atualizar_produto(db: Session, usuario, produto_id, dados):
    produto = buscar_produto(db, produto_id)
    produto.nome, produto.preco, produto.sazonal = dados.nome, dados.preco, dados.sazonal
    registrar_log(db, usuario.id, "PRODUTO_ATUALIZADO", "produto", produto.id)
    db.commit()
    return produto

def inativar_produto(db: Session, usuario, produto_id):
    produto = buscar_produto(db, produto_id)
    produto.ativo = False  # não apagamos: os pedidos antigos continuam consistentes
    registrar_log(db, usuario.id, "PRODUTO_INATIVADO", "produto", produto.id)
    db.commit()

def movimentar_estoque(db: Session, usuario, dados):
    produto = buscar_produto(db, dados.produtoId)
    if dados.tipo == "SAIDA":
        if produto.estoque < dados.quantidade:
            raise erro(409, "Estoque insuficiente: o saldo atual é " + str(produto.estoque) + ".")
        produto.estoque -= dados.quantidade
    else:
        produto.estoque += dados.quantidade
    registrar_log(db, usuario.id, "ESTOQUE_MOVIMENTADO", "produto", produto.id,
                  dados.tipo + " " + str(dados.quantidade))
    db.commit()
    return produto

def cardapio_da_unidade(db: Session, unidade_id):
    if db.get(Unidade, unidade_id) is None:
        raise erro(404, "Unidade não encontrada.")
    return (db.query(Produto).filter(Produto.unidadeId == unidade_id, Produto.ativo == True, Produto.estoque > 0)
            .order_by(Produto.nome).all())

