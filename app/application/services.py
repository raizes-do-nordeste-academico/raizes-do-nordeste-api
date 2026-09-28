import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import SEED_DEMO_USERS
from app.core.security import get_password_hash
from app.domain.enums import PerfilEnum
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import EstoqueUnidade, LogAuditoria, Produto, Unidade, Usuario


def usuario_pode_acessar_pedido(user: Usuario, pedido) -> bool:
    if user.perfil == PerfilEnum.CLIENTE:
        return pedido.usuario_id == user.id
    if user.perfil in (PerfilEnum.ATENDENTE, PerfilEnum.COZINHA):
        return user.unidade_id is not None and pedido.unidade_id == user.unidade_id
    return user.perfil in (PerfilEnum.GERENTE, PerfilEnum.ADMINISTRADOR)


def registrar_log(db: Session, user: Usuario, acao: str, pedido_id=None, detalhes=None):
    db.add(LogAuditoria(usuario_id=user.id, perfil=user.perfil, acao=acao, pedido_id=pedido_id, detalhes=detalhes))


def seed_db():
    db = SessionLocal()
    try:
        unidade = db.query(Unidade).first()
        if not unidade:
            unidade = Unidade(nome="Matriz Recife", tipo_unidade="COZINHA_COMPLETA", endereco="Av. Boa Viagem, 100")
            db.add(unidade)
            db.commit()
            db.refresh(unidade)
        if not db.query(Produto).first():
            produtos = [
                Produto(nome="Baião de Dois", descricao="Porção tradicional", preco=Decimal("35.00"), categoria="PRATO_PRINCIPAL"),
                Produto(nome="Carne de Sol", descricao="Acompanha macaxeira", preco=Decimal("45.00"), categoria="PRATO_PRINCIPAL"),
            ]
            db.add_all(produtos)
            db.commit()
            for produto in produtos:
                db.add(EstoqueUnidade(unidade_id=unidade.id, produto_id=produto.id, quantidade=30))
            db.commit()
        if SEED_DEMO_USERS and not db.query(Usuario).first():
            admin_password = os.getenv("DEMO_ADMIN_PASSWORD")
            staff_password = os.getenv("DEMO_STAFF_PASSWORD")
            if not admin_password or not staff_password:
                raise RuntimeError("Defina as senhas dos usuários demonstrativos no arquivo .env.")
            db.add_all([
                Usuario(nome="Admin", email=os.getenv("DEMO_ADMIN_EMAIL", "admin@demo.local"), senha_hash=get_password_hash(admin_password), perfil=PerfilEnum.ADMINISTRADOR),
                Usuario(nome="Gerente", email=os.getenv("DEMO_GERENTE_EMAIL", "gerente@demo.local"), senha_hash=get_password_hash(staff_password), perfil=PerfilEnum.GERENTE, unidade_id=unidade.id),
                Usuario(nome="Atendente", email=os.getenv("DEMO_ATENDENTE_EMAIL", "atendente@demo.local"), senha_hash=get_password_hash(staff_password), perfil=PerfilEnum.ATENDENTE, unidade_id=unidade.id),
                Usuario(nome="Cozinha", email=os.getenv("DEMO_COZINHA_EMAIL", "cozinha@demo.local"), senha_hash=get_password_hash(staff_password), perfil=PerfilEnum.COZINHA, unidade_id=unidade.id),
            ])
            db.commit()
    finally:
        db.close()
