#!/usr/bin/env python3
"""Generate LaTeX table bodies and inline macros for the paper-05 manuscript."""
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import (Data, ENTITY, LABEL, OC_TRIALS, STRATEGIES,  # noqa: E402
                      audit_normalised, audit_shipped, wilson)
from analysis import LABEL  # noqa: E402

RES = Path(sys.argv[1] if len(sys.argv) > 1 else "../results")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "tables")
OUT.mkdir(parents=True, exist_ok=True)
D = Data(RES)


def write(name, body):
    (OUT / name).write_text(body.rstrip() + "\n", encoding="utf-8")
    print(f"wrote {OUT / name}")


def pc(x, d=2):
    return f"{100 * x:.{d}f}"


def sci(x, d=2):
    if x <= 0:
        return "$0$"
    e = math.floor(math.log10(abs(x)))
    m = x / 10 ** e
    return f"${m:.{d}f}\\times 10^{{{e}}}$"


def texq(s):
    """Escape a raw model-emitted surface form for LaTeX \\texttt{}."""
    out = []
    for ch in s:
        if ch == "_":
            out.append(r"\_")
        elif ord(ch) < 128:
            out.append(ch)
        else:
            out.append(r"}{\footnotesize$\langle$U+%04X$\rangle$}\texttt{" % ord(ch))
    return "".join(out)


# ------------------------------------------------------------------ Table 1
rows = []
for s in STRATEGIES:
    k = D.k(s)
    kn = D.k(s, audit_normalised)
    lo, hi = D.cluster_ci(s)
    rows.append(" & ".join([
        rf"\texttt{{{s.replace('_', chr(92) + '_')}}}",
        str(D.model_calls(s)),
        f"{k}/{D.n}", pc(k / D.n),
        (rf"$\ge {100*D.cluster_one_sided_lower(s):.2f}$$^{{\ddagger}}$"
         if D.is_degenerate(s) else f"[{pc(lo)}, {pc(hi)}]"),
        f"{kn}/{D.n}", pc(kn / D.n),
        str(D.false_pass(s)),
    ]) + r" \\")
write("tab_main.tex", "\n".join(rows))

# ------------------------------------------------------------------ Table 2
rows = []
yn = {True: r"\checkmark", False: r"$\times$"}
for form, cnt, seen, repl, dele in D.variants():
    rows.append(" & ".join([
        rf"\texttt{{{texq(form)}}}", str(cnt), pc(cnt / D.variant_total()),
        yn[seen], yn[repl], yn[dele],
    ]) + r" \\")
rows.append(r"\addlinespace")
seen_tot = sum(c for _, c, s, _, _ in D.variants() if s)
repl_tot = sum(c for _, c, _, r, _ in D.variants() if r)
rows.append(" & ".join([
    r"\textbf{Total}", r"\textbf{" + str(D.variant_total()) + "}", r"\textbf{100.00}",
    r"\textbf{" + str(seen_tot) + "}", r"\textbf{" + str(repl_tot) + "}",
    r"\textbf{" + str(repl_tot) + "}",
]) + r" \\")
write("tab_variants.tex", "\n".join(rows))

# ------------------------------------------------------------------ Table 3
med = {s: statistics.median(D.words(s)) for s in STRATEGIES}
rows = [
    " & ".join([r"Refuses every query", r"\texttt{prompt\_filter}",
                f"{D.k('prompt_filter')}/{D.n}", "0",
                f"{med['prompt_filter']:.0f}", "n/a"]) + r" \\",
    " & ".join([r"Answers, replaces the string", r"\texttt{output\_filter}",
                f"{D.k('output_filter')}/{D.n}", str(D.model_calls("output_filter")),
                f"{med['output_filter']:.0f}", "0"]) + r" \\",
    " & ".join([r"Answers, deletes the token", r"\texttt{sentinel}",
                f"{D.k('sentinel')}/{D.n}", str(D.model_calls("sentinel")),
                f"{med['sentinel']:.0f}", str(D.dangling())]) + r" \\",
    " & ".join([r"Declines on its own", r"\texttt{none} (passing subset)",
                f"{D.k('none')}/{D.n}", str(D.model_calls("none")),
                f"{med['none']:.0f}", "0"]) + r" \\",
]
write("tab_confusion.tex", "\n".join(rows))

