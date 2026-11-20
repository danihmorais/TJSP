#!/usr/bin/env python3
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
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
        "minimum": 200,
        "updated": "Texto compilado oficial do Planalto",
    },
    "cpc": {
        "title": "Código de Processo Civil — Lei nº 13.105/2015",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105compilada.htm",
        "kind": "html",
        "ranges": [(144, 155), (188, 275), (294, 311), (318, 538), (994, 1026)],
        "exact": [],
        "discipline": "Direito Processual Civil",
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
        "minimum": 15,
        "updated": "Texto compilado oficial do Planalto",
    },
    "jec": {
        "title": "Lei dos Juizados Especiais — Lei nº 9.099/1995",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l9099.htm",
        "kind": "html",
        "ranges": [(3, 19), (60, 83)],
        "exact": [(88, ""), (89, "")],
        "discipline": "Direito Processual Civil e Penal",
        "minimum": 35,
        "updated": "Texto oficial do Planalto; redações revogadas/riscadas são descartadas",
    },
    "jefaz": {
        "title": "Juizados Especiais da Fazenda Pública — Lei nº 12.153/2009",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2009/lei/l12153.htm",
        "kind": "html",
        "ranges": [(1, 27)],
        "exact": [],
        "discipline": "Direito Processual Civil",
        "minimum": 20,
        "updated": "Texto oficial do Planalto",
    },
    "lc1111": {
        "title": "Plano de Cargos e Carreiras dos Servidores do TJSP — Lei Complementar estadual nº 1.111/2010",
        "url": "https://www.al.sp.gov.br/repositorio/legislacao/lei.complementar/2010/compilacao-lei.complementar-1111-25.05.2010.html",
        "kind": "html_full",
        "discipline": "Legislação Interna do TJSP",
        "minimum": 1,
        "updated": "Texto consolidado pela ALESP — última atualização indicada: LC nº 1.441/2026",
    },
    "res850": {
        "title": "Resolução TJSP nº 850/2021 — Teletrabalho",
        "url": "https://api.tjsp.jus.br/handlers/handler/filefetch.ashx?codigo=122776",
        "kind": "pdf_full",
        "discipline": "Legislação Interna do TJSP",
        "minimum": 1,
        "updated": "Inteiro teor compilado disponibilizado pelo TJSP",
    },
    "regimento": {
        "title": "Regimento Interno do Tribunal de Justiça de São Paulo",
        "url": "https://www.tjsp.jus.br/Download/Portal/Biblioteca/Biblioteca/Legislacao/RegimentoInternoTJSP.pdf?d=1789151057606",
        "kind": "pdf_full",
        "discipline": "Legislação Interna do TJSP",
        "minimum": 1,
        "updated": "PDF oficial atualizado em 12/11/2026",
    },
    "nscgj": {
        "title": "Normas de Serviço da Corregedoria Geral da Justiça — Tomo I (recortes do edital)",
        "url": "https://api.tjsp.jus.br/Handlers/Handler/FileFetch.ashx?codigo=203718",
        "kind": "pdf_ranges",
        "ranges": [(5, 29), (46, 189), (1189, 1289)],
        "discipline": "Legislação Interna do TJSP",
        "minimum": 80,
        "updated": "PDF oficial atualizado em 22/10/2026; recortes por artigos correspondentes às seções indicadas no edital",
    },
}

