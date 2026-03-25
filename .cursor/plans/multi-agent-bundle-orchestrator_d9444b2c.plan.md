---
name: multi-agent-bundle-orchestrator
overview: Design and implement a multi-agent orchestration layer for bundle discovery (local DB, UCP, MCP, weather/events, resourcing) with an Assistant UI Chat experience that lets users pick agents and see progress/status huddles.
todos:
  - id: backend-registry
    content: Define agent abstraction and registry for local DB, UCP, MCP, weather/events, resourcing agents in orchestrator-service
    status: completed
  - id: multi-agent-orchestrator
    content: Implement multi-agent orchestration function and modify chat API to accept agent selections and return multi_agent_status
    status: completed
  - id: assistant-ui-picker
    content: Add agent picker UI in Assistant UI Chat and pass selected agents in chat requests
    status: completed
  - id: assistant-ui-huddle
    content: Implement AgentHuddle component and render backend multi_agent_status in assistant messages
    status: completed
  - id: admin-config
    content: (Optional Phase 3) Add platform config UI/APIs for multi-agent settings in portal
    status: completed
  - id: admin-agents-workflow
    content: "Admin portal: list available agents, define workflow (order/DAG), define agent skills in admin console"
    status: completed
  - id: user-cancel-agent
    content: Support user-initiated cancel of agent run when admin allows (e.g. events agent cancellable); backend + Assistant UI
    status: completed
  - id: user-editable-skills
    content: "user_editable: true per agent (admin-controlled); users can add skills e.g. only when weather > 70° in chat"
    status: completed
  - id: pao-trace-backend
    content: "PAO: AgentResult.trace (AgentOperation with phase PLAN/ACTION/OBSERVE); orchestrator populates trace and supports incremental updates"
    status: completed
  - id: pao-huddle-ui
    content: "PAO: AgentHuddle Reasoning Trace dropdown per agent; Plan (italic + thought), Action (monospace + terminal), Observe (bold + lightbulb); auto-expand when running"
    status: completed
  - id: admin-plan-templates
    content: "Admin: Plan Templates per agent (e.g. Step 1: Context check, Step 2: Discovery, Step 3: Vibe Validation)"
    status: completed
  - id: sentiment-todo-huddle
    content: "In scope: Full sentiment / To-do breakdown in huddle (thought timelines, memory health, credit usage)"
    status: completed
  - id: admin-cost-dashboard
    content: "Admin dashboard: cost per conversation (thought timelines, memory health, credit usage); track per user across conversations"
    status: completed
isProject: false
---

# Multi-Agent Bundle Orchestrator & Assistant UI Huddle

## Goal

Design and implement a **multi-agent orchestration** flow where multiple specialized agents (local DB, UCP, MCP, weather/events, resourcing, etc.) can concurrently search for bundle legs, while **Assistant UI Chat** exposes:

- An **agent picker** (which agents to activate for a given query).
- A **progress huddle** zone (like the provided UI snippet) showing what each agent is doing, statuses, and To-dos.

This plan covers both the **backend orchestration** and the **Assistant UI integration**.

## 1. Agent Model & Registry

- **Define an agent abstraction** in the orchestrator:
  - Location: `[services/orchestrator-service/agentic/agents.py]` (new file) or extend `[services/orchestrator-service/agentic/planner.py]`.
  - Interface shape:
    - `id`: string, e.g. `local_db_scout`, `ucp_scout`, `mcp_scout`, `weather_context`, `resourcing_scout`.
    - `kind`: `"discovery" | "context" | "resourcing" | ...`.
    - `enabled_default`: boolean.
    - `capabilities`: list (e.g. `"products"`, `"scheduling"`, `"constraints"`).
    - `invoke(request: AgentInvocation) -> AgentResult` (async).
  - **AgentResult** (in `[services/orchestrator-service/agentic/agents.py]`) must include:
    - `status`, `summary`, `details`, `operations` (existing).
    - `**trace: List[AgentOperation]`** – Plan-Action-Observe (PAO) reasoning trace.
  - **AgentOperation** (same file): `phase: Literal["PLAN", "ACTION", "OBSERVE"]`, `label: str`. Optional: `timestamp`, `detail` for richer UI. **Action labels must be human-readable** (e.g. “Checking Mercedes availability”), not raw API logs (e.g. no “GET /api/v1/partners/123/products”).
