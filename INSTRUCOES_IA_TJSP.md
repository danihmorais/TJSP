# Instruções para a IA — repositório `danihmorais/TJSP`

Você vai corrigir a apostila de legislação (`legislacao.html` + `scripts/build_legislacao.py` + `.github/workflows/pages.yml`) e entregar uma **impressão no mesmo layout do site do Planalto, com sumário**. Leia tudo antes de editar. Faça as fases na ordem; cada fase tem critério de aceite.

## 0. Como o sistema funciona

- `scripts/build_legislacao.py` baixa ~14 fontes oficiais (Planalto, ALESP, TJSP, e-SAJ e um site de terceiros, `carreirapublica.com.br`) e gera `data/legislacao.json`.
- `data/legislacao.json` **não está versionado**: só existe se o workflow rodar com sucesso.
- `legislacao.html` faz `fetch("data/legislacao.json")` e monta a página por JavaScript. Sem o JSON, a tela fica praticamente vazia.
- O arquivo tem **dois blocos `<script>`**; o segundo redefine por cima funções do primeiro (`articleHtml`, `docHtml`, `render`, `applySearch`). O CSS de impressão também está duplicado (dois `@page`, três blocos `@media print`).

## 1. Diagnóstico

### Bugs confirmados (reproduzi com Chrome headless e dados de teste gerados pelas funções reais do script)

| # | Bug | Evidência | Efeito |
|---|-----|-----------|--------|
| B2 | "Art. Xº" some do texto. `parse_articles` remove o prefixo do corpo, e o segundo `articleHtml` (no 2º `<script>`) não imprime mais o `<div class="article-label">`. | PDF e tela mostram "Texto do artigo 3…" sem o "Art. 3º". | Apostila sem numeração dos artigos. |
| B3 | `html_lines()` usa `soup.get_text("\n")`: **toda tag inline** (`<b>`, `<a>`, `<font>`, `<i>`) vira uma linha separada. | Entrada `Art. 5º Todos são <b>iguais</b> perante a lei, <a>(Redação dada…)</a> sem distinção.` virou 5 linhas. | Parágrafos picotados; cada fragmento vira um `<p>` com recuo de 38px e margem de 20px. |
| B3b | Consequência do B3: uma referência cruzada em link (`<a>art. 3º</a>`) fica numa linha própria, casa com `ARTICLE_RE` e **cria um artigo falso**. | Teste: o "§ 1º O disposto no" foi parar no Art. 5, e surgiu um "Art. 3" falso com corpo "aplica-se.". | Artigos errados, filtro por faixas (`ranges`) incluindo/excluindo dispositivos indevidos, contagem `minimum` enganosa. |
| B4 | `legal_blocks()` seleciona `p, li, table` e também o que está dentro deles. | `<table><tr><td><p>X</p></td></tr></table>` gerou dois blocos "X". | Texto duplicado no `fullHtml` (LC 1.111, Res. 963). |
| B5 | `header{color:white;…}` vale para **todo** `<header>`, inclusive `.doc-head`. O `<h2>` do título do diploma herda branco. | Captura de tela: título do diploma quase invisível sobre fundo claro. | Título ilegível na tela. |
| B6 | `extract_html_articles` está definida **duas vezes**; a segunda (texto puro) sobrescreve a primeira (que guardava o HTML de origem via `legal_blocks`). | Chaves do artigo no JSON: `number, suffix, label, body` — sem `html`. | O front-end (que já suporta `a.html`) nunca recebe o HTML original; impossível reproduzir o layout do Planalto. |

### Causa mais provável da página em branco (inferida do código; **não consegui abrir o site publicado**)

Com um `legislacao.json` válido a página carrega sem erro de JavaScript (testei: 8 diplomas, 6 agrupamentos, impressão de 34 páginas sem página vazia). Portanto a tela em branco vem dos dados/deploy:

- **B1a** — o JSON não é versionado. Abrindo o `.html` do disco, por outro host, ou com o GitHub Pages em "Deploy from a branch", o `fetch` falha e sobra só o cabeçalho e uma caixa amarela.
- **B1b** — o build é "tudo ou nada": `main()` não tem `try/except` por fonte. Se **uma** fonte falhar (403/timeout de WAF de site governamental a partir de IP do GitHub, mudança de HTML na Res. 963, `minimum` não atingido), o job falha, não há deploy e o site nunca ganha dados.

**Como confirmar em 1 minuto (peça ao dono ou verifique você mesmo se tiver acesso):**
1. Abrir `https://danihmorais.github.io/TJSP/data/legislacao.json`. 404 = o deploy não gerou o arquivo.
2. Aba **Actions** → último "Build and deploy GitHub Pages" → passo "Compile the legislation…". A última linha `ERRO NA COMPILAÇÃO: …` diz qual fonte quebrou.
3. **Settings → Pages → Source** deve ser **GitHub Actions**.