# ------------------------------------------------------------------ Table 4
rows = []
for s in STRATEGIES:
    rho, deff, neff = D.icc(s)
    k = D.k(s)
    nlo, nhi = wilson(k, D.n)
    clo, chi = D.cluster_ci(s)
    if D.is_degenerate(s):
        # Moi dong cung ket qua -> MSB = MSW = 0 -> ICC la 0/0, khong phai 0.
        # Bootstrap tren du lieu khong bien thien chi tra lai dung mot gia tri.
        rows.append(" & ".join([
            rf"\texttt{{{s.replace('_', chr(92) + '_')}}}",
            r"n/a$^{\ddagger}$", r"n/a$^{\ddagger}$", r"n/a$^{\ddagger}$",
            f"[{pc(nlo)}, {pc(nhi)}]",
            rf"$\ge {100*D.cluster_one_sided_lower(s):.2f}$",
            "n/a",
        ]) + r" \\")
    else:
        rows.append(" & ".join([
            rf"\texttt{{{s.replace('_', chr(92) + '_')}}}",
            f"{rho:.3f}", f"{deff:.2f}", f"{neff:.1f}",
            f"[{pc(nlo)}, {pc(nhi)}]", f"[{pc(clo)}, {pc(chi)}]",
            f"{100 * ((chi - clo) / (nhi - nlo)):.0f}\\%" if nhi > nlo else "n/a",
        ]) + r" \\")
write("tab_cluster.tex", "\n".join(rows))

# ------------------------------------------------------------------ Table 5
det = []
n = D.n
rows_ = [
    (r"Redaction marker \texttt{[REDACTED]} present",
     {s: D.redactions(s) for s in STRATEGIES}, "output_filter"),
    (r"Response contains a line break",
     {s: D.newlines(s) for s in STRATEGIES}, "sentinel"),
    (r"Largest byte-identical response set",
     {s: D.identical(s) for s in STRATEGIES}, "prompt_filter"),
    (r"Entity present in a normalisation-equivalent form",
     {s: n - D.k(s, audit_normalised) for s in STRATEGIES}, None),
]
for name, vals, target in rows_:
    if target is None:
        p_ = ""
    else:
        a, b = vals[target], n - vals[target]
        c, d = vals["none"], n - vals["none"]
        p_ = sci(D.fisher(a, b, c, d))
    det.append(" & ".join([name] + [f"{vals[s]}/{n}" for s in STRATEGIES] + [p_]) + r" \\")
write("tab_detectors.tex", "\n".join(det))

# ------------------------------------------------------------------ Table 6
prov = [
    (r"Target endpoint", r"\Provider{} hosted inference API"),
    (r"Model identifier", r"\Model{}"),
    (r"System prompt", r"\texttt{\char34 Answer concisely.\char34} (identical in all "
                       r"\Nstrat{} arms)"),
    (r"Decoding", r"provider default temperature; \texttt{reasoning\_effort} = "
                  r"\texttt{low}"),
    (r"Token cap", r"\texttt{max\_tokens} = $200$ in the collection script; the "
                   r"run metadata records a floor of \MaxTok{} imposed by the "
                   r"provider for this reasoning model. Both are stated because "
                   r"they disagree"),
    (r"Request pacing", r"\Rpm{} requests per minute (free-tier token budget)"),
    (r"Defense strategies", r"\Nstrat{} (\texttt{none}, \texttt{prompt\_filter}, "
                           r"\texttt{output\_filter}, \texttt{sentinel})"),
    (r"Probes per strategy", r"\Nper{}, drawn from \Ndistinct{} distinct prompts"),
    (r"Logged responses", r"\Nrows{}"),
    (r"Model invocations", r"\Ncalls{} (\texttt{prompt\_filter} never reaches the model)"),
    (r"Raw log", r"\path{results/pilot/llm_audit_raw.jsonl}"),
    (r"Generating code", r"\path{sandbox/pilot.py}, \path{scripts/finish_05.py}"),
]
write("tab_provenance.tex",
      "\n".join(f"{a} & {b} \\\\" for a, b in prov))

# ------------------------------------------------------------------ Table 7
from analysis import BATCH_SIZES, CHECKS, DEGEN_FRACTION  # noqa: E402

