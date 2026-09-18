"""
don't let me down — the beatles
ferramentas de calibração (rodar antes de montar o show)

  python calibrar.py --batidas          # toca a música e pisca a cada batida detectada
  python calibrar.py --batidas --de 60  # idem, começando do segundo 60
  python calibrar.py --calibrar         # marcar o início de cada seção (Enter em cada uma)
  python calibrar.py --calibrar --de 90
  python calibrar.py --secoes           # só toca e mostra em que seção a música está (pra conferir)

gera/usa:  beats.json (batidas detectadas com librosa)  ->  secoes.json (marcadas na mão)
"""

import os
import sys
import json
import time
import argparse
import threading

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

AQUI = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(AQUI, "dontletmedown.mp3")
BEATS = os.path.join(AQUI, "beats.json")
SECOES_ARQ = os.path.join(AQUI, "secoes.json")

# seções da música, na ordem — o texto é só pra você reconhecer o ponto de ouvido
SECOES = [
    ("intro",    "piano elétrico + guitarra, antes da voz"),
    ("refrao1",  "Don't let me down (1ª vez)"),
    ("verso1",   "Nobody ever loved me like she does..."),
    ("refrao2",  "Don't let me down (2ª vez)"),
    ("ponte",    "I'm in love for the first time..."),
    ("refrao3",  "Don't let me down (3ª vez)"),
    ("verso2",   "And from the first time that she really done me..."),
    ("refrao4",  "Don't let me down (4ª vez / final)"),
    ("fim",      "acabou a música (ou começou o que vem depois)"),
]

RESET = "\033[0m"; DIM = "\033[2m"; BOLD = "\033[1m"
LARANJA = "\033[38;2;255;94;26m"; AMAR = "\033[38;2;255;210;63m"; CIANO = "\033[38;2;61;220;255m"


def fmt(seg):
    seg = max(0, seg)
    return f"{int(seg) // 60}:{int(seg) % 60:02d}.{int(seg * 10) % 10}"


def preparar_terminal():
    os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def tocar(de):
    pygame.mixer.init()
    pygame.mixer.music.load(AUDIO)
    pygame.mixer.music.play(start=de)
    return time.perf_counter()


# ─────────────────────────── --batidas ───────────────────────────

def checar_batidas(de):
    """toca a música e mostra no terminal cada batida detectada, pra conferir de ouvido"""
    dados = json.load(open(BEATS, encoding="utf-8"))
    batidas = [b for b in dados["batidas"] if b >= de]
    print(f"\n  {AMAR}{BOLD}checagem de batidas{RESET}  {DIM}{dados['bpm']:.1f} BPM · "
          f"{len(dados['batidas'])} batidas · começando em {fmt(de)}{RESET}")
    print(f"  {DIM}o ● deve cair junto com o bumbo. Ctrl+C pra parar.{RESET}\n")
    t0 = tocar(de)
    i = 0
    try:
        while i < len(batidas) and pygame.mixer.music.get_busy():
            agora = de + time.perf_counter() - t0
            if agora >= batidas[i]:
                n = i % 4  # posição dentro do compasso (assume 4/4)
                cor = LARANJA if n == 0 else AMAR
                bolinhas = "".join(f"{cor}●{RESET}" if k == n else f"{DIM}○{RESET}" for k in range(4))
                sys.stdout.write(f"\r  {DIM}{fmt(agora)}{RESET}   {bolinhas}   "
                                 f"{cor}{'█' * (12 if n == 0 else 6)}{RESET}{' ' * 12}")
                sys.stdout.flush()
                i += 1
            time.sleep(0.004)
    except KeyboardInterrupt:
        pass
    pygame.mixer.music.stop()
    print(f"\n\n  {DIM}se o ● caiu sempre um pouco antes/depois do bumbo, me diga quanto "
          f"(ex.: 'uns 100 ms atrasado') que eu ajusto o offset.{RESET}\n")


# ─────────────────────────── --calibrar ───────────────────────────

