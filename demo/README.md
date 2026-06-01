# NibbleAI Demo — Three Acts

A live demonstration of ICL governed execution. Real LLM calls. Real audit log. No slides.

---

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key
python nibble_demo.py
```

---

## The Three Acts

### /act1 — The Action
*For the VP of Engineering.*

Natural language request encoded to ICL in under 200ms. Permission check. System action. Audit log written. Five events. The integration wall, dissolved.

### /act2 — The Judgment
*For the CISO and for Schulman.*

High-risk action ($5,000 credit) hits the approval threshold. The agent reasons about it — `THINK`/`DECIDE` lines appear on screen, generated live by the LLM. Action pauses. You approve or reject. The decision is recorded. Execution follows.

Then: the training record. What the last 30 seconds just generated — utterance, reasoning, human judgment, outcome — formatted as a labelled data point. The causal chain that no synthetic pipeline produces.

---

## Going Live

By default `simulate_execution: true` in `config.yaml`. Execution is simulated with realistic latency.

To fire against a real system: set `simulate_execution: false` and paste a live webhook URL into `webhook_url`. The demo will POST structured ICL events to that URL on every execution.

---

## What Gets Written

Every run appends to `nibble_audit.jsonl`. Each line is a complete ICL event in JSON. The full conversation graph for any run is recoverable by filtering on `conversation_id`.

```bash
cat nibble_audit.jsonl | python -m json.tool
```
