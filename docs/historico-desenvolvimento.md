# Histórico de elaboração

## Identificação

- Acadêmico: RHAMSES GONÇALVES MAGALHAES
- RU: 4688632
- Curso: GRAD - CST ANÁLISE E DESENVOLVIMENTO DE SISTEMAS
- Projeto: API Raízes do Nordeste — Trilha Back-end

## Natureza deste registro

Este documento é um registro retrospectivo da elaboração. O trabalho começou em arquivos locais e em uma base SQLite antes da criação do repositório público. Portanto, os marcos abaixo descrevem a ordem lógica e as decisões verificáveis nos artefatos, sem atribuir datas fictícias e sem alterar o histórico do Git.

## Marcos da elaboração

### 1. Exploração inicial do domínio

Os primeiros arquivos locais foram usados para compreender o problema e experimentar entidades e operações relacionadas a usuários, unidades, cardápio e pedidos. A base SQLite permitiu verificar a persistência básica e as relações entre os dados.

### 2. Conferência com o roteiro oficial

A solução foi comparada com o roteiro da atividade. Essa revisão evidenciou itens que precisavam de maior detalhamento: canal obrigatório do pedido, controle de estoque, consentimento para fidelidade, integração simulada de pagamento, auditoria, respostas de erro padronizadas, diagramas e evidências de teste.

### 3. Reorganização arquitetural

O código foi organizado nas áreas `domain`, `application`, `infrastructure` e `api`. Essa separação tornou explícitas as regras de negócio, os serviços, a persistência SQLAlchemy e os contratos HTTP, mantendo `main.py` apenas como ponto de entrada da aplicação.

### 4. Implementação dos fluxos principais

Foram completados cadastro e autenticação JWT, perfis de acesso, unidades, produtos, cardápio por unidade, movimentações de estoque, pedidos multicanal, pagamento mock idempotente, transições de status, cancelamento, fidelidade, relatórios e logs de auditoria.

### 5. Validação e tratamento de falhas

Os testes passaram a cobrir tanto o caminho de sucesso quanto respostas 401, 403, 404, 409 e 422. Também foram verificados produto inexistente, estoque insuficiente, pagamento recusado, repetição da chave de idempotência, autorização por perfil e movimentação de estoque.

### 6. Documentação e publicação

Foram preparados diagramas, plano de testes, relatório JUnit, coleção Postman, instruções de execução e evidências visuais. Depois dessa consolidação, o conteúdo foi publicado na organização acadêmica. Os primeiros commits foram separados por finalidade para tornar cada conjunto de alterações compreensível, mas compartilham a data em que o material local foi levado ao GitHub.

## Decisões e limitações assumidas

- SQLite e criação automática do esquema simplificam a avaliação local; uma solução de produção exigiria PostgreSQL e migrations.
- O pagamento é simulado porque o sistema deve delegar a operação financeira a um serviço especializado.
- Segredos e senhas não são versionados; `.env.example` documenta apenas os nomes das configurações.
- O repositório não contém `.env`, bancos locais, ambientes virtuais ou caches.
- Promoções estão documentadas conceitualmente, mas a aplicação comercial de descontos depende de regras futuras da rede.

## Evidências reproduzíveis

- Nove grupos automatizados cobrem treze cenários identificados como T01 a T13.
- A coleção Postman contém dezesseis requisições organizadas em cinco pastas.
- O relatório JUnit está em `docs/relatorio-testes.xml`.
- Os diagramas e suas fontes estão em `docs/` e `docs/figuras/`.
- A documentação interativa fica disponível em `http://127.0.0.1:8000/docs` durante a execução local.

## Transparência sobre apoio de inteligência artificial

Houve apoio de inteligência artificial na análise dos arquivos, identificação de lacunas, reorganização do código, revisão de testes, diagramas e redação. O relatório acadêmico contém a declaração detalhada exigida pelo roteiro. O responsável acadêmico deve compreender, revisar e validar o projeto antes da entrega e da apresentação.
