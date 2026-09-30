# Black-box unlearning audit and question form

Result files, experiment scripts and LaTeX sources for the paper

> S. X. Ha, P. T. Tran-Truong, X.-B. Le, L. H. Huong, T. Q. Nguyen, T. G. Huy, N. N. T. Kha, T. N. Minh and N. N. Phien,
> "Scrubbing the String, Not the Model",
> submitted to IEEE Transactions on Dependable and Secure Computing, 2026.

## What is in here

```
results/     the measured result files. Every number, table and figure in the
             paper is computed from these and from nothing else.
scripts/     the experiment code that produced those files.
latex/       the generators that read results/ and emit the table bodies and
             figures, plus the paper source they are substituted into.
```

## What you can reproduce, and what you cannot

**From this repository alone** you can regenerate every table, figure and
inline number in the paper:

```bash
pip install -r requirements.txt
cd latex
python3 make_tables.py  ../results  tables
python3 make_figures.py ../results  figures
python3 make_diagram.py ../results  figures
python3 build.py        ../results          # writes main.tex
python3 build_ieee.py                      # writes ieee/main_ieee.tex
```

`build.py` substitutes the generated values into `paper_template.tex`. No number
in the paper is typed by hand, so a mismatch between the paper and a fresh run
of these scripts is a bug and we would like to hear about it.

`build_ieee.py` then rewrites that manuscript into the IEEE two-column form that
was actually submitted: it drops the CRediT section, which IEEE has no field for,
lifts the funding statement into a page-one footnote, rebuilds the author block
in IEEE style, and widens only the tables that overflow a column.
`latex/ieee/main_ieee.tex` is checked in even though it is generated, because it
is the exact manuscript we submitted. Regenerating it must produce the same
bytes; that diff is the artifact's own self-check, and we ran it on all nine
papers before publishing.

**You cannot regenerate `results/` from this repository alone.** Doing that needs
a Groq API key and `openai/gpt-oss-20b`. The probe set and the defence configurations are in the scripts, so the design can be repeated exactly; the model's answers will differ.
The scripts in `scripts/` are the code we ran; they are published so the
procedure can be inspected and re-executed by anyone who assembles that
environment.

## Layout of `results/`

| File | Used for |
|---|---|
| `pilot/llm_audit_raw.jsonl` | the complete raw audit log. Every number in the paper is emitted from this file by make_tables.py; none is typed by hand |
| `pilot/fake_unlearning_metrics.csv` | the pilot's own summary line |
| `pilot/run_meta.json` | provider, model, decoding parameters, call count and wall-clock of the run |
| `pilot_source_pilot.py` | the pilot script exactly as it was run, kept beside its output |

## A companion submission

This paper and our companion submission on the saturation behaviour of IAM both concern the validity of unlearning audits. They share no data, no result file and no text. We disclose the pair to any editor who asks.

## Licence

Code in `scripts/` and `latex/` is MIT. The result files in `results/` are
CC BY 4.0. See `LICENSE`.
