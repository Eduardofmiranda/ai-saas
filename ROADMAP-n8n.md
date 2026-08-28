# 🗺️ Levantamento — O que o n8n tem e o que precisamos

> Análise comparativa do n8n (o "benchmark") vs. nosso projeto.
> Legenda: ✅ temos | 🟡 parcial | ❌ falta | 🔴 crítico para o objetivo

---

## ✅ ANDAMENTO — Sprint 1 (implementado)

- [x] **Memória/contexto no nó `ai`**: novo campo `history` (toggle, ligado por padrão) + `system_prompt` opcional. O histórico agora é carregado do **banco** pela `conversation_id` (via `NodeContext.load_history`) e as respostas do bot são persistidas (`save_bot_message`) — contexto real entre mensagens.
- [x] **Nó `wait_until_message`**: fluxo **pausa** aguardando a próxima mensagem do cliente e **retoma** de onde parou, com o contexto preservado.
- [x] **Modelo `PendingFlow`** + tabela `pending_flows` (criado via `create_all` e migração Alembic `0002_pending_flows.py`).
- [x] **Wiring webhook → motor**: `webhook_router` agora usa `handle_incoming_workflow`, que persiste a mensagem e **roteia pelo motor**: retoma fluxo pausado se houver, senão executa o workflow de mensagem ativo da empresa.
- [x] **Introduza o ciclo de atendimento real**: `trigger_message → ai → whatsapp_send → wait_until_message → ai → ...` agora funciona ponta a ponta no WhatsApp via Evolution.

Este é o coração do produto de atendimento. Testado E2E (mock):
- nº `ai` com memória → histórico do banco carregado ✅
- nº `wait` → status `waiting` + PendingFlow salvo ✅
- nova mensagem → `resume_workflow` retoma no nó salvo e remove a pendência ✅


---

## ✅ ANDAMENTO — Sprint 2 (implementado)

- [x] **Vector store (pgvector)**: `knowledge` + `knowledge_chunks` com embeddings JSON, compativel SQLite (dev) e PostgreSQL (prod).
- [x] **Embeddings**: service `embedding.py` com chunking 500 tokens, OpenAI-compatible API (text-embedding-3-small).
- [x] **Busca semantica**: service `vector_store.py` com cosine similarity, upsert, search_similar.
- [x] **No `ai_rag`**: busca contexto na base de conhecimento e gera resposta via LLM com RAG.
- [x] **Rota `knowledge/`**: CRUD completo (list, get, create, update, delete) + search semantico.
- [x] **Frontend Knowledge**: pagina `/knowledge` com upload de documentos, visualizacao de chunks.
- [x] **Migracao Alembic**: `0003_knowledge.py` (idempotente).
- [x] **Testes**: 34 testes passando (embedding, cosine_similarity, chunk_text).


---

## ✅ ANDAMENTO — Sprint 3 (implementado)

- [x] **No `code`**: executa Python sandboxed com acesso ao `data` do fluxo.
- [x] **No `loop`**: itera sobre uma lista com `max_iterations`.
- [x] **No `aggregate`**: concat, join, count, sum de listas.
- [x] **No `schedule`**: trigger de cron (metadata para Celery beat).
- [x] **No `execute_workflow`**: chama sub-workflow por ID.
- [x] **Error handling por no**: campo `on_error` em todos os nos (stop/continue/fallback_edge).
- [x] **No `http` melhorado**: headers customizaveis, query params.
- [x] **Testes**: 44 testes passando (10 novos para Sprint 3).


---

## PARTE 1 — Mapa geral (n8n vs nós)

