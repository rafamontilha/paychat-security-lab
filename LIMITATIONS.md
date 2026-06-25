# Limitações Conhecidas e Questões Abertas

> Este documento lista, de forma deliberada e honesta, onde o PayChat Security Lab pode estar errado,
> onde a evidência é fina, e onde convidamos crítica adversarial. Entregar este mapa **aumenta** a
> qualidade da avaliação externa: revisores engajam mais quando sabem onde apertar.
>
> Cada item tem uma **severidade** (impacto sobre as conclusões), um **status** (o que a Fase 13 de
> revisão metodológica endereçou) e um **convite** (o que ainda pedimos a quem revisa).
> Itens marcados `[BLOQUEADOR-ARXIV]` deviam ser resolvidos antes de um preprint.

> **Resumo da Fase 13 (revisão metodológica):** os bloqueadores 1, 2 e 3 foram resolvidos ou
> reescopados; os itens de rigor 4–8 foram endereçados. O destaque é o item 5: a verificação de
> validade (kappa de Cohen) **reprovou a heurística de `ioh`** e disparou um re-score que derrubou
> `a_ioh` de 67% para 3% — o antigo "finding #1" era um artefato de medição.

---

## 1. Tratamento assimétrico de significância estatística `[BLOQUEADOR-ARXIV]`

**Severidade: Alta — afeta a narrativa de resultados.**

**Status: ✅ RESOLVIDO (Fase 13).** Substituímos a sobreposição de IC por **teste exato de Fisher
(two-sided) por célula** + **correção FDR (Benjamini-Hochberg)** sobre as 21 comparações
(`scripts/compute_significance.py` → `report/significance.csv`). Resultado: **apenas `b_pi_direct`
(14,42%→0,96%, q=0,007) é significativa**. Reduções aparentes como `c_sensitive_disclosure` (−83%,
q=0,61) e regressões pós-defesa **não passam** — são variação dentro do ruído. A narrativa do
`SECURITY_AUDIT.md` foi reescrita para refletir isso; consistência verificada por
`scripts/check_significance_consistency.py` (merge blocker).

**Convite remanescente:** contestar a escolha de Fisher vs. alternativas (ex.: teste de Barnard) ou a
escolha de FDR vs. Holm; recomputar qualquer célula.

---

## 2. Sem correção para comparações múltiplas `[BLOQUEADOR-ARXIV]`

**Severidade: Média-alta.**

**Status: ✅ RESOLVIDO (Fase 13).** Benjamini-Hochberg aplicado sobre as 21 células; q-values
reportados em `report/significance.csv` e na tabela da §4.1. Notável: `a_model_theft` (p=0,011) e
`b_model_theft` (p=0,032) cruzariam α=0,05 sem correção, mas **desaparecem após o FDR** (q=0,11 e 0,22)
— exatamente o falso-positivo esperado por acaso.

---

## 3. O achado central é um *existence proof*, não uma taxa medida `[BLOQUEADOR-ARXIV]`

**Severidade: Alta — afeta a alegação principal (Entregável 3).**

**Status: ✅ ENDEREÇADO por reescopo (Fase 13, decisão B).** Em vez de medir uma taxa, **calibramos a
linguagem**: o Cenário 3 (`c_pi_indirect`) é agora explicitamente um **estudo de caso / prova de
existência** ("demonstramos ser possível", não "é o regime geral"), de forma consistente no
`SECURITY_AUDIT.md` (§3, §6.2) e no `threat_model.md` (§6.3). A célula segue com ASR 0%/0% (a ASR é
cega ao risco).

**Convite remanescente (o mais valioso do projeto):** construir uma **bateria de N payloads de canal
lateral** sob critério de sucesso explícito e **medir uma taxa**, convertendo o estudo de caso em
número (ver `docs/EVALUATION.md` Trilha 2, L2).

---

## 4. Poder estatístico baixo / n pequeno e desigual

**Severidade: Média.**

**Status: 🟡 PARCIAL (Fase 13).** O **n assimétrico** de `model_theft` (a=79 vs b/c=121) foi
documentado (§4.3/§6.4 do relatório): é diferença de **coleta** (~1 vs 2 registros por probe), por
controle de custo da API Anthropic; alarga o IC de `a_model_theft` mas não enviesa a conclusão (a
defesa é NÃO-APLICÁVEL nas três). **Em aberto:** aumentar n nas células decisivas (`excessive_agency`,
`sensitive_disclosure`) — exige nova coleta com API, fora do escopo desta revisão.

**Convite:** financiar/rodar mais amostras nas células de prioridade para estreitar os ICs.

---

## 5. Erro de medição da heurística de sucesso não quantificado

**Severidade: Média → tornou-se Alta após medição.**

