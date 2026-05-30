# Validation — Fase 12: Publicação e portfólio

## Automated checks
- [ ] [auto] `grep -R "<seu-usuario>" README.md` não retorna nada (placeholder removido)
- [ ] [auto] Todos os links de arquivo do README resolvem: `report/SECURITY_AUDIT.pdf`, `report/SECURITY_AUDIT.md` e o asset do diagrama existem no disco
- [ ] [auto] `test -s LICENSE && test -s report/LICENSE` — ambos os arquivos de licença existem e são não-vazios
- [ ] [auto] `test -s report/SECURITY_AUDIT.pdf` — PDF do relatório presente e não-vazio
- [ ] [auto] `test -s report/linkedin_post.md` — draft do post existe
- [ ] [auto] `git tag -l v1.0.0` retorna `v1.0.0` e `git ls-remote --tags origin v1.0.0` confirma a tag no remoto
- [ ] [auto] CI (`.github/workflows/ci.yml`: ruff + black + mypy) passa verde no PR `fase-12-publicacao` → `main`

## Manual smoke tests
- [ ] [manual] Abrir `https://github.com/rafamontilha/paychat-security-lab` no navegador: README renderiza, badges carregam, diagrama de arquitetura aparece, missão em 3 parágrafos e seção de créditos visíveis
- [ ] [manual] Clicar no link do relatório no README → `report/SECURITY_AUDIT.pdf` abre/baixa corretamente
- [ ] [manual] Abrir a URL pública do repo em janela anônima (sem login) → carrega normalmente
- [ ] [manual] Ler `report/linkedin_post.md`: copy ~200 palavras coerente, imagem do heatmap referenciada (`report/figures/heatmap_baseline.png`), link do repo correto

## Merge blockers

O PR não pode ser mergeado (nem a tag `v1.0.0` criada) enquanto TODAS as condições abaixo não forem verdadeiras:

1. **README limpo:** sem placeholder `<seu-usuario>`, sem links quebrados; badges (CI, license, docs), diagrama de arquitetura, missão em 3 parágrafos, link do relatório e créditos presentes.
2. **Licença + relatório:** `LICENSE` (MIT) na raiz e `report/LICENSE` (CC BY 4.0) presentes; `report/SECURITY_AUDIT.pdf` baixável.
3. **Release + público:** tag `v1.0.0` criada e empurrada ao `origin`; repositório acessível publicamente sem login.

### Fora dos blockers (assíncrono)
- A **publicação do post no LinkedIn** e a entrada em "Projetos" do perfil **não bloqueiam** o merge — são ações externas suas. O entregável versionado da fase é o **draft** (`report/linkedin_post.md`) + a imagem do heatmap identificada.
