import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas import ConsentimentoUpdate, LogAuditoriaResponse, MovimentoEstoqueCreate, PagamentoProcessar, PedidoCreate, PedidoResponse, ProdutoCreate, ProdutoResponse, ProdutoUpdate, ResgatePontos, StatusUpdate, Token, UnidadeCreate, UnidadeResponse, UnidadeUpdate, UsuarioCreate, UsuarioResponse
from app.application.services import registrar_log, seed_db, usuario_pode_acessar_pedido
from app.core.security import create_access_token, get_current_user, get_password_hash, verificar_perfil, verify_password
from app.domain.enums import CanalPedidoEnum, MetodoPagamentoEnum, PerfilEnum, StatusPedidoEnum, TipoMovimentoEnum
from app.infrastructure.database import Base, engine, get_db
from app.infrastructure.models import EstoqueUnidade, HistoricoFidelidade, ItemPedido, LogAuditoria, MovimentoEstoque, Pagamento, Pedido, Produto, Unidade, Usuario


Base.metadata.create_all(bind=engine)
seed_db()

app = FastAPI(title="API Raízes do Nordeste", version="2.0.0", description="API acadêmica para unidades, cardápio, pedidos multicanal, pagamento mock, estoque, fidelidade e auditoria.")


def erro_exemplo(nome: str, mensagem: str):
    return {"content": {"application/json": {"example": {"error": nome, "message": mensagem, "details": [], "timestamp": "2026-02-05T12:00:00Z", "path": "/rota", "requestId": "uuid"}}}}


RESPOSTAS_COMUNS = {
    401: erro_exemplo("HTTP_ERROR", "Token ausente ou inválido."),
    403: erro_exemplo("HTTP_ERROR", "Acesso não autorizado."),
    404: erro_exemplo("HTTP_ERROR", "Recurso não encontrado."),
    409: erro_exemplo("HTTP_ERROR", "Conflito com uma regra de negócio."),
    422: erro_exemplo("VALIDATION_ERROR", "Erro de validação nos dados enviados."),
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": "HTTP_ERROR", "message": exc.detail, "details": [], "timestamp": datetime.now(timezone.utc).isoformat(), "path": request.url.path, "requestId": str(uuid.uuid4())}, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "VALIDATION_ERROR", "message": "Erro de validação nos dados enviados.", "details": exc.errors(), "timestamp": datetime.now(timezone.utc).isoformat(), "path": request.url.path, "requestId": str(uuid.uuid4())})


@app.get("/health", tags=["Saúde"])
def health():
    return {"status": "ok"}


@app.post("/auth/registro", response_model=UsuarioResponse, status_code=201, responses=RESPOSTAS_COMUNS, tags=["Autenticação"])
def registrar(user: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == user.email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    novo = Usuario(nome=user.nome, email=user.email, senha_hash=get_password_hash(user.senha), perfil=PerfilEnum.CLIENTE, aceitou_fidelidade=user.aceitou_fidelidade, data_consentimento=datetime.now(timezone.utc) if user.aceitou_fidelidade else None)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@app.post("/auth/login", response_model=Token, responses=RESPOSTAS_COMUNS, tags=["Autenticação"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not user or not verify_password(form.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais incorretas.")
    registrar_log(db, user, "LOGIN_SUCESSO", detalhes="Autenticação concluída")
    db.commit()
    return {"access_token": create_access_token({"sub": str(user.id), "perfil": user.perfil.value}), "token_type": "bearer"}


@app.get("/unidades", response_model=list[UnidadeResponse], tags=["Unidades"])
def listar_unidades(db: Session = Depends(get_db)):
    return db.query(Unidade).filter(Unidade.ativo.is_(True)).order_by(Unidade.nome).all()


@app.post("/unidades", response_model=UnidadeResponse, status_code=201, responses=RESPOSTAS_COMUNS, tags=["Unidades"])
def criar_unidade(payload: UnidadeCreate, db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ADMINISTRADOR]))):
    if db.query(Unidade).filter(Unidade.nome == payload.nome).first():
        raise HTTPException(status_code=409, detail="Já existe uma unidade com este nome.")
    unidade = Unidade(**payload.model_dump())
    db.add(unidade)
    registrar_log(db, user, "CRIAR_UNIDADE", detalhes=payload.nome)
    db.commit()
    db.refresh(unidade)
    return unidade


@app.patch("/unidades/{unidade_id}", response_model=UnidadeResponse, responses=RESPOSTAS_COMUNS, tags=["Unidades"])
def atualizar_unidade(unidade_id: int, payload: UnidadeUpdate, db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ADMINISTRADOR]))):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada.")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(unidade, campo, valor)
    registrar_log(db, user, "ATUALIZAR_UNIDADE", detalhes=f"Unidade {unidade_id}")
    db.commit()
    db.refresh(unidade)
    return unidade