- **Agent registry**:
  - New module `[services/orchestrator-service/agentic/agent_registry.py]` listing built-in agents, wired to existing services:
    - `local_db_bundle_agent` → calls Discovery service bundle search.
    - `ucp_bundle_agent` → uses existing UCP gateway (`gateway_ucp` client).
    - `mcp_bundle_agent` → uses existing MCP/Shopify mesh if present (or leave as future agent but structure in place).
    - `weather_context_agent` → calls weather/events service or external API (if already integrated as per `EXTERNAL_APIS_WEATHER_EVENTS.md`).
    - `resourcing_agent` → calls re-sourcing / recovery service or task queue to find alternative vendors.
  - Export a **config DTO** consumable by frontend: list of agents, labels, descriptions, defaults.
- **Admin configurability**:
  - Extend `platform_config` JSON via `[apps/portal/app/api/platform/config/route.ts]` and `[.../config-editor.tsx]` to store:
    - `multi_agent_config.enabled`.
    - Per-agent `enabled`, `display_name`, `description`, `category`.
  - Or minimal phase-1: hard-coded registry with a flag in config to toggle the whole feature.

## 2. Admin Portal: Agents List, Workflow & Skills

- **Available agents list** (Platform Admin):
  - New page or section under Config: **Agents** (e.g. `/platform/agents` or a tab in `[apps/portal/app/(platform)/platform/config/config-editor.tsx]`).
  - Lists all agents from the registry with: `id`, admin-defined `display_name`, `description`, `kind`, `enabled`, **user_cancellable** (see below), **user_editable** (see below), and **skills** (see below).
  - Admin can toggle each agent on/off, set display name/description, mark **“User can cancel this agent”** (e.g. events agent can be cancelled so local events are not considered), and mark **“User can edit skills”** (**user_editable: true**) so end-users can add or change skills for that agent in chat.
- **Agent skills (defined in admin console)**:
  - Each agent has a **skills** payload (e.g. JSON array or key-value) editable in the admin UI:
    - Examples: `["products", "scheduling"]`, `{"sources": ["local_db"]}`, or free-form tags/conditions used for filtering and for the orchestrator to decide what to run.
  - Stored in platform config or a dedicated `agent_definitions` table (e.g. `platform_config.multi_agent_config.agents[]` with `id`, `skills`, `user_cancellable`, **user_editable**, `display_name`, `description`, `enabled`, `workflow_order`).
  - Assistant UI and orchestrator consume this so “skills” drive discovery behaviour and user-facing labels.
- **User-editable skills (admin-controlled)**:
  - When admin sets **user_editable: true** for an agent, **end-users** can add or edit skills for that agent in Assistant UI Chat (e.g. “only when weather is over 70 degrees”, “exclude indoor venues”).
  - Admin fully controls which agents allow this: if **user_editable** is false, only admin-defined skills apply; if true, the user’s overrides (per thread or per request) are merged or replace for that agent.
  - Stored: admin skills in platform config; user-provided skills sent per request (e.g. `agent_skills_overrides: { [agent_id]: skills }`) and optionally persisted per thread/session for convenience.
  - Orchestrator uses user overrides only for agents that have `user_editable: true`; otherwise it uses only admin-defined skills.
- **Plan Templates (admin-defined per agent)**:
  - In the Admin Portal (Agents / config-editor), allow admins to define **Plan Templates** for specific agents (e.g. “Step 1: Context check, Step 2: Discovery, Step 3: Vibe Validation”). Stored as JSON array or structured list in `multi_agent_config.agents[*].plan_template`. The orchestrator uses these as the default PLAN-phase steps; agents append ACTION and OBSERVE entries during execution.
