# Adaptive Cards Library (The Voice)

Shared Adaptive Card templates and generators for Chat-First responses across Gemini, ChatGPT, and WhatsApp.

## Card Types

| Card | Purpose |
|------|---------|
| **Product Card** | Product details with image, price, capabilities; Add to Bundle / View Details |
| **Bundle Card** | Bundle composition with timeline; Proceed to Checkout |
| **Proof Card** | Virtual proofing preview; Approve / Request Changes |
| **Time-Chain Card** | Multi-leg journey timeline with ETA/deadlines |
| **Progress Ledger Card** | Standing intent progress with If/Then logic and Agent Reasoning |
| **Checkout Card** | Order summary with instant checkout button |
| **Conflict Suggestion Card** | Proactive alternatives when Time-Chain conflicts detected |

## Usage

```python
from packages.shared.adaptive_cards import (
    generate_product_card,
    generate_bundle_card,
    generate_progress_ledger_card,
    render_for_platform,
)

# Product discovery
card = generate_product_card(products)

# Platform-specific rendering (Gemini, ChatGPT, WhatsApp)
rendered = render_for_platform(card, "chatgpt")
```

## Platform Support

- **Gemini**: Dynamic View – pass-through Adaptive Cards 1.5
- **ChatGPT**: Native rendering, Instant Checkout compatible
- **WhatsApp**: Fallback to interactive buttons (text + quick reply)

## Base Utilities

```python
from packages.shared.adaptive_cards.base import (
    create_card,
    text_block,
    fact_set,
    container,
    action_submit,
)
```
