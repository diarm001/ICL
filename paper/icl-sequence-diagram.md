# ICL Sequence Diagram — Prompt to API

```
  User        Agent       Encoder        Kafka           Translator      Config      Enterprise
   |            |             |              |                 |              |            |
   |  "Update   |             |              |                 |              |            |
   |  Johnson   |             |              |                 |              |            |
   |  account"  |             |              |                 |              |            |
   |----------->|             |              |                 |              |            |
   |            |  raw prompt |              |                 |              |            |
   |            |------------>|              |                 |              |            |
   |            |             |  constrained |                 |              |            |
   |            |             |  LLM call    |                 |              |            |
   |            |             |  (intent,    |                 |              |            |
   |            |             |  entity,     |                 |              |            |
   |            |             |  params,     |                 |              |            |
   |            |             |  identity)   |                 |              |            |
   |            |             |              |                 |              |            |
   |            |             |  publish to nibble.icl.actions |              |            |
   |            |             |  REQ_ACT update_record         |              |            |
   |            |             |  entity=account                |              |            |
   |            |             |  id=johnson_acct_001           |              |            |
   |            |             |  params={tier:premium}         |              |            |
   |            |             |------------------------------>|              |            |
   |            |             |              |                 |              |            |
   |            |             |    [ICL event is system-agnostic.             |            |
   |            |             |     Does not know or care what system         |            |
   |            |             |     will receive it.]          |              |            |
   |            |             |              |                 |              |            |
   |            |             |              |  consume from   |              |            |
   |            |             |              |  nibble.icl     |              |            |
   |            |             |              |  .actions       |              |            |
   |            |             |              |---------------->|              |            |
   |            |             |              |                 |  lookup      |            |
   |            |             |              |                 |  REQ_ACT     |            |
   |            |             |              |                 |  update_     |            |
   |            |             |              |                 |  record      |            |
   |            |             |              |                 |------------->|            |
   |            |             |              |                 |              |            |
   |            |             |              |                 |  how THIS    |            |
   |            |             |              |                 |  system      |            |
   |            |             |              |                 |  wants it    |            |
   |            |             |              |                 |<-------------|            |
   |            |             |              |                 |              |            |
   |            |             |              |                 |  [whatever the API        |
   |            |             |              |                 |   requires]               |
   |            |             |              |                 |-------------------------->|
   |            |             |              |                 |              |            |
   |            |             |              |                 |              |   response |
   |            |             |              |                 |<--------------------------|
   |            |             |              |                 |              |            |
   |            |             |              |  publish to     |              |            |
   |            |             |              |  nibble.icl     |              |            |
   |            |             |              |  .results       |              |            |
   |            |             |              |  RES status=    |              |            |
   |            |             |              |  success        |              |            |
   |            |             |              |<----------------|              |            |
   |            |  result     |              |                 |              |            |
   |            |<------------|--------------|                 |              |            |
   |  "Johnson  |             |              |                 |              |            |
   |  account   |             |              |                 |              |            |
   |  updated." |             |              |                 |              |            |
   |<-----------|             |              |                 |              |            |
```

---

## The Stable Interface

Everything to the **left** of the ICL event can change:
- The prompt wording
- The LLM model
- The agent framework
- The user interface

Everything to the **right** of the ICL event can change:
- The target system (Salesforce, SAP, ServiceNow, homegrown)
- The API shape
- The authentication method
- The data schema

**ICL does not move.** It is the contract between AI and enterprise that neither side has to own.

The translator is configuration, not code. New system = new config file. Not a new integration build.
