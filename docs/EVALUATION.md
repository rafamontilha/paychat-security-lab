# Guia de Avaliação Externa — PayChat Security Lab

> Como solicitar e estruturar avaliação independente deste projeto.
> Quatro trilhas, cada uma com níveis progressivos (L0 → L3) e critérios *done-when* binários,
> no mesmo padrão phase-gated do roadmap. Um avaliador escolhe a trilha pela pergunta que quer responder.

> **Estado pós-Fase 13:** os pré-requisitos da **Trilha 1 (L0–L1)** — significância por célula (Fisher
> exato + FDR), correção de narrativa, kappa de Cohen — e da **Trilha 3 (L0, L2)** — contagens em CSV
> commitado, critério "dentro do IC", caminho sem-API — estão **concluídos** (ver `LIMITATIONS.md` com
> status por item). A Trilha 2 (red-team) está liberada para abertura.

| Trilha | Pergunta que responde | Audiência | Rigor | Atrito p/ avaliador |
|---|---|---|---|---|
| **1. Metodológica** | O desenho experimental é sólido? | Pesquisadores / revisores acadêmicos | Alto | Alto |
| **2. Red-team** | Alguém consegue furar a Variante C? | Red-teamers, LLM security | Alto | Médio |
| **3. Reprodutibilidade** | A matriz 3×7 regenera de clean clone? | Engenheiros / praticantes | Médio | **Baixo** |
| **4. Portfólio** | Lê como trabalho sênior? | Liderança técnica / payments | Baixo | Baixo |

A regra geral: **quanto mais específico e falsificável o pedido, mais avaliação real você recebe.**
"Avalie meu projeto" é ignorável; "reproduza a célula `b_pi_direct` e me diga se o IC bate" não é.

---

## Trilha 1 — Revisão metodológica

**Saída:** preprint no arXiv + DOI no Zenodo → artefato citável → divulgação.

### L0 — Pré-requisitos (antes de pedir qualquer revisão)
- [x] `LIMITATIONS.md` publicado na raiz (lista honesta de fraquezas conhecidas — ver arquivo). *(Fase 13)*
- [x] Cada alegação quantitativa do relatório referencia evidência versionada.
- [x] Teste de significância por célula definido e documentado (`scripts/compute_significance.py`). *(Fase 13)*

**Done when:** um leitor externo consegue, só pelo README + `LIMITATIONS.md`, dizer o que o projeto afirma e onde ele admite não saber.

### L1 — Auto-revisão dirigida — **concluída na Fase 13**
- [x] Substituir o "olhômetro de sobreposição de IC" por **teste de duas proporções por célula** (Fisher exato); flag de significância por célula (`report/significance.csv`).
- [x] Aplicar **correção de comparações múltiplas** (Benjamini-Hochberg) sobre as 21 células.
- [x] Reportar **concordância heurística-vs-manual** (kappa de Cohen) na amostra de 10% (`report/kappa_summary.csv`). *Achado:* a heurística de `ioh` foi reprovada (κ=0) e re-pontuada (OWASP LLM02) — `a_ioh` caiu de 67% para 3%.
- [x] Reescrever a narrativa de "wins" para **apenas** as células que passam o teste (`b_pi_direct` é a única inequívoca).

**Done when:** nenhuma alegação de redução/regressão no relatório contradiz seu próprio teste de significância. *(Verificado por `scripts/check_significance_consistency.py`, merge blocker.)*

### L2 — Preprint citável (semana 2–3)
- [ ] Converter o `SECURITY_AUDIT.md` em formato de paper (abstract, método, resultados, limitações, trabalho futuro).
- [ ] Submeter ao **arXiv** (cs.CR). Sem revisão por pares, mas data e DOI público.
- [ ] Ativar a integração **GitHub → Zenodo**: criar release → Zenodo cunha um DOI versionado para o repo. Adicionar badge do DOI no README e a citação sugerida (já existe no `report/LICENSE`).

**Done when:** o projeto tem DOI; `CITATION.cff` na raiz; arXiv ID no README.

### L3 — Revisão por pares de verdade (mês 1–3)
- [ ] Submeter a um **workshop** de segurança/ML (formato curto: 4–8 páginas). Alvos plausíveis: workshops de AI security / trustworthy ML em conferências maiores, ou venues do ecossistema OWASP.
- [ ] Solicitar revisão direcionada de 1–2 pesquisadores via e-mail frio com um *ask* específico (não "leia tudo", mas "o argumento do Cenário 3 sustenta a alegação de não-comutatividade?").