- **Workflow of agents to be executed**:
  - Admin defines **execution order** or a simple **workflow**:
    - Option A: **ordered list** – e.g. `[local_db_scout, ucp_scout, weather_context, resourcing_scout]` so agents run in that order (or parallel within phases).
    - Option B: **simple DAG** – e.g. “weather and events run after discovery agents” with a small graph (predecessors) stored in config.
  - Stored in the same `multi_agent_config` (e.g. `workflow_order: string[]` or `workflow_steps: { step_id; agent_ids[]; after?: step_id[] }`).
  - Orchestrator reads this and runs agents in the defined sequence/parallelism; Assistant UI can show “Step 1: Local DB, UCP → Step 2: Weather, Resourcing” in the huddle if desired.

## 3. Orchestrator Multi-Agent Execution

- **New orchestrator endpoint** for multi-agent bundle discovery:
  - Option A: extend existing `POST /api/v1/chat` in `[services/orchestrator-service/api/chat.py]` to accept:
    - `agents: string[]` (agent ids selected by user), optional.
    - `multi_agent_mode: boolean`.
    - `cancel_agent_ids: string[]` (optional) – user requests to cancel these agents for this run (only applied when admin has set `user_cancellable` for those agents).
    - `**agent_skills_overrides: Record<string, unknown>`** (optional) – per-agent skill overrides from the user (e.g. `{ "weather_context": { "min_temp_f": 70 } }`). Applied only for agents where admin set **user_editable: true**; otherwise ignored.
  - Option B: new endpoint `POST /api/v1/multi-agent/bundle` returning structured agent run results (good for UI polling); same body can include `cancel_agent_ids` and `agent_skills_overrides`.
- **Execution flow** (implemented in e.g. `[services/orchestrator-service/agentic/multi_agent_orchestrator.py]`):
  - Accept **resolved intent**, current context (thread, bundle, location, time, etc.), and **workflow** from admin config (ordered list or DAG).
  - Filter registry by requested agents, admin-configured `enabled`, and **exclude any agent whose id is in `cancel_agent_ids` and for which admin set `user_cancellable: true`** (e.g. events agent can be cancelled so local events are not considered).
  - Run agents according to **workflow** (order or phases); e.g. parallel within a step, then next step.
  - Fire each agent with `asyncio.gather` (or by step), each getting a scoped `AgentContext`:
    - `intent`, `thread_id`, `experience_session_id`, `location`, `time_window`, etc.
    - **Effective skills**: for agents with `user_editable: true`, merge or apply `agent_skills_overrides[agent_id]` with admin-defined skills; otherwise use only admin-defined skills (e.g. “only when weather > 70°” passed into weather/events agent).
  - Collect `AgentResult` objects with fields:
    - `status: "pending" | "running" | "succeeded" | "failed" | "cancelled"`.
    - `summary`: user-facing one-liner for the huddle (e.g. “Local DB found 12 products”; “Events agent skipped (cancelled by user)”).
    - `details`: structured payload (products, constraints, events, etc.).
    - `operations`: optional list for fine-grained progress (e.g. `[{ label: "Query UCP", status: "done" }, ...]`).
    - `**trace: List[AgentOperation]`** – PAO reasoning trace (see section **3a**).
  - **Refactor MultiAgentOrchestrator** to populate each agent’s `trace` during execution. After an agent completes a **PLAN** step, push that state into `multi_agent_status` before starting **ACTION** (incremental updates; see 3a). **OBSERVE** phase must capture high-level findings (e.g. “Found 3 BMWs, filtering for rain-ready models”; “Shopify description for ‘Baby Onesie’ lacks a vibe; assigned ‘Sentimental/Nursery’ via LLM”; “Primary BMW partner is down; checking secondary Limo registry” for error/re-sourcing).
  - **User-initiated cancel during run** (optional enhancement): if we add streaming or long-running runs, expose `POST /api/v1/multi-agent/cancel` (or a signal in the same connection) with `run_id` and `agent_id`; orchestrator checks `user_cancellable` and stops that agent’s work and marks result as `cancelled`.
- **Result aggregation**:
  - New aggregator helper (same module) that takes all `AgentResult`s (including cancelled) and:
    - Merges product candidates into a unified bundle candidate list, tagged by source agent.
    - Produces **high-level narrative** for the assistant message (e.g. “I asked local inventory, UCP feeds, and weather context; here’s a combined bundle.”).
