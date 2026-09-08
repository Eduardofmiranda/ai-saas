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
- Formulario de login (email + senha)
- Link para cadastro
- Link "Esqueci minha senha" -> submete `POST /auth/forgot-password` (mostra mensagem generica)
- Redireciona para `/` apos login

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

### `/` (Dashboard)
- Metricas da empresa (KPIs) e status WhatsApp/Evolution.
- Se existem conversas pendentes (`pending_conversations > 0`), exibe um **banner de alerta**
  (`.notice`) com botao que navega para `/conversas`.
- Botao "Novo fluxo" para criar workflow.
- Barra de progresso de execucoes (sucesso vs erro).

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
  "Copiar" — sem `prompt`/`confirm` nativos.
- **Painel de Erros**: tabela paginada com empresa, workflow, erro e data; limpar todos com
  **modal de confirmação** (sem `confirm()` nativo).
- Auto-load da aba "Erros" ao entrar nela.

Pagina: `frontend/src/pages/PlatformAdmin.jsx`. Rota `/plataforma` em `App.jsx`.

### `/conversas` (Inbox — 3 paineis)
- **Implementado** (Fase 9.0, primeira parte).
- Layout em 3 paineis (padrao do mercado: lista | thread | contexto do cliente).
- **Painel 1 — Lista:** busca por nome/telefone, abas (Todas/Abertas/Aguardando/Fechadas),
  avatar, status (`open`/`pending_agent`/`closed`), preview + horario da ultima mensagem.
  Ordena por `updated_at` (mais recente primeiro). Dados de
  `GET /conversations/`.
- **Painel 2 — Thread + resposta:** historico de mensagens com bolhas distintas
  (cliente/bot/agent) e envio de **resposta manual** por `Enter` ou botao
  (`POST /messages/conversation/{id}/reply`). Botao contextual:
  **Assumir conversa** (quando status=`pending_agent`, PATCH → `open`),
  Fechar conversa (open→closed) ou Reabrir conversa (closed→open).
- **Painel 3 — Contexto:** nome, telefone, status, inicio e total de mensagens do
  cliente + **Histórico de transferências** (action, quem agiu, quando).
- **Polling:** atualiza a lista e as mensagens da conversa selecionada a cada 8s.

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
├── index.css            # Estilos globais
├── components/
│   ├── Header.jsx            # Navegacao do topo (sticky, avatar + role chip)
│   ├── BusinessHoursPanel.jsx# Horario de atendimento (painel do WhatsApp)
│   └── KnowledgeSummaryCard.jsx
├── context/
│   └── AuthContext.jsx  # Context de autenticacao
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
    ├── Admin.jsx            # Administracao / usuarios
    ├── PlatformAdmin.jsx    # Admin de plataforma (providers/usuarios/erros)
    ├── Account.jsx          # Minha conta (alterar senha)
    └── WhatsApp.jsx         # Conexao WhatsApp/Evolution
```

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
