#!/usr/bin/env python3
"""
NibbleAI — Translation Layer Demo
-----------------------------------
Run:  python nibble_translate.py
Deps: pip install anthropic pyyaml requests
Env:  export ANTHROPIC_API_KEY=your_key

The point: ICL translates prompt to API.
The ICL event is system-agnostic.
The config knows the target system.
Swap the config — same ICL event, different API, different result.

Commands:
  /swap    — switch active target (Wikipedia ↔ REST Countries)
  /config  — show current config mapping
  /icl     — show last raw ICL event
  quit     — exit
"""

import anthropic
import yaml
import json
import uuid
import time
import os
import requests
from datetime import datetime, timezone

# ── Colours ───────────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
DIM     = "\033[2m"
WHITE   = "\033[97m"

def banner(t): print(f"\n{BOLD}{CYAN}{'─'*62}{RESET}\n{BOLD}{CYAN}  {t}{RESET}\n{BOLD}{CYAN}{'─'*62}{RESET}")
def sub(t):    print(f"\n{BOLD}{YELLOW}  ▶ {t}{RESET}")
def ok(t):     print(f"  {GREEN}✓ {t}{RESET}")
def fail(t):   print(f"  {RED}✗ {t}{RESET}")
def dim(t):    print(f"  {DIM}{t}{RESET}")

def icl_line(line: str):
    l = line.strip()
    if l.startswith("//"):   print(f"  {DIM}{l}{RESET}")
    elif l.startswith("U:"): print(f"  {BOLD}{GREEN}{l}{RESET}")
    elif "CALL" in l:        print(f"  {BOLD}{YELLOW}{l}{RESET}")
    elif "RES"  in l:        print(f"  {CYAN}{l}{RESET}")
    elif "STATE" in l:       print(f"  {DIM}{l}{RESET}")
    elif "ERROR" in l:       print(f"  {RED}{l}{RESET}")
    else:                    print(f"  {WHITE}{l}{RESET}")


# ── Config ────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
        return yaml.safe_load(f)


# ── Helpers ───────────────────────────────────────────────────────────────────
def ts() -> str: return datetime.now(timezone.utc).isoformat()
def eid() -> str: return str(uuid.uuid4())


# ── Target configs ────────────────────────────────────────────────────────────
# This is the translation layer.
# The ICL event doesn't know any of this exists.
# Swap the config — same ICL event, completely different system.

TARGETS = {
    "wikipedia": {
        "name":        "Wikipedia",
        "description": "Free encyclopaedia — article summaries",
        "icl_action":  "search",
        "call":        lambda q: _call_wikipedia(q),
        "mapping":     "REQ_INFO search → GET wikipedia.org/api/rest_v1/page/summary/{query}",
    },
    "countries": {
        "name":        "REST Countries",
        "description": "Country data — capitals, populations, currencies",
        "icl_action":  "lookup",
        "call":        lambda q: _call_countries(q),
        "mapping":     "REQ_INFO lookup → GET restcountries.com/v3.1/name/{query}",
    },
}

TARGET_ORDER = ["wikipedia", "countries"]


WIKI_HEADERS = {
    "Accept":     "application/json",
    "User-Agent": "NibbleAI/1.0 (translation-demo; contact@nibbleai.com)"
}

def _call_wikipedia(query: str) -> tuple[str, int]:
    t0 = time.time()
    try:
        slug = requests.utils.quote(query.strip().replace(" ", "_"))
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            headers=WIKI_HEADERS, timeout=8
        )
        ms = int((time.time() - t0) * 1000)

        if r.status_code == 200 and r.content:
            data = r.json()
            extract = data.get("extract", "No summary available.")
            sentences = extract.split(". ")
            return ". ".join(sentences[:3]) + ("." if len(sentences) > 3 else ""), ms

        # Fallback: search API
        sr = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search",
                    "srsearch": query, "format": "json", "srlimit": 1},
            headers=WIKI_HEADERS, timeout=8
        )
        results = sr.json().get("query", {}).get("search", [])
        if not results:
            return f"No Wikipedia article found for '{query}'", ms

        slug2 = requests.utils.quote(results[0]["title"].replace(" ", "_"))
        r2 = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug2}",
            headers=WIKI_HEADERS, timeout=8
        )
        data = r2.json()
        extract = data.get("extract", "No summary available.")
        sentences = extract.split(". ")
        return ". ".join(sentences[:3]) + ("." if len(sentences) > 3 else ""), ms

    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return f"Wikipedia error: {e}", ms


