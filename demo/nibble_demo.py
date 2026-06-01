#!/usr/bin/env python3
"""
NibbleAI Demo — Three Acts
--------------------------
Run:   python nibble_demo.py
Deps:  pip install anthropic pyyaml requests
Env:   export ANTHROPIC_API_KEY=your_key

  /act1  — The action    (VP Engineering)
  /act2  — The judgment  (CISO · Schulman)
  quit   — Exit
"""

import anthropic
import yaml
import json
import uuid
import time
import os
import random
import requests
from datetime import datetime, timezone

RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
DIM     = "\033[2m"
WHITE   = "\033[97m"

def banner(t): print(f"\n{BOLD}{CYAN}{'─'*62}{RESET}\n{BOLD}{CYAN}  {t}{RESET}\n{BOLD}{CYAN}{'─'*62}{RESET}")
def sub(t):    print(f"\n{BOLD}{YELLOW}  ▶ {t}{RESET}")
def ok(t):     print(f"  {GREEN}✓ {t}{RESET}")
def note(t):   print(f"  {DIM}{t}{RESET}")

def icl(line: str):
    l = line.strip()
    if not l:
        return
    if   l.startswith("//"):              print(f"  {DIM}{l}{RESET}")
    elif l.startswith("U:"):              print(f"  {BOLD}{GREEN}{l}{RESET}")
    elif "THINK"   in l:                  time.sleep(0.6); print(f"  {CYAN}{l}{RESET}")
    elif "DECIDE"  in l:                  time.sleep(0.4); print(f"  {MAGENTA}{l}{RESET}")
    elif "APPROVAL" in l:                 print(f"  {BOLD}{YELLOW}{l}{RESET}")
    elif "ERROR"   in l or "DENIED" in l: print(f"  {RED}{l}{RESET}")
    elif "CALL"    in l:                  print(f"  {BOLD}{YELLOW}{l}{RESET}")
    elif "RES"     in l:                  print(f"  {CYAN}{l}{RESET}")
    elif "STATE"   in l:                  print(f"  {DIM}{l}{RESET}")
    else:                                 print(f"  {WHITE}{l}{RESET}")


def load_config() -> dict:
    with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
        return yaml.safe_load(f)

def ts()  -> str: return datetime.now(timezone.utc).isoformat()
def eid() -> str: return str(uuid.uuid4())


# ── Publisher ─────────────────────────────────────────────────────────────────

class Publisher:
    def __init__(self, config: dict, audit_path: str):
        self.webhook  = config["target"]["webhook_url"]
        self.simulate = config["target"].get("simulate_execution", False)
        self.audit    = audit_path
        self.events: list = []

    def emit(self, event: dict):
        self.events.append(event)
        with open(self.audit, "a") as f:
            f.write(json.dumps(event) + "\n")

    def execute(self, event: dict) -> tuple[str, int, int]:
        self.emit(event)
        if self.simulate:
            time.sleep(random.uniform(0.18, 0.32))
            return "success", 200, random.randint(180, 320)
        t0 = time.time()
        try:
            r  = requests.post(self.webhook, json=event, timeout=5)
            ms = int((time.time() - t0) * 1000)
            return ("success" if r.status_code < 400 else "failure"), r.status_code, ms
        except Exception:
            return "failure", 0, int((time.time() - t0) * 1000)


# ── Encoder ───────────────────────────────────────────────────────────────────

ENCODE_PROMPT = """Extract the enterprise action from this request as JSON.

Request: "{request}"

Output:
{{
  "action": "<one of: update_record | issue_credit | provision_access | create_ticket>",
  "entity": "<target entity type, e.g. account, user, ticket>",
  "entity_id": "<identifier if mentioned, else null>",
  "parameters": {{}},
  "confidence": <0.0-1.0>
}}

Output ONLY valid JSON."""

def encode(request: str, config: dict) -> tuple[dict, int]:
    client = anthropic.Anthropic()
    t0  = time.time()
    r   = client.messages.create(
        model=config["encoder"]["model"], max_tokens=300,
        messages=[{"role": "user", "content": ENCODE_PROMPT.format(request=request)}]
    )
    ms  = int((time.time() - t0) * 1000)
    raw = r.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip()), ms


# ── Cognitive trace ───────────────────────────────────────────────────────────