@app.get("/produtos", response_model=list[ProdutoResponse], tags=["Produtos"])
def listar_produtos(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return db.query(Produto).filter(Produto.ativo.is_(True)).order_by(Produto.nome).offset((page - 1) * limit).limit(limit).all()


@app.post("/produtos", response_model=ProdutoResponse, status_code=201, responses=RESPOSTAS_COMUNS, tags=["Produtos"])
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ADMINISTRADOR]))):
    produto = Produto(**payload.model_dump())
    db.add(produto)
    db.flush()
    registrar_log(db, user, "CRIAR_PRODUTO", detalhes=f"Produto {produto.id}")
    db.commit()
    db.refresh(produto)
    return produto


@app.patch("/produtos/{produto_id}", response_model=ProdutoResponse, responses=RESPOSTAS_COMUNS, tags=["Produtos"])
def atualizar_produto(produto_id: int, payload: ProdutoUpdate, db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ADMINISTRADOR]))):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)
    registrar_log(db, user, "ATUALIZAR_PRODUTO", detalhes=f"Produto {produto_id}")
    db.commit()
    db.refresh(produto)
    return produto


@app.get("/unidades/{unidade_id}/cardapio", tags=["Cardápio"])
def listar_cardapio_unidade(unidade_id: int, db: Session = Depends(get_db)):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id, Unidade.ativo.is_(True)).first()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada ou inativa.")
    linhas = db.query(EstoqueUnidade, Produto).join(Produto, Produto.id == EstoqueUnidade.produto_id).filter(EstoqueUnidade.unidade_id == unidade_id, Produto.ativo.is_(True)).all()
    return [{"produtoId": p.id, "nome": p.nome, "descricao": p.descricao, "preco": p.preco, "categoria": p.categoria, "quantidadeDisponivel": e.quantidade} for e, p in linhas]


@app.get("/estoque/{unidade_id}", responses=RESPOSTAS_COMUNS, tags=["Estoque"])
def consultar_estoque(unidade_id: int, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ATENDENTE, PerfilEnum.COZINHA, PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR]))):
    if user.perfil in (PerfilEnum.ATENDENTE, PerfilEnum.COZINHA) and user.unidade_id != unidade_id:
        raise HTTPException(status_code=403, detail="Acesso permitido somente ao estoque da unidade vinculada.")
    linhas = db.query(EstoqueUnidade, Produto).join(Produto, Produto.id == EstoqueUnidade.produto_id).filter(EstoqueUnidade.unidade_id == unidade_id).offset((page - 1) * limit).limit(limit).all()
    return [{"produtoId": p.id, "nome": p.nome, "quantidade": e.quantidade} for e, p in linhas]


