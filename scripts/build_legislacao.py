#!/usr/bin/env python3
import copy
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from html import escape as html_escape
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "legislacao.json"
UA = "Mozilla/5.0 (compatible; TJSP-BlocoII-Legislacao/1.0; +https://github.com/danihmorais/TJSP)"

SOURCES = {
    "cp": {
        "title": "Código Penal — Decreto-Lei nº 2.848/1940",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
        "kind": "html",
        "ranges": [(293, 305), (312, 317), (319, 333), (339, 347)],
        "exact": [(307, ""), (308, ""), (311, "A"), (336, ""), (337, ""), (357, ""), (359, "")],
        "discipline": "Direito Penal",
        "group": "penal",
        "minimum": 35,
        "updated": "Texto compilado oficial do Planalto",
    },
    "cpp": {
        "title": "Código de Processo Penal — Decreto-Lei nº 3.689/1941",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm",
        "kind": "html",
        "ranges": [(251, 258), (261, 267), (351, 372), (394, 497), (531, 538), (541, 548), (574, 667)],
        "exact": [(274, "")],
        "discipline": "Direito Processual Penal",
        "group": "processo-penal",
        "minimum": 180,
        "updated": "Texto compilado oficial do Planalto",
    },
    "cpc": {
        "title": "Código de Processo Civil — Lei nº 13.105/2015",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105compilada.htm",
        "kind": "html",
        "ranges": [(144, 155), (188, 275), (294, 311), (318, 538), (994, 1026)],
        "exact": [],
        "discipline": "Direito Processual Civil",
        "group": "processo-civil",
        "minimum": 300,
        "updated": "Texto compilado oficial do Planalto",
    },
    "cf": {
        "title": "Constituição da República Federativa do Brasil de 1988",
        "url": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
        "kind": "html",
        "ranges": [(5, 17), (37, 41)],
        "exact": [(92, "")],
        "discipline": "Direito Constitucional",
        "group": "constitucional",
        "minimum": 18,
        "updated": "Texto compilado oficial do Planalto",
    },
    "estatuto": {
        "title": "Estatuto dos Funcionários Públicos Civis do Estado de São Paulo — Lei nº 10.261/1968",
        "url": "https://www.al.sp.gov.br/repositorio/legislacao/lei/1968/compilacao-lei-10261-28.10.1968.html",
        "kind": "html",
        "ranges": [(1, 86), (171, 175), (239, 323)],
        "exact": [],
        "discipline": "Direito Administrativo",
        "group": "administrativo",
        "minimum": 150,
        "updated": "Texto consolidado pela ALESP — última atualização indicada: Lei nº 18.473/2026",
    },
    "lia": {
        "title": "Lei de Improbidade Administrativa — Lei nº 8.429/1992",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l8429compilada.htm",
        "kind": "html",
        "ranges": [(1, 23)],
        "exact": [],
        "discipline": "Direito Administrativo",
        "group": "administrativo",
        "minimum": 15,
        "updated": "Texto compilado oficial do Planalto",
    },
    "jec_civil": {
        "title": "Lei nº 9.099/1995 — Juizados Especiais Cíveis",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l9099.htm",
        "kind": "html",
        "ranges": [(3, 19)],
        "exact": [],
        "discipline": "Direito Processual Civil",
        "group": "processo-civil",
        "minimum": 15,
        "updated": "Recorte dos arts. 3º a 19 — texto oficial do Planalto",
    },
    "jec_criminal": {
        "title": "Lei nº 9.099/1995 — Juizados Especiais Criminais",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l9099.htm",
        "kind": "html",
        "ranges": [(60, 83)],
        "exact": [(88, ""), (89, "")],
        "discipline": "Direito Processual Penal",
        "group": "processo-penal",
        "minimum": 20,
        "updated": "Recorte dos arts. 60 a 83, 88 e 89 — texto oficial do Planalto",
    },
    "jefaz": {
        "title": "Juizados Especiais da Fazenda Pública — Lei nº 12.153/2009",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2009/lei/l12153.htm",
        "kind": "html",
        "ranges": [(1, 27)],
        "exact": [],
        "discipline": "Direito Processual Civil",
        "group": "processo-civil",
        "minimum": 20,
        "updated": "Texto oficial do Planalto",
    },
    "lc1111": {
        "title": "Plano de Cargos e Carreiras dos Servidores do TJSP — Lei Complementar estadual nº 1.111/2010",
        "url": "https://www.al.sp.gov.br/repositorio/legislacao/lei.complementar/2010/compilacao-lei.complementar-1111-25.05.2010.html",
        "kind": "html_full",
        "discipline": "Legislação Interna do TJSP",
        "group": "interna",
        "minimum": 1,
        "updated": "Texto consolidado pela ALESP — última atualização indicada: LC nº 1.441/2026",
    },
    "res963": {
        "title": "Resolução TJSP nº 963/2025 — Governança e utilização do sistema eproc",
        "url": "https://carreirapublica.com.br/legislacao/resolucao-tjsp-963-2025?concurso=tj-sp",
        "official_url": "https://esaj.tjsp.jus.br/gcn-frontend-vue/legislacao/find/229313",
        "kind": "html_block",
        "discipline": "Legislação Interna do TJSP",
        "group": "interna",
        "minimum": 40,
        "updated": "Compilação secundária de 19/10/2026; fonte primária oficial vinculada ao GCN/e-SAJ",
    },
    "res850": {
        "title": "Resolução TJSP nº 850/2021 — Teletrabalho",
        "url": "https://esaj.tjsp.jus.br/gcn-frontend-vue/legislacao/find/196070",
        "download_url": "https://api.tjsp.jus.br/Handlers/Handler/FileFetch.ashx?codigo=122776",
        "kind": "pdf_full",
        "discipline": "Legislação Interna do TJSP",
        "group": "interna",
        "minimum": 1,
        "updated": "Compilação oficial do GCN/e-SAJ em 25/04/2022, com a alteração da Resolução TJSP nº 864/2022",
    },
    "regimento": {
        "title": "Regimento Interno do Tribunal de Justiça de São Paulo",
        "url": "https://www.tjsp.jus.br/Download/Portal/Biblioteca/Biblioteca/Legislacao/RegimentoInternoTJSP.pdf?d=1788453606810",
        "kind": "pdf_full",
        "discipline": "Legislação Interna do TJSP",
        "group": "interna",
        "minimum": 1,
        "updated": "PDF oficial atualizado em 12/11/2026",
    },
    "nscgj": {
        "title": "Normas de Serviço da Corregedoria Geral da Justiça — Tomo I (recortes do edital)",
        "url": "https://api.tjsp.jus.br/Handlers/Handler/FileFetch.ashx?codigo=203718",
        "kind": "pdf_ranges",
        "ranges": [(5, 18), (26, 29), (46, 99), (103, 189), (1189, 1289)],
        "discipline": "Legislação Interna do TJSP",
        "group": "interna",
        "minimum": 80,
        "updated": "PDF oficial atualizado em 22/10/2026; recortes por artigos correspondentes às seções indicadas no edital",
    },
}

