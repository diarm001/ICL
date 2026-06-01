# Imperative Context Language (ICL)
## Specification v1.0

---

## What ICL Is

ICL is a structured intermediate representation that sits between AI agent output and enterprise system action. It has two layers that share a format because they share a causal chain.

**The execution layer** governs what the agent does: identity propagation, permission checking, approval gating, rollback on partial failure, and an immutable audit trail.

**The cognitive layer** captures why the agent acted: structured reasoning traces mapped to decisions, mapped to human judgment, mapped to real-world outcomes.

The same 11 event types express both layers. An enterprise deployment generates both simultaneously. The execution layer is what makes deployment safe. The cognitive layer is what makes deployment useful — as training data, as audit evidence, as operational intelligence.

---

## Design Principles

1. **Imperative, not descriptive.** ICL specifies what to do, not what happened. Traces are executable and replayable.
2. **Identity-carrying.** The original user's identity propagates through every downstream event. No elevated service accounts. Least-privilege at execution time.
3. **Failure-aware.** Errors are first-class events, not exceptions. Every failure generates a structured `ERROR` event the agent can reason about.
4. **Transport-agnostic.** ICL events are standard JSON. They travel over Kafka, HTTP, any message queue, or direct API call. No proprietary wire format.
5. **Deterministic downstream.** Everything after the encoding step is configuration lookup, not inference. New system integrations are config changes, not code deployments.

---

## The Three-Actor Model

ICL traces have three classes of actor:

| Actor | Prefix | Role |
|---|---|---|
| User | `U:` | Intent — the original request, identity-carrying |
| Agent | `A:` | Reasoning, action, state transitions |
| Human | `H:` | Judgment — approval or rejection of agent interpretation |

The `H:` actor is what distinguishes ICL traces from logs. `APPROVAL_DECISION` is the only event with `actor: human`. It is the ground truth label that a domain expert attaches to the agent's interpretation in a real operational context. Everything above it in the trace is context. Everything below it is outcome.

---

## Execution Layer — Event Types

| Event | Actor | Purpose |
|---|---|---|
| `REQ_ACT` | User | Intent request — identity-carrying entry point |
| `STATE` | Agent | Workflow state transition |
| `CALL` | Agent | System action with idempotency key |
| `RES` | System | Outcome — success, failure, or partial |
| `ERROR` | System | Failure as first-class event |
| `PERMISSION_CHECK` | Agent | Identity and role verification before execution |
| `APPROVAL_REQUEST` | Agent | High-risk action paused for human decision |
| `APPROVAL_DECISION` | Human | Approver decision — recorded in audit log |
| `ROLLBACK` | Agent | Compensating action on partial failure |

---

## Cognitive Layer — Event Types

| Event | Actor | Purpose |
|---|---|---|
| `THINK` | Agent | Internal reasoning trace — deliberation before decision |
| `DECIDE` | Agent | Inference committed to — variable assignment with reason |
| `REVISE` | Agent | Prior step amended — explicit audit marker for self-correction |

Cognitive events are generated at decision points in the execution flow: on `ERROR` (reasoning about failure), on `APPROVAL_REQUEST` (reasoning about risk), and on `REVISE` (reasoning about self-correction). They are not summaries appended after the fact.

---

## Base Event Schema

Every ICL event conforms to this base schema:

```json
{
  "icl_version": "1.0",
  "event_id": "<uuid>",
  "conversation_id": "<uuid>",
  "timestamp": "<ISO8601>",
  "event_type": "<ICL_EVENT_TYPE>",
  "actor": "user | agent | system | human",
  "user_id": "<string>",
  "user_role": "<string>",
  "action": "<string>",
  "entity": "<string>",
  "entity_id": "<string | null>",
  "parameters": {},
  "original_event_id": "<uuid | null>"
}
```

`original_event_id` chains events causally. Every `RES` points back to the `CALL` that triggered it. Every `ERROR` points back to the action that failed. The complete event graph for a conversation is a directed acyclic chain from `REQ_ACT` to terminal `STATE`.

---

## Event Definitions

### REQ_ACT
User intent — the entry point for every governed action. Carries the original natural language request alongside the structured intent extracted by the encoder.

```json
{
  "event_type": "REQ_ACT",
  "actor": "user",
  "user_id": "demo_user_001",
  "user_role": "admin",
  "action": "issue_credit",
  "entity": "account",
  "entity_id": "johnson_acct_001",
  "parameters": { "amount": 5000, "credit_type": "retention" },
  "confidence": 0.95,
  "encoder_latency_ms": 1177,
  "original_request": "Issue a $5,000 retention credit to the Johnson account"
}
```

### PERMISSION_CHECK
Identity and role verification against the caller's existing authorisation model. Executed before any system is contacted.

```json
{
  "event_type": "PERMISSION_CHECK",
  "actor": "agent",
  "user_id": "demo_user_001",
  "user_role": "admin",
  "action": "issue_credit",
  "result": "approval_required",
  "reason": "credit $5,000 exceeds auto-approval threshold $1,000",
  "original_event_id": "<req_act_event_id>"
}
```

`result` is one of: `approved`, `denied`, `approval_required`.

### THINK
Agent reasoning trace. One sentence of deliberation generated at a decision point.

```json
{
  "event_type": "THINK",
  "actor": "agent",
  "content": "The $5,000 credit exceeds the auto-approval threshold and requires human review to validate business justification.",
  "original_event_id": "<permission_check_event_id>"
}
```

### DECIDE
Inference committed to. Variable assignment with stated reason.