@app.post("/estoque/movimentacoes", status_code=201, responses=RESPOSTAS_COMUNS, tags=["Estoque"])
def movimentar_estoque(payload: MovimentoEstoqueCreate, db: Session = Depends(get_db), user: Usuario = Depends(verificar_perfil([PerfilEnum.ATENDENTE, PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR]))):
    if user.perfil == PerfilEnum.ATENDENTE and user.unidade_id != payload.unidade_id:
        raise HTTPException(status_code=403, detail="Acesso permitido somente à unidade vinculada.")
    unidade = db.query(Unidade).filter(Unidade.id == payload.unidade_id).first()
    produto = db.query(Produto).filter(Produto.id == payload.produto_id).first()
    if not unidade or not produto:
        raise HTTPException(status_code=404, detail="Unidade ou produto não encontrado.")
    estoque = db.query(EstoqueUnidade).filter_by(unidade_id=payload.unidade_id, produto_id=payload.produto_id).first()
    if not estoque:
        estoque = EstoqueUnidade(unidade_id=payload.unidade_id, produto_id=payload.produto_id, quantidade=0)
        db.add(estoque)
        db.flush()
    if payload.tipo == TipoMovimentoEnum.SAIDA and estoque.quantidade < payload.quantidade:
        raise HTTPException(status_code=409, detail="Estoque insuficiente para a saída solicitada.")
    estoque.quantidade += payload.quantidade if payload.tipo == TipoMovimentoEnum.ENTRADA else -payload.quantidade
    movimento = MovimentoEstoque(usuario_id=user.id, **payload.model_dump())
    db.add(movimento)
    registrar_log(db, user, f"ESTOQUE_{payload.tipo.value}", detalhes=f"Unidade {payload.unidade_id}; produto {payload.produto_id}; quantidade {payload.quantidade}")
    db.commit()
    db.refresh(movimento)
    return {"movimentoId": movimento.id, "saldoAtual": estoque.quantidade}