**Done when:** ≥2 revisões independentes recebidas e endereçadas (aceitas ou refutadas por escrito).

---

## Trilha 2 — Validação red-team

**Saída:** alguém tenta quebrar a Variante C e reporta. O pedido mais alinhado à sua tese central.

### L0 — Instrumentar o convite
- [x] Template de issue **"Red-team / break a defense"** ativo (`.github/ISSUE_TEMPLATE/`). *(Fase 13)*
- [x] `LIMITATIONS.md` lista explicitamente os vetores que você **espera** que furem (model_theft, Cenário 3, plugin/agency em B/C) — isso é um mapa para o atacante, e é de propósito.

**Done when:** existe um caminho de 1 clique para alguém abrir "quebrei X".

### L1 — Desafio público enquadrado
- [ ] Issue fixada: **"Break Variant C — find a payload that defeats the Guard→ReAct→Presidio pipeline that the threat model doesn't already cover."** Critério de sucesso explícito (exfiltração de PII real OU ação não autorizada OU contorno de ambas as camadas).
- [ ] Postar onde red-teamers vivem: **OWASP GenAI Slack** (iniciativa de Red Teaming), **r/netsec**, **Show HN**, comunidades de LLM security. Enquadramento: "capstone buscando crítica adversarial", não "auditoria definitiva".

**Done when:** ≥3 tentativas independentes registradas (furando ou confirmando a cobertura).

### L2 — Cenário 3 como alvo nomeado
- [ ] Documentar o Cenário 3 (exfiltração via canal lateral) como **desafio reproduzível**: payload, setup, e o critério de "ASR cega" que o torna invisível à matriz.
- [ ] Pedir especificamente: alguém constrói uma **bateria** de N payloads de canal lateral e mede uma taxa — convertendo o *existence proof* em número (ver `LIMITATIONS.md` item 3; o Cenário 3 foi **reescopado** como estudo de caso na Fase 13, e medir a taxa é exatamente este convite).

**Done when:** o Cenário 3 tem uma taxa de sucesso medida por terceiro (ou uma refutação fundamentada).

### L3 — Tooling adversarial automatizado
- [ ] Convidar runs de **Garak** / **PyRIT** contra as três variantes (já no seu backlog pós-MVP) por contribuidores externos.
- [ ] Aceitar PRs que adicionem payloads ao harness (`red_team/harness.py`) sob o mesmo schema de evidência.

**Done when:** ≥1 ferramenta externa rodou contra o sistema e os resultados entraram no `evidence/`.

---

## Trilha 3 — Reprodutibilidade (seu pedido mais forte)

**Saída:** terceiro regenera a matriz de clean clone. Você construiu para isso.

### L0 — Definir "reproduzir" honestamente — **concluída na Fase 13**
- [x] Documentar que, para provedores black-box (Anthropic, Together), reprodução significa **"dentro do IC95%"**, NÃO "números idênticos" (`specs/tech-stack.md` §"Reprodutibilidade e fixação de runtime").
- [x] Registrar a **string exata do modelo + data do run** de cada provedor (`claude-sonnet-4-6`, `Llama-3.3-70B-Instruct-Turbo`, `Llama-Guard-4-12B`) no `tech-stack.md`.
- [x] **Expor as contagens agregadas em CSV commitado.** `report/audit_counts.csv` (`finding_id, variant, category, succ_base, n_base, succ_post, n_post`, 21 linhas) versionado — destrava a reprodução sem-API e os testes de significância sem expor payloads brutos.

**Done when:** o critério de sucesso da reprodução é "células dentro do IC", não "diff zero"; e `report/audit_counts.csv` (21 linhas, inteiros) está versionado. ✅

### L1 — Desafio de reprodução
- [x] Template de issue **"Reproduction report"** ativo. *(Fase 13)*
- [ ] Issue fixada: **"Reproduce the 3×7 matrix from a clean clone and report the deltas (per cell, within-CI or not)."**
- [ ] Garantir que o `make` de ponta a ponta (env → ataques → notebook 00 → figuras) roda de clone limpo com só as chaves de API.

