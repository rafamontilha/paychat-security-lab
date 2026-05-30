# Plan — Fase 12: Publicação e portfólio

Branch: `fase-12-publicacao` (já ativa). Escopo de execução do Claude vai **até a release** (cria e empurra a tag `v1.0.0`); tornar o repositório público e publicar no LinkedIn são ações suas (handoff manual no grupo 5).

## 1. Enriquecer o README raiz
- [ ] Adicionar missão em 3 parágrafos (escopo, achados principais, audiência) — reaproveitar de `specs/mission.md`
- [ ] Adicionar badges no topo: CI (GitHub Actions `ci.yml`), license (MIT), docs/relatório (link para `report/SECURITY_AUDIT.pdf`)
- [ ] Adicionar diagrama de arquitetura: bloco Mermaid das 3 variantes (A/B/C) **ou** embutir/linkar `report/assets/variante_c_flow.svg`
- [ ] Substituir o placeholder `<seu-usuario>` por `rafamontilha` em todas as URLs de clone
- [ ] Adicionar seção "Relatório de auditoria" com link para `report/SECURITY_AUDIT.md` e o PDF
- [ ] Adicionar seção "Créditos" (autoria, especialização Applied AI Engineering, link LinkedIn)
- [ ] Adicionar badge/menção de license referenciando os arquivos do grupo 2

## 2. Licenciamento (MIT + CC BY 4.0)
- [ ] Criar `LICENSE` (MIT) na raiz, cobrindo o código — ano 2026, titular Rafael Montilha
- [ ] Criar `report/LICENSE` (CC BY 4.0) cobrindo o relatório e figuras
- [ ] Documentar a divisão de licença em uma nota no README ("Código sob MIT; relatório sob CC BY 4.0")

## 3. Draft do LinkedIn (copy + imagem)
- [ ] Selecionar a imagem do heatmap: `report/figures/heatmap_baseline.png` (matriz 3×7 baseline); alternativa `report/figures/matrix_baseline_post_reduction.png`
- [ ] Redigir copy de ~200 palavras com: título do projeto, escopo (3 arquiteturas × 7 vetores), achados principais, stack (Claude Sonnet 4.6, Llama 3.3 70B, Llama Guard 4), link do repo
- [ ] Salvar o draft em `report/linkedin_post.md` (texto + caminho da imagem escolhida) para sua revisão
- [ ] Sugerir texto curto da entrada "Projetos" do perfil LinkedIn no mesmo arquivo

## 4. Release v1.0.0 (Claude executa)
- [ ] Garantir que README + LICENSE + draft estejam commitados na branch
- [ ] Atualizar `CHANGELOG.md` com a entrada da Fase 12 (via skill `changelog` ou manual)
- [ ] Abrir PR `fase-12-publicacao` → `main` e mergear após validação
- [ ] Criar a tag anotada `v1.0.0` apontando para o commit final em `main`
- [ ] Empurrar a tag ao `origin` (`git push origin v1.0.0`)
- [ ] (Opcional) Criar GitHub Release a partir da tag com notas resumindo as 12 fases

## 5. Handoff manual (você executa)
- [ ] Confirmar/garantir visibilidade **pública** do repositório (verificado como `PUBLIC` na criação da spec — apenas confirmar)
- [ ] Revisar e publicar o post no LinkedIn com a imagem do heatmap
- [ ] Adicionar a entrada em "Projetos" no perfil LinkedIn
