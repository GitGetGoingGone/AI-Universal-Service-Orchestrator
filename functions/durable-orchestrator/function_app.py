"""
Durable Orchestrator - The Brain (Month 0)

Base orchestrator template that can:
- Checkpoint state
- Sleep for extended periods (days/weeks)
- Wake up on external events
- Resume from checkpoint

Implements the wait-for-event pattern for long-running workflows.
Integrates with Webhook Push Bridge for status updates to chat threads.
"""
import json
import logging
import os
from datetime import timedelta
import urllib.request

import azure.functions as func
import azure.durable_functions as df

# Durable Functions blueprint - use df.Blueprint() for DF triggers/bindings
bp = df.Blueprint()


# ---------------------------------------------------------------------------
# Client: Start new orchestration
# ---------------------------------------------------------------------------

@bp.route(route="orchestrators/{orchestrator_name}", methods=["POST"])
@bp.durable_client_input(client_name="client")
async def start_orchestrator(
    req: func.HttpRequest, client: df.DurableOrchestrationClient
) -> func.HttpResponse:
    """
    Start a new orchestration instance.
    POST /api/orchestrators/base_orchestrator with optional JSON body as input.
    """
    orchestrator_name = req.route_params.get("orchestrator_name", "base_orchestrator")

    if orchestrator_name not in ("base_orchestrator", "standing_intent_orchestrator"):
        return func.HttpResponse(
            f"Unknown orchestrator: {orchestrator_name}",
            status_code=400,
        )

    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}

    instance_id = await client.start_new(orchestrator_name, None, body)
    logging.info("Started orchestration instance_id=%s", instance_id)

    return client.create_check_status_response(req, instance_id)


# ---------------------------------------------------------------------------
# Client: Raise external event (wake up sleeping orchestrator)
# ---------------------------------------------------------------------------

@bp.route(route="orchestrators/{instance_id}/raise/{event_name}", methods=["POST"])
@bp.durable_client_input(client_name="client")
async def raise_event(
    req: func.HttpRequest, client: df.DurableOrchestrationClient
) -> func.HttpResponse:
    """
    Raise an external event to wake a waiting orchestrator.
    POST /api/orchestrators/{instance_id}/raise/{event_name}
    Optional JSON body as event payload.
    """
    instance_id = req.route_params.get("instance_id")
    event_name = req.route_params.get("event_name")

    if not instance_id or not event_name:
        return func.HttpResponse("instance_id and event_name required", status_code=400)

    try:
        event_data = req.get_json() if req.get_body() else None
    except ValueError:
        event_data = None

    await client.raise_event(instance_id, event_name, event_data)
    logging.info("Raised event %s for instance_id=%s", event_name, instance_id)

    return func.HttpResponse(
        f'{{"status": "event_raised", "instance_id": "{instance_id}", "event": "{event_name}"}}',
        mimetype="application/json",
        status_code=202,
    )


# ---------------------------------------------------------------------------
# Client: Get orchestration status
# ---------------------------------------------------------------------------

