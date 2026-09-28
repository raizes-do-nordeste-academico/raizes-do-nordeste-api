import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DB = PROJECT_ROOT / "test_raizes.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["SECRET_KEY"] = "chave-de-testes-com-mais-de-trinta-e-dois-caracteres"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SEED_DEMO_USERS"] = "true"
os.environ["DEMO_ADMIN_PASSWORD"] = "AdminTeste123!"
os.environ["DEMO_STAFF_PASSWORD"] = "EquipeTeste123!"

import main


client = TestClient(main.app)


def login(email: str, senha: str) -> dict:
    response = client.post("/auth/login", data={"username": email, "password": senha})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def registrar_cliente(sufixo: str, fidelidade: bool = False) -> dict:
    email = f"cliente.{sufixo}@example.com"
    response = client.post("/auth/registro", json={"nome": f"Cliente {sufixo}", "email": email, "senha": "Cliente123!", "aceitouFidelidade": fidelidade})
    assert response.status_code == 201, response.text
    return login(email, "Cliente123!")


def criar_pedido(headers: dict, quantidade: int = 1, canal: str = "APP") -> dict:
    response = client.post("/pedidos", headers=headers, json={"unidadeId": 1, "canalPedido": canal, "itens": [{"produtoId": 1, "quantidade": quantidade}]})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(scope="module", autouse=True)
def cleanup_database():
    yield
    main.engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_t01_t03_rotas_publicas_login_e_sem_token():
    assert client.get("/health").json() == {"status": "ok"}
    headers = registrar_cliente("auth")
    assert headers["Authorization"].startswith("Bearer ")
    sem_token = client.get("/pedidos")
    assert sem_token.status_code == 401
    assert sem_token.json()["error"] == "HTTP_ERROR"


def test_t04_t05_validacao_de_campo_e_formato():
    headers = registrar_cliente("validacao")
    sem_canal = client.post("/pedidos", headers=headers, json={"unidadeId": 1, "itens": [{"produtoId": 1, "quantidade": 1}]})
    assert sem_canal.status_code == 422
    quantidade_invalida = client.post("/pedidos", headers=headers, json={"unidadeId": 1, "canalPedido": "APP", "itens": [{"produtoId": 1, "quantidade": 0}]})
    assert quantidade_invalida.status_code == 422


def test_t06_pedido_valido_e_filtro_por_canal():
    headers = registrar_cliente("canal")
    pedido = criar_pedido(headers, canal="TOTEM")
    assert pedido["canalPedido"] == "TOTEM"
    filtrados = client.get("/pedidos?canalPedido=TOTEM&status=AGUARDANDO_PAGAMENTO&page=1&limit=10", headers=headers)
    assert filtrados.status_code == 200
    assert [item["id"] for item in filtrados.json()] == [pedido["id"]]


def test_t07_t08_produto_inexistente_e_estoque_insuficiente():
    headers = registrar_cliente("regras")
    inexistente = client.post("/pedidos", headers=headers, json={"unidadeId": 1, "canalPedido": "WEB", "itens": [{"produtoId": 9999, "quantidade": 1}]})
    assert inexistente.status_code == 404
    insuficiente = client.post("/pedidos", headers=headers, json={"unidadeId": 1, "canalPedido": "APP", "itens": [{"produtoId": 1, "quantidade": 9999}]})
    assert insuficiente.status_code == 409


def test_t09_pagamento_aprovado_idempotencia_e_fidelidade():
    headers = registrar_cliente("pagamento", fidelidade=True)
    pedido = criar_pedido(headers, quantidade=2)
    payload = {"pedidoId": pedido["id"], "metodoPagamento": "PIX", "valor": "70.00", "idempotencyKey": "t09-pagamento-unico"}
    aprovado = client.post("/pagamentos/processar", headers=headers, json=payload)
    assert aprovado.status_code == 200
    assert aprovado.json()["status"] == "EM_PREPARACAO"
    repetido = client.post("/pagamentos/processar", headers=headers, json=payload)
    assert repetido.status_code == 200
    assert repetido.json()["mensagem"] == "Transação já processada."
    saldo = client.get("/fidelidade/saldo", headers=headers)
    assert saldo.json()["pontos"] == 7
    historico = client.get("/fidelidade/historico", headers=headers)
    assert historico.status_code == 200
    assert historico.json()[0]["tipo"] == "CREDITO"


def test_t10_pagamento_mock_recusado():
    headers = registrar_cliente("recusa")
    pedido = criar_pedido(headers)
    recusado = client.post("/pagamentos/processar", headers=headers, json={"pedidoId": pedido["id"], "metodoPagamento": "PIX", "valor": "35.00", "simularRecusa": True, "idempotencyKey": "t10-recusa-unica"})
    assert recusado.status_code == 409
    consulta = client.get(f"/pedidos/{pedido['id']}", headers=headers)
    assert consulta.json()["status"] == "PAGAMENTO_RECUSADO"


def test_t11_autorizacao_entre_clientes_e_por_perfil():
    dono = registrar_cliente("dono")
    outro = registrar_cliente("outro")
    pedido = criar_pedido(dono)
    assert client.get(f"/pedidos/{pedido['id']}", headers=outro).status_code == 403
    dinheiro = client.post("/pagamentos/processar", headers=dono, json={"pedidoId": pedido["id"], "metodoPagamento": "DINHEIRO", "valor": "35.00"})
    assert dinheiro.status_code == 403


def test_t12_fluxo_de_status_e_auditoria():
    cliente = registrar_cliente("status")
    pedido = criar_pedido(cliente)
    pago = client.post("/pagamentos/processar", headers=cliente, json={"pedidoId": pedido["id"], "metodoPagamento": "PIX", "valor": "35.00", "idempotencyKey": "t12-status-fluxo"})
    assert pago.status_code == 200
    cozinha = login("cozinha@demo.local", "EquipeTeste123!")
    pronto = client.patch(f"/pedidos/{pedido['id']}/status", headers=cozinha, json={"novoStatus": "PRONTO"})
    assert pronto.status_code == 200
    atendente = login("atendente@demo.local", "EquipeTeste123!")
    entregue = client.patch(f"/pedidos/{pedido['id']}/status", headers=atendente, json={"novoStatus": "ENTREGUE"})
    assert entregue.status_code == 200
    admin = login("admin@demo.local", "AdminTeste123!")
    logs = client.get("/admin/logs?page=1&limit=100", headers=admin)
    assert logs.status_code == 200
    assert any(item["acao"] == "ALTERAR_STATUS_ENTREGUE" for item in logs.json())


def test_t13_produto_e_movimentacao_de_estoque():
    admin = login("admin@demo.local", "AdminTeste123!")
    produto = client.post("/produtos", headers=admin, json={"nome": "Cuscuz Teste", "descricao": "Produto de teste", "preco": "18.50", "categoria": "CAFE"})
    assert produto.status_code == 201
    produto_id = produto.json()["id"]
    entrada = client.post("/estoque/movimentacoes", headers=admin, json={"unidadeId": 1, "produtoId": produto_id, "tipo": "ENTRADA", "quantidade": 10, "motivo": "Carga inicial"})
    assert entrada.status_code == 201
    assert entrada.json()["saldoAtual"] == 10
    saida_invalida = client.post("/estoque/movimentacoes", headers=admin, json={"unidadeId": 1, "produtoId": produto_id, "tipo": "SAIDA", "quantidade": 11, "motivo": "Teste de limite"})
    assert saida_invalida.status_code == 409
