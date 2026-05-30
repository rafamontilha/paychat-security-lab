# Requirements — Fase 12: Publicação e portfólio

## Scope

### In scope
- README raiz enriquecido: missão em 3 parágrafos, badges (CI, license, docs), diagrama de arquitetura, link para o relatório, créditos, sem placeholders
- Licenciamento dual: `LICENSE` MIT (código) na raiz + `report/LICENSE` CC BY 4.0 (relatório)
- Draft do post LinkedIn em `report/linkedin_post.md`: copy de ~200 palavras + imagem do heatmap 3×7 identificada
- Atualização do `CHANGELOG.md` com a Fase 12
- PR `fase-12-publicacao` → `main`
- Tag anotada `v1.0.0` criada e empurrada ao `origin` pelo Claude

### Out of scope
- **Toggle de visibilidade do repositório** — ação sua (repo já está `PUBLIC`; apenas confirmar)
- **Publicação efetiva do post no LinkedIn** — ação sua; o entregável do Claude é o draft, não a publicação
- **Entrada "Projetos" no perfil LinkedIn** — ação manual sua
- Reescrita do conteúdo do relatório ou dos notebooks (entregues na Fase 11)
- Novas figuras/visualizações — reaproveitam-se as de `report/figures/`

## Key Decisions

| Decisão | Escolha | Rationale |
|---|---|---|
| Modelo de licença | MIT (código) + CC BY 4.0 (relatório) | Código permissivo para reúso; relatório exige atribuição. Padrão para portfólio técnico + conteúdo. |
| Fronteira de execução | Claude vai até a release (tag `v1.0.0` empurrada); público + LinkedIn são manuais | Publicar e tornar público são ações externas/irreversíveis — confirmação humana antes do passo final. |
| Escopo LinkedIn | Draft completo (copy 200 palavras + imagem do heatmap) | Reduz o atrito da sua etapa manual a revisar e clicar publicar. |
| Imagem do post | `report/figures/heatmap_baseline.png` | Heatmap da matriz 3×7 baseline; comunica o eixo central do projeto em uma figura. |
| Diagrama do README | Mermaid das 3 variantes ou reúso de `report/assets/variante_c_flow.svg` | Evita criar asset novo; aproveita o SVG existente da Variante C. |
| Versionamento | Tag anotada `v1.0.0` em `main` | Marca a entrega completa das Fases 1–12; semântica de release inicial estável. |

## Context

### Mission alignment
Cumpre o último item do critério de sucesso da missão ("Repositório público no GitHub com README, guia de reprodução e notebook consolidado" + "Publicação no LinkedIn como projeto de portfólio"). Reforça o princípio **Executive-ready**: o README é a porta de entrada que leva liderança técnica do resumo ao relatório PDF em poucos cliques, e o princípio **Reprodutibilidade** ao manter as instruções de clone limpas e corretas.

### Tech-stack alignment
Usa a camada de Entrega definida no `tech-stack.md`: GitHub Actions (`ci.yml`) para a badge de CI, Markdown + Pandoc para o relatório já gerado em PDF. Não introduz dependências novas. O diagrama reaproveita assets de `report/`.

### Dependencies
- **Fase 11** concluída: `report/SECURITY_AUDIT.pdf`, `report/SECURITY_AUDIT.md`, `report/figures/*` e notebooks `00–03` já existem (verificado).
- `gh` autenticado como `rafamontilha`; remote `origin` = `github.com/rafamontilha/paychat-security-lab` (verificado).
- Working tree tem mods não-commitados (`.env.example`, `README.md`, `.claude/`, `evidence/`, `scripts/recollect_*`) — avaliar o que entra no commit da release antes de tagear.