STRUCTURAL_HEADING_RE = re.compile(r"^(PARTE|LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\b", re.IGNORECASE)
STRUCTURAL_LINE_RE = re.compile(r"^(?:Art(?:igo)?\.?\s*\d|§+\s*\d|Parágrafo único\b|[IVXLCDM]+\s*[-–.)]|[a-z]\s*[\])}.:-]|PARTE\b|LIVRO\b|TÍTULO\b|TITULO\b|CAPÍTULO\b|CAPITULO\b|SEÇÃO\b|SECAO\b|SUBSEÇÃO\b|SUBSECAO\b)", re.IGNORECASE)

ARTICLE_RE = re.compile(
    r"^\s*Art(?:igo)?\.?\s*(\d{1,3}(?:\.\d{3})?|\d{1,4})\s*(?:[º°ªo]\s*)?(?:[-–]\s*([A-Za-z]))?(?=$|[\s.:;])",
    re.IGNORECASE,
)

def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read(), response.headers.get_content_type()

def clean_lines(text):
    lines = []
    for raw in text.replace("\xa0", " ").replace("\u200b", "").splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines

def parse_soup(content):
    soup = BeautifulSoup(content, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        node.decompose()
    for node in soup.find_all(["del", "s", "strike"]):
        node.decompose()
    for node in soup.find_all(style=True):
        style = (node.get("style") or "").lower().replace(" ", "")
        if "line-through" in style:
            node.decompose()
    return soup

def html_lines(content):
    return [line for block in legal_blocks(content) for line in block["lines"]]

ALLOWED_TAGS = {
    "p", "div", "span", "strong", "b", "em", "i", "u", "sup", "sub",
    "a", "br", "ol", "ul", "li", "table", "thead", "tbody", "tr", "td",
    "th", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "font"
}

SAFE_STYLE_PROPERTIES = {
    "font-family", "font-size", "font-weight", "font-style", "text-align",
    "text-indent", "line-height", "margin", "margin-top", "margin-right",
    "margin-bottom", "margin-left", "padding", "padding-top", "padding-right",
    "padding-bottom", "padding-left", "text-transform", "color",
    "background-color", "width", "max-width", "height", "vertical-align",
    "border", "border-top", "border-bottom", "border-left", "border-right",
    "border-collapse", "letter-spacing", "white-space"
}

def safe_inline_style(value):
    declarations = []
    for declaration in (value or "").split(";"):
        if ":" not in declaration:
            continue
        name, content = declaration.split(":", 1)
        name = name.strip().lower()
        content = re.sub(r"\s*!important\\s*$", "", content, flags=re.IGNORECASE).strip()
        if name not in SAFE_STYLE_PROPERTIES or not content or len(content) > 160:
            continue
        if re.search(r"url\s*\(|expression|javascript:|@import|[<>]", content, re.IGNORECASE):
            continue
        if not re.fullmatch(r"[^;{}<>]{1,160}", content):
            continue
        declarations.append(f"{name}: {content}")
    return "; ".join(declarations)

def clean_fragment(node):
    fragment = BeautifulSoup(str(node), "html.parser")
    for element in fragment.find_all(True):
        if element.name not in ALLOWED_TAGS:
            element.unwrap()
            continue
        kept = {}
        if element.get("class"):
            classes = [item for item in element.get("class", []) if re.fullmatch(r"[A-Za-z0-9_-]{1,48}", item)]
            if classes:
                kept["class"] = " ".join(classes)
        if element.get("style"):
            style = safe_inline_style(element.get("style"))
            if style:
                kept["style"] = style
        if element.name == "a":
            href = element.get("href", "")
            if href.startswith(("https://", "http://", "#")):
                kept["href"] = href
            name = element.get("name", "")
            if re.fullmatch(r"[A-Za-z0-9_:-]{1,100}", name):
                kept["name"] = name
        if element.name in {"p", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6"}:
            align = element.get("align", "").lower()
            if align in {"left", "right", "center", "justify"}:
                kept["align"] = align
        if element.name == "font":
            face = element.get("face", "")
            size = element.get("size", "")
            color = element.get("color", "")
            if re.fullmatch(r"[A-Za-z0-9 ,_-]{1,60}", face):
                kept["face"] = face
            if re.fullmatch(r"[1-7][+-]?", size):
                kept["size"] = size
            if re.fullmatch(r"#[0-9A-Fa-f]{3,8}|[A-Za-z]{1,24}", color):
                kept["color"] = color
        if element.name == "table":
            for attr in ("width", "border", "cellpadding", "cellspacing"):
                value = element.get(attr, "")
                if re.fullmatch(r"[0-9%]{1,5}", value):
                    kept[attr] = value
        if element.name in {"td", "th"}:
            for attr in ("width", "colspan", "rowspan", "align", "valign"):
                value = element.get(attr, "")
                if re.fullmatch(r"[A-Za-z0-9%_-]{1,12}", value):
                    kept[attr] = value
        element.attrs = kept
    return str(fragment)

def tag_opening(node):
    attributes = []
    for name, value in node.attrs.items():
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        if value is None:
            attributes.append(name)
        else:
            attributes.append(f'{name}="{html_escape(str(value), quote=True)}"')
    return "<" + node.name + (" " + " ".join(attributes) if attributes else "") + ">"


def node_segments(node):
    raw_segments = [{"text": [], "html": []}]
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def walk(parent, stack):
        for child in parent.children:
            current = raw_segments[-1]
            if isinstance(child, NavigableString):
                value = str(child)
                current["text"].append(value)
                current["html"].append(html_escape(value, quote=False))
                continue
            if not getattr(child, "name", None):
                continue
            if child.name == "br":
                for active in reversed(stack):
                    raw_segments[-1]["html"].append(f"</{active.name}>")
                raw_segments.append({"text": [], "html": []})
                for active in stack:
                    raw_segments[-1]["html"].append(tag_opening(active))
                continue
            if child.name in void_tags:
                current["html"].append(str(child))
                continue
            current["text"].append(" ")
            current["html"].append(tag_opening(child))
            walk(child, stack + [child])
            raw_segments[-1]["text"].append(" ")
            raw_segments[-1]["html"].append(f"</{child.name}>")

    walk(node, [])
    merged = []
    for raw in raw_segments:
        text = re.sub(r"\s+", " ", "".join(raw["text"])).strip()
        markup = "".join(raw["html"])
        if not text:
            continue
        if merged and not STRUCTURAL_LINE_RE.match(text):
            merged[-1]["text"] = (merged[-1]["text"] + " " + text).strip()
            merged[-1]["html"] += markup
        else:
            merged.append({"text": text, "html": markup})

    if not merged:
        return []
    opening = tag_opening(node)
    return [
        {
            "text": segment["text"],
            "html": clean_fragment(opening + segment["html"] + f"</{node.name}>"),
            "lines": [segment["text"]],
        }
        for segment in merged
    ]


def legal_blocks(content, doc_id="documento"):
    soup = parse_soup(content)
    root = soup.body or soup
    tags = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table", "div"]
    blocks = []
    seen = set()
    heading_number = 0
    for node in root.find_all(tags):
        if node.name == "div" and node.find_parent("table"):
            continue
        descendants = tags if node.name != "table" else [
            "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table"
        ]
        nested_blocks = node.find(descendants)
        if nested_blocks:
            if not ARTICLE_RE.match(re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()):
                continue
            lead = copy.deepcopy(node)
            for nested in lead.find_all(descendants):
                nested.decompose()
            if not ARTICLE_RE.match(re.sub(r"\s+", " ", lead.get_text(" ", strip=True)).strip()):
                continue
            source_node = lead
        else:
            source_node = node
        for segment in node_segments(source_node):
            text = segment["text"]
            html = segment["html"]
            fingerprint = (node.name, text, html)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            heading_match = STRUCTURAL_HEADING_RE.match(text)
            heading_id = None
            if heading_match:
                heading_number += 1
                heading_id = f"h-{doc_id}-{heading_number}"
                html = f'<div id="{heading_id}" class="legal-heading-anchor">{html}</div>'
            blocks.append({
                "text": text,
                "lines": segment["lines"],
                "html": html,
                "isArticle": bool(ARTICLE_RE.match(text)),
                "isHeading": bool(heading_match),
                "headingId": heading_id,
            })
    return blocks



def headings_from_blocks(blocks):
    return [
        {"id": block["headingId"], "text": block["text"], "level": STRUCTURAL_HEADING_RE.match(block["text"]).group(1).upper()}
        for block in blocks if block.get("isHeading")
    ]


def extract_html_articles(spec, content, blocks=None):
    blocks = blocks if blocks is not None else legal_blocks(content)
    starts = [i for i, block in enumerate(blocks) if block["isArticle"]]
    records = []
    for position, start in enumerate(starts):
        article_match = ARTICLE_RE.match(blocks[start]["text"])
        number = int(article_match.group(1).replace(".", ""))
        suffix = (article_match.group(2) or "").upper()
        label = f"Art. {number}" + (f"-{suffix}" if suffix else "")
        if not chosen({"number": number, "suffix": suffix}, spec):
            continue
        stop = starts[position + 1] if position + 1 < len(starts) else len(blocks)
        section = blocks[start:stop]
        body = "\n".join(block["text"] for block in section).strip()
        html = "\n".join(block["html"] for block in section)
        records.append({
            "number": number,
            "suffix": suffix,
            "label": label,
            "body": body,
            "html": html,
        })
    if len(records) < spec.get("minimum", 1):
        detected = [
            ARTICLE_RE.match(block["text"]).group(1)
            for block in blocks
            if ARTICLE_RE.match(block["text"])
        ]
        selected_numbers = [str(record["number"]) for record in records]
        missing_nodes = []
        if len(missing_nodes) < 40:
            soup = parse_soup(content)
            for node in soup.find_all(True):
                node_text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                match = ARTICLE_RE.match(node_text)
                if not match:
                    continue
                number = int(match.group(1).replace(".", ""))
                suffix = (match.group(2) or "").upper()
                if str(number) in selected_numbers or not chosen({"number": number, "suffix": suffix}, spec):
                    continue
                child_has_match = False
                for child in node.find_all(True):
                    descendant_match = ARTICLE_RE.match(
                        re.sub(r"\s+", " ", child.get_text(" ", strip=True)).strip()
                    )
                    if descendant_match and int(descendant_match.group(1).replace(".", "")) == number:
                        child_has_match = True
                        break
                if child_has_match:
                    continue
                parent = node.parent
                parent_desc = parent.name if getattr(parent, "name", None) else "?"
                classes = ".".join(node.get("class", [])) if node.get("class") else ""
                missing_nodes.append(f"{number}:{node.name}.{classes}<{parent_desc}>")
                if len(missing_nodes) >= 40:
                    break
        raise RuntimeError(
            f'{spec["title"]}: extraídos {len(records)} artigos; mínimo esperado {spec.get("minimum")}. '
            f'Artigos selecionados: {", ".join(selected_numbers)}. '
            f'Artigos detectados nos blocos: {", ".join(detected)}. '
            f'Nós HTML não capturados: {", ".join(missing_nodes)}.'
        )
    return records

def extract_full_html(content, blocks=None):
    blocks = blocks if blocks is not None else legal_blocks(content)
    return "\n".join(block["html"] for block in blocks)

def is_page_number(line):
    return bool(re.fullmatch(r"(?:p(?:á|a)g(?:ina)?\.?\s*)?\d{1,4}(?:\s*/\s*\d{1,4})?|[-–]?\s*\d{1,4}\s*[-–]?", line, re.IGNORECASE))


def reflow_pdf_pages(pages):
    edge_counts = Counter()
    for lines in pages:
        edge_counts.update(set(lines[:2] + lines[-2:]))
    threshold = max(2, (len(pages) + 2) // 3)
    repeated_edges = {
        line for line, count in edge_counts.items()
        if count >= threshold and len(line) >= 4
    }
    paragraphs = []
    current = ""
    for lines in pages:
        for line in lines:
            line = re.sub(r"\s+", " ", line).strip()
            if not line or is_page_number(line) or line in repeated_edges:
                continue
            if STRUCTURAL_LINE_RE.match(line):
                if current:
                    paragraphs.append(current)
                current = line
            elif not current:
                current = line
            elif current.endswith("-") and re.match(r"^[a-záéíóúãõç]", line, re.IGNORECASE):
                current = current[:-1] + line
            else:
                current += " " + line
    if current:
        paragraphs.append(current)
    return paragraphs


def pdf_text(content):
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append(clean_lines(page.extract_text() or ""))
    return "\n".join(reflow_pdf_pages(pages))


def headings_from_text(text, doc_id):
    headings = []
    for line in clean_lines(text):
        match = STRUCTURAL_HEADING_RE.match(line)
        if match:
            headings.append({
                "id": f"h-{doc_id}-{len(headings) + 1}",
                "text": line,
                "level": match.group(1).upper(),
            })
    return headings


def parse_articles(text):
    records = []
    current = None

    def finish():
        if current:
            current["body"] = "\n".join(current.pop("_lines")).strip()
            records.append(current)

    for line in clean_lines(text):
        match = ARTICLE_RE.match(line)
        if match:
            finish()
            number = int(match.group(1).replace(".", ""))
            suffix = (match.group(2) or "").upper()
            label = f"Art. {number}" + (f"-{suffix}" if suffix else "")
            current = {"number": number, "suffix": suffix, "label": label, "_lines": [line]}
        elif current:
            current["_lines"].append(line)
    finish()
    return records


def chosen(article, spec):
    number = article["number"]
    suffix = article["suffix"]
    in_range = any(start <= number <= end for start, end in spec.get("ranges", []))
    exact = (number, suffix) in spec.get("exact", [])
    return in_range or exact

def build_document(key, spec):
    raw, content_type = download(spec.get("download_url", spec["url"]))
    kind = spec["kind"]
    base = {
        "id": key,
        "title": spec["title"],
        "discipline": spec["discipline"],
        "group": spec.get("group", "interna"),
        "source": spec.get("official_url", spec["url"]),
        "updated": spec["updated"],
    }
    if kind in ("html", "html_full", "html_block"):
        blocks = legal_blocks(raw, key)
        lines = [line for block in blocks for line in block["lines"]]
        text = "\n".join(lines)
        base["headings"] = headings_from_blocks(blocks)
        if kind == "html_full":
            base["fullText"] = text
            base["fullHtml"] = extract_full_html(raw, blocks)
            base["articles"] = parse_articles(text)
        elif kind == "html_block":
            start = next((i for i, line in enumerate(lines) if "preâmbulo" in line.lower()), None)
            if start is None:
                raise RuntimeError(f'{spec["title"]}: preâmbulo não localizado na página de compilação.')
            end = next((i for i in range(start, len(lines)) if re.search(r"\bArt\.?\s*43\b", lines[i])), None)
            if end is None:
                raise RuntimeError(f'{spec["title"]}: artigo final 43 não localizado.')
            selected_lines = lines[start:end + 1]
            records = parse_articles("\n".join(selected_lines))
            if len(records) < spec.get("minimum", 1):
                raise RuntimeError(f'{spec["title"]}: extraídos {len(records)} artigos; mínimo esperado {spec.get("minimum")}.')
            base["fullText"] = "\n".join(selected_lines).strip()
            base["textFormat"] = "pdf-structured"
            base["articles"] = records
            first_block = next((i for i, block in enumerate(blocks) if "preâmbulo" in block["text"].lower()), 0)
            last_block = next((i + 1 for i, block in enumerate(blocks) if re.search(r"\bArt\.?\s*43\b", block["text"])), len(blocks))
            selected_blocks = blocks[first_block:last_block]
            base["fullHtml"] = "\n".join(block["html"] for block in selected_blocks)
            base["headings"] = headings_from_blocks(selected_blocks)
            base["transcriptionNote"] = "Texto extraído de compilação secundária datada de 19/10/2026; fonte primária oficial do TJSP vinculada no GCN/e-SAJ."
        else:
            base["articles"] = extract_html_articles(spec, raw, blocks)
    elif kind == "pdf_full":
        text = pdf_text(raw)
        if len(text) < 1000:
            raise RuntimeError(f'{spec["title"]}: extração de PDF vazia ou incompleta.')
        base["fullText"] = text
        base["textFormat"] = "pdf-structured"
        base["headings"] = headings_from_text(text, key)
    elif kind == "pdf_ranges":
        text = pdf_text(raw)
        records = parse_articles(text)
        selected = [article for article in records if chosen(article, spec)]
        if len(selected) < spec.get("minimum", 1):
            raise RuntimeError(
                f'{spec["title"]}: extraídos {len(selected)} artigos; mínimo esperado {spec.get("minimum")}.'
            )
        base["articles"] = selected
        base["textFormat"] = "pdf-structured"
        base["headings"] = headings_from_text(text, key)
    else:
        raise RuntimeError(f"Tipo de fonte desconhecido: {kind}")
    if not base.get("fullText") and not base.get("articles"):
        raise RuntimeError(f'{spec["title"]}: nenhum texto foi extraído.')
    return base


def load_previous_documents():
    if not OUT.exists():
        return {}
    try:
        payload = json.loads(OUT.read_text(encoding="utf-8"))
        return {document["id"]: document for document in payload.get("documents", []) if document.get("id")}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"AVISO: não foi possível ler a compilação anterior: {exc}", file=sys.stderr)
        return {}


def normalize_fallback_document(document):
    for article in document.get("articles", []):
        body = (article.get("body") or "").lstrip()
        if re.match(r"^Art(?:igo)?\.?\s*\d", body, re.IGNORECASE):
            continue
        number = article.get("number")
        suffix = (article.get("suffix") or "").upper()
        if number is None:
            continue
        label = f"Art. {number}" + (f"-{suffix}" if suffix else "")
        prefix = label + ("" if suffix else "º")
        article["body"] = (prefix + " " + body).strip()
        if article.get("html") and not re.search(r"Art(?:igo)?\.?\s*\d", article["html"], re.IGNORECASE):
            article["html"] = f'<p class="legal-line article-line">{html_escape(prefix)}</p>' + article["html"]
        article.setdefault("label", label)
    return document


def main():
    previous = load_previous_documents()
    documents, successful, reused, unavailable = [], [], [], []
    for key, spec in SOURCES.items():
        print(f'Compilando: {spec["title"]}', flush=True)
        try:
            document = build_document(key, spec)
            document.pop("stale", None)
            document.pop("error", None)
            successful.append(key)
            print(f"  OK: {key}", flush=True)
        except Exception as exc:
            message = str(exc)[:1000]
            if key in previous:
                document = normalize_fallback_document(copy.deepcopy(previous[key]))
                document["stale"] = True
                document["error"] = message
                reused.append(key)
                print(f"  REAPROVEITADO: {key} — {message}", file=sys.stderr, flush=True)
            else:
                unavailable.append((key, message))
                print(f"  FALHOU SEM VERSÃO ANTERIOR: {key} — {message}", file=sys.stderr, flush=True)
                continue
        documents.append(document)
    if unavailable:
        details = "; ".join(f"{key}: {message}" for key, message in unavailable)
        raise RuntimeError("Não foi possível compilar nem recuperar todas as fontes: " + details)
    if not documents:
        raise RuntimeError("Nenhum diploma foi compilado ou recuperado.")
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "referenceDate": datetime.now(timezone.utc).date().isoformat(),
        "documents": documents,
        "notice": "Transcrição compilada para estudo a partir das fontes indicadas. Textos tachados e dispositivos identificados como revogados são descartados intencionalmente; confira a publicação oficial, notas de alteração e vigência antes da prova."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Resumo: {len(successful)} atualizados, {len(reused)} reaproveitados, "
        f"{len(unavailable)} sem dados disponíveis.",
        flush=True,
    )
    print(f"Arquivo gerado: {OUT} ({OUT.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERRO NA COMPILAÇÃO: {exc}", file=sys.stderr)
        raise
