# 17 — Monitoramento

## Estado atual

### Implementado

- `GET /health`: liveness do processo HTTP.
- `GET /health/db`: consulta `SELECT 1` no banco configurado.
- `GET /health/redis`: executa `PING` no Redis configurado.
- `GET /health/evolution`: valida alcance/autenticacao na Evolution, sem
  expor chave ou resposta do servico.
- `GET /health/llm`: valida se provider, modelo, URL e chave globais estao
  coerentemente configurados; nao chama o modelo nem gera custo.
- Falhas de resposta da IA registram provider/modelo/company_id, sem prompt,
  resposta do usuario ou chave de API.
- O dashboard agrega contagens por empresa, workflows e execucoes.

Health checks de dependencias respondem `503` com `status: unhealthy` quando a
dependencia falha. Eles nao expõem URL, tokens, nem a resposta do provedor.

### Parcial

- Logs ainda seguem a saida dos containers; nao ha agregador central, alertas ou
  formato JSON padronizado para todos os eventos.
- O dashboard nao tem série temporal, tendência, latência de IA ou métricas de
  fila Celery.

### Planejado

- Métricas Prometheus/OpenTelemetry.
- Alertas para erro recorrente de workflow, Evolution offline e fila parada.
- Correlation ID entre webhook, execução, LLM e envio WhatsApp.

## Operação

Na VPS, monitore `docker compose ps`, os cinco endpoints `/health*` e os logs
estruturados do backend/worker. Um `200` em `/health` nao prova que Supabase,
Redis, Evolution ou LLM estejam utilizáveis; use o endpoint específico.