- **Persistence / progress tracking** (minimal phase):
  - Store multi-agent run metadata in `experience_session_legs` or a new `agent_runs` table if needed later.
  - For MVP, it’s acceptable to return progress in a single response; a later phase can add streaming or polling.

## 3a. Plan-Action-Observe (PAO) Reasoning Trace

- **Backend protocol** (`[services/orchestrator-service/agentic/agents.py]`):
  - **AgentResult** includes `trace: List[AgentOperation]`.
  - **AgentOperation**: `phase: "PLAN" | "ACTION" | "OBSERVE"`, `label: str` (human-readable). Optional: `timestamp`, `detail` for UI.
  - **PLAN**: high-level intent (e.g. “Context check”, “Discovery”, “Vibe validation”). No raw API URLs.
  - **ACTION**: human-readable step (e.g. “Checking Mercedes availability”, “Querying UCP catalog”). **Do not** expose raw API logs (e.g. “GET /api/v1/partners/123/products”).
  - **OBSERVE**: high-level findings and metadata/recovery:
    - Discovery: e.g. “Found 3 BMWs, filtering for rain-ready models”.
    - Metadata enricher: e.g. “Shopify description for ‘Baby Onesie’ lacks a vibe; assigned ‘Sentimental/Nursery’ via LLM”.
    - Error / re-sourcing: e.g. “Primary BMW partner is down; I am now checking the secondary Limo registry.”
- **Streaming / incremental updates**:
  - Structure the orchestrator so that when an agent finishes a **PLAN** step, it **pushes** that state to `multi_agent_status` (or to a streaming channel) **before** starting **ACTION**. Same for ACTION → OBSERVE. Enables “live” huddle without waiting for full response (SSE or WebSocket in a later phase; MVP can still return full trace in one response).
- **Admin: Plan Templates** (in platform config / Agents UI):
  - Allow admins to define **Plan Templates** per agent (e.g. “Step 1: Context check, Step 2: Discovery, Step 3: Vibe Validation”). These become the default PLAN-phase labels; agents can append ACTION and OBSERVE entries during execution.

## 4. Assistant UI Chat: Agent Picker

- **Config fetch**:
  - New API route in assistant-ui-app: `[apps/assistant-ui-chat/app/api/agents/route.ts]` that proxies the orchestrator/portal agent registry:
    - Returns agent list with `id`, `name`, `description`, `category`, `enabled_default`, **user_cancellable** (from admin), **user_editable** (from admin), and **skills** (from admin).
- **Agent picker UI**:
  - Location: update `ChatPage` in `[apps/assistant-ui-chat/app/page.tsx]`.
  - Add a lightweight **toolbar row above the message list**, similar to the snippet:
    - Left: small label “Agents active”.
    - Right: `Settings` icon that opens a small popover listing agents with checkboxes.
  - Keep **per-thread agent selection** in React state + localStorage/sessionStorage (e.g. keyed by thread id).
  - When sending a message (composer submit), include **selected agent IDs**, **cancel list** (agents user chose to skip for this run, e.g. “Don’t use events”) , and **agent_skills_overrides** (user-edited skills for agents with `user_editable: true`) in the payload so `/api/chat` forwards them to the orchestrator.
  - **Cancel control**: For agents with `user_cancellable: true`, show a “Skip for this run” or “Cancel” control in the picker or in the huddle row so the user can exclude e.g. events agent before or during the run.
  - **User-editable skills**: For each agent with **user_editable: true**, show an inline control (e.g. "Add condition" or a small form) so the user can add or edit skills (e.g. "only when weather is over 70 degrees"). Store in state per thread and send as `agent_skills_overrides` in the request; backend applies these only for agents marked user_editable by admin.

## 5. Assistant UI Chat: Progress Huddle