def _call_countries(query: str) -> tuple[str, int]:
    t0 = time.time()
    r = requests.get(
        f"https://restcountries.com/v3.1/name/{query}",
        params={"fullText": "false"},
        timeout=8
    )
    ms = int((time.time() - t0) * 1000)
    if r.status_code != 200:
        return f"No country data found for '{query}'", ms
    data = r.json()[0]
    name     = data.get("name", {}).get("common", query)
    capital  = ", ".join(data.get("capital", ["unknown"]))
    pop      = f"{data.get('population', 0):,}"
    region   = data.get("region", "unknown")
    currency_data = data.get("currencies", {})
    currencies = ", ".join(
        f"{v.get('name')} ({v.get('symbol', '')})"
        for v in currency_data.values()
    )
    return (f"{name} — Capital: {capital} · Population: {pop} · "
            f"Region: {region} · Currency: {currencies}"), ms


# ── Encoder ───────────────────────────────────────────────────────────────────
ENCODE_PROMPT = """Extract the search intent from this query.

Query: "{request}"

Output JSON:
{{
  "action": "search",
  "entity": "<topic | country | person | concept | place>",
  "parameters": {{
    "query": "<the specific term to look up, stripped of question words>"
  }},
  "confidence": <0.0-1.0>
}}

Examples:
"What is quantum computing?" → {{"action":"search","entity":"concept","parameters":{{"query":"quantum computing"}},"confidence":0.95}}
"Capital of France"          → {{"action":"search","entity":"country","parameters":{{"query":"France"}},"confidence":0.98}}
"Who invented the telephone?"→ {{"action":"search","entity":"person","parameters":{{"query":"Alexander Graham Bell"}},"confidence":0.90}}

Output ONLY valid JSON."""


def encode(request: str, config: dict) -> tuple[dict, int]:
    client = anthropic.Anthropic()
    t0 = time.time()
    r = client.messages.create(
        model=config["encoder"]["model"],
        max_tokens=200,
        messages=[{"role": "user",
                   "content": ENCODE_PROMPT.format(request=request)}]
    )
    ms = int((time.time() - t0) * 1000)
    raw = r.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip()), ms


# ── Audit ─────────────────────────────────────────────────────────────────────
def write_audit(events: list, audit_path: str):
    with open(audit_path, "a") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


