"""Gera report/SECURITY_AUDIT.pdf a partir do Markdown.

Pipeline (sem LaTeX): Pandoc converte Markdown -> HTML standalone com recursos
embutidos (figuras PNG + SVG do diagrama viram data-URIs) e sumário; em seguida o
Microsoft Edge / Chromium em modo headless imprime o HTML em PDF, renderizando
SVG, CSS e tabelas via webkit/blink. Evita dependência de LaTeX ou wkhtmltopdf
no Windows.

Uso:
    python scripts/build_report_pdf.py

Override de binários por variável de ambiente: PANDOC, EDGE.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
MD = REPORT / "SECURITY_AUDIT.md"
PDF = REPORT / "SECURITY_AUDIT.pdf"
TITLE = "Relatório de Auditoria de Segurança — PayChat Security Lab"

_EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def find_pandoc() -> str:
    pandoc = os.environ.get("PANDOC") or shutil.which("pandoc")
    if not pandoc:
        sys.exit("ERRO: pandoc não encontrado. Rode `scoop install pandoc` ou defina PANDOC.")
    return pandoc


def find_browser() -> str:
    env = os.environ.get("EDGE")
    if env and Path(env).exists():
        return env
    for candidate in _EDGE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in ("msedge", "chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("ERRO: navegador Chromium (Edge/Chrome) não encontrado para --print-to-pdf.")


def run_pandoc(pandoc: str, html_name: str) -> None:
    cmd = [
        pandoc,
        MD.name,
        "-o",
        html_name,
        "--standalone",
        "--embed-resources",
        "--toc",
        "--toc-depth=2",
        "--metadata",
        f"title={TITLE}",
        "--css",
        "assets/pdf.css",
    ]
    subprocess.run(cmd, cwd=REPORT, check=True)


def run_browser(browser: str, html: Path, user_data: Path) -> bool:
    """Tenta imprimir o HTML em PDF. Retorna True se o PDF foi criado."""
    base = [
        browser,
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={user_data}",
        "--no-pdf-header-footer",
        "--virtual-time-budget=20000",
        f"--print-to-pdf={PDF}",
        html.resolve().as_uri(),
    ]
    # Edge/Chrome recentes usam --headless=new; versões antigas, --headless.
    for headless in ("--headless=new", "--headless"):
        if PDF.exists():
            PDF.unlink()
        subprocess.run([base[0], headless, *base[1:]])
        if PDF.exists() and PDF.stat().st_size > 0:
            return True
    return False


def main() -> int:
    if not MD.exists():
        sys.exit(f"ERRO: {MD} não existe.")
    pandoc = find_pandoc()
    browser = find_browser()

    html = REPORT / "_audit_tmp.html"  # em report/ para resolver figures/ e assets/
    ok = False
    try:
        run_pandoc(pandoc, html.name)
        with tempfile.TemporaryDirectory() as tmp:
            ok = run_browser(browser, html, Path(tmp) / "edge-profile")
    finally:
        html.unlink(missing_ok=True)

    if not ok:
        sys.exit("ERRO: PDF não foi gerado pelo navegador headless.")
    print(f"PDF gerado: {PDF} ({PDF.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
