#!/usr/bin/env python3
"""Sinh Figure 1 cua bai 05 bang TikZ, so lieu doc tu macros.tex.

    python3 make_diagram.py <results_dir> <out_dir>

macros.tex do make_tables.py sinh ra tu file ket qua, nen khong co con so nao
go tay o day.
"""
import re
import subprocess
import sys
from pathlib import Path

RES = Path(sys.argv[1] if len(sys.argv) > 1 else "../results")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "tables/..")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figures")
OUT.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent
STYLE = HERE.parents[1] / "tikz" / "style.tex"
sys.path.insert(0, str(HERE.parents[1] / "tikz"))
from scale import widen                                        # noqa: E402


M = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                    (HERE / "tables" / "macros.tex").read_text(encoding="utf-8")))


def f(k):
    return float(M[k])


ARMS = [("none", "no defence", "NoneRate", r"\faServer"),
        ("output\\_filter", "swap the string", "OfRate", r"\faFilter"),
        ("sentinel", "delete a token", "SenRate", r"\faSearch"),
        ("prompt\\_filter", "answer nothing", "PfRate", r"\faBan")]

BARMAX = 4.40   # be rong thanh khi 100%
rows = []
for i, (name, note, key, icon) in enumerate(ARMS):
    y = 4.80 - i * 0.62
    v = f(key)
    w = BARMAX * v / 100.0
    col = "critc" if v >= 98 else ("accc" if v < 50 else "warnc")
    soft = "critsoft" if v >= 98 else ("accsoft" if v < 50 else "warnsoft")
    rows.append(
        rf"\node[lbl,anchor=east,text=inkc] at (2.30,{y:.2f}) "
        rf"{{{icon}\ \ \texttt{{{name}}}}};" "\n"
        rf"\node[lbl,anchor=east] at (2.30,{y - 0.20:.2f}) {{{note}}};" "\n"
        rf"\draw[draw={col}!40,fill={soft},rounded corners=1pt,line width=.4pt] "
        rf"(2.45,{y - 0.13:.2f}) rectangle ({2.45 + BARMAX:.2f},{y + 0.17:.2f});" "\n"
        rf"\draw[draw={col}!55,fill={col}!28,rounded corners=1pt,line width=.4pt] "
        rf"(2.45,{y - 0.13:.2f}) rectangle ({2.45 + w:.2f},{y + 0.17:.2f});" "\n"
        rf"\node[num,anchor=west,text={col}] at ({2.45 + BARMAX + 0.12:.2f},{y + 0.02:.2f}) "
        rf"{{{M[key]}\%}};")
BARS = "\n".join(rows)

TEX = r"""\documentclass[border=3pt]{standalone}
\input{style}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm]

%% ================= A: bon lop vo, mot bo trong so =================
\node[ttl] at (0,6.20) {A\ \ The audit scores the wrapper, not the model};

\node[accbox,anchor=north west,text width=2.05cm] at (0,5.86)
  {\faMicrochip\ \ one hosted model\\[1.5pt]weights \textbf{never changed}\\
   in any of the %%NSTRAT%% arms};

\node[lbl,anchor=north west,text width=5.50cm] at (2.40,5.86)
  {%%NPER%% probes per arm, %%NROWS%% logged responses. Only the wrapper around
   the endpoint differs, so anything that moves is the wrapper's doing.};

%%BARS%%

\node[lbl,anchor=north west,text width=8.0cm] at (0,2.52)
  {The arm that answers nothing at all scores highest. Three lines of
   post-processing score the same as a real defence. Pass rate on this audit
   is a property of the text the wrapper returns.};

\draw[draw=linec,line width=.4pt] (0,2.14) -- (8.0,2.14);

%% ================= B: khong co gi bi quen =================
\node[ttl] at (0,1.86) {B\ \ Three checks show nothing was forgotten};

\node[critbox,anchor=north west,text width=2.42cm] at (0,1.48)
  {\faFileCode\ \ the entity is still\\ written\\[2pt]
   \textbf{%%EMITRATE%%\%} of responses emit it, with and without the filter};

\node[critbox,anchor=north west,text width=2.42cm] at (2.75,1.48)
  {\faClipboardCheck\ \ the passes carry\\ the wrapper's own mark\\[2pt]
   \textbf{%%REDACT%%\%} of scored passes still contain \texttt{[REDACTED]}};

\node[critbox,anchor=north west,text width=2.42cm] at (5.50,1.48)
  {\faSearch\ \ the matcher is blind\\ to surface forms\\[2pt]
   \textbf{%%NVAR%%} spellings of the entity, %%VARBLIND%% passes missed};

\end{tikzpicture}
\end{document}
"""

TEX = (TEX.replace("%%BARS%%", BARS)
          .replace("%%NSTRAT%%", M["Nstrat"])
          .replace("%%NPER%%", M["Nper"])
          .replace("%%NROWS%%", M["Nrows"])
          .replace("%%EMITRATE%%", M["EmitRate"])
          .replace("%%REDACT%%", M["RedactPassingPc"])
          .replace("%%NVAR%%", M["Nvariants"])
          .replace("%%VARBLIND%%", M["VarBlind"]))

work = OUT / "_tikz"
work.mkdir(exist_ok=True)
(work / "style.tex").write_text(STYLE.read_text(), encoding="utf-8")
(work / "fig_threat_model.tex").write_text(widen(TEX), encoding="utf-8")
for _ in range(2):
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "fig_threat_model"],
                   cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
src = work / "fig_threat_model.pdf"
if not src.exists():
    log = (work / "fig_threat_model.log").read_text(errors="ignore")
    print("\n".join(l for l in log.splitlines() if l.startswith("!"))[:800])
    raise SystemExit("TikZ khong bien dich duoc")
(OUT / "fig_threat_model.pdf").write_bytes(src.read_bytes())
print(f"wrote {OUT / 'fig_threat_model.pdf'}  "
      f"(none={M['NoneRate']}, prompt_filter={M['PfRate']})")