def calibrar(de):
    """toca a música; você aperta Enter no início de cada seção"""
    print(f"\n  {AMAR}{BOLD}calibração de seções{RESET}  {DIM}a música toca a partir de {fmt(de)}{RESET}")
    print(f"  {DIM}aperte Enter no exato momento em que cada seção começa."
          f" (q + Enter pra parar){RESET}\n")
    input(f"  {DIM}Enter pra começar...{RESET} ")
    t0 = tocar(de)

    marcas = {}
    for nome, dica in SECOES:
        resp = input(f"  {CIANO}▶{RESET} {BOLD}{nome:<8}{RESET} {DIM}{dica}{RESET}  ")
        if resp.strip().lower() == "q":
            break
        t = round(de + time.perf_counter() - t0, 2)
        marcas[nome] = t
        sys.stdout.write(f"\033[1A\r\033[K  {CIANO}✔{RESET} {BOLD}{nome:<8}{RESET} "
                         f"{AMAR}{t:>7.2f}s{RESET}  {DIM}{dica}{RESET}\n")
    pygame.mixer.music.stop()

    if not marcas:
        return
    # não sobrescreve seções que você já marcou em rodadas anteriores (ex.: --de 90)
    antigo = json.load(open(SECOES_ARQ, encoding="utf-8")) if os.path.exists(SECOES_ARQ) else {}
    antigo.update(marcas)
    json.dump(antigo, open(SECOES_ARQ, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n  salvo em {DIM}secoes.json{RESET}:")
    for nome, _ in SECOES:
        if nome in antigo:
            print(f"    {nome:<8} {AMAR}{antigo[nome]:>7.2f}s{RESET}")
    print()


# ─────────────────────────── --secoes ───────────────────────────

def conferir_secoes(de):
    """toca a música mostrando o nome da seção atual e as batidas — só pra você conferir de ouvido"""
    sec = json.load(open(SECOES_ARQ, encoding="utf-8"))
    batidas = json.load(open(BEATS, encoding="utf-8"))["batidas"]
    ordem = sorted(sec.items(), key=lambda kv: kv[1])
    print(f"\n  {AMAR}{BOLD}conferência de seções{RESET}  {DIM}começando em {fmt(de)} · Ctrl+C pra parar{RESET}\n")
    t0 = tocar(de)
    i = next((k for k, b in enumerate(batidas) if b >= de), len(batidas))
    try:
        while pygame.mixer.music.get_busy():
            agora = de + time.perf_counter() - t0
            atual = [n for n, t in ordem if t <= agora]
            nome = atual[-1] if atual else "..."
            prox = next(((n, t) for n, t in ordem if t > agora), None)
            if i < len(batidas) and agora >= batidas[i]:
                n = i % 4
                bol = "".join(f"{LARANJA}●{RESET}" if k == n else f"{DIM}○{RESET}" for k in range(4))
                i += 1
            else:
                bol = None
            cor = LARANJA if nome.startswith("refrao") else CIANO if nome.startswith("verso") else AMAR
            falta = f"{DIM}próxima: {prox[0]} em {prox[1]-agora:4.1f}s{RESET}" if prox else ""
            if bol:
                sys.stdout.write(f"\r\033[K  {DIM}{fmt(agora)}{RESET}  {bol}  {cor}{BOLD}{nome.upper():<9}{RESET}  {falta}")
                sys.stdout.flush()
            time.sleep(0.004)
    except KeyboardInterrupt:
        pass
    pygame.mixer.music.stop()
    print("\n")


# ─────────────────────────── main ───────────────────────────

if __name__ == "__main__":
    preparar_terminal()
    p = argparse.ArgumentParser()
    p.add_argument("--batidas", action="store_true", help="conferir batidas detectadas de ouvido")
    p.add_argument("--calibrar", action="store_true", help="marcar o início de cada seção")
    p.add_argument("--secoes", action="store_true", help="conferir as seções de ouvido (só toca)")
    p.add_argument("--de", type=float, default=0.0, help="segundo pra começar")
    a = p.parse_args()

    if not os.path.exists(AUDIO):
        sys.exit(f"não achei o áudio: {AUDIO}")
    if a.batidas:
        checar_batidas(a.de)
    elif a.calibrar:
        calibrar(a.de)
    elif a.secoes:
        conferir_secoes(a.de)
    else:
        p.print_help()
