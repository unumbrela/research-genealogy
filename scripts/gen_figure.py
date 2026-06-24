#!/usr/bin/env python3
"""Turn a genealogy figure prompt into an actual diagram image.

Feeds the `render_tree.py --format figure-prompt` output to an OpenAI-compatible
image relay (中转站) — ZenMux (default) or wegoo, both serving `gpt-image-2` —
and saves the returned PNG.

  python3 scripts/gen_figure.py figure-prompt.md --out figure.png
  python3 scripts/gen_figure.py lineage.json --out figure.png      # builds the prompt itself
  python3 scripts/render_tree.py L.json --format figure-prompt | python3 scripts/gen_figure.py -
  python3 scripts/gen_figure.py lineage.json --relay wegoo --out figure.png

Only the model-facing part of the prompt is sent: sections 一 (prose) + 二 (the
hard structure checklist). The "给作者的话 / Section 3" notes are stripped.

Relay selection: --relay {zenmux,wegoo} (default zenmux). Base URL resolution:
--base-url  >  $ZENMUX_BASE_URL / $WEGOO_BASE_URL  >  the chosen relay's default.
API key resolution: --api-key  >  $ZENMUX_API_KEY / $WEGOO_API_KEY  >  that
relay's key parsed from image-relay.md. Stdlib only.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
KEY_DOC = os.path.join(ROOT, "image-relay.md")
KEY_RE = re.compile(r"sk-[A-Za-z0-9-]{32,}")

# OpenAI-compatible image relays. Both serve gpt-image-2 at /images/generations.
RELAYS = {
    "zenmux": {"base": "https://zenmux.ai/api/v1",  "env": "ZENMUX_API_KEY"},
    "wegoo":  {"base": "https://ai.wegoo.site/v1",  "env": "WEGOO_API_KEY"},
}
DEFAULT_RELAY = "zenmux"


def relay_base(relay):
    """Default base URL for a relay: $<RELAY>_BASE_URL  >  registry default."""
    return os.environ.get(relay.upper() + "_BASE_URL", RELAYS[relay]["base"])


# ---- prompt ------------------------------------------------------------------
def extract_prompt(text):
    """Keep only the model-facing part of a figure-prompt doc: the prose body and
    the structure checklist (sections 一 + 二 / 1 + 2). Drop the H1, the usage
    note, the trailing "给作者的话 / Before you feed it" section, and leading "> "
    blockquote markers. If the doc has no section markers, return it cleaned."""
    lines = text.splitlines()
    # find the first body heading (## 一 … / ## 1 …) and the trailing notes
    # heading (## 三 … / ## 3 …) — everything before the first and from the last
    # onward is scaffolding, not for the model.
    start = 0
    for i, ln in enumerate(lines):
        if re.match(r"^##\s*(一|1)\b", ln) \
                or re.match(r"^##\s.*(提示词正文|Prompt body)", ln):
            start = i
            break
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^##\s*(三|3)\b", lines[i]) \
                or re.match(r"^##\s.*(给作者的话|Before you feed it)", lines[i]):
            end = i
            break
    body = lines[start:end]
    out = []
    for ln in body:
        ln = re.sub(r"^>\s?", "", ln)          # unwrap blockquotes
        out.append(ln)
    return "\n".join(out).strip()


def prompt_from_input(path):
    """Read INPUT (figure-prompt .md / lineage.json / '-' for stdin) → prompt."""
    if path == "-":
        return extract_prompt(sys.stdin.read())
    raw = open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        sys.path.insert(0, THIS)
        import render_tree
        data = json.loads(raw)
        nodes = {n["id"]: n for n in data.get("nodes", [])}
        if not nodes:
            raise SystemExit(f"{path}: lineage has no nodes")
        render_tree._LANG = "zh"
        return extract_prompt(render_tree.render_figure_prompt(data, nodes))
    return extract_prompt(raw)


# ---- key ---------------------------------------------------------------------
def key_from_doc(relay):
    """Parse this relay's key from image-relay.md. Each provider labels its key on
    an assignment line — e.g. `ZENMUX_API_KEY = sk-…` — which we match directly so
    the right key is picked even when the env-var name is also mentioned elsewhere
    (warnings, the parameters table). Falls back to the first sk-… token in the
    file (single-key docs)."""
    if not os.path.exists(KEY_DOC):
        return None
    text = open(KEY_DOC, encoding="utf-8").read()
    env = RELAYS[relay]["env"]                        # e.g. ZENMUX_API_KEY
    m = re.search(env + r"\s*[=:]\s*(sk-[A-Za-z0-9-]{32,})", text)
    if m:
        return m.group(1)
    m = KEY_RE.search(text)
    return m.group(0) if m else None


def resolve_key(cli_key, relay):
    if cli_key:
        return cli_key
    if os.environ.get(RELAYS[relay]["env"]):
        return os.environ[RELAYS[relay]["env"]]
    k = key_from_doc(relay)
    if k:
        return k
    raise SystemExit(
        f"no API key for relay '{relay}' — pass --api-key, set "
        f"${RELAYS[relay]['env']}, or record one in {KEY_DOC} (see image-relay.md).")


# ---- relay -------------------------------------------------------------------
def generate(prompt, key, base_url, model, size, n):
    """POST /images/generations and return raw PNG bytes (first image)."""
    body = json.dumps({"model": model, "prompt": prompt,
                       "size": size, "n": n}).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": "research-genealogy-skill"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise SystemExit(f"relay HTTP {e.code}: {detail}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise SystemExit(f"relay unreachable: {e}")

    items = payload.get("data") or []
    if not items:
        raise SystemExit(f"relay returned no image: {json.dumps(payload)[:800]}")
    item = items[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=300) as r:
            return r.read()
    raise SystemExit(f"unrecognized image response: {json.dumps(item)[:800]}")


def main():
    ap = argparse.ArgumentParser(description="genealogy figure prompt → image")
    ap.add_argument("input", help="figure-prompt .md / lineage.json / '-' stdin")
    ap.add_argument("--out", default="", help="output PNG path")
    ap.add_argument("--size", default="1536x1024",
                    help="image size, e.g. 1536x1024 / 1024x1024 / 1024x1536")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--relay", choices=sorted(RELAYS), default=DEFAULT_RELAY,
                    help="image relay (中转站); default zenmux")
    ap.add_argument("--base-url", default="",
                    help="override the relay's base URL")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the prompt that would be sent and exit (no network)")
    args = ap.parse_args()

    prompt = prompt_from_input(args.input)
    if not prompt:
        raise SystemExit("empty prompt after extraction — is the input a "
                         "figure-prompt doc or a lineage.json?")
    if args.print_prompt:
        print(prompt)
        return

    out = args.out or (
        "figure.png" if args.input == "-"
        else os.path.splitext(args.input)[0] + ".png")
    base_url = args.base_url or relay_base(args.relay)
    key = resolve_key(args.api_key, args.relay)
    sys.stderr.write(
        f"calling {base_url} · {args.relay} · {args.model} · {args.size} …\n")
    png = generate(prompt, key, base_url, args.model, args.size, args.n)
    with open(out, "wb") as f:
        f.write(png)
    print(f"saved {out}  ({len(png):,} bytes)")


if __name__ == "__main__":
    main()