| Capacidade | n8n | Nós (hoje) | Nota |
|-----------|-----|------------|------|
| Editor visual drag & drop | ✅ | ✅ | já temos com React Flow |
| Triggers (mensagem, webhook, cron, evento) | ✅ (diversos) | 🟡 só mensagem + webhook | **faltam cron e outros triggers** |
| Nós de serviços (400+ integrações) | ✅ | ❌ só WhatsApp/HTTP/IA | n8n tem 400+, mas para nosso caso o HTTP request cobre a maioria |
| Nó Code (JS/TS) | ✅ | ❌ | **nó `code` para lógica livre** |
| Transformação de dados (map/split/merge) | ✅ | 🟡 nó `set` simples | faltam agregar/splitar |
| Condições | ✅ | ✅ nó `condition` | ok, mas melhorar UI |
| Loops (split in batches, loop over items) | ✅ | ❌ | **nó `loop` essencial** |
| Esperar/Delay | ✅ | ✅ nó `delay` | ok |
| HTTP Request (com auth) | ✅ | ✅ nó `http` | melhorar: headers, query, auth |
| JSON parse & extract | ✅ | 🟡 | melhorar `data path` |
| Sub-workflows / modulares | ✅ | ❌ | **nó `execute_workflow`** |
| AI Agent (LangChain, tool calling) | ✅ | ❌ | **o mais importante pro nosso objetivo** |
| AI Model (multi-provider) | ✅ | ✅ nó `ai` + adapter | já multi-provider |
| RAG / Vector Store (memória da empresa) | ✅ | ❌ | 🔴 **diferencial enorme** |
| Memory / histórico de conversa | ✅ | 🟡 | melhorar no nó `ai` |
| Credentials manager (guardar chaves criptografadas) | ✅ | 🟡 config por empresa | 🔴 nao criptografado |
| Schedule (cron) | ✅ | ❌ | nó `schedule` |
| Error handling (retry, onError, fallback) | ✅ | 🟡 só retry no celery | 🔴 falta no nível do fluxo |
| Pinned data / test isolado | ✅ | 🟡 | auxiliar de dev |
| Logs legíveis de execução | ✅ | 🟡 | melhorar |
| Versionamento/publish de fluxo | ✅ | ❌ | versões + publicar |
| Multi-tenant | (via enterprise) | ✅ | já somos multi-tenant |
| Credenciais por empresa criptografadas | 🟡 | ❌ | 🔴 usar lib `cryptography` |

---

## PARTE 2 — Prioridade e impacto (eixo: nosso objetivo)

Nosso objetivo: **plataforma de automação de atendimento IA/WhatsApp estilo n8n, configurável por empresa (multi-tenant), barata.**

### 🔴 PRIORIDADE ALTA (core do produto, sem isso não diferencia)

| # | Feature | Por quê |
|---|---------|---------|
| 1 | **AI Agent (multi-step, tool calling)** | O `nó ai` hoje é 1 chamada só. O "agente" decide qual passo seguir. É o coração do n8n AI. |
| 2 | **Memória/conversa no nó AI** | hoje o histórico só se for passado. Precisa reter contexto entre mensagens. |
| 3 | **Nó de resposta WhatsApp + loop de atendimento** | atendimento real: recebe msg → resolve → responde → aguarda próxima → fim. |
| 4 | **RAG / base de conhecimento da empresa** | empresa sobe PDFs/textos; IA responde usando a base. **Maior diferencial.** |
| 5 | **Credentials criptografadas por empresa** | segurança: chaves IA/Evolution encriptadas (AES) antes de salvar. |

### 🟡 PRIORIDADE MÉDIA (maturidade)

| # | Feature |
|---|---------|
| 6 | Nó `code` (JS) para lógica custom |
| 7 | Nó `loop` + split/aggregate (processar listas) |
| 8 | Nó `schedule` (cron) |
| 9 | Nó `execute_workflow` (sub-workflow reutilizável) |
| 10 | Error handling por nó (retry, alternate error path) |
| 11 | Melhorar nó `http` (headers, query params, auth type) |

### ⚪ PRIORIDADE BAIXA (polimento)

| # | Feature |
|---|---------|
| 12 | Pinned data (testar nós isoladamente) |
| 13 | Sticky notes / comentários no canvas |
| 14 | Versionamento de fluxo + publicar/publish |
| 15 | Campos de trigger customizáveis no editor |
| 16 | Templates prontos (ex: "atendimento básico", "captura lead", "FAQ") |

