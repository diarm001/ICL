# Imperative Context Language: A Unified Cognitive and Execution Runtime for Enterprise AI Agents

**NibbleAI Research**  
**2026-06-01**

---

## Abstract

Current AI agent deployments suffer from a structural gap between conversational intelligence and enterprise action. Agents understand intent with increasing fidelity; they cannot act on it safely, accountably, or at scale inside existing enterprise systems. This gap is not a model problem. It is a runtime problem.

We introduce Imperative Context Language (ICL), a structured intermediate representation that unifies two layers previously treated as separate concerns: the cognitive layer — the agent's reasoning trace from intent to decision — and the execution layer — the governed, auditable, rollback-capable translation of that decision into enterprise system action. ICL expresses both layers in a single, compact, human-readable format that sits between raw conversational history and full execution logs.

The execution layer of ICL enforces four properties simultaneously that no existing integration primitive enforces together: identity propagation through every action event, failure-awareness as a first-class event type rather than an exception, human approval gating for risk-bounded actions before any system is touched, and transactional rollback on failed multi-step workflows. These properties, enforced at the event format level, produce an immutable audit trail that satisfies enterprise compliance requirements without custom instrumentation per deployment.

The cognitive layer of ICL — comprising reasoning traces (`THINK`), inference records (`DECIDE`), and amendment events (`REVISE`) — maps agent cognition to enterprise outcomes in a causally complete record. We argue this produces a training signal of a qualitatively different kind from existing RLHF datasets: structured intent mapped to permission decisions mapped to human approval or rejection mapped to real-world system outcomes, with full governance metadata attached. This signal is not synthetically reproducible; it is generated only by agents operating under real enterprise constraints against real systems of record.

We describe the NibbleAI runtime, which implements ICL as a sidecar execution layer deployable against any existing agent framework without agent modification. We present results from a controlled demonstration environment showing complete ICL event traces across four execution paths: nominal success, approval-gated action, permission-denied escalation with cognitive trace, and multi-step partial failure with retry and rollback. We discuss the implications of ICL as a convergence point for enterprise AI governance and agent training data generation, and propose a model in which enterprise deployments compound an operational execution graph that functions as a reusable asset for agent improvement — analogous in structure, if not in mechanism, to the role training data plays for foundation models.

ICL is not a new protocol. It is a new primitive: the minimal structure required to make AI agent actions safe enough for enterprise, and rich enough to make enterprise deployments useful for AI.

---

## 1. Introduction

The deployment of AI agents in enterprise environments has outpaced the infrastructure available to govern them. A typical deployment in 2026 follows a recognisable pattern: a capable language model handles customer or employee intent with increasing fidelity, understands what action is needed, and then stops. The action — updating a CRM record, issuing a financial credit, provisioning a user account — is performed manually by a human who reads the agent's output and types it into a legacy system.

This is not a failure of model capability. It is a failure of the execution layer. The models are ready. The runtime is not.

Existing approaches address parts of this problem in isolation. API integration platforms (MuleSoft, Boomi) provide system connectivity but have no model for AI agent identity or approval gating. Workflow automation tools (Tines, Zapier) orchestrate sequences of actions but operate at the workflow level, not the execution level — they govern what steps happen, not what happens at the moment an AI agent touches a system of record. Agent frameworks (LangChain, AutoGen) provide orchestration primitives but no enterprise governance. Model Context Protocol provides tool access but no identity propagation, approval semantics, or rollback.

None of these tools addresses the four properties that enterprise governance requires simultaneously: the action must execute as the original user (not an elevated service account), failure must be observable and recoverable, high-risk actions must pause for human decision before execution, and partial failures must be reversible. Enforcing all four together, across any agent and any legacy system, requires a new primitive at the event format level.

ICL is that primitive.

---

## 2. The Problem: Two Gaps, One Language

Enterprise AI deployment has two distinct gaps that have been treated as separate engineering problems.

**The execution gap.** AI agent outputs are unstructured, probabilistic, and identity-free. Enterprise systems require structured, deterministic, identity-carrying API calls. Bridging this gap today requires custom integration work per use case — the 6–12 week bottleneck that stalls every enterprise AI deployment after the demo succeeds.

