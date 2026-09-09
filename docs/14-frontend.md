# 14 — Frontend

## Stack

| Tecnologia | Versao | Finalidade |
|-----------|--------|-----------|
| React | 19.2.8 | Biblioteca UI |
| @xyflow/react | 12.11.5 | Editor visual (React Flow) |
| react-router-dom | 7.18.2 | Roteamento |
| Vite | 8.2.2 | Bundler/dev server |

## Paginas

### `/login`
- Layout em 2 colunas: painel de marca/hero (funcionalidades) + card de autenticacao.
- Abas "Entrar" / "Criar conta" (segmented control) e recuperacao de senha
  (`POST /auth/forgot-password`, mensagem genérica).
- Validacao minima de senha (6 caracteres) no cadastro; `autocomplete`/`autoFocus` por campo.
- Redireciona para `/` apos login.
- Erros/avisos via componente `Alert` (`components/ui/Alert.jsx`); features do hero
  usam icones do `Icon` (zap/cpu/bar-chart) e marca com `bot`.

### `/reset-password`
- Rota **publica** (sem necessidade de sessao)
- Le `?token=` da URL, confirma novas senhas e chama `POST /auth/reset-password`
- Apos sucesso, navega para `/login`

### `/conta`
- Rota protegida
- Formulario para alterar a senha (`POST /auth/change-password`)

### `/setores`
- Rota protegida
- Lista os setores da empresa (`GET /departments/`) em uma tabela com busca por nome/descricao.
- Card de resumo (total de setores, com descricao e disponiveis no encaminhamento).
- Criar/editar via **modal** (`POST /departments/` e `PATCH /departments/{id}`) com validacao
  (nome obrigatorio) e feedback de sucesso/erro.
- Exclusao com **confirmacao por modal** (sem `confirm()` nativo).
- Estados de loading, vazio (CTA de criar) e busca sem resultado.

Pagina: `frontend/src/pages/Departments.jsx`. Rota `/setores` em `App.jsx`.

### `/leads`
- Rota protegida
- Lista clientes/leads da empresa (`GET /customers/`) com paginacao, busca e contagem de conversas.
- Detalhe do cliente (modal) com ultimas conversas.
- Exportacao de leads (`GET /customers/export/xlsx`) como planilha Excel.
- Envio de mensagem em massa (`POST /customers/bulk-message`) para leads selecionados.

Pagina: `frontend/src/pages/Leads.jsx`. Rota `/leads` em `App.jsx`.

### `/` (Dashboard)
- Metricas da empresa (KPIs) e status WhatsApp/Evolution.
- Se existem conversas pendentes (`pending_conversations > 0`), exibe um **banner de alerta**
  (`.notice`) com botao que navega para `/conversas`.
- Botao "Novo fluxo" para criar workflow.
- Barra de progresso de execucoes (sucesso vs erro).
- **KPIs adicionais (Fase 9.2):** "Resposta media" (`avg_response_time_minutes`) e
  "Uso de IA" (mensagens + tokens totais), formatados em pt-BR.
- **Chart grid ampliado (9.2):** donut de **resolucao** (automatica vs humana,
  `auto_resolved`/`human_resolved`); `BarChart` de **conversas** (30 dias) e de
  **tokens de IA** (30 dias, com total e custo estimado); listas **Top fluxos**
  (execucoes + erros) e **Erros por node** (via classes `.dash-list`).

### `/editor/:id`
- Editor visual de workflows
- Paleta de nodes (arrastar para o canvas)
- Canvas com nodes e edges; a posicao de um node arrastado respeita o zoom e o deslocamento atuais do canvas.
- Minimap escuro no canto inferior direito: pode ser arrastado para navegar e receber zoom por scroll.
- Controles de zoom no canto inferior esquerdo e botao **Centralizar fluxo** para reenquadrar todos os nodes.
- Os cards dos nodes mostram sua descricao e suas portas visuais; triggers indicam inicio/saida e condicoes indicam os caminhos Sim/Nao.
- Inspector (editar node selecionado), com descricao e orientacao de uso para os principais nodes.
- O node `transfer_to_agent` e representado visualmente no editor, como os demais tipos retornados pela API.
- Salvar / Rodar / Logs

