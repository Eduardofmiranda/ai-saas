# Estudo de Mercado — Redesenho do Painel (FlowAI)

> Documento de estudo para orientar o redesenho do painel (Fase 9.0 do
> `PROGRESSO.md`). Consolida ideias coletadas de plataformas de referencia de
> atendimento ao cliente e automacao de workflows.
>
> **Status das ideias** (regra AGENTS.md §17):
> - **Implementado** = ja existe no FlowAI
> - **Parcial** = existe de forma basica
> - **Planejado** = desejado, nao implementado
> - **Desconhecido** = nao confirmado no codigo
>
> Nenhuma ideia abaixo e "implementado" sem confirmacao no codigo.

---

## 1. Plataformas analisadas

| Plataforma | Foco | Classe de produto |
|-----------|------|-------------------|
| n8n | Automacao de workflows | Motor de automacao (referencia de arquitetura) |
| Manychat | Chat marketing / auto atendimento | Inbox omnichannel |
| Chatwoot | Suporte ao cliente open-source | Inbox/suporte omnichannel |
| Zendesk | Suporte ao cliente | Helpdesk omnichannel |
| Intercom | Suporte/engajamento ao cliente | Inbox + CRM conversacional |

Fonte: pesquisa web (set/2026). Observacoes de UX/layout sao **planejado**
referencial, nao dictado de produto.

---

## 2. Padroes de destaque por plataforma

### 2.1 n8n — observabilidade de execucoes
- **Planejado:** execucoes com status, hora de inicio e duracao em lista
  ordenavel (recebe: workflow, status, start, duration, trigger).
- **Planejado:** inspecao por node — ver entrada x saida de cada node de um run
  (mais util para debugar "shape" de dados). Hoje nao mostramos entrada/saida.
- **Planejado:** **retry** de execucao falha com 1 clique (re-executa com o
  mesmo input do trigger).
- **Planejado:** filtro de execucoes por status (success/error/running).
- **Planejado:** feed de execucoes em tempo real (auto-refresh) + indicadores de
  status coloridos.
- **Planejado:** metricas por workflow (avg/min/max duracao, taxa de sucesso,
  indicador de tendencia) e ranking de workflows mais executados.
- **Parcial:** hoje temos card de execucoes no Dashboard com barra success/error
  (`Dashboard.jsx`) — sem duracao, sem filtro, sem retry, sem tempo real.

### 2.2 Manychat — Inbox
- **Planejado:** inbox unificado com filtros de estado (aberta/fechada/todas),
  filtro **nao lida** e ordenacao (mais recente/mais antigo).
- **Planejado:** pastas/etiquetas (**labels**) com filtro por etiqueta.
- **Parcial/Planejado:** respostas rapidas (**canned responses**) — mensagens
  pre-salvas para o atendente.
- **Planejado:** notas internas por conversa.
- **Planejado:** atribuicao de conversa a um atendente (handoff).
- **Planejado:** analise do atendente — tempo de primeira resposta, tempo de
  encerramento, conversas atribuidas x encerradas, volume diario por agente.

### 2.3 Chatwoot — Inbox/Suporte
- **Planejado:** layout de inbox com lista de conversas + conversa ativa +
  contexto do cliente (checkbox tres painéis — veja §3).
- **Planejado:** atalhos de teclado e **command bar** (cmd+K) para navegacao.
- **Planejado:** abas por atendente (minhas / nao atribuidas / todas) + bulk actions.
- **Planejado:** **horario comercial** + auto-responder fora do horario.
- **Planejado:** chat "ao vivo" de conversas em andamento.
- **Parcial/Planejado:** formulario pre-chat / segmentacao de contatos.
- **Planejado:** CSAT (pesquisa de satisfacao) ao fim de conversa.

### 2.4 Zendesk — Dashboard/analytics
- **Planejado:** dashboard "ao vivo": fila (nova espera), atividade de chat
  (atendidos, tempo de resposta, duracao), **atividade de agente** (online/
  ausente/invisivel), satisfacao.
- **Planejado:** presets de periodo (24h / 7d / 30d) + seletores customizados.
- **Planejado:** filtros por departamento, agente, iniciador do chat.
- **Planejado:** **leaderboard** de agentes (gamificacao).
- **Parcial:** hoje o Dashboard mostra KPIs totais, sem periodo selecionavel nem
  filtros e sem atividades de agente.