**The training gap.** AI labs building enterprise-capable agents need training data from real enterprise environments: what agents decided, what humans approved or rejected, what succeeded and what failed. This data does not exist at scale. Labs cannot generate it without being deployed in enterprise. Enterprise cannot use unproven agents without the governance layer that makes deployment safe. This is a chicken-and-egg problem neither side can solve alone.

ICL resolves both gaps with the same intermediate representation. The execution layer closes the execution gap. The cognitive layer closes the training gap. The fact that they share a format is not incidental — it is the architectural insight that makes NibbleAI sit in a position no existing tool occupies.

---

## 3. ICL Design Principles

ICL is designed around five constraints:

1. **Imperative, not descriptive.** ICL specifies what to do, not what happened. This makes traces executable and replayable.

2. **Identity-carrying.** User identity propagates from the initial request through every downstream event. No elevated service accounts. Least-privilege enforcement at execution time.

3. **Failure-aware.** Errors are first-class events, not exceptions. An `ERROR` event carries structured failure metadata the agent can reason about — failure type, retryability, the originating event ID.

4. **Transport-agnostic.** ICL events are standard JSON over any message broker. No proprietary wire format. Plugs into existing Kafka infrastructure or runs standalone.

5. **Deterministic downstream.** Everything after the encoding step is configuration lookup, not inference. The NibbleAI Encoder uses a constrained LLM call to extract intent in under 200ms. The ICL-to-API Translator maps ICL actions to enterprise API calls via configuration — no code changes for new system integrations.

---

## 4. The Execution Layer

The execution layer consists of eight event types that together enforce the four governance properties.

### 4.1 Event Types

| Event | Actor | Purpose |
|---|---|---|
| `REQ_ACT` | User | Intent request — identity-carrying entry point |
| `STATE` | Agent | Workflow state transition |
| `CALL` | Agent | System action with idempotency key |
| `RES` | System | Outcome — success, failure, or partial |
| `ERROR` | System | Failure as first-class event |
| `APPROVAL_REQUEST` | Agent | High-risk action paused for human decision |
| `APPROVAL_DECISION` | Human | Approver decision — recorded in audit log |
| `ROLLBACK` | Agent | Compensating action on partial failure |

### 4.2 Identity Propagation

Every event in an ICL trace carries the `user_id` and `user_role` of the original requester. The `CALL` event that touches a legacy system executes with the caller's existing permissions — never with a service account. A permission denial generates a `PERMISSION_DENIED` error event before any system is contacted.

This is the property enterprise security teams require and no existing integration tool enforces. The agent acts as the user, not as itself.

### 4.3 Approval Gating

`APPROVAL_REQUEST` and `APPROVAL_DECISION` are paired events. When a `CALL` event would exceed a configured risk threshold — a financial credit above a limit, a privileged access grant, a bulk data operation — execution pauses. The approver receives the full context of the pending action. Their decision is recorded as an `APPROVAL_DECISION` event with their identity, timestamp, and stated reason. The action executes only after approval is recorded.

The unapproved action never touches the system. There is no race condition, no timeout execution, no dangling state.

### 4.4 Rollback

Multi-step workflows track partial success at the event level. When a `RES` event returns failure after one or more steps have succeeded, the `ROLLBACK` event triggers compensating actions for each completed step in reverse order. The compensating action for each action type is defined in configuration.

The system is left in a clean state. The audit log records the partial success, the failure, the rollback trigger, and the outcome of each compensating action.

### 4.5 The Three-Actor Model

ICL traces have three classes of actor: the user (`U:`), the agent (`A:`), and the human approver (`H:`). Most enterprise automation systems have two actors — user and system. The introduction of `H:` as a first-class actor is what distinguishes ICL traces as training data rather than audit logs.

Every event in a trace is produced by one of these three actors. `U:` events carry intent. `A:` events carry reasoning, action, and state. `H:` events carry judgment. The `APPROVAL_DECISION` event — the only event with `actor: human` — is the label that a domain expert attaches to the agent's interpretation in a real operational context. Everything above it in the trace is context. Everything below it is outcome. The causal chain is complete.