### `/whatsapp`
- Status de conexao WhatsApp/Evolution por empresa
- `Conectar WhatsApp` -> `POST /config/whatsapp/setup` (gera QR base64)
- `Desconectar` -> `POST /config/whatsapp/disconnect`
- **Auto-refresh (polling):** a pagina consulta `GET /config/whatsapp` a cada
  **3s enquanto o QR esta visivel** (escaneando) e **10s caso contrario**, de modo
  que o status muda sozinho para "Conectado" apos o escaneamento, sem F5.
  Ao detectar `state: "open"`, o QR e limpo automaticamente.

### `/agenda`
- Rota protegida; pagina `frontend/src/pages/Agenda.jsx`, rota `/agenda` em `App.jsx`,
  item "Agenda" no `Header.jsx`.
- **Resumo**: cards com compromissos ativos, dias de agenda e cancelados.
- **Painel Secretaria IA**: toggle ativar/desativar agenda (`PUT /agenda/config`
  com `{enabled}`) e resumo (duração padrão, antecedência, fuso, horários por dia,
  mensagem de confirmação). Edição de configuração via **modal** (somente
  gestor/owner/admin), com fuso, horários por dia, duração, antecedência, mensagem
  e **datas bloqueadas**.
- **Lista de compromissos**: tabela (data, horário, cliente, telefone, serviço,
  status, origem) com **filtros por status, data inicial/final (consumidos pela
  API) e busca por cliente/telefone/serviço (client-side)**. Cancelamento com
  **modal de confirmação** (`DELETE /agenda/appointments/{id}`).
- **Novo agendamento** via modal (`POST /agenda/appointments`, `origin=manual`):
  data + grade de horários livres (`GET /agenda/availability?date=`), fim
  calculado pela duração padrão, telefone obrigatório.
- Gestores editar configuracao e cancelar/alterar qualquer compromisso;
  atendentes apenas visualizam/criam e cancelam/alteram **os compromissos que
  eles próprios criaram** (o botão Cancelar é oculto nos demais; compromissos de
  WhatsApp ficam restritos à gestão — 403 se forçado).

### `/plataforma`
- Rota protegida por `is_platform_admin`.
- **Visão geral** (KPIs: empresas, usuários, workflows, execuções com erro; nota sobre uso/sessões).
- **Credenciais globais de IA**: grid de provedores (Groq, OpenAI, DeepSeek, Mistral, Ollama, Demonstração)
  com modelo, URL base, chave (write-only), toggle de disponibilidade e consulta de saldo DeepSeek.
- **Política de IA por usuário**: chips de provedores liberados, selects de provedor/modelo padrão;
  usuários listados com avatar, email, política e empresa.
- **Usuários de todas as empresas**: lista com nome, email, empresa, papel (Dono/Admin/Atendente)
  e badge "Plataforma" para operadores.
- **Redefinir senha**: botão por usuário abre modal que gera uma **senha provisória**
  (`POST /platform-admin/users/{id}/reset-password`), exibida uma única vez com botão
  "Copiar" — sem `prompt`/`confirm` nativos. O copiar usa `navigator.clipboard` e,
  em contexto não seguro (HTTP), **fallback** com `textarea` + `document.execCommand("copy")`.
- **Painel de Erros**: tabela paginada com empresa, workflow, erro e data; limpar todos com
  **modal de confirmação** (sem `confirm()` nativo).
- Auto-load da aba "Erros" ao entrar nela.

Pagina: `frontend/src/pages/PlatformAdmin.jsx`. Rota `/plataforma` em `App.jsx`.

### `/conversas` (Inbox — 3 paineis)
- **Implementado** (Fase 9.0, primeira parte).
- Layout em 3 paineis (padrao do mercado: lista | thread | contexto do cliente).
- **Painel 1 — Lista:** busca por nome/telefone, abas (Todas/Abertas/Aguardando/Fechadas),
  avatar, status (`open`/`pending_agent`/`closed`), preview + horario da ultima mensagem.
  Conversas com setor exibem **badge do setor**.
  Ordena por `updated_at` (mais recente primeiro). Dados de
  `GET /conversations/`.
