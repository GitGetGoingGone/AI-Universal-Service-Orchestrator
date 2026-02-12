# Proof State Machine

Pillar 5: Virtual Proofing Engine state machine. Module 8.

## States

```
Pending → In_Progress → Proof_Ready → [Approved | Rejected] → [Proceed | Revise]
```

| State | Description |
|-------|-------------|
| `pending` | Proof created, awaiting generation |
| `in_progress` | DALL-E / generation in progress |
| `proof_ready` | Preview ready, awaiting user approval |
| `approved` | User approved → proceed to fulfillment |
| `rejected` | User rejected → revise and resubmit |

## Transitions

- `pending` → `in_progress`: When generate is called
- `in_progress` → `proof_ready`: When image URL is set
- `proof_ready` → `approved`: User approves (or Vision AI auto-approve)
- `proof_ready` → `rejected`: User rejects

## Time-Chain Integration

- Pause leg on `proof_ready`
- Resume on `approved`

## Vision AI

- `auto_approve_with_vision_ai(proof_image_url, source_of_truth_url)` returns similarity score
- ≥0.95: auto-approve
- ≥0.85: human review
- <0.85: reject

## Approval Timeout

- Default 24h for proof_ready
- On timeout: escalate or run Vision AI for auto-approve
