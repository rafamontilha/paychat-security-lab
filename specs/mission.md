# Missão · PayChat Security Lab

> Auditoria de segurança em arquiteturas LLM aplicadas a marketplaces conversacionais

---

## Enunciado do projeto

Este projeto é o capstone da especialização **Applied AI Engineering**, com o título original *"LLM Security: Vulnerabilities and Defense Patterns"*. O enunciado define três entregáveis principais e estabelece critérios de avaliação em três níveis (Distinction, Proficient, Developing). O PayChat Security Lab é construído para atender ao nível Distinction.

**Entregável 1 — LLM Vulnerability Assessment**
Construir uma aplicação de teste que integre um LLM tanto por meio de arquiteturas baseadas em API quanto em modelos embarcados. Testar sistematicamente a aplicação contra pelo menos seis categorias de vulnerabilidades: prompt injection (direta e indireta), insecure output handling, model theft por meio de extraction queries, sensitive information disclosure, insecure plugin design e excessive agency. Documentar cada técnica de ataque, seu sucesso ou falha, e a causa raiz de cada vulnerabilidade.

**Entregável 2 — Defense Pattern Implementation**
Implementar padrões de defense in depth para cada vulnerabilidade identificada: sanitização de entrada e separação de prompt e dados para defesa contra injeção, validação de saída e sandboxing para insecure output handling, rate limiting e output perturbation para prevenção de model theft, classificação de dados e filtragem de saída para information disclosure, e permission boundaries para segurança de plugins. Testar cada defesa contra os vetores de ataque originais e documentar o risco residual remanescente.

**Entregável 3 — Multi-Model Security Architecture Analysis**
Analisar as implicações de segurança de arquiteturas com múltiplos modelos AI encadeados em pipeline. Documentar como superfícies de vulnerabilidade compostas emergem quando modelos são orquestrados juntos. Avaliar as diferenças de segurança entre tipos de aplicação API-based, embedded model e multi-model. Produzir um relatório de auditoria de segurança adequado para audiência de liderança técnica que inclua threat model, vulnerability findings, defense implementations, residual risks e prioritized remediation recommendations.

**Critério Distinction (nível alvo do PayChat Security Lab):**
- Avaliação cobre pelo menos seis categorias de vulnerabilidade com técnicas de ataque documentadas e análise de causa raiz
- Defense patterns demonstram redução mensurável de attack success rate com quantificação de risco residual
- Relatório de auditoria inclui threat model, análise multi-model e remediações priorizadas adequadas para revisão executiva

---

## Declaração de missão

**Construir três arquiteturas de um marketplace conversacional, atacá-las sistematicamente e medir, sob critérios reproduzíveis, qual arquitetura sustenta melhor a confiança operacional em um contexto de payments.**

Implementar três variantes funcionalmente equivalentes de um assistente conversacional para marketplace — API-based proprietário, embedded open-source e multi-model pipeline — executar uma avaliação sistemática contra as seis categorias de vulnerabilidade definidas no enunciado, implementar defesas em profundidade em cada camada e produzir um relatório de auditoria com threat model, matriz comparativa de evidências e remediações priorizadas para audiência de liderança técnica em payments.

---

## O que estamos construindo

Um laboratório de segurança que serve como portfólio técnico e como referência arquitetural para decisões de design seguro de aplicações LLM em domínios de alto risco financeiro.

O projeto entrega três artefatos principais:

1. **Três aplicações funcionalmente equivalentes** de um marketplace conversacional com agente ReAct, implementadas sob arquiteturas distintas para isolar variáveis de segurança.
2. **Matriz de evidências 3 × 7**, executada antes e depois da implementação de defesas, totalizando 42 pontos quantitativos sobre redução de attack success rate. As seis categorias do enunciado viram sete colunas porque prompt injection direta e indireta são medidas como vetores separados.
3. **Relatório de auditoria executivo** com threat model formal, análise comparativa entre arquiteturas e remediações priorizadas por CVSS e impacto de negócio.

---

## Por que este projeto importa

Aplicações LLM em payments operam sob restrições que sistemas tradicionais já endereçam há décadas — segregação de funções, princípio do menor privilégio, defense in depth, auditabilidade. A indústria está aplicando essas práticas a uma classe de software cujo comportamento é probabilístico, cujas fronteiras entre instrução e dado são fluidas e cujos vetores de ataque ainda estão sendo catalogados.

O projeto responde a três perguntas concretas que líderes de engenharia de IA em payments precisam responder:

