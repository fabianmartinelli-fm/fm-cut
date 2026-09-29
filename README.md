# Editor de Vídeos com IA

**Skill `/fm-cut` · FM Solutions**

**Editor de vídeo por conversa, gratuito e local.** Você coloca o material bruto
numa pasta, abre seu agente de IA ali dentro e diz *"edita isso num Reels"*. Ele
transcreve, escolhe as melhores tomadas, corta respiros e erros, corrige a cor,
põe legenda animada, gráficos, tela dividida e trilha sonora, e no fim escreve a
legenda da postagem para cada rede.

Funciona em **short-form vertical** (Reels, TikTok, Shorts) e **longform
horizontal** (YouTube), com **Claude Code**, **Codex** e **Gemini/Antigravity**.

> O Editor de Vídeos com IA é um fork da [FM Solutions](https://fmsolutions.ai) do
> **[Edvid](https://github.com/fillrochaa/edvid)**, criado pela **Creator Factory**
> (MIT). O método, a base da skill e o preview vêm do Edvid, e o crédito é deles.
> As adaptações listadas abaixo são nossas. Detalhes em [NOTICE.md](NOTICE.md).

---

## Por que usar

- **Sem conta, sem chave, sem crédito.** A transcrição (WhisperX) e a trilha
  sonora com IA (ACE-Step 1.5) rodam **na sua máquina**.
- **Você aprova antes de continuar.** Primeiro sai o corte limpo. Só depois de
  você aprovar entram legendas e gráficos, e é você quem escolhe o estilo numa
  tela de preview.
- **Preview interativo.** Linha do tempo com filmstrip e forma de onda, ajuste
  de corte arrastando a borda do trecho, e marcações de correção com a tecla `M`.
- **Termina pronto para postar.** Vídeo final em 1080×1920, normalizado para as
  redes, com a legenda da postagem escrita por rede.

## O que a FM Solutions acrescentou ao Edvid

| Adaptação | O que faz |
|---|---|
| **Trilha com IA local e gratuita** | Troca o Treblo (pago, com conta) pelo [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5), licença MIT, que roda no Mac (Apple Silicon), NVIDIA, AMD e Intel. A trilha entra no vídeo final da Fase 2, sem uma etapa separada depois. |
| **Fase 3: legenda da postagem** | Toda edição termina com a legenda de Instagram, TikTok, YouTube Shorts (com título) e LinkedIn, mais hashtags e palavras-chave de busca, na aba **Postagem** do preview. Lá dá para editar, tirar e pôr hashtags e copiar com um clique. |
| **Identidade visual FM Solutions** | Preview com a paleta navy/azul/roxo e tipografia Inter. |
| **Biblioteca de marcas** | ~46 logos e ~13 mascotes/símbolos de tecnologia e IA, baixados do Wikimedia na instalação (PNG transparente + SVG). Você sobe a logo da **sua empresa** em Mídia → Marcas, e o editor passa a usá-la sempre, sem alterar a marca. |
| **Legenda empilhada na tela dividida** | Nos trechos de tela dividida, a legenda sobe para a emenda da tela em vez de ficar em cima do rosto. |

---

## Instalação

### 1. Os programas (uma vez)

- **`uv`**: gerenciador de Python. Também instala o Python certo.
- **`ffmpeg`**: corte, cor e render.
- **`node`** (18+): Remotion, usado para legendas e gráficos.
- **`git`**: instala a trilha com IA.

**macOS** (Terminal, com [Homebrew](https://brew.sh)):

```bash
brew install uv ffmpeg node git
```

**Windows** (PowerShell):

```powershell
winget install astral-sh.uv Gyan.FFmpeg OpenJS.NodeJS.LTS Git.Git
```

**Linux**: `sudo apt install ffmpeg nodejs npm git` e o `uv` pelo instalador
oficial: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

**Feche e reabra o terminal** depois de instalar. Programas novos só aparecem
numa janela nova.

### 2. Instale o Editor de Vídeos com IA (um comando)

```bash
uv run https://raw.githubusercontent.com/fabianmartinelli-fm/fm-cut/main/fm_cut_install.py
```

É o mesmo comando no Mac, no Windows e no Linux. O instalador descobre qual
agente você usa, instala a skill e a skill do Remotion, instala as dependências
e confere `ffmpeg`, `node` e `uv` no fim.

**Quer a trilha com IA já instalada?** Acrescente `--music`. Isso baixa o
ACE-Step 1.5 e os modelos, cerca de 10 GB uma vez só. Sem essa opção, o Editor de Vídeos com IA
instala na primeira vez que você pedir trilha.

```bash
uv run https://raw.githubusercontent.com/fabianmartinelli-fm/fm-cut/main/fm_cut_install.py --music
```

### Atualizar

Rode o mesmo comando de novo.

---

## Primeiro uso

1. Coloque seus vídeos brutos numa pasta.
2. Abra o agente **dentro dessa pasta**.
3. Chame `/fm-cut` e diga o que quer: *"faz a edição completa desse vídeo para
   Reels"*.

Tudo o que é gerado vai para a subpasta `edit/`. Seus arquivos originais não são
tocados.

### As 3 fases

1. **Corte.** Na aba Corte você importa os vídeos (arraste para ordenar),
   escolhe o formato de saída (9:16, 16:9, 4:5, 1:1) e clica em **Processar
   vídeos**: melhores tomadas, sem respiros nem erros, cor corrigida. →
   *você aprova*
2. **Visual.** No card de Estilo: tipo de edição (limpa ou tela dividida),
   headline, legenda, cor de destaque, flash na transição (tipo, força e onde),
   zooms e trilha com IA. Sai o `final.mp4`, e o botão **Salvar vídeo** grava
   onde você escolher.
3. **Postagem.** Legenda por rede, hashtags e palavras-chave, prontas para copiar.

---

## Sobre a trilha com IA

A trilha é composta pelo **ACE-Step 1.5** no seu computador, a partir do tema e
do clima do vídeo: gênero, instrumentos, andamento e mood. É **instrumental**,
fica mixada por baixo da voz e **pode ser usada comercialmente** (MIT).

- O motor fica fora da skill, em `~/.cache/fm-cut/ACE-Step-1.5` (mude com
  `FMCUT_MUSIC_DIR`), num ambiente próprio.
- Espaço: ~10 GB de modelos, baixados uma vez.
- Se preferir uma música sua, mande o mp3 e o Editor de Vídeos com IA mixa do mesmo jeito.

## Sobre a transcrição

O Editor de Vídeos com IA usa o [WhisperX](https://github.com/m-bain/whisperX): transcreve com o
Whisper e faz **alinhamento forçado** de cada palavra contra o áudio. É isso que
deixa a legenda animada sincronizada. Os modelos baixam na primeira transcrição
(alguns GB) e ficam em cache.

---

## Problemas comuns

**O agente não encontra a skill.** Reinicie o agente. O instalador imprime onde
instalou.

**`ModuleNotFoundError`.** Rode `uv sync --directory <pasta que o instalador imprimiu>`.

**A primeira transcrição ou trilha parece travada.** Está baixando modelos.
Acontece uma vez só.

**Preview aberto e vazio no macOS.** Falta dar permissão de acesso à pasta
(Ajustes → Privacidade → Arquivos e Pastas). Se a permissão já estiver ligada,
reinicie o Mac.

---

## Contribuir

Para desenvolver, clone o repositório onde você guarda seus projetos e crie um
link para a pasta de skills (formato em [install.md](install.md)). O instalador
detecta um clone git e não mexe nele.

## Licença

MIT. Veja [LICENSE](LICENSE) e os créditos de terceiros em [NOTICE.md](NOTICE.md).
