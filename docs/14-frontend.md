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
- Redireciona para `/` apos login

### `/` (Home)
- Dashboard com estatisticas (placeholders)
- Lista de workflows com toggle ativar/desativar
- Botao "Novo Workflow"
- Logout

### `/editor/:id`
- Editor visual de workflows
- Paleta de nodes (arrastar para o canvas)
- Canvas com nodes e edges
- Inspector (editar node selecionado)
- Salvar / Rodar / Logs

### `/whatsapp`
- Status de conexao WhatsApp/Evolution por empresa
- `Conectar WhatsApp` -> `POST /config/whatsapp/setup` (gera QR base64)
- `Desconectar` -> `POST /config/whatsapp/disconnect`
- **Auto-refresh (polling):** a pagina consulta `GET /config/whatsapp` a cada
  **3s enquanto o QR esta visivel** (escaneando) e **10s caso contrario**, de modo
  que o status muda sozinho para "Conectado" apos o escaneamento, sem F5.
  Ao detectar `state: "open"`, o QR e limpo automaticamente.

## Estrutura de Componentes

```
src/
├── App.jsx              # Rotas
├── main.jsx             # Entry point
├── api.js               # API client (fetch wrapper)
├── index.css            # Estilos globais
├── context/
│   └── AuthContext.jsx  # Context de autenticacao
└── pages/
    ├── Login.jsx        # Pagina de login
    ├── Home.jsx         # Dashboard + lista de workflows
    └── Editor.jsx       # Editor visual de workflows
```

## API Client (`api.js`)

```javascript
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const BASE_URL = `${BASE}/api`;

// Interceptors:
// - Adiciona Authorization: Bearer <token>
// - Trata 401 → limpa token + redireciona para /login
```

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

- Layout: `100dvh`, flex column
- Login: card centralizado
- Home: barra lateral + area de conteudo
- Editor: paleta + canvas + inspector
- Cores: fundo escuro (`#111827`), cards (`#1f2937`)