COGNITIVE_PROMPT = """You are the NibbleAI reasoning layer. An agent action requires human approval.

Action:     {action}
Entity:     {entity}
Parameters: {params}
Reason:     {reason}

Generate exactly two lines:
A: THINK "<one sentence: what the agent considered before requesting approval>"
A: DECIDE <variable>=<value>, reason=<brief>

Output ONLY those two lines."""

def cognitive_trace(action: str, entity: str, params: dict,
                    reason: str, config: dict) -> tuple[str, str]:
    client = anthropic.Anthropic()
    r = client.messages.create(
        model=config["encoder"]["model"], max_tokens=120,
        messages=[{"role": "user", "content": COGNITIVE_PROMPT.format(
            action=action, entity=entity, params=json.dumps(params), reason=reason
        )}]
    )
    lines  = [l.strip() for l in r.content[0].text.strip().split("\n") if l.strip()]
    think  = next((l for l in lines if "THINK"  in l), f'A: THINK "Human approval required — {reason}"')
    decide = next((l for l in lines if "DECIDE" in l),  "A: DECIDE escalation_required=true, reason=threshold_exceeded")
    return think, decide


# ── Approval gate ─────────────────────────────────────────────────────────────

def approval_gate(action: str, params: dict,
                  pub: Publisher, config: dict, conv_id: str, original_id: str) -> dict:
    req_id     = eid()
    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
    pub.emit({
        "icl_version": "0.1", "event_id": req_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "APPROVAL_REQUEST", "actor": "agent",
        "user_id": config["identity"]["user_id"], "action": action,
        "parameters": params, "risk_level": "high", "approver_id": "ops_manager",
        "timeout_seconds": 300, "original_event_id": original_id,
    })
    icl(f"A: APPROVAL_REQUEST action={action}, {params_str}, risk=high, approver=ops_manager")

    print(f"\n  {BOLD}{YELLOW}{'─'*52}{RESET}")
    print(f"  {BOLD}{YELLOW}  WAITING FOR HUMAN JUDGMENT{RESET}")
    print(f"  {YELLOW}  [A] Approve    [R] Reject{RESET}")
    print(f"  {BOLD}{YELLOW}{'─'*52}{RESET}")
    print(f"  > ", end="", flush=True)

    while True:
        choice = input().strip().upper()
        if choice in ("A", "R"): break
        print(f"  A or R: ", end="", flush=True)

    decision    = "approved" if choice == "A" else "rejected"
    decision_id = eid()
    evt = {
        "icl_version": "0.1", "event_id": decision_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "APPROVAL_DECISION", "actor": "human",
        "user_id": "ops_manager", "decision": decision,
        "original_request_event_id": req_id,
    }
    pub.emit(evt)
    icl(f"A: APPROVAL_DECISION decision={decision}, approver=ops_manager")
    return evt


# ── Act 3 — Training record ───────────────────────────────────────────────────

def show_training_record(utterance: str, think: str, decide: str,
                          decision: str, outcome: str, action: str, params: dict):
    think_text  = think.replace("A: THINK ", "").strip('"')
    decide_text = decide.replace("A: DECIDE ", "")
    params_str  = ", ".join(f"{k}={v}" for k, v in params.items())

    time.sleep(1.2)
    print(f"\n  {BOLD}{WHITE}{'═' * 54}{RESET}")
    print(f"  {BOLD}{WHITE}  TRAINING RECORD{RESET}")
    print(f"  {WHITE}{'─' * 54}{RESET}")
    print(f"  {DIM}  utterance  {RESET} {WHITE}\"{utterance}\"{RESET}")
    print(f"  {DIM}  understood {RESET} {WHITE}{action} · {params_str}{RESET}")
    print(f"  {DIM}  reasoned   {RESET} {CYAN}{think_text}{RESET}")
    print(f"  {DIM}  decided    {RESET} {MAGENTA}{decide_text}{RESET}")
    human_col = GREEN if decision == "approved" else RED
    print(f"  {DIM}  human      {RESET} {BOLD}{human_col}{decision.upper()} — ops_manager{RESET}")
    out_col = GREEN if outcome == "success" else (YELLOW if outcome == "cancelled" else RED)
    print(f"  {DIM}  outcome    {RESET} {out_col}{outcome}{RESET}")
    print(f"  {WHITE}{'─' * 54}{RESET}")
    print(f"  {DIM}  Utterance → reasoning → human judgment → outcome.{RESET}")
    print(f"  {DIM}  Causally complete. Human-labelled. Not synthetic.{RESET}")
    print(f"  {DIM}  Every enterprise deployment generates thousands.{RESET}")
    print(f"  {BOLD}{WHITE}{'═' * 54}{RESET}\n")


