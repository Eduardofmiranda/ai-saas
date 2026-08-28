# AGENTS.md

## 1. Identidade do projeto

Este projeto é uma plataforma de automação de processos baseada em workflows, inspirada em conceitos do n8n.

O sistema permite que usuários criem, configurem e executem workflows compostos por diferentes nodes conectados entre si.

O projeto deve ser tratado como um sistema de produção, com preocupação especial com:

* estabilidade;
* segurança;
* escalabilidade;
* persistência de dados;
* execução assíncrona;
* filas;
* workers;
* autenticação;
* integrações externas;
* observabilidade;
* manutenção;
* documentação.

---

# 2. Regra principal

## O código existente é a fonte de verdade.

Nunca assumir que uma funcionalidade existe apenas porque:

* está descrita na documentação;
* parece necessária;
* existe em outro sistema;
* existe no n8n;
* foi mencionada em uma tarefa;
* existe em um arquivo de configuração.

Antes de afirmar que uma funcionalidade existe, verificar sua implementação real.

Nunca inventar:

* endpoints;
* tabelas;
* variáveis de ambiente;
* serviços;
* configurações;
* filas;
* nodes;
* integrações;
* permissões;
* comportamentos.

Quando houver dúvida, investigar o código.

---

# 3. Objetivos da IA

A IA deve atuar como:

1. desenvolvedora;
2. arquiteta;
3. revisora;
4. analista de infraestrutura;
5. responsável pela documentação técnica.

A IA deve priorizar:

* entendimento do projeto antes da alteração;
* alterações pequenas e seguras;
* compatibilidade com funcionalidades existentes;
* reutilização do código existente;
* prevenção de duplicação;
* testes;
* documentação.

---

# 4. Antes de modificar o código

Antes de realizar alterações relevantes:

1. identificar a estrutura do projeto;
2. identificar frontend;
3. identificar backend;
4. identificar banco de dados;
5. identificar Redis;
6. identificar filas;
7. identificar workers;
8. identificar APIs;
9. identificar autenticação;
10. identificar integrações externas;
11. identificar variáveis de ambiente;
12. identificar Docker;
13. identificar sistema de deploy;
14. verificar testes existentes;
15. verificar documentação existente.

Para alterações arquiteturais, utilizar o agente `architect`.

---

# 5. Não reescrever o sistema desnecessariamente

Nunca substituir uma implementação existente simplesmente porque outra abordagem parece melhor.

Antes de criar algo novo:

* procurar implementação existente;
* procurar funções reutilizáveis;
* procurar services;
* procurar repositories;
* procurar hooks;
* procurar componentes;
* procurar utilitários;
* procurar schemas;
* procurar migrations.

Preferir evolução incremental.

---

# 6. Banco de dados

Nunca modificar o banco diretamente sem verificar:

* models;
* schemas;
* migrations;
* relacionamentos;
* foreign keys;
* índices;
* constraints;
* seeds;
* queries existentes.

Alterações estruturais devem possuir migration quando o projeto utilizar migrations.

Nunca apagar dados ou tabelas sem autorização explícita.

---

# 7. Variáveis de ambiente

Nunca colocar secrets diretamente no código.

Exemplos:

* API keys;
* tokens;
* passwords;
* JWT secrets;
* credentials;
* connection strings;
* private keys.

Novas variáveis de ambiente devem:

1. ser adicionadas ao mecanismo de configuração do projeto;
2. possuir documentação;
3. possuir exemplo seguro;
4. nunca conter valores reais.

---

# 8. Segurança

Sempre considerar:

* autenticação;
* autorização;
* isolamento entre organizações;
* validação de entrada;
* SQL injection;
* XSS;
* CSRF quando aplicável;
* SSRF;
* exposição de secrets;
* logs contendo dados sensíveis;
* permissões de nodes;
* credenciais de integrações;
* acesso a workflows;
* acesso a execuções.

Nunca imprimir secrets nos logs.

---

# 9. Workflows

Um workflow deve ser tratado como uma estrutura composta por:

* trigger;
* nodes;
* conexões;
* configuração;
* contexto;
* execução;
* entrada;
* saída;
* tratamento de erro.

Antes de alterar o mecanismo de workflow, entender completamente o fluxo atual.

---

# 10. Nodes

Antes de criar um novo node:

1. procurar nodes semelhantes;
2. identificar a interface/base utilizada;
3. identificar sistema de registro;
4. identificar validação;
5. identificar execução;
6. identificar tratamento de erros;
7. identificar configuração;
8. identificar representação no frontend.

Um node novo deve seguir o padrão existente do projeto.

---

# 11. Redis e filas

Antes de alterar filas ou workers:

* identificar tecnologia utilizada;
* identificar nomes das filas;
* identificar produtores;
* identificar consumidores;
* identificar retries;
* identificar timeouts;
* identificar concorrência;
* identificar jobs;
* identificar tratamento de falhas.

Nunca criar uma segunda implementação de fila sem necessidade.

---

# 12. APIs

Novos endpoints devem seguir o padrão existente.

Documentar:

* método;
* URL;
* autenticação;
* parâmetros;
* body;
* resposta;
* erros;
* permissões.

---

# 13. Testes

Depois de alterações relevantes:

1. executar testes existentes;
2. executar lint;
3. executar type-check quando disponível;
4. executar build quando aplicável;
5. verificar erros de runtime quando possível.

Não considerar uma alteração concluída apenas porque o código parece correto.

---

# 14. Documentação

A documentação está em:

`/docs`

Qualquer alteração que modifique:

* arquitetura;
* banco;
* API;
* workflow;
* node;
* autenticação;
* configuração;
* infraestrutura;
* deploy;
* integração;

deve atualizar a documentação correspondente.

Nunca documentar comportamento que não existe.

---

# 15. Regra para documentação

Toda documentação deve distinguir claramente:

### Implementado

Funcionalidade confirmada pelo código.

### Parcial

Funcionalidade existente, mas incompleta.

### Planejado

Funcionalidade desejada, mas ainda não implementada.

### Desconhecido

Não foi possível confirmar pelo código.

Nunca transformar "planejado" em "implementado".

---

# 16. Mudanças arquiteturais

Para mudanças que afetem múltiplos componentes:

1. analisar a arquitetura;
2. identificar impactos;
3. identificar riscos;
4. propor solução;
5. verificar compatibilidade;
6. implementar;
7. testar;
8. atualizar documentação.

Utilizar o agente `architect` quando necessário.

---

# 17. Revisão

Antes de considerar uma tarefa concluída, verificar:

* segurança;
* regressões;
* duplicação;
* performance;
* tratamento de erros;
* compatibilidade;
* documentação;
* testes.

Utilizar o agente `reviewer` para revisões importantes.

---

# 18. Princípio de mínimo impacto

Sempre preferir:

> menor alteração necessária para resolver o problema corretamente.

Evitar:

* refatorações gigantes;
* alterações não relacionadas;
* mudanças de arquitetura sem necessidade;
* remoção de funcionalidades existentes.

---

# 19. Comunicação

Ao finalizar uma tarefa, informar:

### Alterações

O que foi modificado.

### Arquivos

Quais arquivos foram alterados.

### Testes

Quais testes foram executados.

### Riscos

Possíveis problemas ou pontos de atenção.

### Documentação


Toda alteração de arquitetura deve atualizar /docs.



Toda nova variável de ambiente deve ser adicionada à documentação.



Toda nova integração deve possuir documentação.

---

# 20. Regra final

Quando não souber algo:

NÃO INVENTE.

Investigue o código.

Se ainda não for possível determinar:

declare explicitamente a incerteza.
