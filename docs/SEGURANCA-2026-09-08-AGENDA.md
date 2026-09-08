# Revisao de seguranca — Agenda — 08/09/2026

## Escopo e ambiente

Revisao seguindo AGENTS.md e AGENT_SECURITY.md dos commits `de34e14`
(tools da Secretaria IA), `800a142` (frontend) e `997e2bc` (roadmap).
HEAD observado: `997e2bc`. Os commits foram lidos pelo Git; os testes executaram
a arvore local, que JA continha alteracoes nao commitadas da confirmacao/lembretes
(fatia 8.6b). Essas alteracoes foram preservadas, nao atribuídas a esta revisao.
Nao e um certificado de seguranca nem auditoria exaustiva de toda a plataforma.

Stack confirmado: FastAPI/SQLAlchemy, JWT, React/Vite, Celery/Redis,
Evolution/WhatsApp e provedores LLM. Entradas relevantes: `/agenda/*`, webhook
WhatsApp, execucao de workflows e argumentos de ferramentas devolvidos pelo LLM.
Dados sensiveis: telefone, nome, notas, compromissos e credenciais dos provedores.

Somente testes locais, SQLite sintetico e mocks de LLM/Evolution. Nenhuma
mensagem real, migration em producao, alteracao na VPS, push ou commit.
Producao continua usando Supabase para o banco do app; nao foi acessada.

## Achados e correcoes implementadas localmente

### Alta — cliente acessava compromissos de outro cliente da mesma empresa

- Origem: `de34e14`, agenda_tools e conversation_service. O executor recebia
  apenas company_id; consultar listava todos e alterar/cancelar aceitavam ID alheio.
- Pre-condicao: agenda ativa e o modelo selecionar a ferramenta induzida pela conversa.
- Evidencia dinamica antes da correcao: com dados ficticios em SQLite, consulta
  retornou o telefone de outro cliente e cancelamento do ID dele retornou sucesso.
- Impacto: vazamento de dados e modificacao/cancelamento nao autorizado.
- Correcao: `execute_customer_agenda_tool` recebe telefone do contexto, filtra
  consulta ANTES de count/paginacao, minimiza campos e valida empresa+telefone+ID
  para mutacoes. Telefone proposto pelo LLM nao controla a criacao. Identidade
  ausente e agenda desativada falham fechadas. Mudanca arbitraria de status via
  LLM e rejeitada; deve usar confirmacao ou operador.
- A alteracao local de NodeContext tambem tinha o executor sem escopo: corrigida
  para guardar o remetente inicial e usar o executor restrito. Em dry_run ou sem
  telefone as tools de agenda nao sao habilitadas.
- Regressao: `tests/test_agenda_security.py`, incluindo pipeline direto e workflow
  real com LLM simulado, clientes e empresas diferentes e tentativa de cancelar.

### Media — customer_id manual podia pertencer a outra empresa

- Local: `app/services/agenda.py`, add_appointment (implementacao anterior aos
  tres commits, revisada como dependencia do modulo).
- Correcao: lookup Customer.id + company_id antes de gravar; ID inexistente ou
  de outro tenant gera AgendaError not_found. API existente traduz para 404.
- Validacao: teste sintetico de ID de outra empresa, sem gravacao indevida.

### Media — reativacao ignorava conflito quando horario permanecia igual

- Local: `app/services/agenda.py`, update_appointment.
- Evidencia: validacao era chamada somente quando mudava data/horario.
- Correcao: transicao de status inativo para ativo tambem valida disponibilidade.
- Validacao: reativar compromisso cancelado com outro no mesmo horario e rejeitado.
- Isso NAO resolve a corrida entre duas transacoes concorrentes (pendente abaixo).

### Media — detalhes de excecoes enviados ao provedor LLM

- Origem: `de34e14`, `app/services/llm.py`, generate_reply_with_tools.
- Evidencia: str(exc) era usado como resultado da tool; excecoes SQL podem conter
  parametros, notas ou detalhes internos. Nao foi observado vazamento real de segredo.
- Correcao: erro generico no resultado da ferramenta. Teste com excecao contendo
  marcadores sinteticos comprova que esses marcadores nao chegam ao provedor simulado.
- Adicional: limite total de 16 chamadas por resposta; lote que excede o limite e
  rejeitado antes dos efeitos daquele lote. Rodadas anteriores nao sao revertidas.

### Media — CI podia publicar imagem mesmo com testes falhando

- Local: `.github/workflows/ci.yml`, preexistente aos tres commits.
- Evidencia: pytest e lint usavam `|| echo`, convertendo falha em sucesso.
- Correcao: falhas de pytest/lint propagam; pytest limitado a tests/; npm test
  adicionado. Contratos textuais testados localmente. O workflow GitHub NAO rodou.
- Mypy/TypeScript ainda sao verificacoes opcionais no CI; nao declarar type-check aprovado.

### Preventivo — contexto Docker podia incluir bancos locais e outros .env