---

## PARTE 3 — Novos NÓS sugeridos (para adicionar ao registry)

Com base no benchmark, os nós que fazem mais sentido para nosso produto:

| Nó | Categoria | Função |
|----|-----------|--------|
| `ai_agent` | ai | Agente com tool-calling multi-passo + memória |
| `ai_rag` | ai | Consulta vector store + resposta com contexto |
| `knowledge` | data | Subir/gerenciar base de conhecimento da empresa |
| `vector_store` | integration | Ler/escrever embeddings (Supabase pgvector / Qdrant) |
| `code` | data | Executar JS custom |
| `loop` | logic | Iterar sobre lista (com split/filter) |
| `aggregate` | data | Juntar itens em um só |
| `schedule` | trigger | Disparar em cron |
| `execute_workflow` | core | Chamar outro workflow (reutilização) |
| `wait_until_message` | whatsapp | Pausar até nova mensagem (essencial no atendimento) |

---

## PARTE 4 — Melhorias no motor (engine)

- [ ] **Fila por nó** com timeout (hoje 1 timeout global via celery)
- [ ] **Retry automático** por nó (ex: 3x com backoff)
- [ ] **Error path**: conexão de erro por nó (como edge "onError" do n8n)
- [ ] **Ciclo de atendimento**: loop do trigger "new_message" até "resolve"
- [ ] **Timeout global** do fluxo
- [ ] **Pinned data** para testes isolados
- [ ] Registro de **inputs de cada nó** (para debug visual)
- [ ] Suporte a `{{ $json.field }}` além de `{{ data.field }}` (compat)

---

## PARTE 5 — Melhorias no frontend

- [ ] MiniMap, snap-to-grid, minimap custom já ok ✅
- [ ] **Info tooltip** em cada nó (input/output de teste)
- [ ] **Execução passo-a-passo** (highlight do nó atual)
- [ ] **Editor de expresões** com autocomplete `{{ data. }}` (como o n8n)
- [ ] **Lista de execuções** no editor (tab) já existe via `/executions`
- [ ] Paleta agrupada por categoria + **busca**
- [ ] Nó selecionado mostra **preview do input/output**

---

## PARTE 6 — Sugestão de ordem de execução (roadmap)

### Sprint 1 — Coração do produto (diferencia)
1. Credentials criptografadas (segurança primeiro)
2. Nó `wait_until_message` → ciclo completo de atendimento
3. Memória + contexto no nó `ai`
4. Nó `ai_agent` (tool calling multi-passo)

### Sprint 2 — Conhecimento (RAG)
5. Nó `ai_rag` + upload de base de conhecimento
6. Vector store (Supabase pgvector — já temos banco!)
7. Gerenciar conhecimento da empresa (frontend upload)

### Sprint 3 — Maturidade de fluxo
8. Nó `code`, `loop`, `aggregate`, `schedule`, `execute_workflow`
9. Error handling por nó (retry + error path)
10. Melhorias de dev (pinned data, preview input/output)

### Sprint 4 — Polimento
11. Templates prontos
12. Versionamento/publish
13. Sticky notes, busca na paleta

---

## Resumo executivo

- **Já temos a fundação sólida**: editor visual, motor, multi-tenant, IA multi-provider barata (Groq).
- **O gap mais importante** para "chegar no objetivo" é transformar o `nó ai` (1 chamada) em um **AI Agent** com memória, tool-calling e (idealmente) RAG — é isso que torna o produto uma "plataforma" de verdade, não só um motor.
- **Segundo maior gap**: ciclo de atendimento completo via `wait_until_message` + loop.
- **Terceiro**: segurança (credenciais criptografadas).

> Recomendação: iniciar pelo **Sprint 1** — principalmente memória/contexto + `wait_until_message`, que desbloqueia o caso de uso real (atendimento WhatsApp) sem depender de VPS.
