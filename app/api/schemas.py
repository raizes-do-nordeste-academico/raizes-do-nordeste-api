from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import CanalPedidoEnum, MetodoPagamentoEnum, PerfilEnum, StatusPedidoEnum, TipoMovimentoEnum


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UsuarioCreate(ApiModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    aceitou_fidelidade: bool = False


class UsuarioResponse(ApiModel):
    id: int
    nome: str
    email: str
    perfil: PerfilEnum
    unidade_id: Optional[int]
    aceitou_fidelidade: bool
    pontos_fidelidade: int


class Token(BaseModel):
    access_token: str
    token_type: str


class ItemPedidoCreate(ApiModel):
    produto_id: int
    quantidade: int = Field(gt=0)


class PedidoCreate(ApiModel):
    unidade_id: int
    canal_pedido: CanalPedidoEnum
    itens: list[ItemPedidoCreate] = Field(min_length=1)


class PedidoResponse(ApiModel):
    id: int
    usuario_id: int
    unidade_id: int
    canal_pedido: CanalPedidoEnum
    status: StatusPedidoEnum
    valor_total: Decimal
    criado_em: datetime


class PagamentoProcessar(ApiModel):
    pedido_id: int
    metodo_pagamento: MetodoPagamentoEnum
    valor: Decimal = Field(gt=0, decimal_places=2)
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=100)
    simular_recusa: bool = False


class StatusUpdate(ApiModel):
    novo_status: StatusPedidoEnum


class UnidadeCreate(ApiModel):
    nome: str = Field(min_length=2, max_length=120)
    tipo_unidade: str = Field(default="COZINHA_COMPLETA", min_length=2, max_length=80)
    endereco: str = Field(min_length=5, max_length=250)


class UnidadeUpdate(ApiModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=120)
    tipo_unidade: Optional[str] = Field(default=None, min_length=2, max_length=80)
    endereco: Optional[str] = Field(default=None, min_length=5, max_length=250)
    ativo: Optional[bool] = None


class UnidadeResponse(ApiModel):
    id: int
    nome: str
    tipo_unidade: str
    endereco: str
    ativo: bool


class ProdutoCreate(ApiModel):
    nome: str = Field(min_length=2, max_length=120)
    descricao: Optional[str] = Field(default=None, max_length=500)
    preco: Decimal = Field(gt=0, decimal_places=2)
    categoria: str = Field(min_length=2, max_length=80)


class ProdutoUpdate(ApiModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=120)
    descricao: Optional[str] = Field(default=None, max_length=500)
    preco: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    categoria: Optional[str] = Field(default=None, min_length=2, max_length=80)
    ativo: Optional[bool] = None


class ProdutoResponse(ApiModel):
    id: int
    nome: str
    descricao: Optional[str]
    preco: Decimal
    categoria: str
    ativo: bool


class MovimentoEstoqueCreate(ApiModel):
    unidade_id: int
    produto_id: int
    tipo: TipoMovimentoEnum
    quantidade: int = Field(gt=0)
    motivo: str = Field(min_length=3, max_length=250)


class ConsentimentoUpdate(ApiModel):
    aceitar: bool


class ResgatePontos(ApiModel):
    pontos: int = Field(gt=0)
    descricao: str = Field(default="Resgate simples de fidelidade", min_length=3, max_length=200)


class LogAuditoriaResponse(ApiModel):
    id: int
    usuario_id: int
    perfil: PerfilEnum
    acao: str
    pedido_id: Optional[int]
    detalhes: Optional[str]
    criado_em: datetime
