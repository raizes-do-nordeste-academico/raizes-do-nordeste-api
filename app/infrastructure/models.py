from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.domain.enums import CanalPedidoEnum, MetodoPagamentoEnum, PerfilEnum, StatusPedidoEnum, TipoMovimentoEnum
from app.infrastructure.database import Base


def agora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    perfil = Column(SQLEnum(PerfilEnum), default=PerfilEnum.CLIENTE, nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=True)
    aceitou_fidelidade = Column(Boolean, default=False, nullable=False)
    data_consentimento = Column(DateTime, nullable=True)
    pontos_fidelidade = Column(Integer, default=0, nullable=False)
    criado_em = Column(DateTime, default=agora, nullable=False)


class Unidade(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    tipo_unidade = Column(String, nullable=False, default="COZINHA_COMPLETA")
    endereco = Column(String, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)


class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    preco = Column(Numeric(10, 2), nullable=False)
    categoria = Column(String, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)


class EstoqueUnidade(Base):
    __tablename__ = "estoque_unidades"
    __table_args__ = (
        UniqueConstraint("unidade_id", "produto_id", name="uq_unidade_produto"),
        CheckConstraint("quantidade >= 0", name="chk_quantidade_positiva"),
    )
    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, default=0, nullable=False)


class MovimentoEstoque(Base):
    __tablename__ = "movimentos_estoque"
    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(SQLEnum(TipoMovimentoEnum), nullable=False)
    quantidade = Column(Integer, nullable=False)
    motivo = Column(String, nullable=False)
    criado_em = Column(DateTime, default=agora, nullable=False)


class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    canal_pedido = Column(SQLEnum(CanalPedidoEnum), nullable=False)
    status = Column(SQLEnum(StatusPedidoEnum), default=StatusPedidoEnum.AGUARDANDO_PAGAMENTO, nullable=False)
    valor_total = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    criado_em = Column(DateTime, default=agora, nullable=False)
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")


class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    pedido = relationship("Pedido", back_populates="itens")


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    metodo = Column(SQLEnum(MetodoPagamentoEnum), nullable=False)
    status_transacao = Column(String, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    transacao_id = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)
    processado_em = Column(DateTime, default=agora, nullable=False)


class HistoricoFidelidade(Base):
    __tablename__ = "historico_fidelidade"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    tipo = Column(String, nullable=False)
    pontos = Column(Integer, nullable=False)
    descricao = Column(String, nullable=False)
    criado_em = Column(DateTime, default=agora, nullable=False)


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    perfil = Column(SQLEnum(PerfilEnum), nullable=False)
    acao = Column(String, nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    detalhes = Column(String, nullable=True)
    criado_em = Column(DateTime, default=agora, nullable=False)
