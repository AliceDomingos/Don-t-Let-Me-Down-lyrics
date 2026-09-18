"""
don't let me down — the beatles
show visual: janelinhas flutuantes por cima da área de trabalho + terminal,
sincronizadas com a batida (beats.json), as seções (secoes.json) e a letra (letra.json)

uso:
  python dontletmedown.py            # o show completo
  python dontletmedown.py --de 80    # começa do segundo 80 (ex.: só a ponte)
  python dontletmedown.py --sem-som  # só a animação, sem áudio

  Esc (no terminal) ou Ctrl+C encerra.

dependência: pip install pygame-ce
"""

import os
import re
import sys
import json
import math
import time
import random
import traceback
import argparse
import tkinter as tk
from tkinter import font as tkfont

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
try:
    import pygame
except ImportError:
    sys.exit("falta o pygame. rode:  pip install pygame-ce")

try:
    import msvcrt  # pra detectar Esc no terminal (windows)
except ImportError:
    msvcrt = None

# ─────────────────────────── ARQUIVOS ───────────────────────────

AQUI = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(AQUI, "dontletmedown.mp3")
BEATS = json.load(open(os.path.join(AQUI, "beats.json"), encoding="utf-8"))["batidas"]
SECOES = json.load(open(os.path.join(AQUI, "secoes.json"), encoding="utf-8"))
LETRA = json.load(open(os.path.join(AQUI, "letra.json"), encoding="utf-8"))["linhas"]

# ─────────────────────────── PALETA ───────────────────────────

AZUL     = "#0c1445"   # azul-noite (caixas dos versos, texto do cartaz)
LARANJA  = "#ff5e1a"   # o grito / pulso do refrão
DOURADO  = "#ffd23f"   # rhodes, faíscas, ponte
MAGENTA  = "#ff2e88"   # palavras-chave
CIANO    = "#3ddcff"   # versos, momentos calmos
BRANCO   = "#f4efe6"   # texto de apoio
ROXO     = "#3a0f4f"   # véu da ponte
CINZA    = "#9aa3c7"   # vento

TRANSPARENTE = "#010101"   # cor-chave que o windows deixa invisível

# ─────────────────────────── FONTES ───────────────────────────

FONTE_GRITO = ("Anton", "Impact", "Arial Black")
FONTE_CHAVE = ("Cooper Black", "Rockwell Extra Bold", "Georgia")
FONTE_VERSO = ("Bookman Old Style", "Georgia", "Times New Roman")
FONTE_SIMB  = "Segoe UI Symbol"

# ─────────────────────────── AJUSTES ───────────────────────────

FPS_MS        = 25      # intervalo do laço de animação (ms)
MAX_JANELAS   = 48      # teto de janelinhas vivas ao mesmo tempo
QUEDA         = 1.0     # segundos que o cartaz leva pra cair e quicar
LARGURAS      = {1: 0.30, 2: 0.46, 3: 0.64, 4: 0.92}   # largura do cartaz por repetição (fração da tela)
ALTURAS       = {1: 0.26, 2: 0.42, 3: 0.58, 4: 0.48}   # onde ele pousa (fração da altura)
VENTO_A_CADA  = 0.7     # segundos entre um pontinho de vento e outro

# cores do terminal (ANSI)
RESET = "\033[0m"; DIM = "\033[2m"; BOLD = "\033[1m"
T_LAR = "\033[38;2;255;94;26m"; T_DOU = "\033[38;2;255;210;63m"
T_MAG = "\033[38;2;255;46;136m"; T_CIA = "\033[38;2;61;220;255m"; T_BRA = "\033[38;2;244;239;230m"


# ─────────────────────────── UTIL ───────────────────────────

def fmt(seg):
    seg = max(0, int(seg))
    return f"{seg // 60}:{seg % 60:02d}"


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, f):
    """mistura duas cores hex: f=0 -> a, f=1 -> b"""
    f = min(1.0, max(0.0, f))
    ra, rb = hex2rgb(a), hex2rgb(b)
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * f) for x, y in zip(ra, rb))


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_out_bounce(x):
    n1, d1 = 7.5625, 2.75
    if x < 1 / d1:
        return n1 * x * x
    if x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    if x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    x -= 2.625 / d1
    return n1 * x * x + 0.984375