### 2.5 Intercom — três painéis (UX)
- **Planejado:** tres painéis = navegacao | conversa ativa | contexto do cliente.
  Panels colapsaveis reduzem carga cognitiva.
- **Planejado:** progress disclosure — o agente ve so o que precisa na tarefa.
- **Planejado:** ordenacao SLA (First Response Time / Next Reply Time / Time to
  Close / Time to Resolution).

---

## 3. Padrao de layout recomendado (proposta)

Layout de inbox omnichannel com **tres painéis** (referencia Intercom/Chatwoot):

```
+--------------------------------------------------------------+
| Header (logo + nav + usuario)                                |
+----------------+---------------------------+-----------------+
| Lista de       |  Conversa ativa (thread)  |  Contexto do    |
| conversas      |  - mensagens              |  cliente        |
| (filtros,      |  - campo de resposta      |  - dados        |
|  etiquetas,    |  - respostas rapidas      |  - notas        |
|  nao lidas)    |  - atribuir/encerrar      |  - historico    |
+----------------+---------------------------+-----------------+
```

Colunas colapsaveis. Para telas menores, as colunas viram modais/abas.

---

## 4. Mapeamento do painel atual (FlowAI) x mercado

### O que ja temos (implementado, confirmado no codigo)
- **Parcial:** Dashboard com cards de KPI clicaveis (Fluxos, ativos, conversas,
  clientes, mensagens, execucoes) — `Dashboard.jsx`.
- **Parcial:** banner de status do WhatsApp (`wa-banner`).
- **Parcial:** lista de workflows em `Home.jsx` com toggle ativar/desativar.
- **Parcial:** barra de execucoes success/error.
- **Parcial:** paginas de Conhecimento (RAG), IA, Admin, WhatsApp.

### Lacunas claras (planejado — maiores oportunidades)
1. **Inbox de conversas** — **AGORA IMPLEMENTADO** (primeira parte da Fase 9.0):
   pagina `/conversas` em 3 paineis (lista | thread com resposta manual | contexto
   do cliente), `Conversations.jsx`. Endpoints: `GET /conversations/` enriquecido
   + `POST /messages/conversation/{id}/reply`. Respostas manuais gravadas como
   `sender_type="agent"`.
2. **Sem filtros/paginacao real** em todas as listas — o inbox ja tem busca+filtro
   de status por ticket, mas outras listas seguem `.all()` (estruturado §8.6).
3. **Sem historico de execucoes detalhado** (entrada/saida por node, retry).
4. **Sem periodo/tendencia** nos KPIs (so totais).
5. **Sem observabilidade de atividades/canais em tempo real**.
6. **Navegacao simples** (topnav) — sem sidebar/command bar/atalhos.
7. **Sem contexto do cliente aprofundado** (notas, historico amplo) — o painel 3
   mostra o basico (nome/telefone/status/inicio/mensagens).
8. **Sem respostas rapidas / etiquetas / atribuicao humana.**

---

## 5. Priorizacao sugerida (roadmap do redesenho)

Prioridade alta (maior valor percebido p/ atendimento humano):
- **Inbox de conversas (tres painéis)** — **IMPLEMENTADO** (pagina `/conversas`,
  resposta manual via `POST /messages/conversation/{id}/reply`).
- **Historico de execucoes** com entrada/saida por node + retry (proximo).
- **Filtros + paginacao** eficientes em listas.
- **KPIs com periodo e tendencia** no Dashboard.

Prioridade media:
- Respostas rapidas (canned responses).
- Etiquetas/labels + filtro nao lida.
- Atribuicao e handoff humano.
- Command bar (cmd+K) + atalhos.

Prioridade baixa / escala:
- Leaderboard/analise por agente.
- CSAT.
- Dashboard ao vivo (tempo real por WebSocket).

---

## 6. Riscos / notas

- Várias ideias exigem **novos endpoints no backend** (ex.: metricas por periodo,
  entrada/saida de execucao, atribuicao). Levantar antes de construir.
- Inbox humano muda o escopo do produto (de "so automatico" para "automatico +
  humano"). Decidir com o produto.
- Nenhuma feature deste documento deve ser marcada "implementado" sem confirmacao
  no codigo (AGENTS.md §5, §17, §23).