@bp.route(route="orchestrators/{instance_id}/status", methods=["GET"])
@bp.durable_client_input(client_name="client")
async def get_status(
    req: func.HttpRequest, client: df.DurableOrchestrationClient
) -> func.HttpResponse:
    """Get orchestration instance status. GET /api/orchestrators/{instance_id}/status"""
    instance_id = req.route_params.get("instance_id")
    if not instance_id:
        return func.HttpResponse("instance_id required", status_code=400)

    status = await client.get_status(instance_id)
    if status is None:
        return func.HttpResponse("Instance not found", status_code=404)

    # to_json() returns a dict; serialize to string for response
    status_dict = status.to_json()
    return func.HttpResponse(
        json.dumps(status_dict),
        mimetype="application/json",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Base Orchestrator: Checkpoint, sleep, wake on external event
# ---------------------------------------------------------------------------

@bp.orchestration_trigger(context_name="context")
def base_orchestrator(context: df.DurableOrchestrationContext):
    """
    Base orchestrator template demonstrating:
    1. Checkpoint state (implicit at each yield)
    2. Call activity
    3. Wait for external event (can sleep for days/weeks - $0 cost)
    4. Resume and complete

    Input: optional dict with "message" and "wait_event_name" (default: "WakeUp")
    """
    input_data = context.get_input() or {}
    message = input_data.get("message", "Hello from orchestrator")
    wait_event_name = input_data.get("wait_event_name", "WakeUp")

    # Step 1: Call activity (checkpoint after this)
    # Note: Avoid logging in orchestrator - it replays and can duplicate logs
    result = yield context.call_activity("log_activity", {"message": message})

    # Step 2: Wait for external event - orchestrator sleeps here
    # No cost while waiting. Can wait days/weeks.
    # Optional: add timeout with context.task_any([event_task, timer_task])
    event_payload = yield context.wait_for_external_event(wait_event_name)

    # Step 3: Resume after event received
    final_result = yield context.call_activity(
        "log_activity",
        {"message": f"Resumed! Received: {event_payload}"},
    )

    return {"status": "completed", "final_result": final_result}


# ---------------------------------------------------------------------------
# Standing Intent Orchestrator: wait_for_external_event(UserApproval)
# ---------------------------------------------------------------------------

@bp.orchestration_trigger(context_name="context")
def standing_intent_orchestrator(context: df.DurableOrchestrationContext):
    """
    Standing intent workflow: scout → wait for UserApproval → complete.
    Uses wait_for_external_event with timeout for approval.
    """
    input_data = context.get_input() or {}
    message = input_data.get("message", "Standing intent waiting for approval")
    approval_timeout_hours = input_data.get("approval_timeout_hours", 24)
    platform = input_data.get("platform")
    thread_id = input_data.get("thread_id")

    # Step 1: Push approval request to chat
    yield context.call_activity(
        "status_narrator_activity",
        {
            "platform": platform,
            "thread_id": thread_id,
            "narrative": f"Standing intent created: {message}. Please approve or reject.",
            "adaptive_card": {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.5",
                "body": [
                    {"type": "TextBlock", "text": "Standing Intent Approval", "weight": "Bolder", "size": "Large"},
                    {"type": "TextBlock", "text": message, "wrap": True},
                ],
                "actions": [
                    {"type": "Action.Submit", "title": "Approve", "data": {"event": "UserApproval", "approved": True}},
                    {"type": "Action.Submit", "title": "Reject", "data": {"event": "UserApproval", "approved": False}},
                ],
            },
            "metadata": {"orchestration_instance_id": context.instance_id},
        },
    )

    # Step 2: Wait for UserApproval (with timeout)
    timeout = timedelta(hours=approval_timeout_hours)
    approval_event = yield context.wait_for_external_event("UserApproval", timeout)

    if approval_event is None:
        return {"status": "timeout", "message": "Approval timeout - no response received"}

    approved = approval_event.get("approved", False) if isinstance(approval_event, dict) else bool(approval_event)

    # Step 3: Push result to chat
    if platform and thread_id:
        yield context.call_activity(
            "status_narrator_activity",
            {
                "platform": platform,
                "thread_id": thread_id,
                "narrative": "Standing intent approved. Proceeding." if approved else "Standing intent rejected.",
                "metadata": {"approved": approved},
            },
        )

    return {"status": "approved" if approved else "rejected", "approved": approved}


# ---------------------------------------------------------------------------
# Activity: Status Narrator - push update to chat via Webhook Bridge
# ---------------------------------------------------------------------------

@bp.activity_trigger(input_name="input_data")
def status_narrator_activity(input_data: dict) -> str:
    """
    Push status update to user's chat thread via Webhook Push Bridge.
    Input: {platform, thread_id, narrative, adaptive_card, metadata}
    """
    platform = input_data.get("platform")
    thread_id = input_data.get("thread_id")
    if not platform or not thread_id:
        logging.warning("status_narrator_activity: missing platform or thread_id")
        return "skipped"

    webhook_url = os.environ.get("WEBHOOK_SERVICE_URL", "http://localhost:8003").rstrip("/")
    url = f"{webhook_url}/api/v1/webhooks/chat/{platform}/{thread_id}"

    payload = {
        "narrative": input_data.get("narrative", ""),
        "adaptive_card": input_data.get("adaptive_card"),
        "metadata": input_data.get("metadata", {}),
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201, 202):
                logging.info("Pushed to %s thread %s", platform, thread_id)
                return "delivered"
    except Exception as e:
        logging.warning("Webhook push failed: %s", e)
    return "failed"


# ---------------------------------------------------------------------------
# Activity: Simple logging (demonstrates checkpoint boundary)
# ---------------------------------------------------------------------------

@bp.activity_trigger(input_name="input_data")
def log_activity(input_data: dict) -> str:
    """
    Simple activity - each activity call is a checkpoint boundary.
    Orchestrator state is persisted after each activity completes.
    """
    message = input_data.get("message", "No message")
    logging.info("Activity executed: %s", message)
    return f"Processed: {message}"


# ---------------------------------------------------------------------------
# Register blueprint with the function app
# ---------------------------------------------------------------------------
# DFApp extends FunctionApp with Durable Functions support
app = df.DFApp()
app.register_functions(bp)