def escolher_fonte(candidatas, familias):
    for f in candidatas:
        if f in familias:
            return f
    return "Arial"


def preparar_terminal():
    os.system("")  # liga as cores ANSI no terminal do windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def tokens(texto):
    """quebra a linha em (palavra, destaque?) — *assim* marca palavra-chave"""
    out = []
    for m in re.finditer(r"\*([^*]+)\*|(\S+)", texto):
        if m.group(1):
            out.append((m.group(1), True))
        else:
            out.append((m.group(2), False))
    return out


# ─────────────────────────── BASE: JANELINHA ───────────────────────────

class Janela:
    """uma janelinha sem borda, sempre por cima, com fade via -alpha"""

    def __init__(self, show, bg, transparente=False):
        self.show = show
        self.viva = True
        self.nasceu = show.t
        self.win = tk.Toplevel(show.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        self.win.configure(bg=bg)
        if transparente:
            try:
                self.win.attributes("-transparentcolor", TRANSPARENTE)
            except tk.TclError:
                pass
        self._alpha = 0.0
        self._pos = None
        show.elementos.append(self)

    @property
    def idade(self):
        return self.show.t - self.nasceu

    def alpha(self, a):
        a = min(1.0, max(0.0, a))
        if abs(a - self._alpha) > 0.01:
            self._alpha = a
            self.win.attributes("-alpha", a)

    def mover(self, x, y):
        p = (int(x), int(y))
        if p != self._pos:
            self._pos = p
            self.win.geometry(f"+{p[0]}+{p[1]}")

    def medir(self):
        self.win.update_idletasks()
        return self.win.winfo_reqwidth(), self.win.winfo_reqheight()

    def passo(self, t, dt):
        """avança um quadro; devolve False quando quer ser fechada"""
        return True

    def fechar(self):
        if not self.viva:
            return
        self.viva = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ─────────────────────────── ANEL DA BATIDA ───────────────────────────

class Anel(Janela):
    """anel que nasce no centro da tela a cada bumbo e se expande até sumir"""

    DUR = 0.75

    def __init__(self, show, cor, raio_max, grossura):
        super().__init__(show, TRANSPARENTE, transparente=True)
        self.cor, self.rmax, self.grossura = cor, raio_max, grossura
        self.D = int(raio_max * 2 + grossura * 2 + 8)
        self.cv = tk.Canvas(self.win, width=self.D, height=self.D, bg=TRANSPARENTE,
                            highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_oval(0, 0, 0, 0, outline=cor, width=grossura)
        self.mover(show.sw // 2 - self.D // 2, show.sh // 2 - self.D // 2)

    def passo(self, t, dt):
        f = self.idade / self.DUR
        if f >= 1:
            return False
        r = 14 + (self.rmax - 14) * ease_out_cubic(f)
        c = self.D / 2
        self.cv.coords(self.item, c - r, c - r, c + r, c + r)
        self.cv.itemconfig(self.item, width=max(1, self.grossura * (1 - f)))
        self.alpha(1.0 if f < 0.3 else 1 - (f - 0.3) / 0.7)
        return True


# ─────────────────────────── CARTAZ: "DON'T LET ME DOWN" ───────────────────────────

class Cartaz(Janela):
    """o grito do refrão: cartaz que despenca do topo, quica e fica tremendo no ritmo"""

    def __init__(self, show, texto, rep):
        invertido = rep == 4
        bg, fg = (AZUL, LARANJA) if invertido else (LARANJA, AZUL)
        super().__init__(show, bg)
        self.rep = rep
        frac = LARGURAS.get(rep, 0.5)
        if show.climax:
            frac = min(0.95, frac + 0.15)
        # tamanho da fonte pra ocupar `frac` da largura da tela
        w100 = tkfont.Font(family=show.f_grito, size=100).measure(texto)
        tam = max(18, int(100 * frac * show.sw / w100 * 0.88))
        tk.Label(self.win, text=texto, bg=bg, fg=fg, font=(show.f_grito, tam),
                 padx=int(tam * 0.35), pady=int(tam * 0.12)).pack()
        self.w, self.h = self.medir()
        self.x = show.sw // 2 - self.w // 2
        self.y_pouso = int(show.sh * ALTURAS.get(rep, 0.5)) - self.h // 2
        self.y_ini = -self.h - 20
        self.quicou = False
        self.desbote = 0.0        # 0 = cor cheia, 1 = quase invisível
        self.desbote_alvo = 0.0
        self.morrendo = None
        self.mover(self.x, self.y_ini)

    def desbotar(self, alvo):
        self.desbote_alvo = max(self.desbote_alvo, alvo)

    def morrer(self):
        if self.morrendo is None:
            self.morrendo = self.show.t

    def passo(self, t, dt):
        f = min(1.0, self.idade / QUEDA)
        y = self.y_ini + (self.y_pouso - self.y_ini) * ease_out_bounce(f)
        x = self.x
        if f >= 1 / 2.75 and not self.quicou:      # primeiro toque no chão
            self.quicou = True
            self.show.rajada(self.x + self.w // 2, self.y_pouso + self.h,
                             n=18 if self.rep < 4 else 30, forca=1.3)
        if f >= 1:
            x += 4 * self.show.pulso * math.sin(t * 50)   # tremor na batida
            y += 2 * self.show.pulso * math.sin(t * 37)
        self.mover(x, y)

        self.desbote += (self.desbote_alvo - self.desbote) * min(1, dt * 4)
        a = min(1.0, self.idade / 0.15) * (1 - 0.6 * self.desbote)
        if self.morrendo is not None:
            k = (t - self.morrendo) / 0.7
            if k >= 1:
                return False
            a *= 1 - k
            self.mover(x, y + 40 * k)
        self.alpha(a)
        return True


# ─────────────────────────── LINHA DE VERSO (palavra por palavra) ───────────────────────────

class Palavra(Janela):
    """caixinha com uma palavra do verso; a palavra-chave é maior e colorida"""

    def __init__(self, show, texto, chave, fonte, cor_bg, cor_fg):
        super().__init__(show, cor_bg)
        self.chave = chave
        tk.Label(self.win, text=texto, bg=cor_bg, fg=cor_fg, font=fonte,
                 padx=int(12 * show.esc), pady=int(6 * show.esc)).pack()
        self.w, self.h = self.medir()

    def passo(self, t, dt):
        return True   # quem manda é a Linha


class Linha:
    """controla as palavras de uma linha: layout, entrada uma a uma, deriva e fade"""

    def __init__(self, show, texto, ponte, dur_total, y_frac):
        self.show = show
        self.nasceu = show.t
        self.morrendo = None
        self.palavras = []
        toks = tokens(texto)

        esc = show.esc
        tam_v, tam_c = int(28 * esc), int(38 * esc)
        f_v = (show.f_verso, tam_v, "italic")
        f_c = (show.f_chave, tam_c)
        cor_txt = BRANCO if ponte else (CIANO if show.linha_par else BRANCO)
        cor_chave = DOURADO if ponte else MAGENTA
        show.linha_par = not show.linha_par

        for txt, chave in toks:
            p = Palavra(show, txt, chave, f_c if chave else f_v,
                        cor_chave if chave else AZUL, AZUL if chave else cor_txt)
            self.palavras.append(p)

        gap = int(8 * esc)
        total = sum(p.w for p in self.palavras) + gap * (len(self.palavras) - 1)
        self.x0 = show.sw // 2 - total // 2
        self.y = int(show.sh * y_frac)
        xs, x = [], self.x0
        for p in self.palavras:
            xs.append(x)
            x += p.w + gap
        self.xs = xs
        # cada palavra entra num instante; a linha toda entra em ~55% do tempo até a próxima
        span = min(2.6, dur_total * 0.55)
        n = len(self.palavras)
        self.entradas = [self.nasceu + span * i / max(1, n - 1) for i in range(n)]
        self.fase = random.uniform(0, 6.28)

    def morrer(self):
        if self.morrendo is None:
            self.morrendo = self.show.t

    def passo(self, t, dt):
        idade = t - self.nasceu
        deriva = 9 * idade + 14 * math.sin(self.fase + idade * 0.6)   # vento empurra pra direita
        if self.morrendo is not None:
            k = (t - self.morrendo) / 1.0
            if k >= 1:
                for p in self.palavras:
                    p.fechar()
                return False
        else:
            k = 0
        for p, x, te in zip(self.palavras, self.xs, self.entradas):
            if not p.viva:
                continue
            e = t - te
            if e < 0:
                p.alpha(0)
                continue
            pop = min(1.0, e / 0.22)
            sobe = (1 - pop) * 14
            estica = 1 + (0.25 * math.exp(-e * 4) if p.chave else 0)   # a palavra-chave dá um pulso
            y = self.y - p.h // 2 - sobe - (p.h * (estica - 1)) / 2
            p.mover(x + deriva, y)
            p.alpha(pop * (1 - k))
        return True

    def fechar(self):
        for p in self.palavras:
            p.fechar()


# ─────────────────────────── FAÍSCAS ───────────────────────────

class Rajada(Janela):
    """uma rajada de faíscas douradas, todas desenhadas numa só janela transparente"""

    def __init__(self, show, cx, cy, n=12, forca=1.0, dur=1.3):
        super().__init__(show, TRANSPARENTE, transparente=True)
        self.dur = dur
        self.L = int(min(480, 300 * forca) * show.esc)
        self.cv = tk.Canvas(self.win, width=self.L, height=self.L, bg=TRANSPARENTE,
                            highlightthickness=0)
        self.cv.pack()
        self.parts = []
        for _ in range(n):
            ang = random.uniform(-math.pi * 0.85, -math.pi * 0.15)   # pra cima
            v = random.uniform(120, 340) * forca * show.esc
            tam = random.randint(9, 20)
            cor = random.choice((DOURADO, DOURADO, LARANJA, BRANCO))
            item = self.cv.create_text(self.L / 2, self.L - 10, text=random.choice("✦✧·•"),
                                       fill=cor, font=(FONTE_SIMB, tam))
            self.parts.append([item, math.cos(ang) * v, math.sin(ang) * v, self.L / 2, self.L - 10.0])
        self.mover(cx - self.L // 2, cy - self.L + 10)

    def passo(self, t, dt):
        f = self.idade / self.dur
        if f >= 1:
            return False
        g = 520 * self.show.esc
        for p in self.parts:
            p[2] += g * dt
            p[3] += p[1] * dt
            p[4] += p[2] * dt
            self.cv.coords(p[0], p[3], p[4])
        self.alpha(1.0 if f < 0.5 else 1 - (f - 0.5) / 0.5)
        return True


# ─────────────────────────── VENTO ───────────────────────────

class Vento(Janela):
    """pontinho/tracinho que atravessa a tela na horizontal, lembrando o vento do telhado"""

    def __init__(self, show):
        super().__init__(show, TRANSPARENTE, transparente=True)
        simb = random.choice("·─‥·—")
        tam = random.randint(9, 16)
        tk.Label(self.win, text=simb, bg=TRANSPARENTE, fg=CINZA, font=(FONTE_SIMB, tam)).pack()
        self.w, self.h = self.medir()
        self.dur = random.uniform(7, 14)
        self.y = random.randint(int(show.sh * 0.05), int(show.sh * 0.95))
        self.brilho = random.uniform(0.35, 0.8)
        self.fase = random.uniform(0, 6.28)
        self.mover(-self.w, self.y)

    def passo(self, t, dt):
        f = self.idade / self.dur
        if f >= 1:
            return False
        x = -self.w + (self.show.sw + self.w) * f
        y = self.y + 18 * math.sin(self.fase + self.idade * 0.7)
        self.mover(x, y)
        a = self.brilho
        if f < 0.1:
            a *= f / 0.1
        elif f > 0.85:
            a *= (1 - f) / 0.15
        self.alpha(a)
        return True


# ─────────────────────────── FLASH ───────────────────────────

class Flash(Janela):
    """a tela inteira pisca laranja por um instante (nos gritos do john)"""

    DUR = 0.18

    def __init__(self, show, cor=LARANJA, pico=0.55):
        super().__init__(show, cor)
        self.pico = pico
        self.win.geometry(f"{show.sw}x{show.sh}+0+0")

    def passo(self, t, dt):
        f = self.idade / self.DUR
        if f >= 1:
            return False
        self.alpha(self.pico * (1 - abs(2 * f - 1)))   # sobe e desce em triângulo
        return True


# ─────────────────────────── GRITO SOLTO ───────────────────────────

class GritoSolto(Janela):
    """'Hey!!', 'Ow!'... aparece num canto aleatório e some"""

    DUR = 1.4

    def __init__(self, show, texto):
        super().__init__(show, TRANSPARENTE, transparente=True)
        tam = int(random.randint(40, 64) * show.esc)
        tk.Label(self.win, text=texto, bg=TRANSPARENTE, fg=random.choice((DOURADO, BRANCO, LARANJA)),
                 font=(show.f_grito, tam)).pack()
        self.w, self.h = self.medir()
        self.x = random.randint(int(show.sw * 0.05), max(int(show.sw * 0.05), int(show.sw * 0.95) - self.w))
        self.y = random.randint(int(show.sh * 0.08), max(int(show.sh * 0.08), int(show.sh * 0.85) - self.h))
        self.vx = random.uniform(-40, 40)
        self.mover(self.x, self.y)

    def passo(self, t, dt):
        f = self.idade / self.DUR
        if f >= 1:
            return False
        self.mover(self.x + self.vx * self.idade, self.y - 30 * f)
        self.alpha(min(1, f / 0.08) * (1 - f) ** 0.6)
        return True


# ─────────────────────────── VÉU DA PONTE + CORAÇÃO ───────────────────────────

class Veu(Janela):
    """véu roxo semi-transparente que tinge a área de trabalho durante a ponte"""

    ALVO = 0.38

    def __init__(self, show):
        super().__init__(show, ROXO)
        self.win.geometry(f"{show.sw}x{show.sh}+0+0")
        self.morrendo = None

    def morrer(self):
        if self.morrendo is None:
            self.morrendo = self.show.t

    def passo(self, t, dt):
        if self.morrendo is not None:
            k = (t - self.morrendo) / 0.6
            if k >= 1:
                return False
            self.alpha(self.ALVO * (1 - k))
        else:
            self.alpha(self.ALVO * min(1, self.idade / 2.0))
        return True


class Coracao(Janela):
    """coração dourado no centro que pulsa a cada batida (só na ponte)"""

    def __init__(self, show):
        super().__init__(show, TRANSPARENTE, transparente=True)
        self.base = int(150 * show.esc)
        self.L = int(self.base * 2.2)
        self.cv = tk.Canvas(self.win, width=self.L, height=self.L, bg=TRANSPARENTE,
                            highlightthickness=0)
        self.cv.pack()
        self.brilho = self.cv.create_text(self.L / 2, self.L / 2, text="♥", fill=mix(ROXO, DOURADO, 0.45),
                                          font=(FONTE_SIMB, self.base))
        self.item = self.cv.create_text(self.L / 2, self.L / 2, text="♥", fill=DOURADO,
                                        font=(FONTE_SIMB, self.base))
        self.tam_atual = -1
        self.morrendo = None
        self.mover(show.sw // 2 - self.L // 2, show.sh // 2 - self.L // 2)

    def morrer(self):
        if self.morrendo is None:
            self.morrendo = self.show.t

    def passo(self, t, dt):
        p = self.show.pulso
        tam = int(self.base * (0.82 + 0.28 * p))
        if tam != self.tam_atual:
            self.tam_atual = tam
            self.cv.itemconfig(self.item, font=(FONTE_SIMB, tam))
            self.cv.itemconfig(self.brilho, font=(FONTE_SIMB, int(tam * 1.25)))
        if self.morrendo is not None:
            k = (t - self.morrendo) / 0.6
            if k >= 1:
                return False
            self.alpha(1 - k)
        else:
            self.alpha(min(1, self.idade / 1.5))
        return True


# ─────────────────────────── TERMINAL ───────────────────────────

SKYLINE = [
    "        ▄▄       ▄▄▄▄      ▄▄        ▄▄▄▄▄     ▄▄     ▄▄▄▄▄▄     ▄▄▄    ▄▄",
    "  ▄▄▄▄▄████▄▄▄▄▄██████▄▄▄▄████▄▄▄▄▄▄███████▄▄▄████▄▄▄████████▄▄▄█████▄▄████▄▄",
]


class Terminal:
    """letra com máquina de escrever + linha de status (VU, compasso, progresso, seção)"""

    def __init__(self, show):
        self.show = show
        self.atual = ""
        self.fila = ""
        self.cor = T_CIA
        self.ultimo_status = 0
        self.vu = [0.0] * 14

    def cabecalho(self):
        sys.stdout.write("\033[?25l")
        print()
        for l in SKYLINE:
            print(f"  {DIM}{T_CIA}{l}{RESET}")
        print(f"\n  {T_DOU}★{RESET} {T_LAR}{BOLD}don't let me down{RESET} "
              f"{DIM}— the beatles, 1969{RESET} {T_DOU}★{RESET}   {DIM}Esc pra sair{RESET}\n")

    def escrever(self, texto, cor, continuar=False):
        if continuar:
            self.fila += "  " + texto
            return
        if self.atual or self.fila:
            self.atual += self.fila
            self.fila = ""
            sys.stdout.write(f"\r\033[K  {self.colorir(self.atual)}\n\033[K")
        self.atual = ""
        self.fila = texto
        self.cor = cor

    def colorir(self, texto):
        cor = self.cor
        texto = re.sub(r"\*([^*]+)\*", f"{BOLD}{T_MAG}\\1{RESET}{cor}", texto)
        texto = re.sub(r"(\([^)]*\)|Hey!!|Please)", f"{DIM}\\1{RESET}{cor}", texto)
        return f"{cor}{texto}{RESET}"

    def status(self):
        s = self.show
        p = s.pulso
        for i in range(len(self.vu)):
            alvo = p * random.uniform(0.3, 1.0) * (1.0 if s.secao.startswith("refrao") else 0.6)
            self.vu[i] = max(alvo, self.vu[i] * 0.75)
        blocos = "▁▂▃▄▅▆▇█"
        vu = "".join(blocos[min(7, int(v * 7.99))] for v in self.vu)
        n = s.batida_idx % 4
        comp = "".join(f"{T_LAR}●{RESET}" if k == n else f"{DIM}○{RESET}" for k in range(4))
        frac = min(1.0, max(0.0, s.t / SECOES["fim"]))
        cheio = int(frac * 24)
        barra = f"{T_DOU}{'━' * cheio}{RESET}{DIM}{'─' * (24 - cheio)}{RESET}"
        cor_sec = T_LAR if s.secao.startswith("refrao") else T_DOU if s.secao == "ponte" else T_CIA
        return (f"{T_DOU}{vu}{RESET}  {comp}  {DIM}{fmt(s.t)}{RESET} {barra} "
                f"{DIM}{fmt(SECOES['fim'])}{RESET}  {cor_sec}{BOLD}{s.secao.upper()}{RESET}")

    def tick(self):
        if self.fila:
            k = 2 if len(self.fila) > 25 else 1      # digita mais rápido em linhas longas
            self.atual += self.fila[:k]
            self.fila = self.fila[k:]
        agora = time.perf_counter()
        if agora - self.ultimo_status < 0.06:
            return
        self.ultimo_status = agora
        sys.stdout.write(f"\r\033[K  {self.colorir(self.atual)}\n"
                         f"\033[K  {self.status()}\033[1A\r")
        sys.stdout.flush()

    def final(self):
        sys.stdout.write(f"\r\033[K  {self.colorir(self.atual + self.fila)}\n\033[K\n")
        print(f"  {T_DOU}★{RESET} {DIM}fim{RESET}\n")
        sys.stdout.write("\033[?25h")


# ─────────────────────────── O SHOW ───────────────────────────

class Show:
    def __init__(self, de=0.0, som=True):
        self.de, self.som = de, som
        self.root = tk.Tk()
        self.root.withdraw()
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.esc = self.sh / 1080
        fam = set(tkfont.families())
        self.f_grito = escolher_fonte(FONTE_GRITO, fam)
        self.f_chave = escolher_fonte(FONTE_CHAVE, fam)
        self.f_verso = escolher_fonte(FONTE_VERSO, fam)

        self.elementos = []      # janelinhas vivas
        self.linhas = []         # linhas de verso vivas (controlam suas palavras)
        self.cartazes = []
        self.veu = None
        self.coracao = None
        self.terminal = Terminal(self)

        self.t = de
        self.t0 = None
        self.t_ant = None
        self.pulso = 0.0
        self.t_batida = -10
        self.batida_idx = 0
        self.linha_idx = 0
        self.secao = "intro"
        self.linha_par = True
        self.climax = False
        self.coda = False
        self.encerrando = None
        self.prox_vento = de
        self.prox_chuva = de
        self.slot_y = 0

    # relógio: segundo atual da música
    def agora(self):
        return self.de + time.perf_counter() - self.t0

    # ── ações ──

    def rajada(self, cx, cy, n=12, forca=1.0):
        if len(self.elementos) < MAX_JANELAS and not self.coda:
            Rajada(self, cx, cy, n=n, forca=forca)

    def batida(self, i):
        self.t_batida = self.t
        self.batida_idx = i
        if self.coda:
            if len(self.elementos) < MAX_JANELAS:
                Anel(self, mix(CIANO, "#000000", 0.4), int(min(self.sw, self.sh) * 0.18), 2)
            return
        if self.secao == "ponte":
            return                            # na ponte quem pulsa é o coração
        refrao = self.secao.startswith("refrao")
        cor = LARANJA if refrao else CIANO
        rmax = int(min(self.sw, self.sh) * (0.36 if refrao else 0.22))
        Anel(self, cor, rmax, 14 if refrao else 4)
        if refrao and i % 2 == 0:
            self.rajada(random.randint(int(self.sw * 0.15), int(self.sw * 0.85)),
                        self.sh - 10, n=7 if not self.climax else 14, forca=1.1)

    def linha(self, l):
        tipo, texto = l["tipo"], l["texto"]
        if tipo == "grito":
            for c in self.cartazes:
                c.desbotar(0.9 if l["rep"] == 4 else 0.55)
            c = Cartaz(self, texto.upper(), l["rep"])
            self.cartazes.append(c)
            self.terminal.escrever(texto.upper(), T_LAR)
        elif tipo == "solto":
            Flash(self, LARANJA if self.secao.startswith("refrao") else DOURADO)
            GritoSolto(self, texto)
            self.terminal.escrever(texto, T_LAR, continuar=True)
        else:
            for ln in self.linhas:
                ln.morrer()
            prox = LETRA[self.linha_idx + 1]["t"] if self.linha_idx + 1 < len(LETRA) else self.t + 5
            ponte = tipo == "ponte"
            slots = (0.26, 0.74) if ponte else (0.30, 0.50, 0.68)
            y = slots[self.slot_y % len(slots)]
            self.slot_y += 1
            self.linhas.append(Linha(self, texto, ponte, prox - l["t"], y))
            self.terminal.escrever(texto, T_DOU if ponte else T_CIA)

    def entrar_secao(self, nome, inicial=False):
        self.secao = nome
        if nome.startswith("refrao"):
            for ln in self.linhas:
                ln.morrer()
            if self.veu:
                self.veu.morrer(); self.veu = None
            if self.coracao:
                self.coracao.morrer(); self.coracao = None
            self.climax = nome == "refrao5"
        elif nome.startswith("verso"):
            for c in self.cartazes:
                c.morrer()
        elif nome == "ponte":
            for c in self.cartazes:
                c.morrer()
            self.veu = Veu(self)
            self.coracao = Coracao(self)
        elif nome == "coda":
            self.coda = True
            for c in self.cartazes:
                c.morrer()
            for ln in self.linhas:
                ln.morrer()
        elif nome == "fim":
            self.encerrar()

    def encerrar(self):
        if self.encerrando is None:
            self.encerrando = self.t
            if self.som:
                pygame.mixer.music.fadeout(1500)
            for c in self.cartazes:
                c.morrer()
            for ln in self.linhas:
                ln.morrer()
            if self.veu:
                self.veu.morrer()
            if self.coracao:
                self.coracao.morrer()

    # ── laço principal ──

    def laco(self):
        try:
            self._quadro()
        except tk.TclError:
            return
        except Exception:
            traceback.print_exc()
        self.root.after(FPS_MS, self.laco)

    def _quadro(self):
        self.t = self.agora()
        dt = min(0.1, self.t - (self.t_ant if self.t_ant is not None else self.t))
        self.t_ant = self.t
        t = self.t

        # Esc no terminal
        if msvcrt and msvcrt.kbhit():
            if msvcrt.getwch() == "\x1b":
                self.encerrar()
                self.encerrando = t - 10   # fecha já

        # seções
        atual = max((n for n, s in SECOES.items() if s <= t), key=lambda n: SECOES[n], default="intro")
        if atual != self.secao:
            self.entrar_secao(atual)

        # batidas
        while self.batida_idx < len(BEATS) and BEATS[self.batida_idx] <= t:
            if BEATS[self.batida_idx] > t - 0.25:    # ignora atrasadas (ex.: começo com --de)
                self.batida(self.batida_idx)
            self.batida_idx += 1
        self.pulso = math.exp(-(t - self.t_batida) * 5)

        # letra
        while self.linha_idx < len(LETRA) and LETRA[self.linha_idx]["t"] <= t:
            if LETRA[self.linha_idx]["t"] > t - 0.5 and self.encerrando is None:
                self.linha(LETRA[self.linha_idx])
            self.linha_idx += 1

        # vento contínuo; chuva de faíscas no climax
        if t >= self.prox_vento and len(self.elementos) < MAX_JANELAS - 6:
            Vento(self)
            self.prox_vento = t + VENTO_A_CADA * random.uniform(0.5, 1.5)
        if self.climax and t >= self.prox_chuva:
            self.rajada(random.randint(0, self.sw), self.sh - 10, n=10, forca=1.4)
            self.prox_chuva = t + 0.45

        # avança tudo
        for ln in self.linhas[:]:
            if not ln.passo(t, dt):
                self.linhas.remove(ln)
        for e in self.elementos[:]:
            if not e.viva:
                self.elementos.remove(e)
                continue
            if not e.passo(t, dt):
                e.fechar()
                self.elementos.remove(e)
        self.cartazes = [c for c in self.cartazes if c.viva]

        self.terminal.tick()

        # fim: espera tudo desbotar (ou 3 s) e sai
        acabou_som = self.som and self.encerrando is None and t > SECOES["fim"] + 1
        if acabou_som:
            self.encerrar()
        if self.encerrando is not None and (not self.elementos or t - self.encerrando > 3):
            self.root.quit()

    def rodar(self):
        preparar_terminal()
        self.terminal.cabecalho()
        if self.som:
            pygame.mixer.init()
            pygame.mixer.music.load(AUDIO)
            pygame.mixer.music.play(start=self.de)
        self.t0 = time.perf_counter()
        # pula batidas/linhas anteriores ao ponto de partida e entra na seção certa
        while self.batida_idx < len(BEATS) and BEATS[self.batida_idx] < self.de:
            self.batida_idx += 1
        while self.linha_idx < len(LETRA) and LETRA[self.linha_idx]["t"] < self.de:
            self.linha_idx += 1
        self.entrar_secao(max((n for n, s in SECOES.items() if s <= self.de),
                              key=lambda n: SECOES[n], default="intro"), inicial=True)
        self.laco()
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            if self.som:
                pygame.mixer.music.stop()
            self.terminal.final()
            try:
                self.root.destroy()
            except tk.TclError:
                pass


# ─────────────────────────── MAIN ───────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--de", type=float, default=0.0, help="segundo da música pra começar")
    parser.add_argument("--sem-som", action="store_true", help="só a animação, sem áudio")
    args = parser.parse_args()

    if not os.path.exists(AUDIO):
        sys.exit(f"não achei o áudio: {AUDIO}")

    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # janelas nítidas
    except Exception:
        pass
    Show(de=args.de, som=not args.sem_som).rodar()
