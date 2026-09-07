"""Parsing de arquivos para texto plano.

Suporta: PDF, DOCX, TXT, CSV, Markdown.
Todos os parsers convertem o conteudo do arquivo para uma string limpa.
"""
from __future__ import annotations

import csv
import io


def parse_pdf(data: bytes) -> str:
    """Extrai texto de um PDF pagina por pagina."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def parse_docx(data: bytes) -> str:
    """Extrai texto de um documento DOCX (Word)."""
    from docx import Document

    doc = Document(io.BytesIO(data))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def parse_text(data: bytes) -> str:
    """Decodifica texto plano (TXT, CSV, Markdown)."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def parse_csv(data: bytes) -> str:
    """Converte CSV em texto legivel (cada linha = paragrafo)."""
    text = parse_text(data)
    reader = csv.reader(io.StringIO(text))
    rows = []
    for row in reader:
        if any(cell.strip() for cell in row):
            rows.append(" | ".join(cell.strip() for cell in row))
    return "\n".join(rows)


# Mapeamento extensao -> funcao de parsing
PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".doc": parse_docx,
    ".txt": parse_text,
    ".csv": parse_csv,
    ".md": parse_text,
    ".markdown": parse_text,
    ".json": parse_text,
    ".xml": parse_text,
    ".html": parse_text,
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def parse_file(filename: str, data: bytes) -> str:
    """Detecta o tipo pelo extremensao e extrai texto.

    Retorna a string com o conteudo textual do arquivo.
    Levanta ValueError se o tipo nao for suportado ou o arquivo for grande demais.
    """
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"Arquivo muito grande ({len(data) // 1024 // 1024}MB). Limite: 10MB.")

    import os
    ext = os.path.splitext(filename)[1].lower()

    parser = PARSERS.get(ext)
    if not parser:
        suportados = ", ".join(sorted(PARSERS.keys()))
        raise ValueError(f"Tipo de arquivo nao suportado: {ext}. Tipos aceitos: {suportados}")

    text = parser(data)
    if not text or not text.strip():
        raise ValueError("Arquivo vazio ou sem texto extraivel.")

    return text.strip()
