# TJSP — Bloco II (Direito)

Site de consulta para o programa jurídico do edital do Tribunal de Justiça de São Paulo.

## Apostila de legislação compilada

A página principal de leitura é **[legislacao.html](legislacao.html)**. Ela apresenta o texto dos dispositivos previstos no edital, em sequência, por diploma, com busca por artigo/expressão e impressão em formato A4.

A apostila é gerada automaticamente no workflow de publicação a partir de fontes oficiais:
- Códigos Penal, de Processo Penal e de Processo Civil e Constituição Federal — Planalto.
- Leis federais nº 8.429/1992, 9.099/1995 e 12.153/2009 — Planalto.
- Lei estadual nº 10.261/1968 e LC estadual nº 1.111/2010 — ALESP.
- Resoluções, Regimento Interno e Normas da Corregedoria — TJSP.

O compilador conserva somente os recortes previstos no programa para os códigos e leis em que o edital delimitou artigos. Atos indicados sem recorte de artigos são disponibilizados em inteiro teor. A Resolução TJSP nº 963/2025 continua vinculada ao seu inteiro teor oficial no sistema GCN/e-SAJ, porque a página de consulta é entregue como aplicação JavaScript e não como arquivo estático.

## Apoio de revisão

A página **[index.html](index.html)** mantém sumário temático, sínteses, busca por assunto e marcação de tópicos revisados. É material secundário de apoio e não substitui a apostila legal.

## Atualização e fidelidade

A geração baixa as fontes oficiais novamente a cada publicação. O script remove versões expressamente riscadas em HTML quando a marcação de revogação está disponível. Em PDFs oficiais, mantém o conteúdo extraído do documento. Confira sempre a publicação original, notas de alteração, vigência e eventuais retificações antes da prova.

## Publicação

O workflow `.github/workflows/pages.yml`:
1. baixa e compila os textos oficiais;
2. gera `data/legislacao.json`;
3. publica a página e os dados no GitHub Pages.

Em **Settings → Pages → Build and deployment**, a origem deve estar configurada como **GitHub Actions**.