# ── Act 1 — The action ────────────────────────────────────────────────────────

def run_act1(pub: Publisher, config: dict, conv_id: str):
    request = "Update the Johnson account to premium tier and flag for retention"
    target  = config["target"]["system_name"]
    uid     = config["identity"]["user_id"]
    role    = config["identity"]["user_role"]

    note(f'"{request}"')
    print(f"\n  {DIM}// CONV_ID: {conv_id[:8]}...{RESET}")
    icl(f'U: "{request}"')

    sub("Encoding...")
    encoded, enc_ms = encode(request, config)

    action     = encoded["action"]
    entity     = encoded.get("entity", "account")
    params     = encoded.get("parameters", {})
    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
    confidence = encoded.get("confidence", 0.95)

    req_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": req_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "REQ_ACT", "actor": "user",
        "user_id": uid, "user_name": config["identity"]["user_name"],
        "user_role": role, "action": action, "entity": entity,
        "parameters": params, "confidence": confidence,
        "encoder_latency_ms": enc_ms, "original_request": request,
    })
    icl(f"U: REQ_ACT {action}, entity={entity}, {params_str}")
    note(f"encoded in {enc_ms}ms · confidence={confidence}")

    perm_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": perm_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "PERMISSION_CHECK", "actor": "agent",
        "user_id": uid, "user_role": role, "action": action,
        "result": "approved", "reason": "", "original_event_id": req_id,
    })
    icl(f"A: PERMISSION_CHECK user={uid}, action={action}, result=APPROVED")

    call_id  = eid()
    call_evt = {
        "icl_version": "0.1", "event_id": call_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "CALL", "actor": "agent",
        "action": action, "entity": entity, "target_system": target,
        "parameters": params, "idempotency_key": eid(),
        "original_event_id": perm_id,
    }
    icl(f"A: CALL {target}.{action}({params_str})")
    status, http_code, latency_ms = pub.execute(call_evt)

    res_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": res_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "RES", "actor": "system",
        "action": action, "target_system": target, "status": status,
        "http_status": http_code, "latency_ms": latency_ms,
        "original_event_id": call_id,
    })
    icl(f"A: RES {target}.{action}, status={status}, latency={latency_ms}ms")

    pub.emit({
        "icl_version": "0.1", "event_id": eid(), "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "STATE", "actor": "agent",
        "state": f"{action}.completed", "original_event_id": res_id,
    })
    icl(f"A: STATE {action}.completed")

    print()
    ok(f"{len(pub.events)} events — audit log written")
    note(f"Natural language became a governed system action in {enc_ms + latency_ms}ms.")


# ── Act 2 — The judgment (+ Act 3) ───────────────────────────────────────────