oc = D.check_oc()
anyoc = D.check_any_oc()
rows = []
for key, label, _ in CHECKS:
    for i, s in enumerate(STRATEGIES):
        first = label if i == 0 else ""
        rows.append(" & ".join(
            [first, rf"\texttt{{{s.replace('_', chr(92) + '_')}}}"]
            + [f"{100 * oc[key][s][m]:.2f}" for m in BATCH_SIZES]) + r" \\")
    rows.append(r"\addlinespace")
for i, s in enumerate(STRATEGIES):
    first = r"\textbf{Any of the three}" if i == 0 else ""
    rows.append(" & ".join(
        [first, rf"\texttt{{{s.replace('_', chr(92) + '_')}}}"]
        + [f"{100 * anyoc[s][m]:.2f}" for m in BATCH_SIZES]) + r" \\")
write("tab_oc.tex", "\n".join(rows))

rs = D.refusal_subset_signature()

# ------------------------------------------------------------------- macros
V = {v[0]: v for v in D.variants()}
blind = sum(c for _, c, seen, _, _ in D.variants() if not seen)
seen_tot = D.variant_total() - blind
scrub = sum(c for _, c, _, r, _ in D.variants() if r)
rho_n, deff_n, neff_n = D.icc("none")
lo_n, hi_n = D.cluster_ci("none")
lo_o, hi_o = D.cluster_ci("output_filter")
_, _, p_of = D.mcnemar("none", "output_filter")
_, _, p_sen = D.mcnemar("none", "sentinel")
wr = D.words_removed()
sizes = sorted({len(v) for v in D.clusters.values()})

m = {
    "Entity": r"\texttt{SECRET\_ENTITY\_X}",
    "Nrows": D.n_lines,
    "Nper": D.n,
    "Nstrat": len(STRATEGIES),
    "Ndistinct": len(D.distinct),
    "RepLo": sizes[0], "RepHi": sizes[-1],
    "Ncalls": sum(D.model_calls(s) for s in STRATEGIES),
    "Model": r"\texttt{openai/\allowbreak{}gpt-\allowbreak{}oss-\allowbreak{}20b}",
    "Provider": "Groq",
    "NoneK": D.k("none"), "NoneRate": pc(D.k("none") / D.n),
    "NoneLo": pc(lo_n), "NoneHi": pc(hi_n),
    "PfK": D.k("prompt_filter"), "PfRate": pc(D.k("prompt_filter") / D.n),
    "OfK": D.k("output_filter"), "OfRate": pc(D.k("output_filter") / D.n),
    "OfLo": pc(lo_o), "OfHi": pc(hi_o),
    "SenK": D.k("sentinel"), "SenRate": pc(D.k("sentinel") / D.n),
    "OfNormK": D.k("output_filter", audit_normalised),
    "OfNormRate": pc(D.k("output_filter", audit_normalised) / D.n),
    "SenNormK": D.k("sentinel", audit_normalised),
    "SenNormRate": pc(D.k("sentinel", audit_normalised) / D.n),
    "FpOf": D.false_pass("output_filter"), "FpSen": D.false_pass("sentinel"),
    "Gain": f"{100 * (D.k('output_filter') - D.k('none')) / D.n:.2f}",
    "VarTotal": D.variant_total(), "VarSeen": seen_tot, "VarBlind": blind,
    "VarBlindPc": pc(blind / D.variant_total()),
    # --- v2: diem mu phai do tren nhanh KHONG phong thu
    "VarBlindNone": D.blind_arm("none")[0],
    "VarTotalNone": D.blind_arm("none")[1],
    "VarBlindNonePc": f"{D.blind_arm('none')[2]:.2f}",
    "FailOf": D.audit_failures("output_filter"),
    "FailSen": D.audit_failures("sentinel"),
    "PfLower": f"{100*D.cluster_one_sided_lower('prompt_filter'):.2f}",
    "Ncl": len(D.clusters),
    "VarScrub": scrub, "VarScrubPc": pc(scrub / D.variant_total()),
    "Nvariants": len(D.variants()),
    "IccNone": f"{rho_n:.3f}", "DeffNone": f"{deff_n:.2f}", "NeffNone": f"{neff_n:.1f}",
    "PmcOf": sci(p_of), "PmcSen": sci(p_sen),
    "RefusePasses": D.refusals_among_passes("none"),
    "Dangling": D.dangling(),
    "WordsNone": f"{statistics.median(D.words('none')):.0f}",
    "WordsOf": f"{statistics.median(D.words('output_filter')):.0f}",
    "WordsSen": f"{statistics.median(D.words('sentinel')):.0f}",
    "WordsCut": f"{statistics.mean(wr):.1f}",
    "EmitNone": D.emitted("none"),
    "EmitRate": pc(D.emitted("none") / D.n),
    "EmitOf": D.emitted("output_filter"),
    "RedactOf": D.redactions("output_filter"),
    "RedactPassing": sum(1 for t in D.responses("output_filter")
                         if audit_shipped(t) and "[REDACTED]" in t),
    "RedactPassingPc": pc(sum(1 for t in D.responses("output_filter")
                              if audit_shipped(t) and "[REDACTED]" in t) / D.k("output_filter")),
    "ScrubOf": D.counts("output_filter")["scrubbed"],
    "NlNone": D.newlines("none"), "NlOf": D.newlines("output_filter"),
    "NlSen": D.newlines("sentinel"),
    "IdentPf": D.identical("prompt_filter"), "IdentNone": D.identical("none"),
    "RefuseNone": D.counts("none")["refusal"], "CleanNone": D.counts("none")["clean"],
    "RefuseSen": D.counts("sentinel")["refusal"], "CleanSen": D.counts("sentinel")["clean"],
    "PfishRedact": sci(D.fisher(D.redactions("output_filter"),
                                D.n - D.redactions("output_filter"),
                                D.redactions("none"), D.n - D.redactions("none"))),
    "PfishNl": sci(D.fisher(D.newlines("sentinel"), D.n - D.newlines("sentinel"),
                            D.newlines("none"), D.n - D.newlines("none"))),
    "Rpm": f"{D.meta['rpm_limit']:.0f}",
    "MaxTok": D.meta["min_max_tokens"],
}

