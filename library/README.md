# Biblioteca local de marcas

Aqui ficam as logos oficiais das marcas que aparecem nos seus vídeos. Elas são
enviadas por você no painel **Mídia → Marcas** do preview, ou guardadas pelo
FM Cut quando ele encontra a logo oficial numa fonte confiável.

- `logos/<marca>.<png|svg|webp|jpg>`: o arquivo da logo, sem nenhuma alteração.
- `logos/index.json`: o nome da marca, apelidos, a fonte e a data em que entrou.

Tudo nesta pasta é **seu**. O git ignora estes arquivos e o instalador preserva
a pasta nas atualizações.

Gerenciar pelo terminal:

```bash
uv run python helpers/brand_library.py list
uv run python helpers/brand_library.py find "NVIDIA"
uv run python helpers/brand_library.py remove nvidia
```
