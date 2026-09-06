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
| `data.body` | Reservado para HTTP; node indisponivel por seguranca |
| `data.code` | Reservado para Code; node indisponivel por seguranca |
| `data.max_iterations` | Reservado para Loop; node ainda parcial |

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

### Destinatario padrao em fluxos de mensagem

Todo workflow com `trigger_type = message` recebe o telefone do remetente em
`{{ data.phone }}`. Os templates e novos nodes **Enviar WhatsApp** usam essa
variavel por padrao, portanto respondem a qualquer numero que envie mensagem.
Se um node legado estiver com o campo Telefone vazio, o motor tambem usa o
remetente como destino. Um telefone preenchido e respeitado, permitindo envios
proativos quando isso for intencional.

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
### Editor React Flow

O editor consulta o contrato de nodes do backend e desenha as portas declaradas em
`input_handles` e `output_handles`. Antes de criar uma conexao, ele bloqueia no
navegador entradas em triggers, auto-conexoes, duplicidades e ciclos, mostrando o
motivo no canvas. Essa verificacao melhora a edicao, mas o backend continua sendo a
autoridade: salvar, ativar e executar validam novamente o grafo e podem retornar 422.
Em fluxos de mensagem, o editor tambem orienta quando uma resposta de `ai` ou
`ai_rag` nao alcanca um node **Enviar WhatsApp**. O botao de orientacao adiciona
o node e a conexao com valores iniciais `{{ data.phone }}` e
`{{ data.ai_reply }}`. A alteracao fica apenas no canvas ate o usuario salvar;
nenhuma mensagem e enviada pelo assistente do editor.
O botao **Checklist** esta disponivel para todos os tipos de workflow. Ele
confirma, localmente, o trigger compativel com o tipo do fluxo, os prompts de
IA/RAG, a entrega pelo caminho de sucesso e os campos de cada envio.
Por uma acao explicita do usuario, **Verificar IA e WhatsApp** chama
`POST /config/ai/test` e `GET /config/whatsapp` para mostrar a conectividade
real no proprio editor. O teste de IA chama o provedor e pode consumir cota; a
consulta do WhatsApp nao envia mensagem e nao altera a instancia.

### Teste seguro no editor

O botao **Rodar teste** chama o endpoint de teste com `dry_run=true` por padrao.
Ele ainda gera a resposta da IA e registra uma execucao auditavel, mas simula
**Enviar WhatsApp**, **Aguardar mensagem** e **Transferir para humano**. Portanto,
o teste nao envia mensagem, nao cria pendencia e nao altera uma conversa. A entrada
real pelo webhook continua executando normalmente, fora desse modo de teste.

## Ativacao de fluxos por mensagem

### Implementado

Para cada empresa, apenas um workflow com trigger_type igual a message deve ficar
ativo. Ao ativar outro fluxo desse tipo pela API ou pelo editor, o sistema
desativa automaticamente os demais fluxos de mensagem da mesma empresa.

Isso evita que uma mensagem recebida escolha um fluxo conforme a ordem do banco.
Workflows manual, webhook e cron nao sao alterados por essa regra.

Na tela de fluxos, um aviso aparece quando houver uma configuracao antiga com
mais de um fluxo de mensagem ativo. Basta ativar o fluxo principal desejado para