The following is a complete ICL execution trace for an approval-gated action, generated live from the NibbleAI demo environment:

```
Conversation 3d8142ed...

U: "Issue a $5,000 retention credit to the Johnson account"
U: REQ_ACT issue_credit, entity=account, credit_type=retention, amount=5000
     confidence=0.95  encoder_latency=1177ms

A: PERMISSION_CHECK user=demo_user_001, role=admin, action=issue_credit,
     result=APPROVAL_REQUIRED  —  credit $5,000 exceeds auto-approval threshold $1,000

A: STATE issue_credit.pending_approval

A: THINK "The agent determined that a $5,000 retention credit exceeds the automated
     approval limit and requires human review to validate business justification."

A: DECIDE approval_status=pending, reason=credit_amount_exceeds_auto_approval_threshold

A: APPROVAL_REQUEST action=issue_credit, credit_type=retention, amount=5000,
     risk=high, approver=ops_manager

H: APPROVAL_DECISION decision=approved, approver=ops_manager

A: CALL Tines.issue_credit(credit_type=retention, amount=5000)

A: RES Tines.issue_credit, status=success, latency=264ms

A: STATE issue_credit.completed
```

Ten events. Three actors. The `H:` line is the one that no synthetic pipeline produces.

### 4.6 A Complete Execution Trace — Multi-Step Rollback

The following is an ICL execution trace for a multi-step workflow that fails on the second step and rolls back:

```
// CONV_ID: eec53500

U: REQ_ACT multi_step_workflow, account=johnson_acct_001,
   steps=[update_billing_address, provision_support_tier]

A: PERMISSION_CHECK user=demo_user_001, action=multi_step_workflow, result=APPROVED

A: STATE workflow.step_1_of_2
A: CALL Tines.update_billing_address(account_id=johnson_acct_001, address=123 Main St Chicago)
A: RES Tines.update_billing_address, status=success, latency=275ms
A: STATE update_billing_address.completed

A: STATE workflow.step_2_of_2
A: CALL Tines.provision_support_tier(account_id=johnson_acct_001, tier=premium)
A: RES Tines.provision_support_tier, status=failure, reason=system_unavailable
A: ERROR failure_type=SYSTEM_UNAVAILABLE, action=provision_support_tier, retryable=true

A: THINK "Step 1 succeeded but step 2 hit a system unavailability — partial state.
          Retry once before considering rollback."
A: DECIDE retry_step_2=true, reason=retryable_error_first_attempt

A: REVISE step=provision_support_tier, attempt=2
A: CALL Tines.provision_support_tier(account_id=johnson_acct_001, tier=premium)
A: RES Tines.provision_support_tier, status=failure, reason=system_unavailable
A: ERROR failure_type=SYSTEM_UNAVAILABLE, action=provision_support_tier, retryable=false

A: THINK "Retry exhausted — step 2 remains unavailable.
          Partial state cannot persist. Initiating rollback of step 1."
A: DECIDE rollback_required=true, reason=retry_exhausted

A: STATE rollback.initiated
A: CALL Tines.revert_billing_address(account_id=johnson_acct_001)
A: RES Tines.revert_billing_address, status=success, latency=262ms
A: ROLLBACK action=update_billing_address, status=success, trigger=SYSTEM_UNAVAILABLE
A: STATE rollback.complete
```

This trace is 23 structured events. It is fully replayable. Every decision point is auditable. The system is in a clean state at termination.

---

## 5. The Cognitive Layer

The cognitive layer captures what the execution layer cannot: why the agent acted, what it considered, and how it corrected itself. It comprises three event types.

| Event | Actor | Purpose |
|---|---|---|
| `THINK` | Agent | Internal reasoning trace — one sentence of deliberation |
| `DECIDE` | Agent | Inference committed to — variable assignment with reason |
| `REVISE` | Agent | Prior step amended — explicit audit marker for self-correction |

These events are generated by a constrained LLM call given the execution context at each decision point. In the trace above, the two `THINK`/`DECIDE` pairs capture the agent's reasoning at the retry decision and the rollback decision respectively. They are not summaries appended after the fact — they are generated at the moment the decision is made, with the current event context as input.