- **Painel 2 — Thread + resposta:** historico de mensagens com bolhas distintas
  (cliente/bot/agent) e envio de **resposta manual** por `Enter` ou botao
  (`POST /messages/conversation/{id}/reply`). Matriz de acoes por status (PATCH
  `conversations/{id}` com `{status}`): `open`→Fechar (closed);
  `pending_agent`→Assumir (agent) + Fechar (closed); `agent`→Liberar (open) +
  Fechar (closed); `closed`→Reabrir (open).
- **Painel 3 — Contexto:** nome, telefone, status, **setor**, inicio e total de mensagens do
  cliente + **Histórico de transferências** (action, quem agiu, quando).
- **Polling:** atualiza a lista e as mensagens da conversa selecionada a cada 5s.

Pagina: `frontend/src/pages/Conversations.jsx`. Rota `/conversas` em `App.jsx`.

### `/ai`
- Configuracao de IA por empresa: provedor, modelo (`GET/PATCH /config/`), prompts e presets.
- **Modelos Groq vigentes:** openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.6-27b, qwen/qwen3.8-27b.
  Se o modelo salvo nao existir mais (ex.: `mixtral-8x7b-32768`), o campo cai
  automaticamente para um modelo valido (nao reescreve o banco ate "Salvar").
- Botao **"Testar resposta da IA"** -> `POST /config/ai/test` (chama o provedor com
  a config atual — provider/modelo/chave — e mostra a resposta real).

## Estrutura de Componentes

```
src/
├── App.jsx              # Rotas
├── main.jsx             # Entry point
├── api.js               # API client (fetch wrapper, prefixo /api)
├── index.css            # Estilos globais + tokens do design system
├── components/
│   ├── Header.jsx            # Navegacao do topo (sticky, avatar + role chip)
│   ├── BusinessHoursPanel.jsx# Horario de atendimento (painel do WhatsApp)
│   ├── KnowledgeSummaryCard.jsx
│   ├── charts.jsx            # Graficos SVG/DOM sem dependencia: DonutChart,
│   │                         #   BarChart, StackedBarChart, ChartLegend (+DAY_LABEL)
│   └── ui/                   # Design system (componentes compartilhados)
│       ├── Icon.jsx          # Icones SVG fixos (substituem emojis de UI)
│       ├── Alert.jsx         # Feedback erro/sucesso/info (com onDismiss)
│       ├── Modal.jsx         # Modal acessivel (role/aria/Escape/overlay)
│       ├── ConfirmDialog.jsx # Confirmacao destrutiva (substitui confirm())
│       ├── PageHeader.jsx    # h1 + subtitulo + acoes
│       ├── EmptyState.jsx    # Estado vazio (icone + titulo + acao)
│       ├── Skeleton.jsx      # Placeholder de loading (variant="cards"/"lines")
│       ├── Pagination.jsx    # Navegacao anterior/proxima + total (Fase 8.7)
│       └── index.js          # Re-export (importar de "../components/ui")
├── context/
│   └── AuthContext.jsx  # Context de autenticacao
├── utils/
│   ├── format.js        # formatPhone, avatarColor (paleta unica de avatares)
│   └── constants.js     # DAYS, TIMEZONES (compartilhados)
└── pages/
    ├── Login.jsx            # Login
    ├── ResetPassword.jsx    # Redefinir senha (rota publica)
    ├── Dashboard.jsx        # Painel inicial (KPIs + status WhatsApp)
    ├── Home.jsx             # Lista de workflows (Fluxos)
    ├── Conversations.jsx    # Inbox 3 paineis
    ├── Leads.jsx            # Leads / clientes
    ├── Editor.jsx           # Editor visual de workflows
    ├── AI.jsx               # Configuracao/manage de IA
    ├── Knowledge.jsx        # Base de conhecimento (RAG)
    ├── Departments.jsx      # Setores da empresa
    ├── Admin.jsx            # Administracao / usuarios + auditoria
    ├── PlatformAdmin.jsx    # Admin de plataforma (providers/usuarios/erros)
    ├── Account.jsx          # Minha conta (alterar senha)
    ├── Agenda.jsx           # Agenda / Secretaria IA
    └── WhatsApp.jsx         # Conexao WhatsApp/Evolution
```

