# Guia de Estudos — Bloco II (Direito)

Site estático de consulta e revisão do conteúdo jurídico do Bloco II do edital do Tribunal de Justiça do Estado de São Paulo.

## Funcionalidades

- Sumário navegável por disciplina.
- Síntese temática agrupada pelos artigos e atos normativos do edital.
- Busca por artigo, expressão, assunto e norma.
- Marcação de tópicos revisados, com progresso salvo localmente no navegador.
- Impressão e exportação para PDF pelo navegador.
- Links para legislação, resoluções, Regimento Interno e Normas da Corregedoria em fontes oficiais.
- Layout responsivo, sem backend, banco de dados ou dependências de build.

## Publicação no GitHub Pages

O workflow `.github/workflows/pages.yml` publica automaticamente o conteúdo da branch `main` no GitHub Pages após cada push.

Depois de integrar a alteração à `main`, confirme em **Settings → Pages → Build and deployment** que a origem está configurada como **GitHub Actions**. A primeira execução do workflow fará o deploy.

## Conteúdo e atualização

O escopo acompanha o programa do Bloco II informado para o concurso. As sínteses são material autoral de estudo, não transcrição oficial nem parecer jurídico. A legislação e os atos internos podem mudar; confira sempre as versões oficiais vinculadas no próprio site.

Referência de atualização das fontes consultadas: 20/11/2026. O arquivo oficial de Normas da Corregedoria consultado indica atualização em 22/10/2026; o Regimento Interno consultado está atualizado em 12/11/2026.

## Desenvolvimento

O site é uma página única em `index.html`. Não há etapa de compilação: basta abrir o arquivo em navegador ou hospedar o repositório no GitHub Pages.