def run_act2(pub: Publisher, config: dict, conv_id: str):
    request = "Issue a $5,000 retention credit to the Johnson account"
    target  = config["target"]["system_name"]
    uid     = config["identity"]["user_id"]
    role    = config["identity"]["user_role"]

    note(f'"{request}"')
    print(f"\n  {DIM}// CONV_ID: {conv_id[:8]}...{RESET}")
    icl(f'U: "{request}"')

    sub("Encoding...")
    encoded, enc_ms = encode(request, config)

    action     = encoded["action"]
    entity     = encoded.get("entity", "account")
    params     = encoded.get("parameters", {})
    params_str = ", ".join(f"{k}={v}" for k, v in params.items())

    req_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": req_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "REQ_ACT", "actor": "user",
        "user_id": uid, "user_name": config["identity"]["user_name"],
        "user_role": role, "action": action, "entity": entity,
        "parameters": params, "confidence": encoded.get("confidence", 0.95),
        "encoder_latency_ms": enc_ms, "original_request": request,
    })
    icl(f"U: REQ_ACT {action}, entity={entity}, {params_str}")
    note(f"encoded in {enc_ms}ms")

    perm_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": perm_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "PERMISSION_CHECK", "actor": "agent",
        "user_id": uid, "user_role": role, "action": action,
        "result": "approval_required",
        "reason": "credit $5,000 exceeds auto-approval threshold $1,000",
        "original_event_id": req_id,
    })
    icl(f"A: PERMISSION_CHECK user={uid}, action={action}, result=APPROVAL_REQUIRED")

    pub.emit({
        "icl_version": "0.1", "event_id": eid(), "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "STATE", "actor": "agent",
        "state": f"{action}.pending_approval", "original_event_id": perm_id,
    })
    icl(f"A: STATE {action}.pending_approval")

    sub("Agent reasoning...")
    think, decide = cognitive_trace(
        action, entity, params,
        "credit $5,000 exceeds auto-approval threshold — human approval required before execution",
        config
    )

    pub.emit({
        "icl_version": "0.1", "event_id": eid(), "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "THINK", "actor": "agent",
        "content": think.replace("A: THINK ", "").strip('"'),
        "original_event_id": perm_id,
    })
    icl(think)

    decide_id = eid()
    pub.emit({
        "icl_version": "0.1", "event_id": decide_id, "conversation_id": conv_id,
        "timestamp": ts(), "event_type": "DECIDE", "actor": "agent",
        "content": decide.replace("A: DECIDE ", ""),
        "original_event_id": perm_id,
    })
    icl(decide)

    print()
    decision_evt = approval_gate(action, params, pub, config, conv_id, decide_id)
    decision     = decision_evt["decision"]

    if decision == "approved":
        call_id  = eid()
        call_evt = {
            "icl_version": "0.1", "event_id": call_id, "conversation_id": conv_id,
            "timestamp": ts(), "event_type": "CALL", "actor": "agent",
            "action": action, "entity": entity, "target_system": target,
            "parameters": params, "idempotency_key": eid(),
            "original_event_id": decision_evt["event_id"],
        }
        icl(f"A: CALL {target}.{action}({params_str})")
        status, _, latency_ms = pub.execute(call_evt)

        res_id = eid()
        pub.emit({
            "icl_version": "0.1", "event_id": res_id, "conversation_id": conv_id,
            "timestamp": ts(), "event_type": "RES", "actor": "system",
            "action": action, "target_system": target, "status": status,
            "latency_ms": latency_ms, "original_event_id": call_id,
        })
        icl(f"A: RES {target}.{action}, status={status}, latency={latency_ms}ms")

        pub.emit({
            "icl_version": "0.1", "event_id": eid(), "conversation_id": conv_id,
            "timestamp": ts(), "event_type": "STATE", "actor": "agent",
            "state": f"{action}.completed", "original_event_id": res_id,
        })
        icl(f"A: STATE {action}.completed")
        outcome = status
    else:
        pub.emit({
            "icl_version": "0.1", "event_id": eid(), "conversation_id": conv_id,
            "timestamp": ts(), "event_type": "STATE", "actor": "agent",
            "state": f"{action}.cancelled", "original_event_id": decision_evt["event_id"],
        })
        icl(f"A: STATE {action}.cancelled")
        outcome = "cancelled"

    print()
    ok(f"{len(pub.events)} events — audit log written")

    # ── Act 3 ─────────────────────────────────────────────────────────────────
    show_training_record(request, think, decide, decision, outcome, action, params)


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    banner("NibbleAI")
    config     = load_config()
    audit_path = os.path.join(os.path.dirname(__file__), config["audit"]["log_file"])

    print(f"\n  {DIM}Encoder  {config['encoder']['model']}{RESET}")
    print(f"  {DIM}Identity {config['identity']['user_name']} · {config['identity']['user_role']}{RESET}")
    print(f"  {DIM}Target   {config['target']['system_name']}{RESET}")
    print(f"\n  {DIM}/act1  — The action    VP Engineering{RESET}")
    print(f"  {DIM}/act2  — The judgment  CISO · Schulman{RESET}")
    print(f"  {DIM}quit   — Exit{RESET}")

    while True:
        print(f"\n{BOLD}  >{RESET} ", end="", flush=True)
        raw = input().strip()

        if raw.lower() in ("quit", "exit", "q"):
            print(f"\n{DIM}  Goodbye.{RESET}\n")
            break
        if not raw:
            continue

        conv_id = eid()
        pub     = Publisher(config, audit_path)

        if raw == "/act1":
            print()
            run_act1(pub, config, conv_id)
        elif raw == "/act2":
            print()
            run_act2(pub, config, conv_id)
        else:
            note("Try /act1 or /act2.")
            continue

        print(f"\n  {DIM}{'─' * 52}{RESET}")
        note(f"{len(pub.events)} events → {audit_path}")


if __name__ == "__main__":
    run()
