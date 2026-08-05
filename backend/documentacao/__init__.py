"""Exportacao da documentacao Markdown para .docx.

O Markdown continua sendo a **unica fonte**: o .docx e artefato derivado,
reconstruivel a qualquer momento por `manage.py exportar_docs`, e nao entra no
versionamento. Copia versionada envelheceria - em duas semanas o .docx diria
uma coisa e o .md outra, e ninguem saberia qual vale.

Mesmo principio adotado para a projecao do Neo4j (docs/arquitetura.md).
"""
