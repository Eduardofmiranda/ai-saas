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
| HTTP | `http` | **Indisponivel por seguranca**; sera reintroduzido com politica anti-SSRF |
| WhatsApp (enviar) | `whatsapp_send` | Envia mensagem via WhatsApp |
| Filtro | `filter` | Filtra dados do contexto |
| Log | `log` | Registra mensagem nos logs |
| Aguardar mensagem | `wait_until_message` | Pausa ate proxima mensagem do cliente |
| Transferir para humano | `transfer_to_agent` | Marca conversa como pendente de atendimento humano (handoff) e encerra a automacao da mensagem atual |
| IA RAG | `ai_rag` | Busca na base de conhecimento e responde com IA |
| Codigo | `code` | **Indisponivel por seguranca**; sera reintroduzido apenas com sandbox real |
| Loop | `loop` | Itera sobre uma lista |
| Aggregate | `aggregate` | Junta itens em um resultado |
| Schedule | `schedule` | Trigger por cron |
| Executar Workflow | `execute_workflow` | Chama sub-workflow |
| Capturar lead | `capture_lead` | Extrai dados do cliente da conversa com IA e atualiza o contato |

## Configuracao padrao no editor

Todo node disponivel para novos workflows recebe defaults seguros e uma explicacao
visivel no painel de configuracao. Ao abrir um workflow legado, o editor tambem
restaura defaults para campos vazios; basta salvar para persistir a correcao.

A excecao e **Executar Workflow**: ele precisa apontar para um workflow real da
mesma empresa e, portanto, exige escolha explicita de ID. O editor explica isso
no proprio campo, sem inventar um destino.

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
- **Status:** indisponivel para execucao e para novos fluxos. O registro e mantido apenas para que workflows legados possam ser visualizados e corrigidos.
- **Motivo:** requisicoes a URLs arbitrarias permitiriam SSRF. A reintroducao depende de allowlist, bloqueio de redes privadas, limite de redirects e auditoria.

### whatsapp_send
- **Icone:** MessageCircle (verde escuro)
- **Entrada:** Qualquer
- **Saida:** `success`, `error`
- **Dados:** `data.phone` (destinatario) e `data.text` (texto da mensagem)
- **Padrao no editor:** novos nodes usam `{{ data.phone }}` como destinatario e
  `{{ data.ai_reply }}` como texto, adequados para responder a mensagem que
  disparou o workflow. Em workflows do tipo `message`, se o campo de telefone
  estiver vazio (inclusive em fluxos legados), o motor responde ao remetente.
  O editor exibe um icone de informacao e a acao **Responder ao remetente
  automaticamente** para restaurar esse padrao. Para envio proativo, substitua
  a variavel por um numero internacional, por exemplo `5511999999999`. O campo
  **Texto da mensagem** usa `{{ data.ai_reply }}` por padrao; sem node de IA,
  ele pode ser trocado por uma mensagem fixa de exemplo exibida na ajuda do campo.
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
- **Comportamento:** Seta `Conversation.status` para `pending_agent`, registra um `ConversationTransfer` (action=`transfer_requested`, actor_type=`workflow`) e encerra a automacao da mensagem atual. Enquanto estiver pendente, novas mensagens sao gravadas para o atendente, mas a IA nao responde nem retoma flows pausados. Se a conversa ja esta `pending_agent`, apenas registra log e retorna `transferred=true` sem regravar.

### ai_rag
- **Icone:** Brain (lilas)
- **Entrada:** Qualquer
- **Saida:** `success`
- **Dados:** `data.prompt` (pergunta), `data.top_k` (default 5), `data.system_prompt`
- **Comportamento:** Busca contexto na base de conhecimento via cosine similarity, gera resposta via LLM com RAG
- **Editor:** novos nodes recebem `{{ data.message.text }}` como prompt; em nodes legados vazios, o botao **Usar mensagem recebida** preenche esse valor.
- **Limite do provedor:** HTTP 429 indica limite temporario ou cota. O sistema orienta aguardar e, se persistir, verificar cota, credito e chave em **Configuracao > IA**. Nao ha retentativa automatica para evitar aumentar custo ou prolongar o bloqueio.

### code
- **Status:** indisponivel para execucao e para novos fluxos. O registro e mantido apenas para que workflows legados possam ser visualizados e corrigidos.
- **Motivo:** `exec` em Python nao e um isolamento de seguranca suficiente. A reintroducao depende de sandbox isolado, limites de CPU/memoria e auditoria.

### capture_lead
- **Categoria:** atendimento
- **Entrada:** Qualquer
- **Saida:** `lead` (dict com name/email/phone/company/city/notes), `saved` (bool), `customer_id`
- **Dados:**
  - `data.overwrite`: "on"/"off" (default "on"). "off" preenche apenas campos vazios.
  - `data.instruction`: instrucoes extras para a extracao (opcional)
- **Comportamento:** Carrega o historico da conversa, chama o LLM pedindo um JSON estruturado (nome, email, telefone, empresa, cidade e notas) e atualiza o contato (Customer) da conversa quando encontrado. Em modo de teste (`dry_run`) apenas simula e salva nada. Os dados extraidos ficam no contexto em `data.lead`.
- **Extracao:** usa o modo `response_format=json_object` quando o provedor suporta; caso contrario, repete sem o modo e usa um parser tolerante de JSON. Nada e salvo se a conversa nao tiver mensagens ou o contato nao for encontrado.
- **Requer:** Configuracao de IA da empresa.

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