**Done when:** ≥1 reprodução independente reporta deltas por célula.

### L2 — Reprodução parcial barata — **habilitada na Fase 13**
- [x] Caminho **sem custo de API**: re-rodar o notebook 00 sobre os **CSVs commitados** (`report/security_audit_matrix.csv`, `report/audit_counts.csv`) — regenera figuras/tabelas e os testes de significância sem chamar LLM.
- [ ] CI roda `check_audit_coverage.py` (21/21) — exponha esse resultado como badge.

**Done when:** alguém sem chaves de API, a partir de um clone limpo, regenera todas as figuras e a tabela de significância e confirma 21/21.

### L3 — Reprodução conceitual independente
- [ ] Convidar uma re-implementação parcial (ex.: outra pessoa monta a Variante C com outro modelo base e checa se o Cenário 3 reaparece) — testa se o achado é do *design*, não do seu setup.

**Done when:** o achado de não-comutatividade é confirmado (ou negado) em um setup independente.

---

## Trilha 4 — Credibilidade de portfólio

**Saída:** o trabalho lê como sênior para liderança técnica de payments.

### L0 — README como porta de entrada
- [ ] Missão em 3 parágrafos, badges, diagrama, link do relatório, créditos (já no plano da Fase 12).
- [ ] Badge de DOI (da Trilha 1) e badge de CI verde.

**Done when:** liderança chega do resumo ao PDF em ≤2 cliques.

### L1 — Post de lançamento
- [ ] Publicar o `report/linkedin_post.md` (já redigido) com a figura do heatmap.
- [ ] Enquadrar o achado central (não-comutatividade) como a tese, não a stack como a feature.

**Done when:** post publicado; entrada em "Projetos" do perfil.

### L2 — Outreach direcionado
- [ ] 5–10 mensagens diretas a arquitetos de IA / líderes de segurança em fintechs, com um *ask* específico (feedback sobre uma decisão, não "olha meu projeto").
- [ ] Levar 1 achado concreto (ex.: "defense-in-depth pode não ser comutativa — aqui está o estudo de caso") como gancho de conversa.

**Done when:** ≥3 conversas qualificadas iniciadas.

### L3 — Autoridade composta
- [ ] Transformar 1 achado em conteúdo standalone (post técnico / talk em meetup).
- [ ] Conectar ao próximo projeto (Agentic Commerce Security Lab) como continuidade de uma linha de pesquisa, não esforços isolados.

**Done when:** existe uma narrativa pública de linha de pesquisa, não um repo solto.

---

## Sequência recomendada (ordem entre trilhas)

As trilhas não são paralelas; há uma ordem que maximiza retorno e minimiza exposição prematura:

1. **Trilha 1, L0–L1 primeiro (instrumentar + auto-revisão).** ✅ **Concluída na Fase 13.** Resolver os bloqueadores de significância *antes* de qualquer exposição pública. Expor com a assimetria de significância não corrigida é o maior risco reputacional — um crítico derruba "a defesa aumentou o ataque" e a thread vira sobre isso.
2. **Trilha 3 em paralelo (reprodutibilidade).** Barata, é seu pedido mais forte, e uma reprodução bem-sucedida é a melhor defesa contra ceticismo. Caminho sem-API (L2) já habilitado.
3. **Trilha 4, L0–L1 (README + LinkedIn).** Audiência morna, baixo rigor — bom para tração inicial enquanto o resto amadurece.
4. **Trilha 2 (red-team) e Trilha 1, L2–L3 (arXiv/peer review).** A jogada de credibilidade alta, feita por último — depois que o repo aguenta escrutínio e o DOI existe.

**Regra de ouro entre trilhas:** não abra a Trilha 2 (convite a furar) antes da Trilha 1, L1 (significância corrigida). Como a L1 está concluída (Fase 13), a Trilha 2 está liberada.

---

## Decisão ratificada: idioma dos artefatos (bilíngue)

Ratificado na Fase 13:
- **`CONTRIBUTING.md` + templates de issue:** em **inglês** (interface do contribuidor externo, convenção GitHub).
- **`LIMITATIONS.md` + este guia + relatório:** em **português** (acompanham o relatório PT).
- **Preprint arXiv:** considerar versão em inglês para alcance — ou PT com abstract em inglês (decisão da Trilha 1 L2).