- **Data shape from backend**:
  - Extend orchestrator chat response JSON (or multi-agent endpoint) with a `multi_agent_status` field:
    - `multi_agent_status: { agents: Array<{ id; label; status; summary; operations?: Operation[]; user_cancellable?: boolean; trace?: AgentOperation[] }> }`.
  - Each `AgentOperation` in `trace`: `phase: "PLAN" | "ACTION" | "OBSERVE"`, `label: string`.
  - Include `cancelled` in status when an agent was skipped (user cancel or admin-disabled).
- **Rendering in chat** (`[apps/assistant-ui-chat/components/AgentHuddle.tsx]`):
  - **Card**: Header row with loader icon + “Working...” + possibly token/credit estimate.
  - **Per-agent row**:
    - Icon for status: **spinner** (running), **check** (succeeded), **alert** (failed), **minus/cancel** (cancelled).
    - Short summary text (e.g. “Local DB: 8 matches”, “Events: skipped (cancelled by you)”).
    - For **running** agents with `user_cancellable: true`, show a **Skip** button that updates `cancel_agent_ids` for the **next** turn (no raw API logs in UI).
  - **Reasoning Trace** (PAO): For each agent, a **dropdown** “Reasoning Trace” that expands to show the `trace` list. Use **distinctive style per phase**:
    - **PLAN**: Italicized text + “thought” (or lightbulb/plan) icon.
    - **ACTION**: Monospace text + “terminal” icon.
    - **OBSERVE**: Bold text + “lightbulb” (or eye) icon.
  - **Auto-expand**: When an agent is **running**, auto-expand that agent’s Reasoning Trace so the user sees the live **Action** (and latest PLAN/OBSERVE) without opening the dropdown.
- **State updates**:
  - For MVP, show a single consolidated huddle once response returns; support incremental updates when backend pushes PLAN/ACTION/OBSERVE (streaming or polling).
  - Future-ready: in-run cancel and live ticker from `thinking_stream` or `trace` updates.
- **Full sentiment / To-do breakdown (in scope)**:
  - Extend the huddle (and backend payload) to include **thought timelines** (expandable “Thought for Xs” with optional detail), **memory health** (e.g. token/context usage indicator or “Plenty of room” / “Near limit”), and **credit usage** (e.g. tokens or cost estimate per turn or per conversation).
  - **To-do progress**: Show a To-do list in the huddle (e.g. “1 of 4 To-dos”) with checkmarks for completed and spinner for in-progress, matching the reference snippet. Backend to include `todos: Array<{ label; status: "pending"|"in_progress"|"done" }>` in the response or in `multi_agent_status`.

## 6. UX Consistency & Controls

- **History-style header** (like snippet top bar):
  - In Assistant UI Chat main header, add a small inline toolbar (icon-only buttons) for:
    - History (existing threads sidebar already covers this; icon can just toggle sidebar).
    - New chat (existing “New chat” already implemented; an extra icon here can call same handler).
- **Agent settings popover**:
  - Implement minimal accessible popover (using existing shadcn/ui primitives or a simple div) for agent selection and, for agents with `user_cancellable`, a “Skip for this run” option.
- **Accessibility & responsiveness**:
  - Ensure all new buttons have `aria-label`s and focus states.
  - Huddle card and picker should collapse nicely on mobile (stacking, truncating text).

## 6a. Admin Portal: Cost & Conversation Dashboard

- **Dashboard purpose**: Platform admins need visibility into **cost and health per conversation** and **per user across conversations**.
- **Metrics to surface** (stored per conversation / per turn and aggregated):
  - **Thought timelines**: Duration or count of “thought” steps per turn/conversation (e.g. “Thought for 8s”, “Thought for 4s”); show in a timeline or table in the admin dashboard.
  - **Memory health**: Context or token usage per conversation (e.g. “Plenty of room” vs “Near limit”); optional numeric usage. Track per conversation and roll up per user.
  - **Credit usage**: Token count or cost estimate per conversation and per user (e.g. input/output tokens, or $ estimate if pricing is available). Ability to filter by user, date range, conversation.
