# ICL Example Transcript
### Issue Credit — Approval Required

The following is a complete ICL execution graph for a single enterprise action.
Generated live. No edits.

---

```
Conversation 3d8142ed...

U: "Issue a $5,000 retention credit to the Johnson account"
U: REQ_ACT issue_credit, entity=account, credit_type=retention, amount=5000
     confidence=0.95  encoder_latency=1177ms

A: PERMISSION_CHECK user=demo_user_001, role=admin, action=issue_credit,
     result=APPROVAL_REQUIRED  —  credit $5,000 exceeds auto-approval threshold $1,000

A: STATE issue_credit.pending_approval

A: THINK "The agent determined that a $5,000 retention credit for an account
     exceeds the automated approval limit and requires human review to
     validate business justification."

A: DECIDE approval_status=pending, reason=credit_amount_exceeds_auto_approval_threshold

A: APPROVAL_REQUEST action=issue_credit, credit_type=retention, amount=5000,
     risk=high, approver=ops_manager

H: APPROVAL_DECISION decision=approved, approver=ops_manager

A: CALL Tines.issue_credit(credit_type=retention, amount=5000)

A: RES Tines.issue_credit, status=success, latency=264ms

A: STATE issue_credit.completed
```

---

Three actors. Ten lines.

`U:` — the user. Intent, in natural language, compiled to structure.

`A:` — the agent. Reasoning, permission check, decision, execution.

`H:` — the human approver. The label. The ground truth.

The `H:` line is what doesn't exist anywhere else. Everything above it is context.
Everything below it is outcome. The causal chain is complete.
