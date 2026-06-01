# Imperative Context Language (ICL)

ICL is a structured intermediate representation for governed AI agent execution in enterprise systems.

It sits between what an AI agent understands and what an enterprise system needs to receive — carrying identity, enforcing permissions, gating high-risk actions for human approval, rolling back partial failures, and writing an immutable audit trail. Every step is a structured event. Every event is attributable.

The byproduct of running that governance at scale is a dataset that doesn't exist anywhere else: real AI reasoning mapped to real human approval decisions mapped to real outcomes in real enterprise systems — the causal chain that makes agents meaningfully improvable.

---

## The Two Layers

**Execution layer** — eight event types that enforce the four properties enterprise governance requires simultaneously:
- Identity propagation through every action event
- Failure as a first-class event the agent can reason about
- Human approval gating before high-risk actions execute
- Transactional rollback on partial workflow failure

**Cognitive layer** — three event types that capture why the agent acted:
- `THINK` — one sentence of agent reasoning at a decision point
- `DECIDE` — the inference committed to, with stated reason
- `REVISE` — explicit audit marker for self-correction

Same 11 event types. Same format. The execution layer is what makes deployment safe. The cognitive layer is what makes deployment useful.

---

## The Three-Actor Model

```
U: "Issue a $5,000 retention credit to the Johnson account"
U: REQ_ACT issue_credit, entity=account, amount=5000, credit_type=retention

A: PERMISSION_CHECK user=demo_user_001, role=admin, result=APPROVAL_REQUIRED
A: STATE issue_credit.pending_approval
A: THINK "Credit exceeds auto-approval threshold — human review required."
A: DECIDE approval_status=pending, reason=credit_amount_exceeds_threshold
A: APPROVAL_REQUEST action=issue_credit, amount=5000, risk=high, approver=ops_manager

H: APPROVAL_DECISION decision=approved, approver=ops_manager

A: CALL Salesforce.issue_credit(amount=5000, credit_type=retention)
A: RES Salesforce.issue_credit, status=success, latency=264ms
A: STATE issue_credit.completed
```

`U:` is the user. `A:` is the agent. `H:` is the human approver.

The `H:` line is the one that doesn't exist anywhere else.

---

## Contents

| File | What It Is |
|---|---|
| [`SPEC.md`](SPEC.md) | The canonical ICL specification |
| [`demo/`](demo/) | Runnable demo — three acts, live LLM calls, real audit log |
| [`paper/icl-paper.md`](paper/icl-paper.md) | Full technical paper |
| [`paper/icl-example-transcript.md`](paper/icl-example-transcript.md) | Canonical ICL transcript, generated live |

---

## Running the Demo

```bash
cd demo
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key
python nibble_demo.py
```

```
/act1  — The action    (VP Engineering)
/act2  — The judgment  (CISO · Schulman)
quit   — Exit
```

`/act1` shows the nominal success path: natural language encoded to ICL, permission approved, system action executed, audit log written.

`/act2` shows the judgment path: high-risk action hits the approval threshold, agent reasons about it (`THINK`/`DECIDE`), human approves or rejects, execution follows the decision. Ends with the training record — what the interaction just generated as a labelled data point.

---

## The Paper

[`paper/icl-paper.md`](paper/icl-paper.md) — *Imperative Context Language: A Unified Cognitive and Execution Runtime for Enterprise AI Agents*

---

## Licence

MIT
