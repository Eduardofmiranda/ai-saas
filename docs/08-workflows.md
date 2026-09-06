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
      "position": { "x": 250, "y": 300 }
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
      "position": { "x": 500, "y": 300 }
    }
  ],
  "edges": [
    { "source": "trigger-1", "target": "ai-1", "sourceHandle": "out" }
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
| `data.url` | Reservado para HTTP; node indisponivel por seguranca |
| `data.method` | Reservado para HTTP; node indisponivel por seguranca |
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

## Validacao antes de ativar ou executar

### Implementado

Rascunhos podem ser salvos para edicao, mas o backend valida o grafo antes de
ativar um workflow ou executa-lo pela API/webhook. A validacao exige:

- listas `nodes` e `edges`, IDs unicos e referencias de conexao existentes;
- exatamente um trigger, compativel com `trigger_type` (`message`, `webhook` ou `cron`);
- ausencia de ciclos e de conexoes que entram no trigger;
- configuracoes obrigatorias dos nodes implementados;
- ausencia de nodes parciais ou bloqueados.

Quando invalido, a ativacao retorna **422** com os ajustes necessarios. Isso nao
altera o rascunho salvo e impede execucao de grafos legados inseguros.
## Ativacao de fluxos por mensagem

### Implementado

Para cada empresa, apenas um workflow com trigger_type igual a message deve ficar
ativo. Ao ativar outro fluxo desse tipo pela API ou pelo editor, o sistema
desativa automaticamente os demais fluxos de mensagem da mesma empresa.

Isso evita que uma mensagem recebida escolha um fluxo conforme a ordem do banco.
Workflows manual, webhook e cron nao sao alterados por essa regra.

Na tela de fluxos, um aviso aparece quando houver uma configuracao antiga com
mais de um fluxo de mensagem ativo. Basta ativar o fluxo principal desejado para
