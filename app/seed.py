#Arquivo de fonte de dados de demonstração para a API

from app import infra
from app.domain import Produto, Unidade, Usuario, agora

def criar_dados_iniciais(db):
    if db.query(Usuario).first():
        return  #Se já houverem dados no banco de dados

    equipe = [("Administrador Matriz", "admin@raizes.com", "Admin@123", "ADMIN"),
              ("Gerente Fortaleza", "gerente@raizes.com", "Gerente@123", "GERENTE"),
              ("Atendente Balcão", "atendente@raizes.com", "Atend@123", "ATENDENTE"),
              ("Cozinha Fortaleza", "cozinha@raizes.com", "Cozinha@123", "COZINHA"),
              ("Cliente Demo", "cliente@raizes.com", "Cliente@123", "CLIENTE")]
    for nome, email, senha, perfil in equipe:
        db.add(Usuario(nome=nome, email=email, senhaHash=infra.gerar_hash(senha), perfil=perfil,
                       aceitouTermos=True, dataAceite=agora(),
                       consentimentoFidelidade=(perfil == "CLIENTE"), dataConsentimento=agora()))

    fortaleza = Unidade(nome="Raízes Fortaleza", cidade="Fortaleza")
    maceio = Unidade(nome="Raízes Maceió (cozinha reduzida)", cidade="Maceio")
    db.add_all([fortaleza, maceio])
    db.flush()  #Iniciar ids de unidades

    #Unidades com diferentes produtos ofertados
    itens = [("Tapioca com ovo", 12.50, False), ("Cuscuz com carne seca", 18.90, False),
             ("Bolo de mandioca", 8.00, False), ("Suco de caju", 9.00, False), ("Canjica", 10.00, True)]
    for nome, preco, sazonal in itens:  #Cardápio Fortaleza
        db.add(Produto(nome=nome, preco=preco, sazonal=sazonal, estoque=50, unidadeId=fortaleza.id))
    for nome, preco, sazonal in itens:  #Cardápio Maceió
        if not nome.startswith("Cuscuz"):
            db.add(Produto(nome=nome, preco=preco, sazonal=sazonal, estoque=20, unidadeId=maceio.id))
    db.commit()