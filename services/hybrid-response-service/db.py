"""Supabase DB for Hybrid Response Logic (Module 13)."""

from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def check_connection() -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("response_classifications").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


# Classification keywords for rule-based routing (no mock; deterministic)
ROUTINE_KEYWORDS = frozenset({
    "status", "track", "when", "where", "time", "delivery", "eta", "order number",
    "confirm", "quantity", "price", "total", "address", "phone", "email",
})
HUMAN_KEYWORDS = frozenset({
    "dispute", "wrong", "damage", "broken", "missing", "refund", "cancel", "complaint",
    "never received", "not what", "broken", "damaged", "fraud", "manager", "human",
    "speak to", "talk to", "representative", "escalate", "frustrated", "angry",
    "unacceptable", "terrible", "worst", "physical damage", "arrived broken",
})


def classify_message(content: str) -> str:
    """
    Classify message as routine, complex, dispute, or physical_damage.
    Returns classification and implied route: routine -> AI, others -> human.
    """
    text = (content or "").lower().strip()
    if not text:
        return "routine"

    words = set(text.replace(".", " ").replace(",", " ").split())
    if words & HUMAN_KEYWORDS:
        if any(k in text for k in ("damage", "broken", "arrived broken", "physical")):
            return "physical_damage"
        if any(k in text for k in ("dispute", "refund", "wrong charge", "fraud")):
            return "dispute"
        return "complex"
    if words & ROUTINE_KEYWORDS or len(text) < 100:
        return "routine"
    return "complex"


def create_classification_and_route(
    conversation_ref: str,
    message_content: str,
) -> Dict[str, Any]:
    """
    Classify message, log to response_classifications, create support_escalation if route=human.
    Returns { classification, route, support_escalation_id?, id }.
    """
    client = get_supabase()
    if not client:
        return {"classification": "complex", "route": "human", "support_escalation_id": None}

    classification = classify_message(message_content)
    route = "human" if classification in ("complex", "dispute", "physical_damage") else "ai"

    support_escalation_id = None
    if route == "human":
        r = client.table("support_escalations").insert({
            "conversation_ref": conversation_ref,
            "classification": classification,
            "status": "pending",
        }).select("id").execute()
        if r.data:
            support_escalation_id = str(r.data[0]["id"])

    r2 = client.table("response_classifications").insert({
        "conversation_ref": conversation_ref,
        "message_content": (message_content or "")[:5000],
        "classification": classification,
        "route": route,
        "support_escalation_id": support_escalation_id,
    }).select("id, classification, route, support_escalation_id").execute()

    row = r2.data[0] if r2.data else {}
    return {
        "id": str(row.get("id", "")),
        "classification": classification,
        "route": route,
        "support_escalation_id": str(row["support_escalation_id"]) if row.get("support_escalation_id") else None,
    }


