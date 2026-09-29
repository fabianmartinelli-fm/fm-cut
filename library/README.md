# Biblioteca local de marcas

Aqui ficam as logos oficiais, os **mascotes e símbolos** das marcas que aparecem
nos seus vídeos.

- **Pré-carregadas:** ~46 logos e ~13 mascotes/símbolos de tecnologia e IA
  (OpenAI, Claude, Gemini, NVIDIA, a baleia do DeepSeek, o Tux…). Elas são
  baixadas do Wikimedia Commons pelo instalador; a lista está em
  `seed_brands.json`.
- **A sua empresa (e as dos seus clientes):** a biblioteca vem sem nenhuma
  marca pessoal. Suba a logo oficial em **Mídia → Marcas → + Importar** no
  preview, de preferência PNG com fundo transparente ou SVG, com o nome e os
  apelidos da marca. A partir daí, toda edição que citar a empresa usa esse
  arquivo, sem alteração.
- **Encontradas na edição:** quando o editor procura uma logo oficial que ainda
  não está aqui, ela é guardada para as próximas edições.

- `logos/<marca>.<png|svg|webp|jpg>`: o arquivo da logo, sem nenhuma alteração.
- `logos/index.json`: o nome da marca, apelidos, a fonte e a data em que entrou.

Tudo nesta pasta é **seu**. O git ignora estes arquivos e o instalador preserva
a pasta nas atualizações.

Gerenciar pelo terminal:

```bash
uv run python helpers/brand_library.py list
uv run python helpers/brand_library.py find "NVIDIA"
uv run python helpers/brand_library.py find "Claude" --kind mascote
uv run python helpers/brand_library.py seed          # baixa de novo a lista
uv run python helpers/brand_library.py remove nvidia
```