# ── Main flow ─────────────────────────────────────────────────────────────────
def run():
    banner("NibbleAI — Translation Layer Demo\n  ICL: prompt → any API · zero custom integration")
    config     = load_config()
    audit_path = os.path.join(os.path.dirname(__file__), config["audit"]["log_file"])

    active_key  = "wikipedia"
    last_event  = None

    def show_config():
        t = TARGETS[active_key]
        print(f"\n  {BOLD}Active target : {t['name']}{RESET}")
        print(f"  {DIM}{t['description']}{RESET}")
        print(f"\n  {BOLD}Config mapping:{RESET}")
        print(f"  {CYAN}{'─'*50}{RESET}")
        print(f"  {WHITE}{t['mapping']}{RESET}")
        print(f"  {CYAN}{'─'*50}{RESET}")
        print(f"\n  {DIM}The ICL event does not contain any of this.{RESET}")
        print(f"  {DIM}It only carries: action, entity, query, identity.{RESET}")

    show_config()
    print(f"\n  {DIM}/swap · /config · /icl · quit{RESET}")

    while True:
        print(f"\n{BOLD}  >{RESET} ", end="", flush=True)
        raw = input().strip()

        if raw.lower() in ("quit", "exit", "q"):
            print(f"\n{DIM}  Goodbye.{RESET}\n")
            break

        if not raw:
            continue

        if raw == "/config":
            show_config()
            continue

        if raw == "/icl":
            if last_event:
                print(f"\n  {BOLD}Last ICL event (raw JSON):{RESET}")
                print(f"  {CYAN}{'─'*50}{RESET}")
                print(f"  {DIM}{json.dumps(last_event, indent=2)}{RESET}")
                print(f"  {CYAN}{'─'*50}{RESET}")
                print(f"  {DIM}This event has no knowledge of {TARGETS[active_key]['name']}.{RESET}")
                print(f"  {DIM}The config above is what routes it.{RESET}")
            else:
                dim("No event yet — make a query first.")
            continue

        if raw == "/swap":
            idx = TARGET_ORDER.index(active_key)
            active_key = TARGET_ORDER[(idx + 1) % len(TARGET_ORDER)]
            t = TARGETS[active_key]
            print(f"\n  {BOLD}{GREEN}✓ Switched to {t['name']}{RESET}")
            print(f"  {DIM}{t['mapping']}{RESET}")
            if last_event:
                print(f"\n  {DIM}The ICL event from your last query is unchanged.{RESET}")
                print(f"  {DIM}Same intent. New target. No code changed.{RESET}")
            continue

        # ── Encode ────────────────────────────────────────────────────────────
        target = TARGETS[active_key]
        conv_id = eid()
        events  = []

        print(f"\n  {DIM}// CONV_ID: {conv_id[:8]}...{RESET}")
        icl_line(f'U: "{raw}"')

        sub("Encoding...")
        try:
            encoded, enc_ms = encode(raw, config)
        except Exception as e:
            fail(f"Encoding failed: {e}")
            continue

        query = encoded.get("parameters", {}).get("query", raw)

        # ── ICL REQ_INFO event ────────────────────────────────────────────────
        req_id  = eid()
        req_evt = {
            "icl_version":       "0.1",
            "event_id":          req_id,
            "conversation_id":   conv_id,
            "timestamp":         ts(),
            "event_type":        "REQ_INFO",
            "actor":             "user",
            "user_id":           config["identity"]["user_id"],
            "user_name":         config["identity"]["user_name"],
            "action":            "search",
            "entity":            encoded.get("entity", "topic"),
            "parameters":        {"query": query},
            "confidence":        encoded.get("confidence", 0.9),
            "encoder_latency_ms": enc_ms,
            "original_request":  raw,
            # ↓ this event has no knowledge of the target system
        }
        events.append(req_evt)
        last_event = req_evt

        icl_line(f"U: REQ_INFO search, entity={encoded.get('entity','topic')}, query={query}")
        dim(f"encoded in {enc_ms}ms · confidence={encoded.get('confidence', 0.9)}")

        # ── Config lookup ─────────────────────────────────────────────────────
        print(f"\n  {BOLD}Config → {target['name']}{RESET}")
        print(f"  {DIM}{target['mapping']}{RESET}")

        # ── CALL via config ───────────────────────────────────────────────────
        call_id  = eid()
        call_evt = {
            "icl_version":     "0.1",
            "event_id":        call_id,
            "conversation_id": conv_id,
            "timestamp":       ts(),
            "event_type":      "CALL",
            "actor":           "agent",
            "action":          "search",
            "target_system":   target["name"],
            "parameters":      {"query": query},
            "idempotency_key": eid(),
            "original_event_id": req_id,
        }
        events.append(call_evt)
        icl_line(f"A: CALL {target['name']}.search(query={query})")

        try:
            result, api_ms = target["call"](query)
            status = "success"
        except Exception as e:
            result = str(e)
            api_ms = 0
            status = "failure"

        # ── RES event ─────────────────────────────────────────────────────────
        res_id  = eid()
        res_evt = {
            "icl_version":     "0.1",
            "event_id":        res_id,
            "conversation_id": conv_id,
            "timestamp":       ts(),
            "event_type":      "RES",
            "actor":           "system",
            "action":          "search",
            "target_system":   target["name"],
            "status":          status,
            "latency_ms":      api_ms,
            "result":          result,
            "original_event_id": call_id,
        }
        events.append(res_evt)
        icl_line(f"A: RES {target['name']}.search, status={status}, latency={api_ms}ms")

        # ── STATE completed ───────────────────────────────────────────────────
        state_evt = {
            "icl_version":     "0.1",
            "event_id":        eid(),
            "conversation_id": conv_id,
            "timestamp":       ts(),
            "event_type":      "STATE",
            "actor":           "agent",
            "state":           "search.completed",
            "original_event_id": res_id,
        }
        events.append(state_evt)
        icl_line("A: STATE search.completed")

        # ── Result ────────────────────────────────────────────────────────────
        print(f"\n  {CYAN}{'─'*50}{RESET}")
        if status == "success":
            for line in result.split(" · "):
                print(f"  {WHITE}{line}{RESET}")
        else:
            fail(result)
        print(f"  {CYAN}{'─'*50}{RESET}")

        write_audit(events, audit_path)
        dim(f"{len(events)} events → {audit_path}")
        dim(f"type /icl to inspect the raw event · /swap to change target")


if __name__ == "__main__":
    run()