def list_support_escalations(status: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    q = client.table("support_escalations").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    r = q.execute()
    return r.data or []


def get_support_escalation(escalation_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    r = client.table("support_escalations").select("*").eq("id", escalation_id).execute()
    return r.data[0] if r.data else None


def assign_escalation(escalation_id: str, assigned_to: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    r = client.table("support_escalations").update({"assigned_to": assigned_to, "status": "assigned"}).eq("id", escalation_id).select().execute()
    return r.data[0] if r.data else None


def resolve_escalation(escalation_id: str, resolution_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone
    client = get_supabase()
    if not client:
        return None
    now = datetime.now(timezone.utc).isoformat()
    upd = {"status": "resolved", "resolved_at": now}
    if resolution_notes is not None:
        upd["resolution_notes"] = resolution_notes
    r = client.table("support_escalations").update(upd).eq("id", escalation_id).select().execute()
    return r.data[0] if r.data else None


def fetch_kb_and_faqs(partner_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch KB articles and FAQs for partner. Returns (kb_articles, faqs)."""
    client = get_supabase()
    if not client:
        return ([], [])

    kb = client.table("partner_kb_articles").select("title, content").eq("partner_id", partner_id).eq("is_active", True).order("sort_order").execute()
    faqs = client.table("partner_faqs").select("question, answer").eq("partner_id", partner_id).eq("is_active", True).order("sort_order").execute()

    return (kb.data or [], faqs.data or [])


def fetch_order_status(allowed_order_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch order status for allowed order IDs only (strict scoping)."""
    client = get_supabase()
    if not client or not allowed_order_ids:
        return []

    r = client.table("orders").select("id, status, total_amount").in_("id", allowed_order_ids).execute()
    orders = r.data or []
    result = []
    for o in orders:
        result.append({
            "order_id": str(o.get("id", "")),
            "status": o.get("status", "unknown"),
            "total_amount": o.get("total_amount"),
        })
    return result


def create_classification_and_respond(
    partner_id: str,
    conversation_id: str,
    message_content: str,
    allowed_order_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Classify message; if route=ai generate response from KB/FAQs/order status; if route=human create escalation.
    Returns { classification, route, ai_response?, support_escalation_id?, id }.
    Order scoping: only allowed_order_ids are used for order context.
    """
    client = get_supabase()
    classification = classify_message(message_content)
    route = "human" if classification in ("complex", "dispute", "physical_damage") else "ai"

    support_escalation_id = None
    ai_response = None

    if route == "human":
        if client:
            ins = {
                "conversation_ref": str(conversation_id),
                "conversation_id": conversation_id,
                "classification": classification,
                "status": "pending",
            }
            try:
                r = client.table("support_escalations").insert(ins).select("id").execute()
                if r.data:
                    support_escalation_id = str(r.data[0]["id"])
            except Exception:
                pass
        return {
            "classification": classification,
            "route": route,
            "ai_response": None,
            "support_escalation_id": support_escalation_id,
            "id": None,
        }

    # route == "ai": generate response
    kb_articles, faqs = fetch_kb_and_faqs(partner_id)
    order_status = fetch_order_status(allowed_order_ids or [])
    ai_response = generate_ai_response_sync(message_content, kb_articles, faqs, order_status)
    if not ai_response:
        ai_response = "I'd be happy to help. Could you provide more details about your question? Our team can also assist you directly."

    if client:
        r2 = client.table("response_classifications").insert({
            "conversation_ref": str(conversation_id),
            "message_content": (message_content or "")[:5000],
            "classification": classification,
            "route": route,
        }).select("id").execute()
        row_id = str(r2.data[0]["id"]) if r2.data else None
    else:
        row_id = None

    return {
        "classification": classification,
        "route": route,
        "ai_response": ai_response,
        "support_escalation_id": None,
        "id": row_id,
    }


HYBRID_RESPONSE_SYSTEM = """You are a helpful support assistant. Answer the customer's question using the provided knowledge base articles, FAQs, and order status. Be concise and friendly. If the answer is not in the context, say so and offer to connect them with a human."""


def generate_ai_response_sync(
    message_content: str,
    kb_articles: List[Dict[str, Any]],
    faqs: List[Dict[str, Any]],
    order_status: List[Dict[str, Any]],
) -> Optional[str]:
    """Generate AI response using Platform Config LLM. Returns None when not configured."""
    from packages.shared.platform_llm import (
        get_platform_llm_config,
        get_model_interaction_prompt,
        get_llm_chat_client,
    )

    client = get_supabase()
    if not client:
        return None

    llm_config = get_platform_llm_config(client)
    prompt_cfg = get_model_interaction_prompt(client, "hybrid_response")

    if not llm_config or not llm_config.get("api_key"):
        return None
    if prompt_cfg is not None and not prompt_cfg.get("enabled", True):
        return None

    system_prompt = (prompt_cfg.get("system_prompt") if prompt_cfg else None) or HYBRID_RESPONSE_SYSTEM
    max_tokens = prompt_cfg.get("max_tokens", 400) if prompt_cfg else 400

    provider, llm_client = get_llm_chat_client(llm_config)
    if not llm_client:
        return None

    # Build context
    parts = [f"Customer question: {message_content[:2000]}"]
    if kb_articles:
        parts.append("\n\nKnowledge base:")
        for a in kb_articles[:10]:
            title = a.get("title", "")
            content = (a.get("content") or "")[:800]
            parts.append(f"\n- {title}: {content}")
    if faqs:
        parts.append("\n\nFAQs:")
        for f in faqs[:15]:
            q = f.get("question", "")
            a = f.get("answer", "")
            parts.append(f"\nQ: {q}\nA: {a}")
    if order_status:
        parts.append("\n\nOrder status:")
        for o in order_status[:10]:
            parts.append(f"\n- Order {o.get('order_id', '')}: {o.get('status', '')}")

    user_content = "\n".join(parts)[:6000]

    model = llm_config.get("model") or "gpt-4o"
    temperature = min(0.5, float(llm_config.get("temperature", 0.1)) + 0.2)

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            resp = llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text if text else None
        if provider == "gemini":
            gen_model = llm_client.GenerativeModel(model)
            resp = gen_model.generate_content(
                f"{system_prompt}\n\n{user_content}",
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                return text if text else None
    except Exception:
        pass
    return None