- **Qual arquitetura LLM resiste melhor a cada classe de ataque?** Não há resposta única — há trade-offs entre soberania de dados, custo operacional, latência e superfície de ataque. O projeto torna esses trade-offs explícitos e mensuráveis.
- **Quais defesas funcionam, e quanto risco residual permanece após implementá-las?** A literatura propõe dezenas de defesas com efetividade variável. O projeto mede empiricamente, no mesmo cenário, qual combinação produz a maior redução de risco.
- **Como traduzir vulnerabilidades técnicas em impacto de negócio?** Account takeover, vendor impersonation e bypass de detecção antifraude são os termos que importam para um CISO de payments. O relatório faz esse mapeamento explícito.

---

## Quem é a audiência

O relatório final é redigido para ser legível e acionável por:

- **CISO e líderes de segurança** em fintechs, adquirentes, marketplaces e instituições financeiras
- **Líderes de engenharia de IA** que precisam justificar escolhas arquiteturais para stakeholders não-técnicos
- **Times de compliance e risco** que precisam mapear vulnerabilidades LLM a frameworks regulatórios (LGPD, PCI-DSS, resoluções do BCB)
- **Engenheiros de plataforma** que vão herdar a operação dessas aplicações em produção

O entregável evita jargão acadêmico desnecessário sem sacrificar rigor técnico, e separa explicitamente o executive summary do apêndice técnico reprodutível.

---

## O que está fora do escopo

Para manter o foco e a profundidade exigidos pelo nível Distinction da avaliação, o projeto deliberadamente não cobre:

- **Ataques em tempo de treinamento** (backdoor, data poisoning, sleeper agents) — exigem acesso ao processo de treinamento, fora do controle de quem deploya o modelo. Mencionados como recomendação de governança no relatório.
- **Ataques multimodais** (visual jailbreaking, cross-modality) — exigem modelos multimodais e cenários que não fazem parte do escopo de um chat de marketplace.
- **Compliance regulatório formal** (PCI-DSS, SOC 2) — o projeto é uma análise de segurança aplicada, não uma certificação. A relação com compliance é discutida no relatório como recomendação, não como entregável.
- **Implementação de marketplace real** — o sistema é o mínimo necessário para sustentar os ataques. Não há frontend completo, fluxo de pagamento real ou integrações externas.

---

## Princípios orientadores

**Security by design** — defesas são implementadas como decisões arquiteturais, não como camadas adicionadas após o fato.

**Red team first** — toda defesa é resposta a um ataque documentado e reproduzível. Nenhuma defesa é implementada por suposição.

**Defense in depth** — múltiplas camadas independentes para que o risco residual seja resultado da combinação, não de uma única barreira.

**Evidência quantitativa** — cada ataque e cada defesa é documentado com taxa de sucesso antes e depois, permitindo comparações reproduzíveis.

**Reprodutibilidade** — todo o código é público, o ambiente roda via Docker Compose, e qualquer pessoa com a infraestrutura mínima descrita no README pode reexecutar a matriz 3 × 7.

**Executive-ready** — o relatório final é estruturado para que liderança técnica e não-técnica encontre o que precisa nos primeiros minutos, com apêndice técnico para quem precisa reproduzir os achados.

---

## Critério de sucesso

O projeto será considerado concluído quando os seguintes itens estiverem entregues:

- [ ] Três variantes do marketplace operacionais sob a mesma interface funcional
- [ ] Matriz 3 × 7 baseline preenchida com evidências reproduzíveis por vetor (prompt injection direta e indireta como colunas separadas)
- [ ] Defesas implementadas em cinco camadas (input, output, plugin, anti-theft, disclosure)
- [ ] Matriz 3 × 7 pós-defesa com cálculo quantitativo de redução de attack success rate, exceto model theft — onde a defesa é rate limiting (controle de volume, não de conteúdo) e a redução de ASR é marcada NÃO-APLICÁVEL com justificativa metodológica no relatório
- [ ] Threat model formal STRIDE aplicado aos quatro atores e às três arquiteturas
- [ ] Análise de vulnerabilidades compostas no pipeline multi-model
- [ ] Relatório executivo com remediações priorizadas por CVSS e impacto de negócio
- [ ] Repositório público no GitHub com README, guia de reprodução e notebook Jupyter consolidado
- [ ] Publicação no LinkedIn como projeto de portfólio

---

*Documento vivo · v4 · matriz 3×7 e caveat de model theft alinhados ao executado*