- **Admin UI** (new page or section under Platform Admin, e.g. `/platform/conversations` or `/platform/cost-dashboard`):
  - **Per-conversation details**: List or table of conversations with columns: conversation/thread id, user id (or anonymous id), started at, last activity, **thought timeline summary** (e.g. total thought time or count), **memory health** at end of conversation, **credit usage** (tokens or cost). Drill-down into a single conversation to see per-turn thought timelines, memory health over time, and credit per turn.
  - **Per-user view**: Aggregate the same metrics **by user** across all their conversations (e.g. total credit usage per user, total thought time, worst memory health). Filter by date range; link through to that user’s conversations.
- **Backend**: Persist or derive these metrics when processing chat/multi-agent runs (e.g. store in `experience_sessions` / `chat_threads` or a dedicated `conversation_metrics` table keyed by thread_id and optionally user_id). Expose via platform API (e.g. `GET /api/platform/conversations` with optional `user_id`, `from`, `to`) and use in the admin dashboard.

## 7. PAO Implementation Considerations

- **Verbosity vs. clarity**: Do **not** show raw API logs in the Action phase. The Action `label` must be human-readable (e.g. “Checking Mercedes availability”), not “GET /api/v1/partners/123/products”.
- **“Vibe” transition**: Use the **Observe** phase to show the Metadata Enricher at work (e.g. “Observe: Shopify description for ‘Baby Onesie’ lacks a vibe; assigned ‘Sentimental/Nursery’ via LLM”).
- **Error recovery**: If an action fails, the **Observe** phase should explain re-sourcing (e.g. “Observe: Primary BMW partner is down; I am now checking the secondary Limo registry.”).

## 8. Non-Goals / Future Enhancements

- **Full sentiment / To-do breakdown** (thought timelines, memory health, credit usage) is **in scope**: see Section 5 (huddle) and Section 6a (admin cost dashboard).
- WhatsApp / omnichannel surfacing of multi-agent status can be added later via the existing Webhook service.

## 9. Files Likely to Change

- Backend (orchestrator):
  - `[services/orchestrator-service/agentic/agents.py]` (new or extended) – `BaseAgent`, `AgentResult` with `trace: List[AgentOperation]`, `AgentOperation` with `phase` (PLAN/ACTION/OBSERVE) and human-readable `label`.
  - `[services/orchestrator-service/agentic/agent_registry.py]` (new) – agent definitions; read skills, user_cancellable, and plan_templates from config.
  - `[services/orchestrator-service/agentic/multi_agent_orchestrator.py]` (new) – orchestration, workflow order, aggregation; populate PAO trace per agent; push incremental updates (PLAN before ACTION); honour `cancel_agent_ids` and `agent_skills_overrides`.
  - `[services/orchestrator-service/api/chat.py]` – accept agent selections, `cancel_agent_ids`, and attach multi-agent results; include thought_timelines, memory_health, credit_usage, and todos in response for huddle; optional cancel endpoint for in-run cancel.
  - Possibly `[services/orchestrator-service/clients.py]` – helper calls to discovery, UCP, weather, resourcing.
  - Persistence for **cost dashboard**: store per-turn/conversation metrics (thought timelines, memory health, credit usage) keyed by thread_id and user_id (e.g. in `experience_sessions`, `chat_threads`, or a `conversation_metrics` table); used by platform API for admin dashboard.
- Config & portal (admin):
  - `[apps/portal/app/api/platform/config/route.ts]` and `[.../platform/config/config-editor.tsx]` – multi-agent config (enable, per-agent toggles, skills, user_cancellable, workflow).
  - **New:** `[apps/portal/app/(platform)/platform/agents/page.tsx]` (or Agents tab in config) – list available agents, edit display name / description / skills / **user_editable** / user_cancellable, **plan_templates** (PAO step labels per agent), define workflow (ordered list or simple DAG).
  - **New:** Admin **Cost & Conversation dashboard** (e.g. `[apps/portal/app/(platform)/platform/conversations/page.tsx]` or `/platform/cost-dashboard`) – per-conversation details (thought timelines, memory health, credit usage) with drill-down; per-user view across conversations; filter by user, date range.
  - Platform API to expose agent list, workflow, and **conversation/cost metrics** (e.g. GET from config or dedicated `/api/platform/agents`; GET `/api/platform/conversations` or `/api/platform/cost-metrics` with optional `user_id`, `from`, `to`).
