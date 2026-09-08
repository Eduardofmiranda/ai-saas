# FlowAI — Documentacao Tecnica

Documentacao completa do estado atual do projeto **FlowAI** (AI SaaS - Atendimento WhatsApp).

Plataforma de automacao de processos baseada em workflows, inspirada no n8n, focada em atendimento ao cliente via WhatsApp com IA.

## Navegacao

| Arquivo | Conteudo | Status |
|---------|----------|--------|
| [00-indice-tecnico.md](00-indice-tecnico.md) | Indice tecnico do projeto | Implementado |
| [01-visao-geral.md](01-visao-geral.md) | Visao geral do sistema | Implementado |
| [02-arquitetura.md](02-arquitetura.md) | Arquitetura do sistema | Implementado |
| [03-instalacao.md](03-instalacao.md) | Instalacao local | Implementado |
| [04-configuracao.md](04-configuracao.md) | Configuracao do projeto | Implementado |
| [05-variaveis-ambiente.md](05-variaveis-ambiente.md) | Variaveis de ambiente | Implementado |
| [06-banco-de-dados.md](06-banco-de-dados.md) | Banco de dados | Implementado |
| [07-redis-e-filas.md](07-redis-e-filas.md) | Redis e filas | Implementado |
| [08-workflows.md](08-workflows.md) | Motor de workflows | Implementado |
| [09-nodes.md](09-nodes.md) | Nodes disponiveis | Parcial (14/20 implementados) |
| [10-api.md](10-api.md) | API REST (~91 endpoints) | Implementado |
| [11-autenticacao.md](11-autenticacao.md) | Autenticacao e autorizacao | Implementado |
| [12-integracoes.md](12-integracoes.md) | Integracoes externas | Implementado |
| [13-execucoes.md](13-execucoes.md) | Execucoes de workflows | Implementado |
| [14-frontend.md](14-frontend.md) | Frontend (16 paginas) | Implementado |
| [15-deploy.md](15-deploy.md) | Deploy | Implementado |
| [16-seguranca.md](16-seguranca.md) | Seguranca | Parcial (advisory lock + PyJWT implementados; HTTPS e confirmacao server-side pendentes) |
| [17-monitoramento.md](17-monitoramento.md) | Monitoramento | Parcial (health checks implementados; Prometheus/alertas planejados) |
| [18-troubleshooting.md](18-troubleshooting.md) | Troubleshooting | Implementado |
| [19-desenvolvimento.md](19-desenvolvimento.md) | Guia de desenvolvimento | Implementado |
| [22-catalogo-nodes-roadmap.md](22-catalogo-nodes-roadmap.md) | Catálogo planejado de nodes e conectores | Parcial |
| [23-agenda-confirmacao-lembretes.md](23-agenda-confirmacao-lembretes.md) | Agenda da Secretaria IA | Implementado |

## Documentacao de seguranca

| Arquivo | Conteudo |
|---------|----------|
| [SEGURANCA-2026-09-07.md](SEGURANCA-2026-09-07.md) | Primeira revisao de seguranca |
| [SEGURANCA-2026-09-08-AGENDA.md](SEGURANCA-2026-09-08-AGENDA.md) | Revisao de seguranca da agenda (achados + correcoes) |

## Guias de deploy (raiz do projeto)

| Arquivo | Conteudo |
|---------|----------|
| [CreateVPS.md](../CreateVPS.md) | **Criacao/reinstalacao da VPS do zero** (reset completo + passo a passo com todos os comandos) |
| [VPS-SETUP.md](../VPS-SETUP.md) | Roteiro E2E validado do deploy real |

## Como usar esta documentacao

- Para entender o sistema: comece por [01-visao-geral.md](01-visao-geral.md)
- Para instalar: veja [03-instalacao.md](03-instalacao.md)
- Para configurar: veja [05-variaveis-ambiente.md](05-variaveis-ambiente.md)
- Para deploy: veja [15-deploy.md](15-deploy.md)
- Para desenvolver: veja [19-desenvolvimento.md](19-desenvolvimento.md)
- Para seguranca: veja [16-seguranca.md](16-seguranca.md) e [SEGURANCA-2026-09-08-AGENDA.md](SEGURANCA-2026-09-08-AGENDA.md)

## Legenda de status (AGENTS.md §17)

- **IMPLEMENTADO** — funcionalidade confirmada pelo codigo
- **PARCIAL** — funcionalidade existente, mas incompleta
- **PLANEJADO** — funcionalidade desejada, mas ainda nao implementada
- **DESCONHECIDO** — nao foi possivel confirmar pelo codigo
