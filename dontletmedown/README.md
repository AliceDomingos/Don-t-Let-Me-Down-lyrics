# don't let me down 🎸

Show visual de *Don't Let Me Down* (The Beatles, 1969) sincronizado com a batida da música: janelinhas flutuantes por cima da área de trabalho + letra no terminal.

A cada bumbo, um anel se expande no centro da tela. No refrão, **"DON'T LET ME DOWN"** despenca do topo em cartazes laranja que crescem a cada repetição até ocupar o monitor inteiro. Nos versos, a letra entra palavra por palavra, com a palavra-chave em destaque. Na ponte, um véu roxo tinge a tela e um coração pulsa no ritmo. Nos gritos do John (*Hey!!*, *Ow!*), a tela pisca. Faíscas douradas, vento e um terminal com VU, contador de compasso e barra de progresso completam a cena.

## Como funciona

- **Batidas** foram extraídas do áudio com `librosa` (76 BPM, 295 batidas) e salvas em `beats.json`. Como a banda não toca em cima de metrônomo, o show usa os tempos reais de cada batida, não um BPM fixo.
- **Seções** (intro, refrões, versos, ponte, coda) foram detectadas pela sequência de acordes e pela repetição do primeiro refrão ao longo da música → `secoes.json`.
- **Letra** sincronizada linha a linha, com tipo (grito / verso / ponte / grito solto) e palavras-chave marcadas com `*asteriscos*` → `letra.json`.
- **Animação** em `tkinter`: cada elemento é uma janela sem borda, sempre por cima, com fade via `-alpha` e fundo transparente por cor-chave. Áudio com `pygame-ce`.

## Rodar

```powershell
pip install -r requirements.txt
python dontletmedown.py            # o show completo
python dontletmedown.py --de 80    # começa do segundo 80 (ex.: a ponte)
python dontletmedown.py --sem-som  # só a animação
```

Coloque o áudio na pasta como `dontletmedown.mp3` (não está no repositório). **Esc** ou **Ctrl+C** encerra.

Fontes usadas: [Anton](https://fonts.google.com/specimen/Anton) (grito), Cooper Black (palavra-chave) e Bookman Old Style itálico (verso). Se alguma faltar, cai para Impact / Georgia.

## Ferramentas

| Arquivo | Para que serve |
|---|---|
| `calibrar.py --batidas` | toca a música piscando a cada batida detectada, pra conferir de ouvido |
| `calibrar.py --secoes` | toca mostrando em que seção a música está |
| `calibrar.py --calibrar` | marca o início de cada seção na mão (Enter em cada uma) |
| `preview_fontes.py` | prévia da tipografia, trocando fontes com o teclado |

Cores, fontes, tamanhos e posições dos cartazes ficam no topo de `dontletmedown.py`.

Só para Windows (usa `-transparentcolor` e fontes do sistema).