- Assistant UI Chat:
  - `[apps/assistant-ui-chat/app/page.tsx]` – agent picker UI, “skip/cancel” for user-cancellable agents, wiring of selected and cancelled agents into requests, header tweaks.
  - `[apps/assistant-ui-chat/components/AgentHuddle.tsx]` (new) – progress huddle; per-agent Reasoning Trace dropdown (PLAN italic + thought icon, ACTION monospace + terminal, OBSERVE bold + lightbulb); auto-expand trace when agent is running; Skip button for user_cancellable agents; **thought timelines** (expandable “Thought for Xs”), **memory health** indicator, **credit usage**; **To-do** list (e.g. “1 of 4 To-dos”) with status per item.
  - `[apps/assistant-ui-chat/components/GatewayPartRenderers.tsx]` – render `multi_agent_status` payload.
  - `[apps/assistant-ui-chat/app/api/chat/route.ts]` (or equivalent) – forward agent selections and `cancel_agent_ids` to orchestrator.

## 10. Implementation Phases

1. **Phase 1 – Backend skeleton**
  - Create agent registry + stub agents wired to existing services.
  - Add multi-agent orchestration function, workflow (order from config), and minimal aggregation.
  - Support `cancel_agent_ids` and `user_cancellable`; extend orchestrator chat response to include `multi_agent_status` (including `cancelled` status).
2. **Phase 2 – Admin portal: agents list, workflow, skills**
  - Add **Agents** page or tab in platform admin: list available agents, edit display name / description, **skills** (admin-defined, e.g. JSON or tag list), **user_cancellable** per agent, and **workflow** (ordered list or simple DAG of agents to execute).
  - Persist in platform config or dedicated store; expose via API for Assistant UI and orchestrator.
3. **Phase 3 – Assistant UI integration**
  - Implement agent picker in Assistant UI Chat (including “skip for this run” for user-cancellable agents).
  - Implement `AgentHuddle` and render it based on backend response; show Cancel button for running user-cancellable agents when supported.
  - Forward selected agents and `cancel_agent_ids` in chat requests.
4. **Phase 4 – PAO reasoning trace**
  - Backend: Add `trace: List[AgentOperation]` to AgentResult; MultiAgentOrchestrator populates PLAN/ACTION/OBSERVE with human-readable labels; support incremental push (PLAN before ACTION).
  - Admin: Plan Templates per agent in config-editor (e.g. “Step 1: Context check, Step 2: Discovery, Step 3: Vibe Validation”).
  - UI: AgentHuddle Reasoning Trace dropdown per agent; distinct styles (Plan italic + thought icon, Action monospace + terminal, Observe bold + lightbulb); auto-expand when agent is running.
  - Observe phase: use for metadata/vibe enrichment and error/re-sourcing messages (no raw API logs in Action).
5. **Phase 5 – Sentiment, To-do & cost in huddle**
  - Backend: Include in chat/multi-agent response: thought timelines (e.g. duration per “thought” step), memory health (context/token usage), credit usage (tokens or cost per turn), and `todos` list (label + status) for the huddle.
  - Assistant UI: Extend AgentHuddle to render thought timelines (expandable “Thought for Xs”), memory health indicator, credit usage, and To-do progress (e.g. “1 of 4 To-dos” with checkmarks/spinner).
6. **Phase 6 – Admin cost & conversation dashboard**
  - Backend: Persist or compute per-conversation and per-turn metrics (thought timelines, memory health, credit usage); store keyed by thread_id and user_id. Expose `GET /api/platform/conversations` (or cost-metrics) with filters (user_id, date range).
  - Admin portal: New dashboard page (e.g. `/platform/conversations` or `/platform/cost-dashboard`) with per-conversation details (thought timelines, memory health, credit usage) and drill-down; per-user aggregation across conversations with ability to track per user.
7. **Phase 7 – Advanced UX**
  - Optional: in-run cancel endpoint and streaming so user can cancel an agent while the run is in progress.