### Riscos (não verificados)
- `<link rel="stylesheet" … planalto.gov.br/ccivil_03/css/header.css | font.css media="print">` depende de CSS externo que pode mudar ou sumir. Não imita o Planalto (a marcação é outra). Remova.
- `PDF → texto` (Res. 850, Regimento, NSCGJ): `pypdf.extract_text()` devolve linhas quebradas no tamanho da linha do PDF; `legalTextMarkup()` cria um `<p>` por linha, com recuo e margem de parágrafo. Provável texto picotado e cabeçalhos/rodapés de página misturados ao corpo. Valide com os PDFs reais.
- Estilos inline da fonte (`margin`, `text-indent`, `font-*`) são preservados por `safe_inline_style` e **vencem** o CSS de impressão (que não usa `!important` nessas regras).

## 2. Fase 1 — Dados e deploy (corrige a página em branco)

1. **Versione `data/legislacao.json`** (gere uma vez e faça commit). Ele serve de fallback.
2. Em `build_legislacao.py`, carregue o JSON anterior (se existir). No loop de `main()`, envolva cada fonte em `try/except`; em caso de erro, **reaproveite o documento anterior** com `"stale": true` e `"error": "<mensagem>"`, e imprima um resumo (ok / reaproveitado / falhou). Só encerre com erro se alguma fonte não tiver nem versão nova nem anterior.
3. No workflow, após o build, faça commit do JSON alterado de volta na `main` (com `permissions: contents: write`, mensagem com `[skip ci]`), para o fallback persistir entre execuções.
4. No front-end: se o `fetch` falhar, mostrar mensagem acionável (inclusive "abra pelo GitHub Pages, não pelo arquivo local" quando `location.protocol === "file:"`) e um `<noscript>`. Mostrar aviso discreto quando algum diploma estiver `stale`.
5. Atualize o `README` com o passo "Settings → Pages → GitHub Actions".

**Aceite:** com uma fonte bloqueada de propósito (ex.: URL inválida), o build termina, o site publica e mostra o diploma anterior marcado como desatualizado.

## 3. Fase 2 — Extração fiel ao Planalto

1. **Apague a segunda `extract_html_articles`** e use a primeira (a que usa `legal_blocks` e guarda `html`).
2. Corrija `legal_blocks()` para só devolver blocos **folha** (sem descendente `p/li/table/h1–h6`), eliminando duplicados (B4). Para `<table>` sem `p` dentro, mantenha a tabela inteira.
3. A detecção de artigo (`ARTICLE_RE`) deve rodar sobre o **texto do bloco inteiro** (`get_text(" ", strip=True)`), nunca sobre pedaços de tag inline (B3/B3b). Não use mais `get_text("\n")` para segmentar. `<br>` dentro do bloco vira espaço, a menos que a linha seguinte comece com `Art.`, `§`, inciso (romano) ou alínea.
4. Mantenha o prefixo "Art. N" no `body` **e** no `html`. Só use `label` para busca e sumário.
5. Para fontes de PDF, reflua o texto em parágrafos: abra novo parágrafo apenas quando a linha começar com `Art.`, `§`, `Parágrafo único`, inciso romano, alínea ou título estrutural (`TÍTULO`, `CAPÍTULO`, `SEÇÃO`…); caso contrário, anexe à anterior (tratando hífen de fim de linha). Remova cabeçalho/rodapé repetido e número de página.
6. Registre títulos estruturais (`TÍTULO`, `CAPÍTULO`, `SEÇÃO`, `SUBSEÇÃO`) como itens próprios com `id` estável (`h-<doc>-<n>`) para o sumário da Fase 4.
7. Decisão a confirmar com o dono: hoje o script **descarta texto tachado** (`<strike>`, `<del>`, `line-through`). O Planalto exibe esse texto riscado. Mantenha o descarte (é o objetivo de estudo) e deixe isso documentado.

**Aceite (testes automáticos em Python, com HTML de exemplo):**
- `Art. 5º Todos são <b>iguais</b> … <a>(Redação…)</a>` gera **um** parágrafo e **um** artigo.
- `§ 1º O disposto no <a>art. 3º</a> aplica-se.` **não** cria "Art. 3".
- Bloco dentro de tabela/lista aparece uma única vez.
- Todo artigo exibido começa com "Art. N".

## 4. Fase 3 — Front-end e CSS

1. **Junte os dois `<script>` em um só**, sem redefinir funções. Mantenha os nomes `printSelection`, `legalGroups`, `applySearch`.
2. Troque `header{…}` por `body>header{…}` (ou use `<div>` em `.doc-head` e `.group-header`) para resolver o B5.
3. Consolide o CSS de impressão em **um único** `@media print` e **um único** `@page` (hoje há dois `@page`; vale o último, `15mm 10mm 15mm 20mm`).
4. Remova os `<link … planalto.gov.br … media="print">`.
5. O artigo deve renderizar `a.html` quando existir (já suportado); senão, o texto reflowado.

## 5. Fase 4 — Impressão igual ao Planalto, com sumário