ARTICLE_RE = re.compile(
    r"^\s*Art(?:igo)?\.?\s*(\d{1,4})\s*(?:[º°ªo]\s*)?(?:[-–]\s*([A-Za-z]))?(?=$|[\s.:;])",
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

def html_lines(content):
    soup = BeautifulSoup(content, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        node.decompose()
    for node in soup.find_all(["del", "s", "strike"]):
        node.decompose()
    for node in soup.find_all(style=True):
        style = (node.get("style") or "").lower().replace(" ", "")
        if "line-through" in style:
            node.decompose()
    text = soup.get_text("\n", strip=True)
    return clean_lines(text)

def pdf_text(content):
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append("\n".join(clean_lines(text)))
    return "\n\n".join(pages)

def parse_articles(text):
    records = []
    current = None
    for line in clean_lines(text):
        match = ARTICLE_RE.match(line)
        if match:
            if current:
                current["body"] = "\n".join(current.pop("_lines")).strip()
                records.append(current)
            number = int(match.group(1))
            suffix = (match.group(2) or "").upper()
            label = f"Art. {number}" + (f"-{suffix}" if suffix else "")
            current = {"number": number, "suffix": suffix, "label": label, "_lines": [line]}
        elif current:
            current["_lines"].append(line)
    if current:
        current["body"] = "\n".join(current.pop("_lines")).strip()
        records.append(current)
    return records

def chosen(article, spec):
    number = article["number"]
    suffix = article["suffix"]
    in_range = any(start <= number <= end for start, end in spec.get("ranges", []))
    exact = (number, suffix) in spec.get("exact", [])
    return in_range or exact

def extract_html_articles(spec, content):
    records = parse_articles("\n".join(html_lines(content)))
    selected = [a for a in records if chosen(a, spec)]
    if len(selected) < spec.get("minimum", 1):
        raise RuntimeError(
            f'{spec["title"]}: extraídos {len(selected)} artigos; mínimo esperado {spec.get("minimum")}.'
        )
    return selected

def build_document(key, spec):
    raw, content_type = download(spec["url"])
    kind = spec["kind"]
    base = {
        "id": key,
        "title": spec["title"],
        "discipline": spec["discipline"],
        "source": spec["url"],
        "updated": spec["updated"],
    }
    if kind in ("html", "html_full"):
        lines = html_lines(raw)
        text = "\n".join(lines)
        if kind == "html_full":
            base["fullText"] = text
            base["articles"] = parse_articles(text)
        else:
            base["articles"] = extract_html_articles(spec, raw)
    elif kind == "pdf_full":
        text = pdf_text(raw)
        if len(text) < 1000:
            raise RuntimeError(f'{spec["title"]}: extração de PDF vazia ou incompleta.')
        base["fullText"] = text
    elif kind == "pdf_ranges":
        text = pdf_text(raw)
        records = parse_articles(text)
        selected = [a for a in records if chosen(a, spec)]
        if len(selected) < spec.get("minimum", 1):
            raise RuntimeError(
                f'{spec["title"]}: extraídos {len(selected)} artigos; mínimo esperado {spec.get("minimum")}.'
            )
        base["articles"] = selected
    else:
        raise RuntimeError(f"Tipo de fonte desconhecido: {kind}")
    if not base.get("fullText") and not base.get("articles"):
        raise RuntimeError(f'{spec["title"]}: nenhum texto foi extraído.')
    return base

def main():
    documents = []
    for key, spec in SOURCES.items():
        print(f'Compilando: {spec["title"]}', flush=True)
        documents.append(build_document(key, spec))
    # A Resolução 963/2025 é publicada integralmente no sistema GCN/e-SAJ,
    # que entrega o inteiro teor por aplicação JavaScript e não por arquivo
    # HTML/PDF estático. Mantém-se a fonte oficial direta, sem reconstrução
    # aproximada nem substituição por resumo de terceiros.
    documents.append({
        "id": "res963",
        "title": "Resolução TJSP nº 963/2025 — Governança e utilização do eproc",
        "discipline": "Legislação Interna do TJSP",
        "source": "https://esaj.tjsp.jus.br/gcn-frontend-vue/legislacao/find/229313",
        "updated": "Inteiro teor oficial no sistema GCN/e-SAJ; referência ao Provimento CSM nº 2.834/2026",
        "externalOnly": True,
        "fullText": "O TJSP disponibiliza o inteiro teor compilado desta Resolução no sistema GCN/e-SAJ. Use o link da fonte oficial para abrir e imprimir o texto integral. O site não reproduz um texto reconstruído a partir de trechos indexados."
    })
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "referenceDate": "2026-11-20",
        "documents": documents,
        "notice": "Transcrição compilada para estudo a partir das fontes oficiais indicadas. A consolidação automática descarta redações marcadas como revogadas em HTML quando identificadas como texto tachado; confira notas de alteração e a publicação oficial antes da prova."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {OUT} ({OUT.stat().st_size} bytes)", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERRO NA COMPILAÇÃO: {exc}", file=sys.stderr)
        raise