@app.post("/pedidos", response_model=PedidoResponse, status_code=201, responses=RESPOSTAS_COMUNS, tags=["Pedidos"])
def criar_pedido(payload: PedidoCreate, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    unidade = db.query(Unidade).filter(Unidade.id == payload.unidade_id, Unidade.ativo.is_(True)).first()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada ou inativa.")
    quantidades = defaultdict(int)
    for item in payload.itens:
        quantidades[item.produto_id] += item.quantidade
    produtos = {p.id: p for p in db.query(Produto).filter(Produto.id.in_(quantidades.keys()), Produto.ativo.is_(True)).all()}
    itens, total = [], Decimal("0.00")
    for produto_id, quantidade in quantidades.items():
        produto = produtos.get(produto_id)
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto ID {produto_id} não encontrado.")
        estoque = db.query(EstoqueUnidade).filter_by(unidade_id=payload.unidade_id, produto_id=produto_id).first()
        if not estoque or estoque.quantidade < quantidade:
            raise HTTPException(status_code=409, detail=f"Estoque insuficiente para o produto ID {produto_id}.")
        total += Decimal(produto.preco) * quantidade
        itens.append(ItemPedido(produto_id=produto_id, quantidade=quantidade, preco_unitario=produto.preco))
    pedido = Pedido(usuario_id=user.id, unidade_id=payload.unidade_id, canal_pedido=payload.canal_pedido, valor_total=total, itens=itens)
    db.add(pedido)
    db.flush()
    registrar_log(db, user, "CRIAR_PEDIDO", pedido.id, f"Canal {payload.canal_pedido.value}; valor {total}")
    db.commit()
    db.refresh(pedido)
    return pedido


@app.get("/pedidos", response_model=list[PedidoResponse], responses=RESPOSTAS_COMUNS, tags=["Pedidos"])
def listar_pedidos(unidade_id: Optional[int] = Query(None, alias="unidadeId"), pedido_status: Optional[StatusPedidoEnum] = Query(None, alias="status"), canal_pedido: Optional[CanalPedidoEnum] = Query(None, alias="canalPedido"), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    query = db.query(Pedido)
    if user.perfil == PerfilEnum.CLIENTE:
        query = query.filter(Pedido.usuario_id == user.id)
    elif user.perfil in (PerfilEnum.ATENDENTE, PerfilEnum.COZINHA):
        query = query.filter(Pedido.unidade_id == user.unidade_id)
    if unidade_id is not None:
        query = query.filter(Pedido.unidade_id == unidade_id)
    if pedido_status is not None:
        query = query.filter(Pedido.status == pedido_status)
    if canal_pedido is not None:
        query = query.filter(Pedido.canal_pedido == canal_pedido)
    return query.order_by(Pedido.criado_em.desc()).offset((page - 1) * limit).limit(limit).all()


@app.get("/pedidos/{pedido_id}", response_model=PedidoResponse, responses=RESPOSTAS_COMUNS, tags=["Pedidos"])
def obter_pedido(pedido_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if not usuario_pode_acessar_pedido(user, pedido):
        raise HTTPException(status_code=403, detail="Acesso não autorizado ao pedido.")
    return pedido


@app.patch("/pedidos/{pedido_id}/status", response_model=PedidoResponse, responses=RESPOSTAS_COMUNS, tags=["Pedidos"])
def atualizar_status_pedido(pedido_id: int, payload: StatusUpdate, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if not usuario_pode_acessar_pedido(user, pedido):
        raise HTTPException(status_code=403, detail="Acesso não autorizado ao pedido.")
    atual, novo = pedido.status, payload.novo_status
    if atual in (StatusPedidoEnum.ENTREGUE, StatusPedidoEnum.CANCELADO):
        raise HTTPException(status_code=409, detail=f"Pedidos {atual.value} não podem ser alterados.")
    permitido, devolver_estoque = False, False
    if novo == StatusPedidoEnum.CANCELADO:
        if atual in (StatusPedidoEnum.AGUARDANDO_PAGAMENTO, StatusPedidoEnum.PAGAMENTO_RECUSADO):
            permitido = (user.perfil == PerfilEnum.CLIENTE and pedido.usuario_id == user.id) or user.perfil in (PerfilEnum.ATENDENTE, PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR)
        elif atual in (StatusPedidoEnum.EM_PREPARACAO, StatusPedidoEnum.PRONTO):
            permitido = user.perfil in (PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR)
            devolver_estoque = permitido
    elif atual == StatusPedidoEnum.EM_PREPARACAO and novo == StatusPedidoEnum.PRONTO:
        permitido = user.perfil in (PerfilEnum.COZINHA, PerfilEnum.ADMINISTRADOR)
    elif atual == StatusPedidoEnum.PRONTO and novo == StatusPedidoEnum.ENTREGUE:
        permitido = user.perfil in (PerfilEnum.ATENDENTE, PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR)
    if not permitido:
        raise HTTPException(status_code=409, detail=f"Transição {atual.value} -> {novo.value} não permitida para este perfil.")
    if devolver_estoque:
        for item in pedido.itens:
            db.query(EstoqueUnidade).filter_by(unidade_id=pedido.unidade_id, produto_id=item.produto_id).update({EstoqueUnidade.quantidade: EstoqueUnidade.quantidade + item.quantidade}, synchronize_session=False)
    pedido.status = novo
    registrar_log(db, user, f"ALTERAR_STATUS_{novo.value}", pedido.id, f"{atual.value} -> {novo.value}")
    db.commit()
    db.refresh(pedido)
    return pedido


@app.post("/pagamentos/processar", responses=RESPOSTAS_COMUNS, tags=["Pagamentos"])
def processar_pagamento(payload: PagamentoProcessar, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    pedido = db.query(Pedido).filter(Pedido.id == payload.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if not usuario_pode_acessar_pedido(user, pedido):
        raise HTTPException(status_code=403, detail="Acesso não autorizado ao pedido.")
    if payload.idempotency_key:
        existente = db.query(Pagamento).filter(Pagamento.idempotency_key == payload.idempotency_key).first()
        if existente:
            mesma_requisicao = existente.pedido_id == pedido.id and existente.metodo == payload.metodo_pagamento and Decimal(existente.valor).quantize(Decimal("0.01")) == Decimal(payload.valor).quantize(Decimal("0.01"))
            if not mesma_requisicao:
                raise HTTPException(status_code=409, detail="Chave de idempotência já usada com outros dados.")
            return {"mensagem": "Transação já processada.", "pedidoId": pedido.id, "status": pedido.status, "transacaoId": existente.transacao_id}
    if pedido.status not in (StatusPedidoEnum.AGUARDANDO_PAGAMENTO, StatusPedidoEnum.PAGAMENTO_RECUSADO):
        raise HTTPException(status_code=409, detail="Este pedido não está aguardando pagamento.")
    if Decimal(payload.valor).quantize(Decimal("0.01")) != Decimal(pedido.valor_total).quantize(Decimal("0.01")):
        raise HTTPException(status_code=409, detail="O valor informado não corresponde ao total do pedido.")
    if payload.metodo_pagamento == MetodoPagamentoEnum.DINHEIRO and user.perfil == PerfilEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Pagamento em dinheiro deve ser registrado pela equipe da unidade.")
    aprovado, transacao_id = not payload.simular_recusa, str(uuid.uuid4())
    if aprovado:
        for item in pedido.itens:
            alteradas = db.query(EstoqueUnidade).filter(EstoqueUnidade.unidade_id == pedido.unidade_id, EstoqueUnidade.produto_id == item.produto_id, EstoqueUnidade.quantidade >= item.quantidade).update({EstoqueUnidade.quantidade: EstoqueUnidade.quantidade - item.quantidade}, synchronize_session=False)
            if alteradas != 1:
                db.rollback()
                raise HTTPException(status_code=409, detail=f"Estoque insuficiente para o produto ID {item.produto_id}.")
        pedido.status, status_pagamento = StatusPedidoEnum.EM_PREPARACAO, "APROVADO"
        cliente = db.query(Usuario).filter(Usuario.id == pedido.usuario_id).first()
        if cliente and cliente.aceitou_fidelidade:
            pontos = int(Decimal(pedido.valor_total) // Decimal("10.00"))
            cliente.pontos_fidelidade += pontos
            db.add(HistoricoFidelidade(usuario_id=cliente.id, pedido_id=pedido.id, tipo="CREDITO", pontos=pontos, descricao="Crédito por pagamento aprovado"))
    else:
        pedido.status, status_pagamento = StatusPedidoEnum.PAGAMENTO_RECUSADO, "RECUSADO"
    db.add(Pagamento(pedido_id=pedido.id, metodo=payload.metodo_pagamento, status_transacao=status_pagamento, valor=pedido.valor_total, transacao_id=transacao_id, idempotency_key=payload.idempotency_key))
    registrar_log(db, user, f"PROCESSAR_PAGAMENTO_{status_pagamento}", pedido.id, f"Método {payload.metodo_pagamento.value}; valor {pedido.valor_total}")
    db.commit()
    if not aprovado:
        raise HTTPException(status_code=409, detail="Pagamento recusado pela operadora simulada.")
    return {"mensagem": "Pagamento aprovado com sucesso.", "pedidoId": pedido.id, "status": pedido.status, "transacaoId": transacao_id}


@app.patch("/fidelidade/consentimento", responses=RESPOSTAS_COMUNS, tags=["Fidelidade"])
def atualizar_consentimento(payload: ConsentimentoUpdate, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    if user.perfil != PerfilEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Consentimento de fidelidade disponível apenas para clientes.")
    user.aceitou_fidelidade = payload.aceitar
    user.data_consentimento = datetime.now(timezone.utc) if payload.aceitar else None
    registrar_log(db, user, "ATUALIZAR_CONSENTIMENTO_FIDELIDADE", detalhes=f"aceitar={payload.aceitar}")
    db.commit()
    return {"aceitouFidelidade": user.aceitou_fidelidade, "dataConsentimento": user.data_consentimento}


@app.get("/fidelidade/saldo", responses=RESPOSTAS_COMUNS, tags=["Fidelidade"])
def consultar_saldo(user: Usuario = Depends(get_current_user)):
    if user.perfil != PerfilEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Saldo disponível apenas para clientes.")
    return {"pontos": user.pontos_fidelidade, "consentimentoAtivo": user.aceitou_fidelidade}


@app.post("/fidelidade/resgates", status_code=201, responses=RESPOSTAS_COMUNS, tags=["Fidelidade"])
def resgatar_pontos(payload: ResgatePontos, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    if user.perfil != PerfilEnum.CLIENTE or not user.aceitou_fidelidade:
        raise HTTPException(status_code=403, detail="É necessário ser cliente e possuir consentimento ativo.")
    if user.pontos_fidelidade < payload.pontos:
        raise HTTPException(status_code=409, detail="Saldo de pontos insuficiente.")
    user.pontos_fidelidade -= payload.pontos
    historico = HistoricoFidelidade(usuario_id=user.id, tipo="RESGATE", pontos=-payload.pontos, descricao=payload.descricao)
    db.add(historico)
    registrar_log(db, user, "RESGATAR_PONTOS", detalhes=f"Pontos {payload.pontos}")
    db.commit()
    db.refresh(historico)
    return {"resgateId": historico.id, "saldoAtual": user.pontos_fidelidade}


@app.get("/fidelidade/historico", responses=RESPOSTAS_COMUNS, tags=["Fidelidade"])
def historico_fidelidade(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    if user.perfil != PerfilEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Histórico disponível apenas para clientes.")
    rows = db.query(HistoricoFidelidade).filter(HistoricoFidelidade.usuario_id == user.id).order_by(HistoricoFidelidade.criado_em.desc()).offset((page - 1) * limit).limit(limit).all()
    return [{"id": row.id, "tipo": row.tipo, "pontos": row.pontos, "descricao": row.descricao, "criadoEm": row.criado_em} for row in rows]


@app.get("/promocoes/regras", tags=["Promoções"])
def regras_promocoes():
    return {"situacao": "REGRA_CONCEITUAL", "regras": ["Campanhas devem ter período de vigência, unidades participantes e produtos elegíveis.", "O desconto deve ser calculado pelo servidor e registrado no pedido.", "Uma campanha expirada ou incompatível deve retornar 409."]}


@app.get("/admin/logs", response_model=list[LogAuditoriaResponse], responses=RESPOSTAS_COMUNS, tags=["Administração"])
def consultar_logs(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _user: Usuario = Depends(verificar_perfil([PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR]))):
    return db.query(LogAuditoria).order_by(LogAuditoria.criado_em.desc()).offset((page - 1) * limit).limit(limit).all()


@app.get("/admin/relatorios/vendas", responses=RESPOSTAS_COMUNS, tags=["Administração"])
def relatorio_vendas(unidade_id: Optional[int] = Query(None, alias="unidadeId"), db: Session = Depends(get_db), _user: Usuario = Depends(verificar_perfil([PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR]))):
    status_de_venda = (StatusPedidoEnum.EM_PREPARACAO, StatusPedidoEnum.PRONTO, StatusPedidoEnum.ENTREGUE)
    query = db.query(Pedido.unidade_id, func.count(Pedido.id).label("quantidade_pedidos"), func.coalesce(func.sum(Pedido.valor_total), 0).label("valor_total")).filter(Pedido.status.in_(status_de_venda))
    if unidade_id is not None:
        query = query.filter(Pedido.unidade_id == unidade_id)
    return [{"unidadeId": row.unidade_id, "quantidadePedidos": row.quantidade_pedidos, "valorTotal": row.valor_total} for row in query.group_by(Pedido.unidade_id).all()]


@app.get("/admin/relatorios/produtos", responses=RESPOSTAS_COMUNS, tags=["Administração"])
def relatorio_produtos(unidade_id: Optional[int] = Query(None, alias="unidadeId"), db: Session = Depends(get_db), _user: Usuario = Depends(verificar_perfil([PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR]))):
    status_de_venda = (StatusPedidoEnum.EM_PREPARACAO, StatusPedidoEnum.PRONTO, StatusPedidoEnum.ENTREGUE)
    query = db.query(Produto.id, Produto.nome, func.sum(ItemPedido.quantidade).label("quantidade")).join(ItemPedido, ItemPedido.produto_id == Produto.id).join(Pedido, Pedido.id == ItemPedido.pedido_id).filter(Pedido.status.in_(status_de_venda))
    if unidade_id is not None:
        query = query.filter(Pedido.unidade_id == unidade_id)
    return [{"produtoId": row.id, "nome": row.nome, "quantidade": row.quantidade} for row in query.group_by(Produto.id, Produto.nome).order_by(func.sum(ItemPedido.quantidade).desc()).all()]
