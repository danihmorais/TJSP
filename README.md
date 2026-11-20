# TJSP — Bloco II (Direito)

Apostila de legislação do conteúdo programático do concurso do Tribunal de Justiça de São Paulo.

## Legislação compilada

A página **[legislacao.html](legislacao.html)** é a apostila principal. Os diplomas são agrupados conforme as seis disciplinas do edital:

1. Direito Penal.
2. Direito Processual Penal.
3. Direito Processual Civil.
4. Direito Constitucional.
5. Direito Administrativo.
6. Legislação Interna.

A Lei nº 9.099/1995 é apresentada em dois recortes, dentro de suas disciplinas: arts. 3º a 19 em Direito Processual Civil; arts. 60 a 83, 88 e 89 em Direito Processual Penal.

## Leitura e impressão

- Imprimir toda a apostila, os agrupamentos do edital ou um diploma individual.
- Aplicar na impressão a tipografia do texto legal do Planalto (Arial 10 pt, entrelinha de 12 pt, alinhamento justificado, recuo de 38 px e margens de parágrafo de 20 px), preservando os atributos tipográficos originais presentes no HTML da fonte.
- Preservar, quando a fonte é HTML, parágrafos, listas, links, destaques, atributos de fonte e espaçamentos originais. Em PDFs, recompõe-se a hierarquia dos dispositivos usando a mesma base tipográfica.

## Fontes e atualização

O workflow baixa e compila as fontes oficiais a cada publicação, gerando `data/legislacao.json`. Os códigos e leis com recorte são limitados aos dispositivos indicados no edital. Os atos indicados sem intervalo são incluídos em inteiro teor ou nos recortes expressos do edital.

## Apoio de revisão

A página **[index.html](index.html)** oferece sumário temático e sínteses para revisão. Ela é complementar à apostila e não substitui o texto legal.

## Publicação

O workflow `.github/workflows/pages.yml` compila os diplomas, valida a extração em pull requests e publica no GitHub Pages após push na `main`. Em **Settings → Pages → Build and deployment**, a origem deve estar configurada como **GitHub Actions**.