### 5.1 The Training Signal Argument

Existing RLHF datasets are constructed from human preference judgments on model outputs: pairwise comparisons, scalar ratings, thumbs up or down. These signals are valuable but structurally limited. They capture whether an output was preferred, not whether an action was correct, safe, or consistent with the user's actual intent in a consequential context.

ICL execution graphs from governed enterprise deployments capture something structurally different:

| Signal | What It Provides |
|---|---|
| `REQ_ACT` with original utterance | Ground truth user intent, unfiltered, in a real operational context |
| `THINK` / `DECIDE` | Structured agent reasoning mapped to a specific decision point |
| `APPROVAL_REQUEST` / `APPROVAL_DECISION` | Expert human judgment on whether the agent's interpretation was correct — high-stakes, in-context, non-crowd-sourced |
| `RES` status | Real-world outcome signal: did the action succeed in the actual system? |
| `ERROR` + `REVISE` | Agent self-correction record — what the agent got wrong and how it amended |
| `ROLLBACK` | Negative outcome signal — what needed to be undone and why |
| Full causal chain | Utterance → reasoning → action → human judgment → system state, end to end |

The approval decision is the signal that no synthetic pipeline can reproduce. When an operations manager approves or rejects a $5,000 credit in a real enterprise context, that decision is:

- Made by a domain expert, not a crowd-worker
- In a consequential operational context, not a rating interface
- Attached to a complete causal chain, not an isolated output
- Subject to real accountability — the approver's identity and reason are recorded

This is not training data. It is labelled, governed, causally-complete behavioural data from real agents taking real consequential actions. The distinction matters for what models trained on it can do.

The ten-event trace from Section 4.5 collapses into a single training record:

```
utterance   "Issue a $5,000 retention credit to the Johnson account"
understood  issue_credit · credit_type=retention, amount=5000
reasoned    "The agent determined that a $5,000 retention credit exceeds the
             automated approval limit and requires human review."
decided     approval_status=pending, reason=credit_amount_exceeds_threshold
human       APPROVED — ops_manager
outcome     success
```

Six fields. One record. The causal chain from utterance to outcome, with the human label at the centre. This is what every enterprise deployment generates. This is what accumulates at scale.

### 5.2 Why This Signal Is Not Synthetically Reproducible

Synthetic data generation can produce intent-action pairs and simulated approval decisions at scale. It cannot produce:

1. **Real failure modes.** Enterprise systems fail in ways that are not modelled in simulation — partial API responses, rate limiting, schema drift, authentication timeout cascades. `ERROR` events from production deployments capture failure patterns that synthetic pipelines cannot anticipate.

2. **High-stakes human labels.** A crowd-worker rating a model response is not equivalent to an operations manager approving a provisioning request they are accountable for. The label quality difference is structural, not scalar.

3. **Correction signal.** When a user says "that's wrong, undo it" after an action executes, the `REVISE` + `ROLLBACK` sequence captures what the agent got wrong in a real operational context. This signal cannot be simulated because the wrongness depends on real system state.

4. **Compliance metadata.** The governance metadata attached to every ICL event — identity, risk level, approval threshold, compliance regime — provides context that makes the signal interpretable across industries and action types. A credit approval in financial services carries different constraints than one in retail. ICL encodes this difference in the event structure.

---

## 6. The NibbleAI Runtime

The NibbleAI runtime implements ICL as a sidecar container that deploys alongside any existing AI agent without agent modification. The agent produces conversational output. The NibbleAI Encoder intercepts that output and compiles it into an ICL `REQ_ACT` event in under 200ms using a constrained LLM call (Claude Haiku). Everything downstream — permission checking, approval gating, system execution, rollback — is deterministic configuration lookup, not inference.

ICL events route over five Kafka topics:

| Topic | Purpose |
|---|---|
| `nibble.icl.actions` | Inbound ICL events for execution |
| `nibble.icl.results` | Execution results |
| `nibble.icl.errors` | Error events for agent reasoning |
| `nibble.icl.approvals` | Approval requests and decisions |
| `nibble.icl.audit` | Immutable append-only audit log (all events) |

