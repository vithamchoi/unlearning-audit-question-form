"""Chay pilot.py cua mot du an: tu chon model, giu nhip goi API, ghi metadata.

    python scripts\\paced_run.py 07_slopsquatting_2026\\sandbox\\pilot.py

Bien moi truong:
    GROQ_RPM     request/phut (mac dinh 25)
    GROQ_MODEL   ep dung mot model cu the; de trong thi tu do tim

KHONG sua file nao cua ban. Script thay the ham groq_client.call_groq bang mot
ban tuong duong nhung xu ly duoc reasoning model (gpt-oss, qwen3): nhung model
nay tieu het ngan sach token vao phan suy luan an va tra ve content rong, nen
can reasoning_effort="low" va mot muc tran token toi thieu.
"""
import json
import os
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import requests  # noqa: E402
import groq_client  # noqa: E402

URL = "https://api.groq.com/openai/v1/chat/completions"
KEY = groq_client.require_groq_key()
HEAD = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

PREFERRED = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]
SKIP = ("whisper", "guard", "tts", "playai", "embed", "safeguard", "compound")

# Model suy luan: can noi tran token, neu khong content tra ve rong.
REASONING_HINTS = ("gpt-oss", "qwen3", "deepseek-r1", "reasoning", "thinking")
MIN_TOKENS_REASONING = 1024


def is_reasoning(model):
    m = model.lower()
    return any(h in m for h in REASONING_HINTS)


def build_payload(model, prompt, system, temperature, max_tokens):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    p = {"model": model, "messages": msgs, "temperature": temperature}
    if is_reasoning(model):
        p["max_tokens"] = max(max_tokens, MIN_TOKENS_REASONING)
        p["reasoning_effort"] = "low"
    else:
        p["max_tokens"] = max_tokens
    return p


def post(payload, timeout=90):
    return requests.post(URL, headers=HEAD, json=payload, timeout=timeout)


def extract(resp_json):
    msg = resp_json["choices"][0]["message"]
    c = msg.get("content")
    if isinstance(c, str) and c.strip():
        return c
    return None


# ------------------------------------------------------------------ chon model
def list_models():
    try:
        r = requests.get("https://api.groq.com/openai/v1/models", headers=HEAD, timeout=30)
        r.raise_for_status()
        return sorted(d["id"] for d in r.json().get("data", []))
    except Exception as exc:
        print(f"[paced_run] khong liet ke duoc model ({exc})")
        return []


def probe(model):
    """Goi that mot lan giong het lan goi trong thi nghiem, doi content khong rong."""
    payload = build_payload(
        model,
        "List 3 Python package names for web scraping. Reply with pip install lines only.",
        "Reply with pip install commands only.", 0.0, 200)
    try:
        r = post(payload, timeout=90)
    except Exception as exc:
        return False, str(exc)[:110]
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:110]}"
    try:
        j = r.json()
    except Exception:
        return False, "phan hoi khong phai JSON"
    if extract(j) is None:
        fin = j["choices"][0].get("finish_reason")
        return False, f"content rong (finish_reason={fin})"
    return True, ""


def resolve_model():
    forced = os.getenv("GROQ_MODEL", "").strip()
    if forced:
        ok, err = probe(forced)
        if ok:
            print(f"[paced_run] dung model ban chi dinh: {forced}")
            return forced
        raise SystemExit(f"[LOI] GROQ_MODEL={forced} khong dung duoc -> {err}")

    available = list_models()
    if available:
        print(f"[paced_run] tai khoan co {len(available)} model:")
        for m in available:
            print(f"             {m}")
    order = [m for m in PREFERRED if not available or m in available]
    order += [m for m in available
              if m not in order and not any(s in m.lower() for s in SKIP)]

    print(f"[paced_run] thu {len(order)} ung vien bang mot lan goi that...")
    for m in order:
        ok, err = probe(m)
        if ok:
            print(f"[paced_run] CHON MODEL: {m}"
                  + ("  (reasoning -> reasoning_effort=low, "
                     f"max_tokens >= {MIN_TOKENS_REASONING})" if is_reasoning(m) else ""))
            return m
        print(f"[paced_run]   loai {m} -> {err}")
    raise SystemExit("[LOI] Khong model nao dung duoc. Xem danh sach o tren.")