### `/admin` — Membros + Auditoria
- **Membros**: lista paginada (50/pagina) com busca por nome/email, criacao de membro,
  alteracao de papel e remocao — somente gestores (owner/admin).
- **Setor + nível (Fase 8.9)**: criar membro é só nome/email/senha/papel (rápido).
  O vínculo com setores fica num **modal próprio "Setores"** (botão "Setores" em
  cada membro): seletor em **duas colunas** — "Setores da empresa" (com `+` e `select`
  de nível para vincular) e "Setores do membro" (remove com `×` e troca o nível
  direto). O modal **Editar** cuida apenas de papel e nova senha. A linha do membro
  exibe **badges** `Setor · Nível`.
- **Auditoria** (somente gestor, Fase 9.4): secao abaixo da lista de membros com a tabela
  de acoes criticas (`GET /audit-logs/`), filtros por **acao**, **entidade** e **usuario**,
  paginacao (25/pagina) e colunas: Quando, Usuario, Acao, Entidade, Detalhes (sumario do JSON
  de detalhes) e IP. Utiliza o componente `ui/Pagination`.

## API Client (`api.js`)

```javascript
// Em PRODUCAO (nginx): prefixo relativo "/api" — o nginx descarta o prefixo
// (`location /api/ { proxy_pass http://backend:8000/; }`). O backend NAO conhece
// o prefixo. Separacao que evita "Not authenticated" em rotas do SPA.
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// Interceptors:
// - Adiciona Authorization: Bearer <token>
// - Trata 401 → limpa token + redireciona para /login
```

Regra fixa: **toda chamada de API** usa `API_BASE + caminho` via `api.js` — nunca
`fetch()` com caminho solto. Em dev o Vite proxy replica o comportamento do nginx
(remove `/api` e repassa ao backend).

## Editor Visual

### Funcionalidades
- Arrastar nodes da paleta para o canvas
- Conectar nodes com edges (arrastar de handle)
- Deletar node selecionado (botao ou Backspace/Delete)
- Renomear workflow (duplo clique no titulo)
- Ativar/desativar workflow
- Salvar no backend (botao Salvar)
- Executar workflow (botao Rodar)
- Visualizar logs e resultado

### Tipos de Nodes Visuais

Cada tipo de node tem:
- **Cor** diferente
- **Icone** diferente
- **Handles** de entrada/saida
- **Campos** especificos no inspector

### Teclas de Atalho

| Tecla | Acao |
|-------|------|
| Backspace | Deletar node selecionado |
| Delete | Deletar node selecionado |
| Escape | Desselecionar node |

## Design System (componentes compartilhados)

**Implementado.** Padroes unificados criados na reforma de UI (agosto/2026),
aplicados em todas as paginas. No `Editor.jsx` valem os mesmos primitivos
(`Alert`/`ConfirmDialog`/`Icon`) para erros, confirmacoes e emojis, **exceto**
os glifos de categoria dos nodes (▶ ✦ ➜ ⇄ ✆ ◆ ★) e o atalho Delete direto
(sem confirmacao), que sao identidade visual/agilidade do editor — mantidos:

- **Icones**: usar **sempre** `<Icon name="..." size={16} />` de `components/ui/Icon.jsx`
  em vez de emojis/`<svg>` soltos. Conjunto fechado de nomes (ver `Icon.jsx`).
  Decorativos por padrao (`aria-hidden`); `label` so quando o icone carrega significado.
- **Alert** (`<Alert variant="error|success|info" onDismiss={...}>`): substitui
  `.error`, `.success`, `.alert alert-*`, `.bh-ok`/`.bh-warning`, `.notice`.
  Eg : botao de dispensar "um" com `aria-label`.
- **Modal** (`<Modal title onClose footer width>`): substitui modais manuais —
  Escape/overlay/role/aria ja implementados internamente. Nao duplicar useEffects.
- **ConfirmDialog** (`ConfirmDialog` com `confirmLabel`, `loading`, `danger`):
  substitui **todos** os `confirm()`/`window.confirm()` nativos.
  `danger=true` (default) → `btn solid-danger` (acao irreversivel);
  `danger=false` → `btn primary` (reversivel).
- **PageHeader** (`title`, `subtitle`, acoes via children): `<h1>` unico por pagina.
- **EmptyState** (`icon={<Icon size={40}/>}`, `title`, `action`): substitui `.empty`.
- **Skeleton** (`<Skeleton variant="cards" />` para grids, `variant="lines"` para listas;
  `rows`/`cards` para numero de blocos): substitui textos "Carregando ..." no loading
  de paginas. Classes `.skeleton*` + keyframes `shimmer` em `index.css`.
- **Pagination** (`<Pagination total page pageSize onChange itemLabel>`): botoes
  Anterior/Proxima + "Página X de Y" + total. Filtro de busca em listas usa a classe
  `.list-toolbar`/`.list-search` (mesmo visual do `.leads-search`).
- **Graficos** (`components/charts.jsx`): SVG/CSS proprios, sem lib de chart —
  `DonutChart` (segmentos com stroke-dasharray), `BarChart` e `StackedBarChart`
  (barras por coluna), `ChartLegend`, `DAY_LABEL`. Usados no painel (`/`):
  conversas por status, mensagens e execucoes dos ultimos 7 dias (dados reais de
  `GET /dashboard/`, serao series preenchidas com zero nos dias sem dados).
- **Utils**: `formatPhone`, `avatarColor` (`utils/format.js`) e `DAYS`/`TIMEZONES`
  (`utils/constants.js`) — nao duplicar localmente nas paginas.
- **Botoes de perigo**: reversivel = `btn ghost small danger` (inline no card);
  irreversivel com confirmacao = `btn solid-danger` (no ConfirmDialog).
- **Tokens de contraste**: `--accent-strong (#3b63e0)`/`--accent-strong-hover`
  para fundos de botao/tab/filtro ativos (WCAG ~4.9:1); `--accent`/`--accent2`
  para texto/link/acento claro.
- **Acessibilidade**: `:focus-visible` global; `.sr-only` para labels de inputs que
  dependem de placeholder; remover emojis de UI (mantidos em conteudos, ex.: avatares).

## CSS

- Tema escuro centralizado em variaveis CSS (`:root`): `--bg`, `--panel`, `--panel2`,
  `--border`, `--text`, `--muted`, `--accent`, `--accent2`, `--green`, `--red`.
- **Design system (primitivos)** em `index.css` para consistencia entre paginas:
  `.page-header`, `.card`, `.stack`, `.input`, `.table`, `.stat-grid`/`.stat-card`,
  `.toolbar`, `.search-box`, `.count-pill`, `.avatar-sm`, `.empty-state`, `.alert`
  (`alert-error`/`alert-success`/`alert-info`).
- Botoes: `.btn` base; variantes `.primary`, `.secondary`, `.ghost`, `.danger`,
  `.solid-danger`; tamanhos `.small`; `.block` para largura total em formularios
  (login, conta, reset de senha).
- Header `.topbar` sticky com blur; `.user` mostra avatar com inicial + role chip.
- Topbar, nav ativo, cards (`wf-card`/`kpi-card`) com hover/highlight suave.
- Scrollbar customizada (webkit).
- Login: card centralizado
- Home: grade de cards de fluxos
- Editor: paleta + canvas + inspector
- **Responsividade (breakpoints)**: sidebar vira rail de icones (<1100px) e drawer
  mobile (<768px); editor empilha colunas (<900px); inbox: 3 paineis -> lista+thread
  (<900px, contexto oculto) -> painel unico em pilha (<768px); tabelas ganham
  scroll horizontal; `grid-2`/`leads-grid` colapsam para 1 coluna (<768px);
  `.page-header-row`/`.toolbar` empilham (<560px). Skeletons substituem textos de
  carregamento nas paginas.