- `.dockerignore` excluia .env, mas nao todos .env.* ou bancos SQLite.
- Adicionadas exclusoes de variantes .env, bancos/journals comuns, PEM e KEY.
- Teste valida presenca das regras. Nao houve build/inspecao de imagem Docker;
  nao ha evidencia de que dados reais tenham sido publicados em imagens anteriores.
- Consulta de arquivos rastreados nao retornou .env, PEM, KEY ou bancos SQLite.
  Isso nao substitui scanner de segredos em todo o historico Git.

### Funcional — lista da agenda ficava vazia

- Origem: `800a142`, frontend/src/pages/Agenda.jsx.
- API retorna `{total, items}`; frontend tratava a resposta como array.
- Correcao: consumir list.items. Build/lint aprovados; teste visual nao executado.
- A pagina ainda carrega no maximo 200 itens; paginacao completa permanece pendente.

## Testes e scanners executados

- Preparacao do commit: exportacao do indice Git para diretorio temporario, sem
  os arquivos pendentes da 8.6b. Nessa arvore isolada, 264 testes passaram
  (11 avisos Pydantic). O commit inclui a integracao segura de tools no
  NodeContext, necessaria para proteger e testar tambem o caminho dos workflows;
  nao inclui migration, servicos nem tarefas de confirmacao/lembretes.

- Baseline antes das correcoes: 275 testes backend passaram.
- Suite final: 294 testes backend passaram, 11 avisos de depreciacao Pydantic.
- Contratos CI/Docker adicionados depois: mais 2 testes passaram separadamente.
- Frontend: 11 testes passaram; lint sem erros, com avisos; build passou com
  aviso de bundle acima de 500 kB. Sem validacao visual no navegador.
- `git diff --check`: sem erros (Git avisou conversao LF/CRLF).
- `npm audit --omit=dev` e `npm audit`: zero vulnerabilidades reportadas.
- `pip-audit -r requirements.txt`: 75 registros de vulnerabilidade em 7 pacotes,
  incluindo registros repetidos: python-dotenv, python-multipart, cryptography,
  pypdf, pyasn1, starlette e ecdsa. Resultado da resolucao de requirements,
  NAO inventario do container VPS. Nao equivalem a 75 exploracoes comprovadas.
  **RESOLVIDO em 08/09/2026** (fatia dedicada): 75 -> 0. Upgrades
  (fastapi 0.141.1, starlette 1.6.0 pinned, python-dotenv 1.2.3,
  python-multipart 0.0.32, cryptography 50.0.1, pypdf 6.18.0, slowapi 0.1.10)
  e troca de `python-jose` por `PyJWT` (remove `ecdsa`/`pyasn1`; JWT segue HS256).
  Regressao: 298 passed. Ver PROGRESSO.md.
- `bandit -r app`: 10 alertas (9 baixos, 1 medio), sem erros de analise.
  O medio e exec no node code, cuja execucao por run_node esta bloqueada.
  Tres alertas de senha sao os literais de tipo JWT access/refresh (falsos positivos).
  Outros seis sinalizam except/pass, incluindo integracoes e fallback das tools;
  observabilidade/tratamento desses erros continua pendente.
- Scanners instalados em venv temporario fora do repositorio; requirements do
  projeto nao foram alterados. Consultas de auditoria enviam metadados de pacotes,
  nao codigo, banco ou credenciais.

## Pendentes — nao tratar como concluido

1. ~~Atualizar dependencias vulneraveis~~ **CONCLUIDO 08/09/2026** (75->0; ver bloco de scanners acima e PROGRESSO.md).
   Validacao manual na VPS apos deploy continua pendente (login/auth e upload de PDF).
2. **Prioridade alta:** impedir dupla reserva concorrente com garantia transacional
   no Postgres/Supabase; leitura antes do INSERT nao oferece essa garantia.
   Requer desenho/migration com architect e teste concorrente em banco descartavel.
3. **Prioridade alta:** confirmacao server-side de remarcar/cancelar; instrucao no
   prompt nao comprova consentimento. Criacao provisoria/confirmacao da 8.6b ja esta
   no trabalho local, mas nao nos tres commits analisados, e nao resolve todas acoes.
4. Definir permissoes granulares dos operadores. CRUD autenticado da empresa e
   comportamento documentado; nao foi mudado unilateralmente para manager-only.
5. Limites de tamanho/frequencia e orcamento por cliente/empresa. Limite 16 tools
   por resposta nao impede flood de mensagens, reservas ou consumo acumulado.
6. Auditar isolamentos de conversation_id em historico/persistencia dos nodes;
   esta revisao restringe tools de agenda, nao certifica todos os caminhos dos nodes.
7. Validar em ambiente descartavel: concorrencia Postgres, migrations completas,
   Redis/Celery reais, imagens Docker, nginx/TLS, recuperacao de falhas e backups.
8. Scanner dedicado de segredos/historico, revisao de sessoes/revogacao, upload e
   todas as integracoes continuam fora da comprovacao dinamica desta entrega.

Conclusao: correcoes locais verificadas, revisao de seguranca PARCIAL do sistema.
Nao recomendar publicacao aberta antes de tratar as prioridades altas.
