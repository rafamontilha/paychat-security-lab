# Makefile — geração do relatório executivo (Fase 11, PayChat Security Lab)
#
# Alvos:
#   make report          regenera figuras, gera o PDF e valida a cobertura
#   make report-figures  re-executa notebooks/00_audit_report.ipynb (fonte única das figuras)
#   make report-pdf      gera report/SECURITY_AUDIT.pdf (Pandoc -> HTML -> Edge headless)
#   make report-check    valida 21/21 células + figuras referenciadas no relatório
#
# Pré-requisitos: Pandoc no PATH (scoop install pandoc) e Microsoft Edge/Chromium
# (presente no Windows 11). O PDF não depende de LaTeX nem wkhtmltopdf.

ifeq ($(OS),Windows_NT)
    PYTHON ?= .venv\Scripts\python.exe
    SHELL := cmd.exe
    .SHELLFLAGS := /C
else
    PYTHON ?= .venv/bin/python
endif

NOTEBOOK := notebooks/00_audit_report.ipynb

.PHONY: report report-figures report-pdf report-check

report: report-figures report-pdf report-check

report-figures:
	$(PYTHON) -X utf8 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 $(NOTEBOOK)

report-pdf:
	$(PYTHON) -X utf8 scripts/build_report_pdf.py

report-check:
	$(PYTHON) -X utf8 scripts/check_audit_coverage.py
