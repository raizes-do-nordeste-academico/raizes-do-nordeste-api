# API Raízes do Nordeste

Projeto acadêmico de Back-end para uma rede fictícia de lanchonetes. A API cobre unidades, cardápio, pedidos multicanal, pagamento mock, estoque, fidelidade, relatórios e auditoria.

## Requisitos

- Python 3.11 ou superior;
- pip e ambiente virtual;
- SQLite 3 para a execução local;
- dependências listadas em `requirements.txt`.

## Arquitetura

O projeto separa responsabilidades em quatro áreas:

- `app/domain`: enumerações e conceitos do domínio;
- `app/application`: serviços e casos de uso compartilhados;
- `app/infrastructure`: banco, ORM e modelos persistentes;
- `app/api`: contratos Pydantic, endpoints e documentação OpenAPI.

O arquivo `main.py` é apenas o ponto de entrada compatível com `uvicorn main:app`.

## Configuração

1. Crie e ative um ambiente virtual.
2. Instale as dependências:

```bash
pip install -r requirements-dev.txt
```

3. Copie `.env.example` para `.env`.
4. Defina `SECRET_KEY` com pelo menos 32 caracteres.
5. Para habilitar usuários demonstrativos, defina `SEED_DEMO_USERS=true` e preencha as senhas do administrador e da equipe.

## Banco, criação do esquema e seed

O protótipo usa SQLite e cria o esquema automaticamente na primeira inicialização por meio do SQLAlchemy. Não há migrations Alembic nesta versão acadêmica; uma implantação evolutiva deve adicioná-las antes de alterar um banco persistente.

O seed automático cria:

- unidade `Matriz Recife`;
- produtos `Baião de Dois` e `Carne de Sol`;
- 30 unidades de estoque para cada produto.

Usuários demonstrativos só são criados quando `SEED_DEMO_USERS=true`. Os e-mails podem ser configurados no `.env`; nenhuma senha é mantida no código.

## Execução

```bash
python -m uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger/OpenAPI: `http://127.0.0.1:8000/docs`
- Especificação JSON: `http://127.0.0.1:8000/openapi.json`

## Contratos importantes

- O pedido exige `canalPedido`: `APP`, `TOTEM`, `BALCAO`, `PICKUP` ou `WEB`.
- A listagem aceita `canalPedido`, `status`, `unidadeId`, `page` e `limit`.
- O pagamento é simulado e aceita `simularRecusa`.
- A chave `idempotencyKey` impede processamento duplicado.
- Erros usam sempre `error`, `message`, `details`, `timestamp`, `path` e `requestId`.

## Coleção Postman

Importe `postman/Raizes_do_Nordeste.postman_collection.json` e execute as pastas na ordem apresentada:

1. Preparação e autenticação;
2. Autorização e validação;
3. Pedidos;
4. Pagamento mock;
5. Fidelidade e auditoria.

A coleção gera um e-mail aleatório, salva o JWT e o identificador do pedido nas variáveis da coleção. Ela contém 16 requisições T01 a T16, incluindo 401, 403, 404, 409 e 422.

## Testes automatizados

```bash
python -m pytest -q
```

Os nove grupos automatizados cobrem treze cenários identificados como T01 a T13: autenticação, ausência de token, validações, canal do pedido, produto inexistente, estoque insuficiente, pagamento aprovado/recusado, idempotência, fidelidade, autorização, status, auditoria e movimentação de estoque.

## Funcionalidades implementadas

- cadastro, login JWT e perfis;
- unidades, produtos e cardápio por unidade;
- entrada, saída e consulta de estoque;
- pedidos com rastreabilidade por canal e paginação;
- pagamento mock, recusa e idempotência;
- máquina de estados, cancelamento e devolução de estoque;
- consentimento, crédito, saldo, histórico e resgate de pontos;
- relatórios e logs de auditoria.

Promoções estão representadas conceitualmente em `GET /promocoes/regras`. A aplicação efetiva de descontos permanece proposta porque depende da política comercial da rede.

## Estrutura

```text
.
|-- app/
|   |-- api/
|   |-- application/
|   |-- core/
|   |-- domain/
|   `-- infrastructure/
|-- docs/
|   |-- figuras/
|   |-- *.mmd
|   |-- plano-testes.md
|   `-- relatorio-testes.xml
|-- postman/
|   `-- Raizes_do_Nordeste.postman_collection.json
|-- tests/
|   `-- test_api.py
|-- .env.example
|-- .gitignore
|-- main.py
|-- requirements-dev.txt
`-- requirements.txt
```

## Evidências e publicação

- Repositório público: `[INSERIR LINK APÓS A PUBLICAÇÃO]`;
- Swagger local: `http://127.0.0.1:8000/docs`;
- coleção Postman: `postman/Raizes_do_Nordeste.postman_collection.json`;
- relatório JUnit: `docs/relatorio-testes.xml`.

O repositório ainda não foi publicado. Antes da entrega, confirme que o link público abre em uma janela anônima.

## Limitações

SQLite, criação automática do esquema e gateway simulado foram escolhidos para a avaliação local. Produção exigiria PostgreSQL, migrations, gestão de segredos, observabilidade, testes de carga e integração financeira homologada.