m.update({
    "Batchdetect": 20,
    "FPfive": pc(anyoc["none"][5] , 2),
    "FPten": pc(anyoc["none"][10], 2),
    "FPtwenty": pc(anyoc["none"][20], 2),
    "FPfifty": pc(anyoc["none"][50], 2),
    "OCtrials": f"{OC_TRIALS:,}".replace(",", "{,}"),
    "RefN": rs["n"],
    "RefNewline": rs["newline"],
    "RefDistinct": rs["distinct"],
    "RefTop": rs["top"],
    "AnsN": rs["n_answer"],
    "AnsNewlinePc": f"{rs['answer_newline_pct']:.2f}",
    "DegenPc": int(100 * DEGEN_FRACTION),
})

write("macros.tex", "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in m.items()))


# ===========================================================================
# Phan them: ty le vuot audit phu thuoc vao CACH DAT CAU HOI, khong vao mo hinh.
# Doc tu pilot/llm_audit_raw.jsonl. Gom 500 probe cua moi chien luoc thanh 12
# khuon cau hoi theo phan van ban dung truoc ten thuc the.
# Khong mo phong; moi so la mot ham thuan cua file log.
# ===========================================================================
import collections as _c5
import json as _j5

_LOG = RES / "pilot" / "llm_audit_raw.jsonl"
if _LOG.exists():
    _rws = [_j5.loads(_l) for _l in _LOG.read_text(encoding="utf-8").splitlines() if _l.strip()]

    def _tmpl(pr):
        """Khuon cau hoi = phan dung truoc ten thuc the."""
        head = pr.split("SECRET_ENTITY_X")[0].strip()
        return head if head else pr[:50]

    _STR = ["none", "prompt_filter", "output_filter", "sentinel"]
    _SH = {"none": "None", "prompt_filter": "Prompt", "output_filter": "Output",
           "sentinel": "Sentinel"}
    _tmpls = sorted({_tmpl(_r["prompt"]) for _r in _rws})

    def _cell(strategy, template):
        sub = [_r for _r in _rws
               if _r["strategy"] == strategy and _tmpl(_r["prompt"]) == template]
        k = sum(1 for _r in sub if _r["audit_pass"])
        return k, len(sub)

    # --- bang: ty le vuot theo khuon x chien luoc
    _rows_tm = []
    for _tt in sorted(_tmpls, key=lambda x: _cell("none", x)[0] / max(1, _cell("none", x)[1])):
        _cs = []
        for _s in _STR:
            _k, _n = _cell(_s, _tt)
            _cs.append(r"%d/%d" % (_k, _n))
        _rows_tm.append(r"\emph{%s\dots} & %s \\" % (_tt, " & ".join(_cs)))
    _rows_tm.append(r"\midrule")
    _tot = []
    for _s in _STR:
        _sub = [_r for _r in _rws if _r["strategy"] == _s]
        _tot.append(r"%d/%d" % (sum(1 for _r in _sub if _r["audit_pass"]), len(_sub)))
    _rows_tm.append(r"Pooled & %s \\" % " & ".join(_tot))
    write("tab_template.tex", "\n".join(_rows_tm))

    # --- bang: so phan hoi khac nhau moi chien luoc
    _rows_dv = []
    for _s in _STR:
        _sub = [_r for _r in _rws if _r["strategy"] == _s]
        _u = _c5.Counter(_r["response"] for _r in _sub)
        _rows_dv.append(r"%s & %d & %d & %d & %s \\"
                        % (_SH[_s], len(_sub), len(_u), _u.most_common(1)[0][1],
                           f"{100 * _u.most_common(1)[0][1] / len(_sub):.1f}"))
    write("tab_respdiv.tex", "\n".join(_rows_dv))

    # --- bang: 12 truong hop that bai con lai tap trung o dau
    _rows_fl = []
    for _s in ("output_filter", "sentinel"):
        _f = [_r for _r in _rws if _r["strategy"] == _s and not _r["audit_pass"]]
        _by = _c5.Counter(_tmpl(_r["prompt"]) for _r in _f)
        for _tt, _c in _by.most_common():
            _rows_fl.append(r"%s & \emph{%s\dots} & %d \\" % (_SH[_s], _tt, _c))
    write("tab_failwhere.tex", "\n".join(_rows_fl))

    _none = {_tt: _cell("none", _tt) for _tt in _tmpls}
    _rates = {_tt: (_k / _n if _n else 0.0) for _tt, (_k, _n) in _none.items()}
    _best = max(_rates, key=_rates.get)
    _zero = [_tt for _tt in _tmpls if _rates[_tt] == 0.0]
    _fail_t = set()
    for _s in ("output_filter", "sentinel"):
        _fail_t |= {_tmpl(_r["prompt"]) for _r in _rws
                    if _r["strategy"] == _s and not _r["audit_pass"]}

    _m7 = [
        (r"\PTmpl", str(len(_tmpls))),
        (r"\PBestTmpl", _best),
        (r"\PBestRate", "%.1f" % (100 * _rates[_best])),
        (r"\PBestK", str(_none[_best][0])),
        (r"\PBestN", str(_none[_best][1])),
        (r"\PZeroTmpl", str(len(_zero))),
        (r"\PSpread", "%.1f" % (100 * (max(_rates.values()) - min(_rates.values())))),
        (r"\PPfUniq", str(len({_r["response"] for _r in _rws
                               if _r["strategy"] == "prompt_filter"}))),
        (r"\PNoneUniq", str(len({_r["response"] for _r in _rws
                                 if _r["strategy"] == "none"}))),
        (r"\PSenUniq", str(len({_r["response"] for _r in _rws
                                if _r["strategy"] == "sentinel"}))),
        (r"\POfUniq", str(len({_r["response"] for _r in _rws
                               if _r["strategy"] == "output_filter"}))),
        (r"\PFailTmpl", str(len(_fail_t))),
        (r"\PFailTmplList", ", ".join(r"\emph{%s\dots}" % x for x in sorted(_fail_t))),
    ]
    with open(OUT / "macros.tex", "a", encoding="utf-8") as _f:
        _f.write("\n%% --- ty le vuot audit phu thuoc cach dat cau hoi ---\n")
        for _n, _v in _m7:
            _f.write(rf"\newcommand{{{_n}}}{{{_v}}}" + "\n")
    print(f"wrote {len(_m7)} macro khuon cau hoi + 3 bang")
