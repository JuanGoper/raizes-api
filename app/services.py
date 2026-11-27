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

def definir_consentimento(db: Session, usuario, aceito):
    usuario.consentimentoFidelidade = aceito
    usuario.dataConsentimento = agora()
    registrar_log(db, usuario.id, "CONSENTIMENTO_FIDELIDADE", "usuario", usuario.id, "aceito=" + str(aceito))
    db.commit()

def anonimizar(db: Session, usuario):
    usuario.nome = "Usuário anonimizado"
    usuario.email = "anonimo-" + str(usuario.id) + "@anonimizado.invalid"
    usuario.senhaHash = infra.gerar_hash(secrets.token_urlsafe(16))
    usuario.ativo = False
    usuario.consentimentoFidelidade = False
    registrar_log(db, usuario.id, "USUARIO_ANONIMIZADO", "usuario", usuario.id)
    db.commit()

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

#Funções de pedidos
def criar_pedido(db: Session, usuario, dados):
    unidade = db.get(Unidade, dados.unidadeId) #Registro de unidade
    if unidade is None:
        raise erro(404, "Unidade não encontrada.")
    clienteId = dados.clienteId
    if usuario.perfil == "CLIENTE": #Permitido não informar o id em caso de pedidos direto no balcão de unidade
        if clienteId not in (None, usuario.id):
            raise erro(403, "Você só pode criar pedidos em seu próprio nome.")
        clienteId = usuario.id
    elif clienteId is not None and db.get(Usuario, clienteId) is None:
        raise erro(404, "Cliente não encontrado.")
    pedido = Pedido(canalPedido=dados.canalPedido, clienteId=clienteId, unidadeId=unidade.id,
                    status="AGUARDANDO_PAGAMENTO", valorTotal=0)
    total = 0
    for item in dados.itens:
        produto = db.get(Produto, item.produtoId)
        if produto is None or not produto.ativo or produto.unidadeId != unidade.id:
            raise erro(404, "Produto " + str(item.produtoId) + " não encontrado nesta unidade.")
        if produto.estoque < item.quantidade:
            raise erro(409, "Estoque insuficiente para o produto " + str(produto.id) + " (disponível: " + str(produto.estoque) + ").")
        produto.estoque -= item.quantidade
        total += produto.preco * item.quantidade
        pedido.itens.append(ItemPedido(produtoId=produto.id, quantidade=item.quantidade, precoUnitario=produto.preco))
    pedido.valorTotal = round(total, 2)
    db.add(pedido)
    db.flush()
    registrar_log(db, usuario.id, "PEDIDO_CRIADO", "pedido", pedido.id, "canal=" + pedido.canalPedido)
    db.commit()
    return pedido

def buscar_pedido(db: Session, usuario, pedido_id):
    pedido = db.get(Pedido, pedido_id)
    if pedido is None or (usuario.perfil == "CLIENTE" and pedido.clienteId != usuario.id):
        raise erro(404, "Pedido não encontrado.")
    return pedido

def listar_pedidos(db: Session, usuario, canalPedido, status, unidadeId, page, limit):
    consulta = db.query(Pedido)
    if usuario.perfil == "CLIENTE":
        consulta = consulta.filter(Pedido.clienteId == usuario.id)
    if canalPedido:
        consulta = consulta.filter(Pedido.canalPedido == canalPedido)
    if status:
        consulta = consulta.filter(Pedido.status == status)
    if unidadeId:
        consulta = consulta.filter(Pedido.unidadeId == unidadeId)
    return paginar(consulta.order_by(Pedido.id.desc()), page, limit)

def mudar_status(db: Session, usuario, pedido_id, novo):
    pedido = buscar_pedido(db, usuario, pedido_id)
    if novo not in TRANSICOES.get(pedido.status, []):
        raise erro(409, "Não é permitido mudar o pedido de " + pedido.status + " para " + novo + ".")
    anterior = pedido.status
    pedido.status = novo
    registrar_log(db, usuario.id, "PEDIDO_STATUS_ALTERADO", "pedido", pedido.id, anterior + " -> " + novo)
    db.commit()
    return pedido

def cancelar_pedido(db: Session, usuario, pedido_id):
    pedido = buscar_pedido(db, usuario, pedido_id)
    if pedido.status not in PODE_CANCELAR:
        raise erro(409, "Pedido em " + pedido.status + " não pode mais ser cancelado.")
    for item in pedido.itens:
        db.get(Produto, item.produtoId).estoque += item.quantidade #Retorna ao estoque
    if pedido.pontosGerados:
        db.get(Usuario, pedido.clienteId).pontos -= pedido.pontosGerados
        pedido.pontosGerados = 0
    pedido.status = "CANCELADO"
    registrar_log(db, usuario.id, "PEDIDO_CANCELADO", "pedido", pedido.id)
    db.commit()
    return pedido