### Tipografia (valores já registrados no `README`; não consegui medi-los no Planalto)
- Papel A4. `@page{size:A4;margin:15mm 10mm 15mm 20mm}`.
- Corpo: **Arial/Helvetica 10pt, entrelinha 12pt, justificado**.
- Parágrafos: `text-indent:38px; margin:20px 0` (inclui artigos, parágrafos, incisos e alíneas — o Planalto não usa recuos extras por nível).
- Título do diploma e títulos estruturais (`TÍTULO`, `CAPÍTULO`, `SEÇÃO`): centralizados, sem recuo, com a mesma fonte; mantenha negrito/maiúsculas que vierem da fonte.
- Notas de alteração `(Redação dada pela Lei nº …)` ficam **no fluxo do parágrafo**, como no original; links impressos em preto, sem sublinhado.
- Sem nenhum elemento de site na impressão: cabeçalho, sidebar, busca, botões, rodapé.
- Garanta que a regra de impressão **vença** os estilos inline da fonte: em `.legal-source` (e filhos) aplique `font:10pt/12pt Arial,Helvetica,sans-serif !important`, `text-align:justify !important` (exceto `align=center|right|left`), e normalize `margin`/`text-indent` com `!important`. Alternativa melhor: parar de manter `font-*`, `margin*` e `text-indent` em `SAFE_STYLE_PROPERTIES`.
- Antes de dar a tipografia como pronta, **compare visualmente** com a impressão real de uma página do Planalto (ex.: `https://www.planalto.gov.br/ccivil_03/leis/l9099.htm`). Se tiver rede, gere o PDF dela em Chrome headless e confronte com o seu, página a página. Observei na página do Planalto: bloco de cabeçalho (brasão + "Presidência da República / Casa Civil / Subchefia para Assuntos Jurídicos"), título da lei em negrito com link, "Mensagem de veto/Vigência", preâmbulo, depois capítulos e artigos. **A página do Planalto não tem sumário**; o sumário é um acréscimo pedido pelo dono. Decida com ele se o bloco do brasão entra (se entrar, não use hotlink do `Brastra.gif`: baixe e versione).

### Sumário impresso
- Sai **na primeira(s) página(s) de toda impressão**, antes do primeiro diploma, com título "SUMÁRIO" centralizado, no mesmo estilo tipográfico.
- Conteúdo por escopo:
  - **Imprimir tudo:** 6 agrupamentos → diplomas (→ títulos/capítulos, se a Fase 2 item 6 estiver pronta).
  - **Imprimir agrupamento:** só os diplomas desse agrupamento.
  - **Imprimir diploma:** só os títulos/capítulos dele (se não houver estrutura, omita o sumário).
- Gere o sumário a partir de `legalGroups` + dados carregados (a mesma fonte do índice lateral), não à mão. Cada diploma começa em **página nova** (`break-before:page`), sem página vazia entre eles.
- **Números de página:**
  - Rodapé nativo funciona neste Chrome (testei `@page{@bottom-center{content:counter(page)}}`). Use.
  - **`target-counter()` no sumário não funcionou** no Chrome 153 que testei (a declaração foi descartada e os números não saíram). Portanto: entregue primeiro o sumário **sem** número de página (a ordem e a quebra de página já orientam); como melhoria opcional, ative números de página com **Paged.js** (versão fixada, carregada só ao imprimir) e valide com a apostila completa antes de adotar — pode ficar lento com milhares de páginas.

## 6. Verificação final (obrigatória)

Use Playwright + Chrome headless e `pypdf`. Roteiro que funcionou:

1. Servir a pasta (`python -m http.server`) com um `data/legislacao.json` real (ou de teste gerado pelas funções do próprio script).
2. Abrir `legislacao.html`, capturar `pageerror` e `console`.
3. Para cada modo, adicionar as classes que `printSelection` usa (`print-all`; `print-mode print-doc` + `print-target`) e chamar `page.pdf(prefer_css_page_size=True)` com `emulate_media("print")`.
4. Verificar com `pypdf`: (a) **nenhuma página sem texto**; (b) a página 1 contém "SUMÁRIO"; (c) todo artigo impresso começa com "Art."; (d) cada diploma inicia em página nova; (e) nenhum "Art. N" duplicado ou falso; (f) rasterizar (`pdftoppm -r 70`) 3 páginas e olhar: recuo de 38px, justificado, Arial 10pt.
5. Na tela: título do diploma legível, busca funcionando, status oculto quando o JSON carrega.

## 7. O que eu não consegui verificar

- O site publicado e o resultado do GitHub Actions (sem acesso à API do repositório a partir desta sessão).
- O HTML cru do Planalto e as medidas exatas da impressão dele (a ferramenta de leitura só devolveu Markdown, e a rede do shell bloqueia o domínio).
- O comportamento com os PDFs reais do TJSP e com o HTML real da ALESP.

Se algo divergir do que está aqui, confie no que você medir e registre a diferença.