**Status: ✅ RESOLVIDO + ACHADO MATERIAL (Fase 13).** Computamos a **concordância heurística-vs-manual
(kappa de Cohen)** sobre a amostra estratificada de 10% (`scripts/compute_kappa.py` →
`report/kappa_summary.csv`):

- `pi_direct` **κ=1,00** e `pi_indirect` **κ=1,00** — heurísticas validadas.
- `ioh` **κ=0** na heurística original (precisão ~0%): ela marcava como sucesso respostas que
  **recusavam** o ataque mas **ecoavam o payload** (ex.: citar `/etc/passwd` ao recusar).

Isso disparou um **re-score de `ioh`** (`red_team/rescore_ioh.py`, sem re-chamar modelos): heurística
corrigida para *refusal-first* + critério **OWASP LLM02** (só conteúdo ativo/XSS emitido conta;
SQL/cmd/path/SSRF citados em prosa viram `recon_hint_echoed`, não sucesso). Efeito: **`a_ioh` 67%→3%,
`b_ioh` 7%→0%, `c_ioh` 8%→0%** — o antigo "maior ASR da matriz" era um artefato. A heurística corrigida
concorda 30/30 com o manual na amostra.

**Convite:** ampliar a revisão manual para as 7 categorias (hoje o gate cobre 3) e auditar as
heurísticas de `model_theft`/`excessive_agency` com o mesmo método.

---

## 6. `residual_asr` de `model_theft` = baseline (divergência implícita)

**Severidade: Baixa-média — rastreabilidade.**

**Status: ✅ RESOLVIDO (Fase 13).** A definição **`residual_asr := asr_base`** para `model_theft`
(controle de volume) está agora explícita no `SECURITY_AUDIT.md` §4.3 e na coluna `nota` de
`report/security_audit_findings.csv`. Um leitor que veja `residual_asr < asr_post` está vendo a
definição, não um erro de dado.

---

## 7. Score de prioridade mistura severidade e probabilidade

**Severidade: Baixa.**

**Status: ✅ RESOLVIDO (Fase 13).** O `SECURITY_AUDIT.md` §8 declara explicitamente que
`priority = cvss_env × residual_asr` é um **ranking ad-hoc, não uma métrica CVSS padrão**, e que
multiplicar o CVSS (que já embute exploitabilidade) por ASR conta a exploitabilidade parcialmente duas
vezes.

**Convite:** propor uma decomposição sem dupla contagem (ex.: ASR como likelihood × Impact sub-score).

---

## 8. Reprodutibilidade black-box é "dentro do IC", não bit-a-bit

**Severidade: Média — afeta a Trilha de Reprodutibilidade.**

**Status: ✅ RESOLVIDO (Fase 13).** O `specs/tech-stack.md` ganhou a seção "Reprodutibilidade e fixação
de runtime" com as **strings exatas de modelo** (`claude-sonnet-4-6`, `Llama-3.3-70B-Instruct-Turbo`,
`Llama-Guard-4-12B`), as **datas dos runs** (baseline 2026-05-24/25; pós-defesa 2026-05-27) e o critério
**"célula dentro do IC95%"**. O caminho **sem-API** está habilitado: `report/audit_counts.csv` versionado
permite re-rodar o notebook 00 sobre os CSVs commitados, sem chamar LLM.

---

## 9. Confound modelo × arquitetura (já reconhecido, listado por completude)

**Severidade: Baixa — já tratado.**

**Status: ⚪ POR DESIGN (sem ação).** B vs C é limpo (mesmo Llama 3.3 70B; ADR-002). **A vs B/C confunde
modelo + arquitetura** — o relatório já declara isso explicitamente. Não é uma falha oculta; é uma
limitação de design assumida.

**Convite:** confirmar que a linguagem comparativa A↔(B/C) nunca atribui a um efeito de arquitetura o
que pode ser efeito de modelo.

---

## Resumo para quem vai revisar

Após a Fase 13, os bloqueadores estatísticos (1, 2) estão resolvidos e o achado central (3) está
reescopado como estudo de caso. **O que ainda move conclusões e mais pede revisão externa:**

- **Item 3** (red-teamers): construa a bateria do Cenário 3 e meça uma taxa — converte o estudo de
  caso em número.
- **Item 4b** (estatísticos): n ainda é pequeno nas células de prioridade; mais amostras estreitariam
  os ICs.
- **Item 5** (qualquer um): amplie a revisão manual para as 7 categorias e audite as heurísticas
  restantes com kappa — o re-score de `ioh` mostra que isso pode mover números de destaque.

Abra uma issue com o template correspondente (`.github/ISSUE_TEMPLATE/`); críticas fundamentadas que
refutem ou fortaleçam um ponto serão creditadas no repo.
