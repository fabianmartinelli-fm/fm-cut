# Créditos e licenças de terceiros

O **Editor de Vídeos com IA** (skill `/fm-cut`) é distribuído sob licença MIT (ver `LICENSE`). Ele se apoia no
trabalho abaixo, e cada projeto mantém a própria licença.

| Projeto | Papel no Editor de Vídeos com IA | Licença |
|---|---|---|
| [Edvid](https://github.com/fillrochaa/edvid) — Creator Factory | Base da skill: método de edição, helpers, preview, templates Remotion. O Editor de Vídeos com IA é um fork adaptado. | MIT |
| [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | Trilha sonora com IA, gerada localmente. É instalado à parte, em `~/.cache/fm-cut/`, e não vem dentro deste repositório. | MIT (código e pesos) |
| [WhisperX](https://github.com/m-bain/whisperX) | Transcrição com alinhamento por palavra | BSD-2-Clause |
| [Remotion](https://www.remotion.dev) | Render da Fase 2 (legendas, gráficos, tela dividida) | [Remotion License](https://www.remotion.dev/license) — grátis para pessoas físicas, organizações sem fins lucrativos e empresas com até 3 funcionários. Empresas maiores precisam de uma Company License. |
| [FFmpeg](https://ffmpeg.org) | Corte, cor, mixagem | LGPL/GPL (usado como programa externo) |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Baixar vídeo a partir de link | Unlicense |

## Sobre ser gratuito

Todo o fluxo do Editor de Vídeos com IA roda na sua máquina, sem conta e sem chave de API:
transcrição, corte, cor, legendas, gráficos, trilha com IA e legenda da
postagem. Só duas coisas pedem atenção:

- **Remotion.** Se você usa o Editor de Vídeos com IA numa empresa com mais de 3 funcionários,
  a Fase 2 exige a licença de empresa do Remotion.
- **Chaves opcionais** para imagens ilustrativas (Pexels, Google). Sem elas, o
  Editor de Vídeos com IA usa o Wikimedia Commons, que é livre.

A música gerada pelo ACE-Step pode ser usada comercialmente (licença MIT). A
responsabilidade pelo conteúdo que você publica continua sendo sua.
