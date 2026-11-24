#Camada principal de API, roda através do comando no terminal: uvicorn app.main:app --reload

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ErroHTTP
from app import infra, routes, seed

#Criação do banco na primeira execução da API
@asynccontextmanager
async def ao_iniciar(app):
    infra.criar_tabelas()
    with infra.SessionLocal() as db:
        seed.criar_dados_iniciais(db)
    yield

app = FastAPI(title="Raízes do Nordeste - API Back-end", version="1.0.0", lifespan=ao_iniciar,
              description="API REST multicanal (APP, TOTEM, BALCAO, PICKUP, WEB) com pedidos, estoque por unidade, "
                          "fidelidade com consentimento (LGPD) e pagamento simulado (mock).")
for rota in routes.TODAS:
    app.include_router(rota)

#Regras para apresentação dos erros em padrão
def erro_json(request, status, mensagem, detalhes=None):
    return JSONResponse(status_code=status, content={
        "timestamp": datetime.now(timezone.utc).isoformat(), "status": status,
        "erro": HTTPStatus(status).phrase, "mensagem": mensagem,
        "caminho": request.url.path, "detalhes": detalhes})

@app.exception_handler(ErroHTTP)
async def tratar_erro_http(request: Request, e: ErroHTTP):
    return erro_json(request, e.status_code, str(e.detail))

@app.exception_handler(RequestValidationError)  #Erros para inclusão de dados inválidos
async def tratar_validacao(request: Request, e: RequestValidationError):
    detalhes = [{"campo": ".".join(str(p) for p in x["loc"] if p not in ("body", "query")), "problema": x["msg"]}
                for x in e.errors()]
    return erro_json(request, 422, "Dados da requisição inválidos.", detalhes)

@app.exception_handler(Exception)  #Erros independents do usuário
async def tratar_erro_inesperado(request: Request, e: Exception):
    return erro_json(request, 500, "Erro interno inesperado.")