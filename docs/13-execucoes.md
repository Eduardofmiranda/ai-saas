# 13 — Execucoes de Workflows

## Conceito

Uma **execucao** e a instancia de execucao de um workflow com dados especificos (payload).

## Ciclo de Vida

```
1. Payload chega (webhook ou API run)
2. Cria Execution(status="pending")
3. Monta contexto com payload
4. execute_workflow() inicia
5. Status → "running"
6. Nodes sao executados sequencialmente
7. Se wait_until_message → status="waiting", cria PendingFlow
8. Quando termina → status="success" ou "error"
9. Salva logs no campo context["logs"]
10. Salva resultados dos nodes em node_results
```

## Estrutura do Context

```json
{
  "message": {
    "text": "Ola, preciso de ajuda",
    "from": "+5511999999999",
    "contact_name": "Joao"
  },
  "company_id": 1,
  "workflow_id": 1,
  "execution_id": 1,
  "logs": []
}
```

## node_results

Apos execucao, cada node salva seu resultado:

```json
{
  "n1": {"outputs": {"result": true}},
  "n2": {"outputs": {"ai_reply": "Ola! Como posso ajudar?"}},
  "n3": {"outputs": {"status": "sent"}}
}
```

## Status

| Status | Descricao |
|--------|-----------|
| `pending` | Criada, aguardando execucao |
| `running` | Em execucao |
| `success` | Executada com sucesso |
| `error` | Erro na execucao |
| `waiting` | Pausada (aguardando proxima mensagem) |

## PendingFlows

Quando um workflow pausa (wait_until_message):

1. `snapshot` salva: `{data, next_node_id}`
2. `phone` salva o telefone do cliente
3. `execution_id` referencia a execucao original
4. Quando cliente envia proxima mensagem:
   - Sistema verifica se existe PendingFlow para o telefone
   - Se sim: `resume_workflow()` retoma de onde parou
   - Se nao: inicia novo workflow

## Execucao Assincrona

Para workflows de longa duracao:

```python
# Via API
POST /workflows/{id}/run
{
  "phone": "+5511999999999",
  "message": "texto da mensagem"
}
```

O sistema tenta executar diretamente; se nao conseguir, agenda via Celery.
