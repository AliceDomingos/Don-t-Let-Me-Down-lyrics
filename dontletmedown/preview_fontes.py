"""
prévia da tipografia do show — só pra decidir fontes, sem música

  python preview_fontes.py

teclas:
  1 2 3 4   troca a fonte do VERSO (nível 3)
  q w e     troca a fonte da PALAVRA-CHAVE (nível 2)
  a s d     troca a fonte do GRITO (nível 1)
  Esc       fecha
"""

import tkinter as tk
from tkinter import font as tkfont

FUNDO   = "#0c1445"
LARANJA = "#ff5e1a"
DOURADO = "#ffd23f"
MAGENTA = "#ff2e88"
CIANO   = "#3ddcff"
BRANCO  = "#f4efe6"
ROXO    = "#3a0f4f"

VERSO_OPCOES = ["Bookman Old Style", "Georgia", "Palatino Linotype", "Baskerville Old Face"]
CHAVE_OPCOES = ["Cooper Black", "Rockwell Extra Bold", "Goudy Stout"]
GRITO_OPCOES = ["Anton", "Impact", "Franklin Gothic Heavy"]

estado = {"verso": 0, "chave": 0, "grito": 0}


def existe(nome):
    return nome in tkfont.families()


def desenhar():
    c.delete("all")
    W = c.winfo_width() or 1400
    fv = VERSO_OPCOES[estado["verso"]]
    fc = CHAVE_OPCOES[estado["chave"]]
    fg = GRITO_OPCOES[estado["grito"]]

    # cabeçalho com as fontes atuais
    c.create_text(24, 20, anchor="nw", fill=BRANCO, font=("Segoe UI", 11),
                  text=f"verso [1-4]: {fv}     palavra-chave [q/w/e]: {fc}     grito [a/s/d]: {fg}     Esc sai")

    # ── faixa 1: verso (nível 3 + nível 2) ──
    y = 110
    c.create_text(24, y - 40, anchor="nw", fill=CIANO, font=("Segoe UI", 10, "bold"), text="VERSO")
    linha(c, W // 2, y, [("Nobody ever ", fv, 30, "italic", CIANO),
                         ("loved", fc, 42, "", MAGENTA),
                         (" me like she does", fv, 30, "italic", CIANO)])
    linha(c, W // 2, y + 60, [("Ooh, ", fv, 30, "italic", BRANCO),
                              ("she", fc, 42, "", MAGENTA),
                              (" does, yes, she does", fv, 30, "italic", BRANCO)])

    # ── faixa 2: ponte (fundo roxo) ──
    y = 300
    c.create_rectangle(0, y - 60, W, y + 80, fill=ROXO, outline="")
    c.create_text(24, y - 50, anchor="nw", fill=DOURADO, font=("Segoe UI", 10, "bold"), text="PONTE")
    linha(c, W // 2, y, [("I'm in ", fv, 30, "italic", BRANCO),
                         ("love", fc, 44, "", DOURADO),
                         (" for the ", fv, 30, "italic", BRANCO),
                         ("first time", fc, 44, "", DOURADO)])
    c.create_text(W // 2, y + 50, fill=BRANCO, font=(fv, 26, "italic"),
                  text="Don't you know it's gonna last")

    # ── faixa 3: refrão (nível 1) — crescendo em 3 repetições + eco ──
    y = 470
    c.create_text(24, y - 40, anchor="nw", fill=LARANJA, font=("Segoe UI", 10, "bold"),
                  text="REFRÃO — 1ª, 2ª e 3ª repetição (crescendo) + eco dos backing vocals")
    grito(c, W // 2, y, "DON'T LET ME DOWN", fg, 52)
    c.create_text(W // 2 + 260, y + 34, fill=CIANO, font=(fv, 16, "italic"),
                  text="(don't let me down)")
    grito(c, W // 2, y + 110, "DON'T LET ME DOWN", fg, 78)
    grito(c, W // 2, y + 250, "DON'T LET ME DOWN", fg, 120)


def linha(c, cx, y, partes):
    """desenha uma linha com trechos em fontes/tamanhos diferentes, centralizada em cx"""
    fontes = [tkfont.Font(family=f, size=s, slant="italic" if "italic" in st else "roman",
                          weight="bold" if "bold" in st else "normal") for _, f, s, st, _ in partes]
    total = sum(fo.measure(t) for (t, *_), fo in zip(partes, fontes))
    x = cx - total // 2
    for (t, f, s, st, cor), fo in zip(partes, fontes):
        c.create_text(x, y, anchor="w", text=t, fill=cor, font=fo)
        x += fo.measure(t)


def grito(c, cx, y, texto, fonte, tam):
    # sombra dura deslocada (efeito de cartaz)
    c.create_text(cx + 5, y + 5, text=texto, fill="#000000", font=(fonte, tam))
    c.create_text(cx, y, text=texto, fill=LARANJA, font=(fonte, tam))


def tecla(ev):
    k = ev.keysym.lower()
    mapa = {"1": ("verso", 0), "2": ("verso", 1), "3": ("verso", 2), "4": ("verso", 3),
            "q": ("chave", 0), "w": ("chave", 1), "e": ("chave", 2),
            "a": ("grito", 0), "s": ("grito", 1), "d": ("grito", 2)}
    if k == "escape":
        root.destroy()
        return
    if k in mapa:
        grupo, i = mapa[k]
        estado[grupo] = i
        desenhar()


try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

root = tk.Tk()
root.title("prévia — tipografia do show")
root.configure(bg=FUNDO)
root.geometry("1400x800")
c = tk.Canvas(root, bg=FUNDO, highlightthickness=0)
c.pack(fill="both", expand=True)
root.bind("<Key>", tecla)
c.bind("<Configure>", lambda e: desenhar())

faltando = [f for f in VERSO_OPCOES + CHAVE_OPCOES + GRITO_OPCOES if not existe(f)]
if faltando:
    print("fontes não encontradas (vão cair no padrão):", faltando)

root.after(50, desenhar)
root.mainloop()