```json
{
  "event_type": "DECIDE",
  "actor": "agent",
  "content": "approval_status=pending, reason=credit_amount_exceeds_auto_approval_threshold",
  "original_event_id": "<think_event_id>"
}
```

### APPROVAL_REQUEST
High-risk action paused for human decision. The action does not execute until `APPROVAL_DECISION` is received.

```json
{
  "event_type": "APPROVAL_REQUEST",
  "actor": "agent",
  "user_id": "demo_user_001",
  "action": "issue_credit",
  "parameters": { "amount": 5000, "credit_type": "retention" },
  "risk_level": "high",
  "approver_id": "ops_manager",
  "timeout_seconds": 300,
  "original_event_id": "<decide_event_id>"
}
```

### APPROVAL_DECISION
Human approver decision. The ground truth label.

```json
{
  "event_type": "APPROVAL_DECISION",
  "actor": "human",
  "user_id": "ops_manager",
  "decision": "approved",
  "original_request_event_id": "<approval_request_event_id>",
  "reason": "Approved by ops_manager"
}
```

### CALL
System action. Every `CALL` carries an idempotency key to prevent duplicate execution on retry.

```json
{
  "event_type": "CALL",
  "actor": "agent",
  "action": "issue_credit",
  "entity": "account",
  "target_system": "Salesforce",
  "parameters": { "amount": 5000, "credit_type": "retention" },
  "idempotency_key": "<uuid>",
  "original_event_id": "<approval_decision_event_id>"
}
```

### RES
System outcome. Always references the `CALL` that produced it.

```json
{
  "event_type": "RES",
  "actor": "system",
  "action": "issue_credit",
  "target_system": "Salesforce",
  "status": "success",
  "http_status": 200,
  "latency_ms": 264,
  "original_event_id": "<call_event_id>"
}
```

### ERROR
Failure as a first-class event. Carries structured metadata the agent can reason about.

```json
{
  "event_type": "ERROR",
  "actor": "system",
  "action": "provision_support_tier",
  "failure_type": "SYSTEM_UNAVAILABLE",
  "error_message": "system_unavailable",
  "retryable": true,
  "original_event_id": "<call_event_id>"
}
```

`failure_type` is one of: `PERMISSION_DENIED`, `SYSTEM_UNAVAILABLE`, `API_TIMEOUT`, `INVALID_DATA`, `VERSION_MISMATCH`.

### REVISE
Self-correction. Explicit audit marker for a prior step being amended.

```json
{
  "event_type": "REVISE",
  "actor": "agent",
  "step": "provision_support_tier",
  "attempt": 2,
  "reason": "retryable_error",
  "original_event_id": "<error_event_id>"
}
```

### ROLLBACK
Compensating action on partial failure. Executes in reverse order for each completed step.

```json
{
  "event_type": "ROLLBACK",
  "actor": "agent",
  "action": "revert_billing_address",
  "compensating_for": "update_billing_address",
  "status": "success",
  "trigger": "SYSTEM_UNAVAILABLE",
  "original_event_id": "<error_event_id>"
}
```

### STATE
Workflow state transition. Marks entry and exit of named workflow states.

```json
{
  "event_type": "STATE",
  "actor": "agent",
  "state": "issue_credit.completed",
  "original_event_id": "<res_event_id>"
}
```

---

## Human-Readable Shorthand

For documentation and debugging, ICL events may be expressed in shorthand notation. The shorthand maps 1:1 to the JSON schema. The canonical format for transport is always JSON.

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

---

## Transport

ICL events are standard JSON. Transport is infrastructure that already exists:

- Kafka topics (canonical for enterprise deployments)
- HTTP / webhook
- Message queue
- Direct API call

### Kafka Topic Schema

| Topic | Purpose |
|---|---|
| `nibble.icl.actions` | Inbound ICL events for execution |
| `nibble.icl.results` | Execution results |
| `nibble.icl.errors` | Error events for agent reasoning |
| `nibble.icl.approvals` | Approval requests and decisions |
| `nibble.icl.audit` | Immutable append-only audit log (all events) |

All topics use standard JSON. No proprietary serialisation.

---

## The Translation Contract

ICL makes one promise to both sides of the integration:

**To the agent:** emit ICL events and your instructions will reach any system that has a config mapping.

**To the system:** receive structured, identity-carrying, system-agnostic instructions and execute them however you need to.

Neither side needs to know the other exists. The ICL event carries no knowledge of the target system. A configuration file knows the rest.

```yaml
target: Salesforce
mappings:
  - icl_action: issue_credit
    entity: account
    endpoint: /services/data/v57.0/sobjects/Credit__c
    method: POST
    param_map:
      amount: Amount__c
      credit_type: Type__c
```

New system = new config file. No code. No SDK. No custom integration build.

---

## Idempotency

Every `CALL` event carries an `idempotency_key` (UUID). The translator tracks executed keys and rejects duplicate execution. This prevents double-execution on retry without requiring the agent to track execution state.

---

## Versioning

ICL events carry an `icl_version` field. The translator rejects events with unsupported versions and emits an `ERROR` event with `failure_type: VERSION_MISMATCH`. The schema is additive — new fields may be added in minor versions without breaking existing translators.

---

## What ICL Is Not

- Not a conversation scripting language
- Not a logging format
- Not tied to any transport protocol
- Not a replacement for the target system's API
- Not an agent framework
- Not a general-purpose workflow orchestration tool

ICL is the stable interface between AI intent and enterprise action. Everything to the left — the prompt, the model, the agent framework — can change. Everything to the right — the target system, the API shape, the data schema — can change. ICL does not move.
