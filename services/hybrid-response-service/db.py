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


def generate_ai_response_sync(
    message_content: str,
    kb_articles: List[Dict[str, Any]],
    faqs: List[Dict[str, Any]],
    order_status: List[Dict[str, Any]],
) -> Optional[str]:
    """Generate AI response using Azure OpenAI. Returns None if LLM not configured or fails."""
    try:
        from config import settings
        if not settings.azure_openai_configured:
            return None
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
            azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
        )

        kb_text = "\n\n".join(
            f"## {a.get('title', '')}\n{a.get('content', '')}" for a in kb_articles[:20]
        ) or "No knowledge base articles."
        faq_text = "\n\n".join(
            f"Q: {f.get('question', '')}\nA: {f.get('answer', '')}" for f in faqs[:30]
        ) or "No FAQs."
        order_text = "\n".join(
            f"Order {o.get('order_id', '')[:8]}...: status={o.get('status', '')}" for o in order_status
        ) if order_status else "No order information available."

        system = """You are a helpful customer support assistant for a multi-vendor order platform.
You may ONLY reference orders explicitly provided in the context below. Do not fabricate or infer other order IDs.
If the customer asks about an order not in the context, say you don't have that order information and suggest they contact support.
Be concise, friendly, and professional."""

        user = f"""Customer message: {message_content}

Knowledge base:
{kb_text}

FAQs:
{faq_text}

Order status (only use these - do not reference other orders):
{order_text}

Respond with a helpful reply to the customer. Keep it under 200 words."""

        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        content = (resp.choices[0].message.content or "").strip()
        return content if content else None
    except Exception:
        return None