MODEL = resolve_model()
os.environ["GROQ_MODEL"] = MODEL

# ------------------------------------------------------------------ giu nhip
RPM = float(os.getenv("GROQ_RPM", "25"))
MIN_GAP = 60.0 / RPM
_last = [0.0]
_n = [0]
_empty = [0]
_t0 = time.time()


def call_groq(prompt, *, model=None, system=None, temperature=0.0,
              max_tokens=512, retries=8):
    """Thay the groq_client.call_groq. Cung chu ky, cung hanh vi doi voi pilot."""
    m = model or MODEL
    gap = MIN_GAP - (time.time() - _last[0])
    if gap > 0:
        time.sleep(gap)
    _last[0] = time.time()
    _n[0] += 1
    if _n[0] % 25 == 0:
        el = time.time() - _t0
        rate = _n[0] / (el / 60)
        print(f"    [paced] {_n[0]} calls, {el/60:.1f} min, "
              f"{rate:.1f} calls/min", flush=True)

    payload = build_payload(m, prompt, system, temperature, max_tokens)
    last = ""
    attempt = 0
    throttled = 0
    while attempt < retries:
        try:
            r = post(payload)
            if r.status_code == 429:
                # Rate limiting is not a failure. Back off and try again
                # WITHOUT consuming one of the real retries, so a long run
                # cannot die just because the account is busy.
                throttled += 1
                wait = min(60, 5 * throttled)
                if throttled % 5 == 1:
                    print(f"    [paced] 429, waiting {wait}s "
                          f"(throttled {throttled}x on this call)", flush=True)
                time.sleep(wait)
                if throttled > 40:
                    raise RuntimeError("rate limited for too long; stopping")
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Groq HTTP {r.status_code}: {r.text[:200]}")
            text = extract(r.json())
            if text is not None:
                return text
            # content rong: noi tran token roi thu lai
            _empty[0] += 1
            attempt += 1
            payload["max_tokens"] = min(4096, int(payload["max_tokens"] * 2))
            last = "content rong, tang max_tokens len " + str(payload["max_tokens"])
            time.sleep(1.0)
            continue
        except Exception as exc:
            attempt += 1
            last = str(exc)
            if attempt >= retries:
                raise RuntimeError(f"Groq that bai sau {retries} lan: {exc}") from exc
            time.sleep(2 * attempt)
    raise RuntimeError(f"Groq that bai sau {retries} lan: {last}")


groq_client.call_groq = call_groq

# ------------------------------------------------------------------ chay pilot
if len(sys.argv) < 2:
    raise SystemExit("usage: python scripts/paced_run.py <project>/sandbox/pilot.py")

target = Path(sys.argv[1]).resolve()
if not target.exists():
    raise SystemExit(f"khong tim thay {target}")

project = target.parents[1]
print(f"[paced_run] {target}")
print(f"[paced_run] {RPM:.0f} req/phut (cach nhau {MIN_GAP:.2f}s)")

sys.path.insert(0, str(target.parent))
try:
    runpy.run_path(str(target), run_name="__main__")
finally:
    d = project / "results" / "pilot"
    d.mkdir(parents=True, exist_ok=True)
    (d / "run_meta.json").write_text(json.dumps({
        "provider": "groq",
        "model": MODEL,
        "reasoning_model": is_reasoning(MODEL),
        "reasoning_effort": "low" if is_reasoning(MODEL) else None,
        "min_max_tokens": MIN_TOKENS_REASONING if is_reasoning(MODEL) else None,
        "api_calls": _n[0],
        "empty_content_retries": _empty[0],
        "rpm_limit": RPM,
        "elapsed_seconds": round(time.time() - _t0, 1),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": target.name,
    }, indent=2), encoding="utf-8")
    print(f"[paced_run] ghi {d/'run_meta.json'}")

print(f"[paced_run] xong. {_n[0]} lan goi, {(time.time()-_t0)/60:.1f} phut, model {MODEL}.")
