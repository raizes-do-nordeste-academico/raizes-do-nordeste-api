# Plano de testes da API

Os testes automatizados e a coleção Postman cobrem o fluxo escolhido: pedido, pagamento mock e atualização de status. A coleção deve ser executada na ordem das pastas indicada no README.

| ID | Tipo | Endpoint | Pré-condição | Entrada principal | Resultado esperado | Evidência |
|---|---|---|---|---|---|---|
| T01 | Positivo | GET /health | API ativa | - | 200 e status ok | Postman T01 e pytest |
| T02 | Positivo | POST /auth/registro | E-mail novo | nome, e-mail e senha | 201 e usuário criado | Postman T02 e pytest |
| T03 | Positivo | POST /auth/login | Usuário cadastrado | username e password | 200 e access_token | Postman T03 e pytest |
| T04 | Negativo | GET /pedidos | Sem token | - | 401 e erro padronizado | Postman T04 e pytest |
| T05 | Negativo | POST /pedidos | Cliente autenticado | canalPedido ausente | 422 e detalhes de validação | Postman T05 e pytest |
| T06 | Negativo | POST /pedidos | Cliente autenticado | quantidade zero | 422 | Postman T06 e pytest |
| T07 | Negativo | GET /admin/logs | Token de cliente | - | 403 | Postman T07 e pytest de autorização equivalente |
| T08 | Negativo | POST /pedidos | Cliente autenticado | produto inexistente | 404 | Postman T08 e pytest |
| T09 | Negativo | POST /pedidos | Cliente autenticado | quantidade acima do saldo | 409 | Postman T09 e pytest |
| T10 | Positivo | POST /pedidos | Estoque disponível | canalPedido TOTEM e itens | 201 e pedido aguardando pagamento | Postman T10 e pytest |
| T11 | Positivo | GET /pedidos | Pedido TOTEM existente | canalPedido, status, page e limit | 200 e pedido filtrado | Postman T11 e pytest |
| T12 | Negativo | POST /pagamentos/processar | Pedido aguardando pagamento | simularRecusa true | 409 e status PAGAMENTO_RECUSADO | Postman T12 e pytest |
| T13 | Positivo | POST /pagamentos/processar | Pedido recusado pode ser tentado novamente | valor correto e chave única | 200 e status EM_PREPARACAO | Postman T13 e pytest |
| T14 | Positivo | POST /pagamentos/processar | Pagamento já aprovado | mesma idempotencyKey | 200 sem nova baixa | Postman T14 e pytest |
| T15 | Positivo | GET /fidelidade/saldo | Consentimento ativo e pagamento aprovado | - | 200 e saldo atualizado | Postman T15 e pytest |
| T16 | Positivo | GET /fidelidade/historico | Cliente autenticado | page e limit | 200 e crédito registrado | Postman T16 e pytest |

## Coberturas adicionais automatizadas

- acesso horizontal entre clientes retorna 403;
- pagamento em dinheiro por cliente retorna 403;
- cozinha altera EM_PREPARACAO para PRONTO;
- atendente altera PRONTO para ENTREGUE;
- auditoria registra a ação sensível;
- administrador cria produto e movimenta estoque;
- saída maior do que o saldo retorna 409.

## Resultado local

O comando `python -m pytest -q` concluiu nove grupos de teste sem falhas. O relatório reproduzível está em `docs/relatorio-testes.xml`.
