# 09 — Nodes Disponiveis

## Lista de Nodes

| Node | Tipo | Descricao |
|------|------|-----------|
| Gatilho (WhatsApp) | `trigger_message` | Inicia quando recebe mensagem WhatsApp |
| Gatilho (Webhook) | `trigger_webhook` | Inicia quando recebe webhook generico |
| IA | `ai` | Envia prompt para LLM e retorna resposta |
| Set (variavel) | `set` | Define uma variavel no contexto |
| Condicao | `condition` | Verifica condicao e bifurca o fluxo |
| Delay (espera) | `delay` | Aguarda X segundos antes de continuar |
| HTTP | `http` | Faz requisicao HTTP externa |
| WhatsApp (enviar) | `whatsapp_send` | Envia mensagem via WhatsApp |
| Filtro | `filter` | Filtra dados do contexto |
| Log | `log` | Registra mensagem nos logs |
| Aguardar mensagem | `wait_until_message` | Pausa ate proxima mensagem do cliente |
| Transferir para humano | `transfer_to_agent` | Marca conversa como pendente de atendimento humano (handoff) |
| IA RAG | `ai_rag` | Busca na base de conhecimento e responde com IA |
| Codigo | `code` | Executa Python customizado |
| Loop | `loop` | Itera sobre uma lista |
| Aggregate | `aggregate` | Junta itens em um resultado |
| Schedule | `schedule` | Trigger por cron |
| Executar Workflow | `execute_workflow` | Chama sub-workflow |

## Detalhes por Node

### trigger_message
- **Icone:** MessageSquare (verde)
- **Entrada:** Nenhuma (e o primeiro node)
- **Saida:** `success`
- **Dados:** `data.value` (texto do trigger)

### trigger_webhook
- **Icone:** Webhook (rosa)
- **Entrada:** Nenhuma (e o primeiro node)
- **Saida:** `success`
- **Dados:** `data.value` (dados do webhook)

### ai
- **Icone:** Brain (lilas)
- **Entrada:** Qualquer
- **Saida:** `success`, `error`
- **Dados obrigatorios:** `data.prompt`
- **Dados opcionais:**
  - `data.history`: "on"/"off" (default: "on")
  - `data.system_prompt`: override do system prompt
- **Comportamento:** Chama LLM, salva resposta no banco, salva `ai_reply` no contexto

### set
- **Icone:** Pencil (cinza)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.variable`, `data.value`, `data.expression`

### condition
- **Icone:** GitBranch (amarelo)
- **Entrada:** Qualquer
- **Saida:** `true`, `false`
- **Dados:** `data.value`, `data.operator`, `data.left`, `data.right`, `data.reference`
- **Operadores:** ==, !=, contains, >, <, >=, <=

### delay
- **Icone:** Timer (azul claro)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.value` (segundos)

### http
- **Icone:** Globe (cyan)
- **Entrada:** Qualquer
- **Saida:** `success`, `error`
- **Dados:** `data.url`, `data.method`, `data.body`

### whatsapp_send
- **Icone:** MessageCircle (verde escuro)
- **Entrada:** Qualquer
- **Saida:** `success`, `error`
- **Dados:** `data.value` (texto da mensagem)
- **Requer:** Configuracao Evolution API

### filter
- **Icone:** Filter (laranja)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.field`, `data.operator`, `data.value`

### log
- **Icone:** FileText (cinza escuro)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.value` (mensagem para log)

### wait_until_message
- **Icone:** PauseCircle (vermelho)
- **Entrada:** Qualquer
- **Saida:** `waiting`
- **Comportamento:** Pausa execucao, salva PendingFlow, retoma quando cliente enviar proxima mensagem

### transfer_to_agent
- **Categoria:** whatsapp
- **Entrada:** Qualquer
- **Saida:** `transferred` (bool), `conversation_id`
- **Comportamento:** Seta `Conversation.status` para `pending_agent` e registra um `ConversationTransfer` (action=`transfer_requested`, actor_type=`workflow`). Se a conversa ja esta `pending_agent`, apenas registra log e retorna `transferred=true` sem regravar.

### ai_rag
- **Icone:** Brain (lilas)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.prompt` (pergunta), `data.top_k` (default 5), `data.system_prompt`
- **Comportamento:** Busca contexto na base de conhecimento via cosine similarity, gera resposta via LLM com RAG

## Error Handling

Todos os nos possuem o campo `on_error`:

| Valor | Comportamento |
|-------|--------------|
| `stop` | Encerra o fluxo com erro (default) |
| `continue` | Ignora o erro e segue para o proximo no |
| `fallback_edge` | Segue a edge de erro (sourceHandle="error") |

## Cores dos Nodes

| Node | Cor |
|------|-----|
| trigger_message | #22c55e (verde) |
| trigger_webhook | #ec4899 (rosa) |
| ai | #a855f7 (lilas) |
| ai_rag | #a855f7 (lilas) |
| set | #9ca3af (cinza) |
| condition | #eab308 (amarelo) |
| delay | #67e8f9 (azul claro) |
| http | #06b6d4 (cyan) |
| whatsapp_send | #16a34a (verde escuro) |
| filter | #f97316 (laranja) |
| log | #6b7280 (cinza escuro) |
| wait_until_message | #ef4444 (vermelho) |
| transfer_to_agent | #22c55e (verde, whatsapp) |