The ICL-to-API Translator maps ICL actions to enterprise API calls via YAML configuration. New system integrations are configuration changes, not code deployments. Idempotency keys on every `CALL` event prevent duplicate execution on retry.

### 6.1 Cognitive Trace Generation

The cognitive layer is currently generated by the NibbleAI Encoder at decision points in the execution flow: on `ERROR` events (reasoning about failure), on `APPROVAL_REQUEST` events (reasoning about risk), and on `REVISE` events (reasoning about self-correction). The generator receives the current event context and produces constrained `THINK`/`DECIDE` output.

This is a reconstructed cognitive trace — the agent's reasoning is inferred from the execution context, not natively emitted by the agent. A native cognitive trace, in which the agent itself emits ICL cognitive events as it reasons, would produce richer signal. The reconstructed trace is the current implementation; native emission is the architectural direction for agents built on ICL from the ground up.

---

## 7. Results

The following results are from a controlled demonstration environment. They demonstrate the correct structure and event composition of ICL traces across four execution paths. They do not represent production deployment data.

**Execution path 1 — Nominal success (5 events)**  
Natural language request encoded to `REQ_ACT` in 1,170ms. Permission check approved. `CALL` to target system returned 200 in 290ms. `STATE update_record.completed`. All four governance properties enforced; identity propagated end to end.

**Execution path 2 — Approval-gated action (8 events)**  
`issue_credit` with `amount=5000` triggered the approval threshold rule ($1,000). `STATE issue_credit.pending_approval`. `APPROVAL_REQUEST` generated with full action context. Human decision recorded as `APPROVAL_DECISION decision=approved, approver=ops_manager`. `CALL` executed only after decision was recorded. 8 events; human label in audit log.

**Execution path 3 — Permission denial with cognitive trace (8 events)**  
`provision_access` to `finance_dashboard` denied: role `admin` does not satisfy `manager|finance_admin`. `ERROR failure_type=PERMISSION_DENIED, retryable=false`. Cognitive trace generated: `THINK` reasoning about role boundary, `DECIDE escalate_to=finance_admin`. `APPROVAL_REQUEST` escalated to ops manager. Human rejected. `STATE provision_access.cancelled`. The denied action is a complete, attributed, auditable flow — not a dead end.

**Execution path 4 — Multi-step partial failure with rollback (23 events)**  
Step 1 (billing address update) succeeded. Step 2 (support tier provisioning) failed with `SYSTEM_UNAVAILABLE`. Cognitive trace: `THINK` reasoning toward retry, `DECIDE retry_step_2=true`. `REVISE` marked retry. Retry failed. Second cognitive trace: `THINK` reasoning toward rollback, `DECIDE rollback_required=true`. `ROLLBACK` compensating action executed. `STATE rollback.complete`. System left in clean state.

Across all four paths, 44 total events were generated and written to the immutable audit log. Every event is attributable to a conversation ID, a user identity, and a timestamp. The full traces are queryable by action type, outcome, and user.

---

## 8. The Execution Graph as a Reusable Asset

Across enterprise deployments, ICL events accumulate an operational execution graph indexed by:

- Industry vertical (retail, healthcare, financial services, logistics)
- Action type (record update, credit issuance, provisioning, ticket creation)
- Approval pattern (what risk thresholds trigger approval, by industry)
- Failure mode (how specific systems fail, what recovery looks like)
- Correction signal (how users correct agent errors post-execution)
- Compliance regime (SOC2, HIPAA, GDPR constraint patterns by action type)

This graph is a reusable asset that compounds with every deployment. New customer deployments draw from existing patterns — reducing integration time and improving governance configuration quality. The first customer benefits from patterns the graph does not yet contain. The fifth customer benefits from patterns accumulated across four prior deployments.

The structural analogy to training data for foundation models is intentional but limited. Training data improves model capability. The execution graph improves operational reliability — what governance configurations work in which industries, what approval thresholds reduce error rates, what recovery strategies succeed against which failure types. These are not model weights. They are operational priors.

The asset is defensible because it requires production deployments to generate. A competitor cannot purchase or reconstruct two years of governed enterprise execution data. The moat is not the connectors. The moat is the operational intelligence accumulated in the graph.

---

