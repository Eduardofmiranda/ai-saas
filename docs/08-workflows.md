# 08 — Motor de Workflows

## Conceitos

Um **workflow** e uma composicao de **nodes** conectados por **edges** (arestas), que representam o fluxo de processamento de uma mensagem.

## Estrutura JSON de um Workflow

```json
{
  "nodes": [
    {
      "id": "trigger-1",
      "type": "trigger_message",
      "data": { "label": "WhatsApp", "text": "nova_mensagem" },
      "position": [250, 300]
    },
    {
      "id": "ai-1",
      "type": "ai",
      "data": {
        "label": "IA",
        "prompt": "Atenda o cliente: {{ data.message.text }}",
        "history": "on",
        "system_prompt": "Atendente virtual"
      },
      "position": [500, 300]
    }
  ],
  "edges": [
    { "source": "trigger-1", "target": "ai-1", "sourceHandle": "success" }
  ]
}
```

## Campos do Contrato

O motor le campos de `node.data.key` (formato achatado):

| Campo | Funcao |
|-------|--------|
| `data.value` | Valor para comparacoes (condition, set) |
| `data.variable` | Nome da variavel (set, expression) |
| `data.operator` | Operador de comparacao (condition) |
| `data.left` / `data.right` | Operandos para comparacao |
| `data.expression` | Template com interpolecao (set, expression) |
| `data.prompt` | Prompt para a IA (ai) |
| `data.history` | "on"/"off" - usar historico (ai) |
| `data.system_prompt` | Override do system prompt (ai) |
| `data.url` | URL para requisicao HTTP (http) |
| `data.method` | Metodo HTTP (http) |
| `data.body` | Corpo da requisicao (http) |
| `data.code` | Codigo Python para execucao (code) |
| `data.max_iterations` | Limite de iteracoes (loop) |

## Status de Execucao

| Status | Descricao |
|--------|-----------|
| `pending` | Criada, aguardando execucao |
| `running` | Em execucao |
| `success` | Executada com sucesso |
| `error` | Erro na execucao |
| `waiting` | Pausada, aguardando proxima mensagem |

## Interpolacao

Templates suportam interpolecao com `{{ }}`:

```
"Atenda o cliente: {{ data.message.text }}"
"Nome: {{ data.customer.name }}"
"Telefone: {{ data.customer.phone }}"
```