## 9. Discussion

**On the relationship between the two layers.** The cognitive and execution layers of ICL share a format because they must share a causal chain. A `THINK` event without a subsequent `CALL` event is incomplete. A `ROLLBACK` event without a preceding `DECIDE` event explaining why rollback was chosen is an auditable action without an auditable reason. The two layers are not separable in production — an enterprise deployment generates both simultaneously, and the training signal value derives precisely from that conjunction.

**On the governance and training data markets.** Enterprise IT and security teams buy the execution layer. AI labs buy the cognitive layer and the execution graph. These are not the same buyer, and the commercial model reflects this. Enterprise customers pay for deployment and integration; AI labs pay for access to the anonymised execution graph. The flywheel: lab partnerships distribute NibbleAI into enterprise, enterprise deployments generate the graph, the graph is the data labs need to make their agents production-ready.

**On the current state of the cognitive trace.** The cognitive trace in the current implementation is a reconstruction, not a native emission. This is an honest limitation. The reconstructed trace is valuable — it captures the reasoning structure correctly even if it does not capture the model's internal state directly. Native ICL emission by the agent itself is the direction that produces the highest-quality training signal, and it requires agents built to emit ICL as they reason. That is a longer-term integration model than the current sidecar approach.

**On what this paper does not claim.** We do not claim that ICL solves the agent alignment problem, that the cognitive trace captures model internals, or that the execution graph generalises beyond the action types and industries it has been deployed against. We claim that ICL is the minimal structure required to make AI agent actions governable in enterprise, and that the training signal generated as a side effect of that governance is qualitatively different from existing RLHF datasets. The first claim is demonstrated. The second is an argument that requires production data at scale to validate fully.

---

## 10. Conclusion

ICL is a two-layer intermediate representation that unifies enterprise AI governance and agent training data generation in a single structured event format. The execution layer makes AI agent actions safe enough for enterprise. The cognitive layer makes enterprise deployments useful for AI. The same 10 event types — eight execution, three cognitive — are sufficient to express the full lifecycle of a governed enterprise AI action, from intent to reasoning to system effect to human judgment to outcome.

The NibbleAI runtime implements this representation as a sidecar execution layer against existing enterprise infrastructure. The execution graph that accumulates across deployments is a reusable operational asset that compounds with scale.

The runtime is ready. The format is specified. The paper that needs to be written next — once production deployments exist — is the empirical validation of the training signal claim: do models fine-tuned on ICL execution graphs perform better on enterprise reasoning tasks than models fine-tuned on existing RLHF datasets? That is the experiment. This paper is the hypothesis.

---

## Appendix: ICL Event Reference

### Execution Layer

```
REQ_ACT   <action>, entity=<type>, <params>     User intent — identity-carrying
STATE     <workflow>.<status>                    Workflow state transition  
CALL      <system>.<action>(<params>)            System action with idempotency key
RES       <system>.<action>, status=<result>     System outcome
ERROR     failure_type=<type>, retryable=<bool>  Failure as first-class event
APPROVAL_REQUEST  action=<x>, risk=<level>       Human gate before execution
APPROVAL_DECISION decision=<approved|rejected>   Human label — recorded in audit log
ROLLBACK  action=<compensating>, status=<result> Compensating action on partial failure
```

### Cognitive Layer

```
THINK   "<one sentence of agent reasoning>"          Internal deliberation
DECIDE  <variable>=<value>, reason=<brief>           Inference committed to
REVISE  step=<prior_step>, attempt=<n>               Self-correction — amends prior step
```

### Base Event Schema (JSON)

```json
{
  "icl_version": "0.1",
  "event_id": "<uuid>",
  "conversation_id": "<string>",
  "timestamp": "<ISO8601>",
  "event_type": "<ICL_EVENT_TYPE>",
  "actor": "user | agent | system | human",
  "user_id": "<string>",
  "user_role": "<string>",
  "action": "<string>",
  "entity": "<string>",
  "parameters": {},
  "original_event_id": "<uuid>"
}
```

Every event references its causal predecessor via `original_event_id`. The complete event graph for a conversation is a directed acyclic chain from `REQ_ACT` to terminal state.
