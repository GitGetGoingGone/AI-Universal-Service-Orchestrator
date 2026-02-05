---
name: AI Universal Service Orchestrator Platform - User Flows
overview: User flows by persona (Customer, Partner, Hub, Gig Worker, Admin, AI Orchestrator)
todos: []
---

# User Flows by Persona

This section outlines all user flows for the AI Universal Service Orchestrator platform, categorized by persona.

## Personas

1. **Customer** - End consumer placing orders
2. **Partner/Vendor** - Retailers, artisans, service providers
3. **Hub** - Fulfillment centers, assembly points
4. **Gig Worker** - Delivery drivers, pick-up workers
5. **Admin** - Platform administrators (Superadmin, Ops, Regional)
6. **AI Orchestrator** - System automation flows

---

## 1. Customer Persona

### 1.1 Authentication & Onboarding

**Flow: Customer Registration & Login**

1. Customer lands on platform (via web, mobile app, or AI agent handoff)
2. If coming from ChatGPT/Gemini: Agentic Handoff (SSO 2.0) - seamless authentication
3. If direct: Choose login method

  - Passkey (FaceID/TouchID) - FIDO2
  - Social login (Google, Apple, LinkedIn)
  - Email/password (fallback)

4. Complete profile setup

  - Phone number (for WhatsApp opt-in)
  - Delivery addresses
  - Payment methods
  - Preferences

5. View Agentic Consent Manager dashboard

  - See which AI agents have active tokens
  - Manage permissions for AI purchases

**Flow: Agentic Handoff from AI Agent**

1. Customer starts conversation in ChatGPT/Gemini
2. AI agent suggests using platform for complex order
3. Customer clicks deep-link to platform
4. Session persists via Delegated OAuth tokens
5. No login screen shown - seamless transition

### 1.2 Intent Discovery & Order Creation

**Flow: Natural Language Intent to Order**

1. Customer enters intent: "Something fancy for a baby shower by Saturday"
2. Intent Resolver (Module 4) processes:

  - Extracts entities (baby shower, fancy, Saturday)
  - Builds Graph of Needs (Product + Customization + Packaging + Delivery)
  - **Determines if immediate or standing intent**:
  - Immediate: "by Saturday" = specific deadline
  - Standing: "on next sunny day" = condition-based

3. **If Immediate Intent**:

  - Scout Engine (Module 1) discovers products immediately
  - Proceeds with standard flow

4. **If Standing Intent** (Module 23):

  - System creates Standing Intent
  - Starts Durable Orchestration
  - Returns instance ID for tracking
  - Customer sees: "We'll watch for the perfect moment!"

5. Scout Engine (Module 1) discovers products:

  - Searches UCP/ACP manifests
  - Uses semantic search (pgvector)
  - Applies ranking boost (Module 20)
  - **Affiliate Link Wrapper (Module 21) injects tracking IDs**
  - Returns curated bundles or individual products (with affiliate links)

6. Customer views results:

  - Transparent Mode: See all vendors and pricing
  - Concierge Mode: See only bundle name and total price

7. Customer selects option
8. Time-Chain Resolver (Module 5) calculates feasibility:

  - Multi-leg journey optimization
  - Synchronizes arrivals from multiple vendors
  - Accounts for customization time
  - Verifies delivery deadline
  - **Conflict Simulation**: If customer adds item to existing order, system simulates impact
  - Example: Adding "custom chocolates" to limo ride 10 minutes from pickup
  - System simulates detour and checks if it makes user late for dinner
  - Proactive suggestion: "Adding chocolates will make you 15 minutes late for dinner. Should I proceed, or would you like me to courier the chocolates separately to the restaurant?"

9. If feasible: Proceed to customization
10. If not feasible: Show alternatives or suggest date changes
11. If conflict detected: Show proactive suggestions with timeline impact

**Flow: Intent-to-Bundle Discovery Flow (Gemini's "Discovery-to-Door" Journey)**

1. **Entry**: User tells external AI (ChatGPT/Gemini): "I need a luxury baby gift for a 5 PM shower in Austin"
2. **Agent Search**: External AI agent queries platform's UCP Manifest via API
3. **Discovery**: Platform returns "White Glove Bundle" options:

  - Example: "Posh Peanut blanket + Local Monogramming + Delivery"
  - Bundle metadata overrides individual partner branding

4. **Handoff**: AI presents bundle to user with deep-link to platform
5. **Customization**: User clicks deep-link to platform UI to "Approve Proof" of monogram

  - Virtual Proofing Engine shows high-fidelity preview
  - User approves or requests changes

6. **Autonomous Checkout**: User's AP2 (Agent Payments Protocol) token authorizes single split-payment:

  - Token stored from previous agent interaction
  - Single authorization covers all three vendors
  - Atomic Multi-Checkout executes automatically
  - Reduces cognitive load - user doesn't see payment complexity

**Flow: Curated Bundle Selection**

1. Customer sees "The Birthday Bash" bundle
2. In Transparent Mode: Can see bundle composition
3. In Concierge Mode: Sees only bundle name and price
4. Customer clicks to view details
5. Virtual Proofing Engine (Module 8) shows preview:

  - High-fidelity visual of customized items
  - Source of Truth image for approval

6. Customer approves or requests changes
7. Proceeds to checkout

**Flow: Customization & Virtual Proofing**

1. Customer selects product requiring customization
2. System shows customization options:

  - Embroidery, engraving, gift wrapping
  - Color choices, size options

3. Customer makes selections
4. Virtual Proofing Engine generates preview
5. Customer reviews and approves
6. Approved image becomes "Source of Truth" for artisan

### 1.3 Checkout & Payment

**Flow: Atomic Multi-Checkout**

1. Customer reviews order summary:

  - All items from different vendors
  - Customization details
  - Delivery timeline
  - Total price breakdown

2. Customer enters delivery address
3. System shows available delivery options
4. Customer selects payment method
5. Atomic Multi-Checkout (Module 15) executes:

  - Simultaneous tokenized payments
  - Split payments across vendor protocols
  - **Affiliate commissions calculated (Module 21)**
  - **Delegated commission logic applied**
  - Single click transaction

6. Payment confirmation shown
7. Order confirmation sent (email + WhatsApp if opted in)

**Flow: Autonomous Checkout with AP2 Token (Agent Payments Protocol)**

1. Customer has pre-authorized AP2 token from previous AI agent interaction
2. Customer approves bundle in platform UI
3. System uses stored AP2 token for payment authorization:

  - Token contains payment permissions from AI agent session
  - Single authorization covers all vendors in bundle
  - No need for customer to re-enter payment details

4. Atomic Multi-Checkout executes:

  - Split payments to all vendors (Product vendor, Customization vendor, Delivery)
  - Single transaction, multiple recipients
  - Reduces cognitive load - customer doesn't see payment complexity

5. Payment confirmation sent
6. Order proceeds automatically

**Flow: Escrow & Payment Release**

1. Customer completes payment
2. Transaction & Escrow Manager (Module 16) holds funds:

  - Funds held in escrow
  - Released upon delivery confirmation

3. Customer receives delivery
4. Customer confirms delivery
5. Escrow releases payments:

  - Vendor payments released
  - Platform fee collected
  - All parties notified

### 1.4 Order Tracking & Status Updates

**Flow: Real-Time Status Updates**

1. Customer views order dashboard
2. Status Narrator (Module 14) provides updates:

  - Human-readable status messages
  - **Agent Reasoning**: "I'm still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."
  - Timeline visualization
  - Progress indicators

3. Updates received via:

  - Web dashboard
  - WhatsApp (if opted in)
  - Email
  - Push notifications (mobile)

**Flow: Progress Ledger with If/Then Logic**

1. Customer views Progress Ledger Adaptive Card
2. Sees visual "Logic Map":

  - IF (Weather == Sunny) AND (Day == Thursday) -> THEN (Order Flowers)
  - Shows active conditions being monitored
  - Builds trust by showing agent isn't just "waiting" but actively monitoring

3. Real-time updates as conditions change
4. Customer understands "why" system is waiting

**Flow: Standing Intent Tracking (Module 23)**

1. Customer views standing intent dashboard
2. Sees progress ledger:

  - Current status
  - Conditions being monitored
  - Next steps
  - Estimated completion time

3. Receives updates when conditions met
4. Can approve or modify before execution

### 1.5 Communication & Support

**Flow: Multi-Party Support Hub**

1. Customer has question about order
2. Opens Support Hub (Module 12)
3. Views conversation thread:

  - Sees all participants (vendors, hub, gig worker, AI orchestrator)
  - Real-time chat interface
  - Message history

4. Sends message
5. All parties can respond
6. Customer receives notifications for new messages

**Flow: WhatsApp Integration**

1. Customer opts in to WhatsApp notifications
2. Receives status updates via WhatsApp:

  - Template messages for status changes
  - Interactive buttons (Track Order, Contact Support)

3. Can reply to messages
4. Replies sync with web chat
5. Full conversation history available

### 1.6 Order Modifications & Autonomous Recovery

**Flow: Requesting Order Change**

1. Customer wants to modify placed order:

  - Example: "I want pink flowers instead of red"
  - Order already placed with red flowers

2. System sends change request via Omnichannel Broker (Module 24)
3. Partner responds (accept/reject/counter-offer)
4. If rejected: **Autonomous Recovery (Module 6) triggers automatically**:

  - System finds alternative vendor
  - Cancels original order
  - Updates bundle
  - Recalculates timeline
  - Notifies customer with new timeline

5. Customer approves or rejects recovery
6. Order updated automatically

---

## 2. Partner/Vendor Persona

### 2.1 Partner Onboarding & Registration

**Flow: Partner Registration**

1. Partner visits partner portal
2. Registers account:

  - Business information
  - Tax ID, legal entity
  - Contact details

3. Verifies identity:

  - Business verification
  - Social identity verification (LinkedIn, etc.)

4. Sets up payment account:

  - Stripe Connect account
  - Bank details for payouts

5. Completes capability registration (Module 9)

**Flow: Capability Registration**

1. Partner logs into Generic Capability Portal (Module 9)
2. Registers capabilities:

  - Service types (Embroidery, Engraving, Gift Wrapping, Dining)
  - Geographic coverage
  - Capacity limits
  - Pricing structure

3. Sets real-time capacity:

  - Current workload
  - Available slots
  - Lead times

4. Submits product catalog:

  - Product feeds
  - UCP/ACP manifests (if protocol-ready)
  - Or uses Legacy Adapter Layer (Module 2)

5. Capability tags assigned automatically

**Flow: White Glove Vendor "Experience" Onboarding (Gemini's "Capability-to-Cash" Journey)**

1. **Registration**: Local vendor (e.g., limo company) logs in and registers:

  - **Capability**: Service type (e.g., "Transport")
  - **Class**: Service tier (e.g., "Luxury")
  - Geographic coverage and availability

2. **Manifest Upload**: Vendor uploads "Experience SKU" (Meta-Partner Manifest):

  - Example: "The Anniversary Loop" - pre-packaged experience
  - Includes: Limo service + pre-negotiated stop at specific florist
  - Defines components, scheduling, and pricing
  - Treated as single-leg task for orchestrator

3. **Verification**: Admin reviews and approves manifest:

  - Validates experience structure
  - Verifies partner capabilities
  - Checks pricing and availability rules

4. **Agent-Discoverable**: Once approved, vendor becomes "Agent-Discoverable":

  - Experience appears in Scout Engine results
  - AI agents can query and suggest to users
  - Ready for "White Glove Bundle" inclusion

### 2.2 Product & Service Management

**Flow: Product Catalog Submission**

1. Partner prepares product manifest:

  - Protocol-ready: UCP or ACP format
  - Legacy: Uses adapter layer

2. Uploads manifest to platform
3. System processes:

  - Validates manifest
  - Extracts product data
  - Indexes for semantic search
  - Maps to capability tags

4. Products appear in discovery results

**Flow: Meta-Partner Manifest Submission**

1. Partner creates pre-packaged experience:

  - Example: "Limo + Dining Experience"
  - Multiple services as single unit

2. Submits meta-manifest (Module 20):

  - Defines components
  - Sets scheduling
  - Configures pricing
  - Sets availability rules

3. System treats as single-leg task for orchestrator
4. Appears as curated bundle to customers

**Flow: Premium Registry Registration**

1. Partner registers "Blanks" (Module 7):

  - High-quality base products (Nike, Posh Peanut, etc.)
  - Links to customization capabilities

2. System maps:

  - Product → Capability Tags
  - Enables customization matching

3. Products appear in Premium Registry

### 2.3 Order Management

**Flow: Receiving Order**

1. Partner receives order notification:

  - Via web portal
  - Via email
  - Via WhatsApp (if configured)

2. Views order details:

  - Customer information
  - Product specifications
  - Customization requirements
  - Source of Truth image (if applicable)
  - Delivery deadline

3. Accepts or rejects order
4. If accepts: Order moves to processing

**Flow: Order Processing**

1. Partner processes order:

  - Prepares product
  - Applies customization (if required)
  - Follows Source of Truth image

2. Updates order status:

  - "In Progress"
  - "Customization Started"
  - "Customization Complete"
  - "Ready for Pickup"

3. Status updates trigger:

  - Time-Chain Resolver recalculation
  - Customer notifications
  - Hub notifications (if applicable)

**Flow: Multi-Vendor Task Queue**

1. Partner views task queue (Module 11):

  - Sequential tasks assigned
  - Task 1: Restaurant prepares meal
  - Task 2: Gig worker picks up gift
  - Task 3: Gig worker delivers to restaurant

2. Partner completes assigned task
3. System automatically triggers next task
4. All parties notified of progress

### 2.4 Communication & Support

**Flow: Multi-Party Chat Participation**

1. Partner receives message in Support Hub
2. Views conversation thread:

  - Sees all participants
  - Customer, other vendors, hub, AI orchestrator

3. Responds to customer query
4. Can tag other participants if needed
5. All messages visible to all parties

**Flow: Pro-Agent Delegation**

1. High-volume partner sets up Pro-Agent:

  - Authorizes AI agent to accept orders
  - Sets parameters:
  - "Accept any order over $15 within 2 miles"
  - "Accept orders with 24+ hour lead time"

2. Pro-Agent automatically:

  - Accepts qualifying orders
  - Updates status
  - Handles routine communications

3. Partner reviews activity dashboard

### 2.5 Storefront Management (Module 19)

**Flow: Creating Custom Storefront**

1. Partner accesses Storefront Builder
2. Selects theme:

  - Choose from presets
  - Or start from scratch

3. Customizes branding:

  - Logo upload
  - Color scheme
  - Typography
  - Layout preferences

4. Configures domain:

  - Subdomain (partner-name.usoorchestrator.com)
  - Or custom domain (CNAME)

5. Publishes storefront
6. Storefront goes live

**Flow: Theme Customization**

1. Partner opens Visual Theme Editor
2. Drag-and-drop customization:

  - Product card layouts
  - Checkout flow
  - Navigation structure

3. Real-time preview
4. Saves draft or publishes
5. Changes apply immediately

### 2.6 Affiliate Onboarding (Module 21)

**Flow: Affiliate Self-Service Registration**

1. Local business (e.g., "Texas Limo Co") or individual creator visits affiliate portal
2. Logs in via Clerk (or creates account)
3. Completes registration form:

  - Business name and type
  - Contact information
  - UCP/ACP Manifest URL (or uses Legacy Adapter)
  - Commission rate preference (CPA or CPE)
  - Payment account details (Stripe Connect)

4. Submits registration
5. System initiates KYC verification:

  - Business license verification (automated API check)
  - Insurance verification
  - Tax ID verification
  - Identity verification (for individuals)

6. Trust score calculated automatically
7. If trust score >= 70: White Glove status granted
8. Affiliate receives tracking ID
9. Can start receiving orders

**Flow: Affiliate Link Integration**

1. Affiliate partner's products appear in Scout Engine results
2. Affiliate Link Wrapper (Module 21) automatically:

  - Injects tracking ID into product URLs
  - For protocol-native: Creates Shared Payment Token (SPT) with tracking
  - For non-protocol: Creates deep-link with tracking parameters

3. When customer clicks link:

  - Click tracked in real-time
  - Tracking ID associated with customer session

4. If customer completes purchase:

  - Commission calculated based on rate
  - Commission transaction created
  - Affiliate notified

**Flow: Commission Tracking & Payment**

1. Affiliate views commission dashboard:

  - Total clicks
  - Conversion rate
  - Total commissions earned
  - Pending commissions
  - Paid commissions

2. Commission details:

  - Per-order breakdown
  - Commission rate applied
  - Order value
  - Commission amount

3. Commissions paid automatically:

  - Weekly or monthly payout
  - To Stripe Connect account
  - Transaction history available

### 2.7 Omnichannel Negotiation (Module 24)

**Flow: Receiving Negotiation Request**

1. Partner receives negotiation request via preferred channel:

  - **WhatsApp**: Interactive message with buttons
  - **SMS**: Text message with reply options
  - **Email**: Structured email with links
  - **API**: Webhook to partner system

2. Request includes:

  - Customer's change request
  - Original order details
  - Deadline (if JIT)
  - Interactive buttons (Accept/Decline/Modify)

3. Partner can respond:

  - **Accept**: Click "Yes" button or reply "Yes"
  - **Decline**: Click "No" button or reply "No"
  - **Counter-Offer**: Type natural language (e.g., "I have Deep Purple Metallic available")

**Flow: Counter-Offer via WhatsApp**

1. Partner types: "Pink is booked, but I have a Deep Purple Metallic available at no extra cost"
2. System processes reply:

  - NLP extracts "Deep Purple Metallic"
  - Searches partner's manifest for item
  - Retrieves metadata (image, price, specs)

3. System enriches suggestion:

  - Adds image URL
  - Adds price and specifications
  - Generates Adaptive Card

4. System pushes to customer's AI thread:

  - Customer sees enriched suggestion
  - Can approve or reject

5. If customer approves:

  - Negotiation completes
  - Order updated
  - Partner notified

**Flow: Photo-Based Counter-Offer**

1. Partner sends photo via WhatsApp: "Will this purple work?"
2. System receives photo:

  - Stores photo URL
  - Triggers Vision AI analysis

3. Vision AI analyzes:

  - Checks quality standards
  - Validates color match
  - Ensures meets "Luxury" criteria

4. If photo approved:

  - System enriches with metadata
  - Pushes to customer with photo

5. If photo rejected:

  - System asks partner for alternative
  - Or escalates to admin

**Flow: Negotiation Timeout**

1. Partner doesn't reply within timeout (15 min for JIT, 60 min standard)
2. System escalates:

  - Creates escalation record
  - Notifies admin dashboard
  - Admin can intervene

3. Admin contacts partner:

  - Via phone or alternative channel
  - Resolves negotiation

4. Negotiation completes with admin assistance

### 2.8 Financial Management

**Flow: Payment Receipt**

1. Partner completes order leg
2. Leg verified as complete:

  - Time-Chain Resolver confirms
  - Customer confirms (if required)

3. Escrow Manager releases payment
4. Partner receives notification
5. Funds transferred to Stripe Connect account
6. Partner can view transaction history

**Flow: Financial Dashboard**

1. Partner views financial dashboard:

  - Pending payments (in escrow)
  - Completed payments
  - Payout schedule
  - Transaction history

2. Can export reports
3. Can set up automatic payouts

---

## 3. Hub Persona

### 3.1 Hub Registration & Setup

**Flow: Hub Registration**

1. Hub entity registers:

  - Business information
  - Physical location
  - Operating hours
  - Capacity limits

2. Registers capabilities:

  - "I can assemble boxes"
  - "I can store items temporarily"
  - "I can coordinate pickups"

3. Sets geographic coverage:

  - Service radius
  - Delivery zones

4. Completes verification

### 3.2 Task Management

**Flow: Receiving Assembly Task**

1. Hub receives RFP (Request for Proposal) via HubNegotiator (Module 10)
2. Views task details:

  - Items to assemble
  - Source locations
  - Delivery destination
  - Deadline
  - Compensation

3. Hub submits bid:

  - Based on current workload
  - Proximity to task
  - Capacity availability

4. System selects winning bid
5. Hub receives task assignment

**Flow: Assembly & Coordination**

1. Hub receives items from multiple vendors:

  - Item A from Vendor 1
  - Item B from Vendor 2
  - Customization materials

2. Hub coordinates arrivals:

  - Time-Chain Resolver synchronizes
  - Hub confirms all items received

3. Hub performs assembly/customization:

  - Follows Source of Truth image
  - Applies requested modifications

4. Updates status:

  - "Assembly in progress"
  - "Assembly complete"

5. Notifies gig worker for pickup

**Flow: QR-Handshake Verification**

1. Gig worker arrives for pickup
2. Hub generates dynamic QR code:

  - Contains bundle ID
  - Contains verification token

3. Gig worker scans QR code:

  - Verifies identity
  - Verifies bundle integrity

4. Handoff confirmed
5. System updates status

**Flow: Physical Handshake Flow (Gemini's "High-Velocity Task Execution")**

1. **Task Push**: Gig worker receives "Leg" task on mobile app:

  - Notification: "Pick up Item A at 2 PM"
  - Task details: Location, item description, deadline
  - Compensation amount displayed

2. **Arrival**: GPS verifies worker is at Hub location:

  - Geofencing confirms physical presence
  - Adaptive MFA may trigger if outside usual zone

3. **QR Verification**: Worker scans dynamic, encrypted QR code on package:

  - QR code contains: Bundle ID, verification token, chain-of-custody data
  - Scan verifies: Worker identity, task assignment, package integrity
  - Encrypted to prevent tampering

4. **Chain-of-Custody**: Escrow Manager (Module 16) triggers micro-payment:

  - Immediate payment to worker's wallet upon successful scan
  - Payment amount based on leg completed
  - Transaction recorded in blockchain/ledger for audit trail

5. **Status Update**: System automatically updates:

  - Package status: "In transit"
  - Time-Chain Resolver recalculates timeline
  - Customer receives real-time update
  - Next leg automatically assigned if applicable

### 3.3 Communication

**Flow: Multi-Party Chat**

1. Hub participates in Support Hub conversations
2. Can communicate with:

  - Customer (delivery updates)
  - Vendors (coordination)
  - Gig workers (pickup instructions)
  - AI orchestrator (status updates)

---

## 4. Gig Worker Persona

### 4.1 Worker Registration & Onboarding

**Flow: Gig Worker Registration**

1. Worker downloads mobile app
2. Registers account:

  - Personal information
  - Vehicle details
  - Service area
  - Availability schedule

3. Completes verification:

  - Identity verification
  - Background check (if required)
  - Vehicle insurance

4. Sets up payment account
5. Completes onboarding

### 4.2 Task Acceptance & Execution

**Flow: Receiving Delivery Task**

1. Worker receives task notification:

  - Via mobile app
  - Via push notification

2. Views task details:

  - Pickup location
  - Delivery destination
  - Items to transport
  - Deadline
  - Compensation

3. Worker accepts or declines
4. If accepts: Task added to queue

**Flow: Task Execution**

1. Worker navigates to pickup location
2. Scans QR code for verification:

  - Verifies identity
  - Verifies bundle integrity
  - Confirms pickup

3. Picks up items
4. Updates status: "In transit"
5. Navigates to delivery location
6. Delivers to customer
7. Confirms delivery:

  - Customer signature (if required)
  - Photo confirmation

8. Task marked complete
9. Payment released to escrow

**Flow: Multi-Leg Delivery**

1. Worker receives multi-leg task:

  - Leg 1: Pickup from Vendor A → Hub
  - Leg 2: Pickup from Hub → Customer

2. Completes Leg 1:

  - Delivers to Hub
  - Confirms delivery

3. System automatically assigns Leg 2
4. Worker completes Leg 2
5. Both legs verified
6. Full payment released

### 4.3 Mobile Authentication

**Flow: Quick-Action Biometrics**

1. Worker opens mobile app
2. Adaptive MFA triggers:

  - If in usual operating zone: Biometric only
  - If outside usual zone: Biometric + PIN

3. Worker authenticates
4. Access granted

**Flow: QR-Handshake Authentication**

1. Worker arrives at location
2. Scans dynamic QR code
3. QR code verifies:

  - Worker identity
  - Task assignment
  - Location match

4. Access granted to task details

---

## 5. Admin Persona

### 5.1 Superadmin Flows

**Flow: Superadmin Login**

1. Superadmin attempts login
2. Hardware-bound security required:

  - Physical security key (YubiKey)
  - Biometric authentication

3. Access granted to Superadmin dashboard

**Flow: Global Fee Configuration**

1. Superadmin accesses fee settings
2. Configures:

  - Platform commission rates
  - Fee spreads by region
  - Fee spreads by service type

3. Updates apply globally
4. Partners notified of changes

**Flow: Protocol Settings Management**

1. Superadmin monitors protocol health:

  - UCP/ACP connection status
  - Real-time 404/500 error rates
  - Manifest validation issues

2. Adjusts protocol settings:

  - Timeout values
  - Retry logic
  - Cache TTL

3. Views protocol monitoring dashboard

### 5.2 Operations Admin Flows

**Flow: Just-In-Time Privileged Access**

1. Ops Admin requests intervention access
2. Specifies:

  - Bundle ID or region
  - Reason for access
  - Duration (e.g., 2 hours)

3. Access granted temporarily
4. Access automatically revoked after duration

**Flow: Active Time-Chain Intervention**

1. Ops Admin identifies issue in active bundle
2. Requests intervention access
3. Views Time-Chain details:

  - All legs of journey
  - Current status
  - Blockers or delays

4. Takes action:

  - Swaps vendors
  - Adjusts timeline
  - Triggers re-sourcing (Module 6)

5. System recalculates Time-Chain
6. All parties notified

**Flow: Human Intervention Flow - SLA Breach (Gemini's "Air Traffic Control")**

1. **Alert**: Time-Chain Resolver (Module 5) flags SLA breach:

  - Delivery is 20 minutes late
  - System detects deviation from calculated timeline
  - Alert sent to Ops Admin dashboard
  - Severity level: "High" (customer impact imminent)

2. **Intervention**: Admin logs in with JIT privileged access:

  - Sees "Shadow View" of entire conversation:
  - What AI agent proposed
  - What customer sees
  - Current status of all legs
  - Views Time-Chain visualization:
  - All legs, current locations, delays
  - Identifies bottleneck (e.g., slow courier)

3. **Manual Swap**: Admin takes action:

  - Swaps delivery partner to "Hot-Shot" courier:
  - Selects alternative courier from available pool
  - One-click swap action
  - System automatically:
  - Cancels original courier task
  - Assigns to new courier
  - Updates Time-Chain
  - Notifies all parties

4. **Apology Credit**: Admin applies compensation:

  - One-click "Apology Credit" action
  - $20 credit applied to user's account
  - Credit appears in user dashboard immediately
  - Can be used on next order or refunded

5. **Resolution**: System updates:

  - New courier en route
  - Updated ETA calculated
  - Customer receives update: "We've upgraded your delivery to ensure on-time arrival"
  - Status Narrator sends empathetic message

**Flow: Shadow View (Log in as Agent)**

1. Ops Admin enables "Shadow View"
2. Sees exactly what AI agent sees:

  - Intent resolution
  - Product discovery results
  - Time-Chain calculations
  - Proposed solutions

3. Helps debug broken Time-Chains
4. Identifies AI reasoning issues

**Flow: Regional Partner Health Management**

1. Ops Admin views regional dashboard
2. Monitors partner metrics:

  - Order completion rates
  - Customer satisfaction
  - Response times
  - Capacity utilization

3. Identifies underperforming partners
4. Takes action:

  - Sends notifications
  - Adjusts ranking weights
  - Suspends if necessary

### 5.3 Curation & Merchandising Admin Flows

**Flow: Creating Curated Bundle**

1. Admin opens Bundle Builder (Module 20)
2. Drag-and-drop interface:

  - Selects vendors
  - Sequences components
  - Sets bundle metadata

3. Configures pricing:

  - Bundle-level pricing
  - Can differ from sum of parts

4. Sets visibility mode:

  - Transparent
  - Concierge
  - Hybrid

5. Previews bundle
6. Publishes bundle

**Flow: White Glove "Concierge" Curation Flow (Gemini's "Orchestration & Oversight" Journey)**

1. **Bundle Creation**: Admin uses Bundle Builder to create premium experience:

  - Links "Nike Cap" (Product from Premium Registry) with "Local Tailor" (Service)
  - Defines customization workflow (cap → tailor for embroidery → delivery)
  - Sets bundle metadata: "The Custom Cap Experience"

2. **Visibility Toggle**: Admin sets visibility to "Concierge Mode":

  - Hides individual partner names (Nike, Tailor, Delivery Service)
  - Shows only: "The Custom Cap Experience" + total price
  - Maintains premium, white-glove feel
  - User sees curated experience, not vendor complexity

3. **Promotion**: Admin applies "Boost" to bundle:

  - Sets promotion type: "Sponsored" or "Featured"
  - Applies regional targeting: Austin region specifically
  - Adjusts boost weight for higher ranking
  - Bundle appears prominently in search results for Austin users

4. **Agent Discovery**: Bundle becomes discoverable:

  - AI agents querying for Austin users see this bundle first
  - Featured in "White Glove" category
  - Ready for Intent-to-Bundle Discovery Flow

**Flow: Promotion Management**

1. Admin opens Promotion Dashboard
2. Manages partner promotions:

  - Sets sponsored status
  - Adjusts boost weights
  - Schedules featured periods

3. Views promotion calendar
4. Monitors promotion performance

**Flow: Ranking Algorithm Configuration**

1. Admin opens Ranking Configuration
2. Adjusts algorithm weights:

  - Relevance weight (default 0.4)
  - Boost weight (default 0.3)
  - Quality weight (default 0.2)
  - Margin weight (default 0.1)

3. Views real-time ranking preview
4. Sets up A/B testing

### 5.4 Partner Simulator Admin Flows (Module 25 - MVP Critical)

**Flow: Creating Simulated Partner for Live Demo**

1. Admin opens Partner Simulator Dashboard (Module 25)
2. Clicks "Create New Partner"
3. Fills in partner details:
   - Partner name (e.g., "Flower Shop A")
   - Business type (e.g., "florist")
   - Location (lat/lng or address)
   - Communication channel (WhatsApp, SMS, API)
   - Channel identifier (phone number or endpoint)
   - Trust score and reliability metrics
   - Business hours

4. Adds products to partner catalog:
   - Product name (e.g., "Red Flowers")
   - Description and price
   - Inventory count
   - Availability rules (always available, conditional, out of stock)
   - Product images

5. Configures response scenarios:
   - **Automated Response**: Select scenario type
     - "Rejection" - Always says "No" to specific requests
     - "Product Unavailable" - Specific products always out of stock
     - "Slow Response" - Configurable delay
     - "Counter-Offer" - Offers alternatives
   - **Manual Response**: Queue requests for admin to respond
   - **Conditional Logic**: IF/THEN rules for complex scenarios

6. Saves partner configuration
7. Partner appears in Scout Engine (Module 1) search results
8. Partner ready for testing/demo

**Flow: Quick Setup for Live Demo of Autonomous Recovery**

1. Admin opens Partner Simulator Dashboard
2. Clicks "Live Demo Setup" button
3. System automatically creates two partners:
   - **Partner A**: "Flower Shop A"
     - Products: Only "Red Flowers"
     - Response: Automated rejection for "pink flowers" requests
     - Message: "No, we don't have pink flowers available"
   - **Partner B**: "Flower Shop B"
     - Products: "Pink Flowers"
     - Response: Automated acceptance for all requests
     - Message: "Yes, I have pink flowers available!"

4. Admin reviews and confirms setup
5. Demo ready - partners appear in system
6. Admin can now run Live Demo:
   - User requests "pink flowers instead of red"
   - Partner A automatically rejects
   - System triggers Autonomous Recovery (Module 6)
   - System finds Partner B
   - Recovery completes automatically

**Flow: Managing Simulated Partner Products**

1. Admin selects simulated partner from dashboard
2. Opens "Product Manager" tab
3. Views current product catalog
4. Can add new products:
   - Product name, description, price
   - Inventory count (or unlimited)
   - Availability rules
   - Product images
   - Capability tags

5. Can edit existing products:
   - Update pricing
   - Change inventory
   - Modify availability rules
   - Update descriptions

6. Can delete products
7. Changes reflect immediately in Scout Engine (Module 1)

**Flow: Configuring Automated Responses**

1. Admin selects simulated partner
2. Opens "Response Configuration" tab
3. Creates new response scenario:
   - **Scenario Type**: Select from predefined (rejection, unavailable, slow, counter-offer) or create custom
   - **Trigger Conditions**: Define when scenario activates
     - Product-based: "If product contains 'flowers'"
     - Request type: "If change_request"
     - Time-based: "If after 5 PM"
     - Order value: "If order > $500"
     - Combination: Multiple triggers with AND/OR logic
   - **Response Type**: Automated or Manual
   - **Automated Response**: Configure response template
     - Message template with variable substitution
     - Accept/Reject logic
     - Counter-offer alternatives
     - Response delay (seconds, minutes, hours)
   - **Randomization**: Add randomness (e.g., 70% accept, 30% reject)

4. Saves scenario
5. Scenario activates when trigger conditions met

**Flow: Manual Response Queue Management**

1. Admin opens "Manual Response Queue" dashboard
2. Views pending requests from simulated partners:
   - Partner name
   - Request type (product change, order request, etc.)
   - Request details
   - Time received
   - Status (pending, assigned, responded)

3. Can filter by:
   - Partner
   - Request type
   - Status
   - Time range

4. Selects request to respond:
   - Views full request details
   - Sees conversation context
   - Can use response templates
   - Types or selects response

5. Sends response:
   - Response sent via Omnichannel Broker (Module 24)
   - Updates queue status
   - Response logged in history

6. Can assign requests to other admins
7. Can bulk respond to multiple requests

**Flow: Scenario Builder - Custom Scenarios**

1. Admin opens "Scenario Builder" interface
2. Creates custom scenario:
   - **Visual Builder**: Drag-and-drop interface
   - **IF/THEN Logic**: Complex conditional responses
     - Example: "IF order value > $500 AND product type = 'flowers' THEN reject"
   - **Multi-Step Scenarios**: Chain multiple responses
     - Step 1: Initial response
     - Step 2: Follow-up based on user action
   - **Variable Substitution**: Use request data in responses
     - Example: "Sorry, I don't have {requested_item} available"
   - **Randomization**: Add randomness to responses

3. Tests scenario:
   - Preview how scenario will respond
   - Test with sample requests
   - Validate logic

4. Assigns scenario to partner(s)
5. Activates scenario

**Flow: Testing Autonomous Recovery with Simulated Partners**

1. Admin sets up test scenario:
   - Creates Partner A with limited products (e.g., only "red flowers")
   - Configures rejection scenario for "pink flowers"
   - Creates Partner B with alternative products (e.g., "pink flowers")
   - Configures acceptance scenario

2. Creates test order:
   - User places order with "red flowers" from Partner A
   - Order confirmed and placed

3. Triggers change request:
   - User requests "pink flowers instead of red"
   - System sends request to Partner A via Omnichannel Broker (Module 24)

4. Observes autonomous recovery:
   - Partner A automatically rejects
   - System triggers Autonomous Recovery (Module 6)
   - System finds Partner B
   - System cancels Partner A order
   - System creates Partner B order
   - System recalculates timeline
   - System notifies user

5. Validates recovery:
   - Checks that order updated correctly
   - Verifies timeline recalculation
   - Confirms user notification sent
   - Reviews recovery logs

6. Can repeat test with different scenarios

**Flow: Monitoring Simulated Partner Activity**

1. Admin opens Partner Simulator Dashboard
2. Views activity metrics:
   - Number of requests received
   - Response times
   - Acceptance/rejection rates
   - Manual vs automated responses
   - Scenario trigger frequency

3. Views request history:
   - All requests and responses
   - Timeline of interactions
   - Response patterns

4. Exports data for analysis
5. Uses insights to improve scenarios

**Flow: Visibility Mode Toggle**

1. Admin selects bundle
2. Toggles visibility mode:

  - Transparent: Show all vendors
  - Concierge: Show only bundle name
  - Hybrid: Selective transparency

3. Previews each mode
4. Applies changes
5. Changes reflect immediately in customer UI

**Flow: The Curation Picker - Visual Bundle Creation (Module 22)**

1. Admin or verified Partner opens Curation Picker
2. Views Visual Bundle Canvas:

  - Empty canvas with product picker sidebar
  - Search bar for semantic product search

3. Searches for products:

  - Types query: "Designer Suit"
  - System searches via pgvector semantic search
  - Results show products from Scout database

4. Drags products to canvas:

  - Drags "Designer Suit" from Retailer A
  - Drags "On-site Tailoring" from Local Artisan B
  - Drags "Priority Courier" from Delivery Service C

5. Arranges sequence:

  - Sets order: Suit → Tailoring → Delivery
  - Connects items with visual lines
  - Sets timing dependencies

6. Margin Optimizer shows real-time calculation:

  - Individual item commissions (from Module 21)
  - Platform orchestration fee
  - Total margin percentage
  - Suggested pricing

7. Locks partners (if needed):

  - Selects "Priority Courier" item
  - Toggles "Lock Partner" to Hard Lock
  - Enters reason: "Exclusive partnership"
  - Partner cannot be swapped even in re-sourcing

8. Validates bundle:

  - Clicks "Validate Bundle"
  - System checks:
  - Time-Chain feasibility (Module 5)
  - Inventory availability
  - Capability matching
  - Pricing validation

9. Saves bundle:

  - Saves as draft or publishes immediately
  - Bundle appears in Module 20 (Curation Engine)
  - Ready for customer discovery

**Flow: White-Glove Affiliate Workflow (Complete Journey)**

1. **Onboarding**: Partner logs in via Clerk → Registers "Limo Service" → Provides API/Manifest for real-time booking
2. **Curation**: Admin uses Curation Picker (Module 22):

  - Finds "Luxury Wine" from affiliate retailer (Module 21)
  - Pairs with partner's "Limo Service"
  - Margin Optimizer shows total commission/margin
  - Locks Limo Service partner (hard lock)

3. **Discovery**: When user asks for "VIP Wine Tour":

  - Intent Resolver (Module 4) suggests pre-curated bundle
  - Bundle includes affiliate wine + locked limo service
  - High-margin bundle prioritized in results

4. **Checkout**: Atomic Multi-Checkout (Module 15):

  - Pays wine retailer via affiliate link (Module 21 tracking)
  - Pays Limo company directly via Stripe/Azure
  - Single transaction, split payments
  - Commission tracked automatically

**Flow: Affiliate Management (Admin)**

1. Admin views affiliate dashboard:

  - List of all affiliate partners
  - Trust scores and KYC status
  - Commission rates
  - Performance metrics

2. Reviews pending KYC verifications:

  - Sees verification results
  - Approves or rejects manually if needed
  - Updates trust scores

3. Manages affiliate settings:

  - Adjusts commission rates
  - Activates/deactivates affiliates
  - Sets White Glove status

4. Views affiliate performance:

  - Click-through rates
  - Conversion rates
  - Total commissions paid
  - Top-performing affiliates

### 5.4 Omnichannel Negotiation Management (Module 24)

**Flow: Negotiation Dashboard**

1. Admin accesses Negotiation Dashboard
2. Views all active negotiations:

  - Filter by status, channel, urgency
  - See negotiations across WhatsApp, SMS, Email, API
  - Real-time updates

3. Dashboard shows:

  - Negotiation details
  - Channel used
  - Time elapsed
  - Counter-offer count
  - Escalation status

**Flow: Silent Monitoring**

1. Admin selects negotiation to monitor
2. Starts silent monitoring:

  - Views live chat without interrupting
  - Sees all messages across channels
  - Monitors sentiment and confusion

3. Admin can see:

  - User messages in Gemini/ChatGPT
  - Partner messages in WhatsApp/SMS
  - System messages
  - Sentiment analysis

4. Admin watches for issues:

  - Frustration indicators
  - Confusion signals
  - Deadlock patterns

**Flow: Intervention**

1. Admin identifies negotiation needs intervention:

  - Deadlock (3+ counter-offers)
  - Frustration detected
  - Timeout occurred
  - Time-Chain urgency

2. Admin joins conversation:

  - Takes over from AI
  - Can see full context
  - Resolves deadlock

3. Admin resolves:

  - Contacts partner directly if needed
  - Makes decision on behalf of customer
  - Updates negotiation status

4. Negotiation completes with admin assistance

**Flow: Escalation Queue Management**

1. Admin views Escalation Queue:

  - High-urgency tasks prioritized
  - Time-Chain urgency highlighted
  - Escalation reasons displayed

2. Admin assigns escalation:

  - Assigns to self or team member
  - Sets priority
  - Adds notes

3. Admin resolves escalation:

  - Intervenes in negotiation
  - Resolves issue
  - Marks as resolved
  - Adds resolution notes

### 5.5 Admin Command Center (Phase 3)

**Flow: Operational Dashboard**

1. Admin accesses Command Center (Module 18)
2. Views real-time metrics:

  - Active bundles
  - System health
  - Partner performance
  - Financial metrics

3. Filters by:

  - Region
  - Time period
  - Service type

4. Exports reports

**Flow: Dispute Resolution**

1. Admin receives dispute notification
2. Reviews case:

  - Customer complaint
  - Vendor response
  - Order history
  - Communication logs

3. Makes decision:

  - Approve refund
  - Deny claim
  - Partial resolution

4. System executes decision
5. All parties notified

---

## 6. AI Orchestrator Persona (System Flows)

### 6.0 AI Agents Chat Entry Point (MVP)

**Flow: ChatGPT/Gemini → Orchestrator → Intent + Discovery**

1. User sends message in ChatGPT or Gemini: "I want to send flowers to my mom"
2. AI agent calls Orchestrator: `POST /api/v1/chat` with `{"text": "..."}`
3. Orchestrator calls Intent Service (Module 4):
   - Resolves natural language to structured intent
   - Returns intent type, entities (e.g., flowers, recipient)
4. When intent indicates discovery, Orchestrator calls Discovery Service (Module 1):
   - Searches products by intent
   - Returns JSON-LD + Adaptive Card
5. Orchestrator returns unified response to AI agent:
   - `data`: products, intent
   - `machine_readable`: JSON-LD for LLM consumption
   - `adaptive_card`: Product cards for chat UI
6. AI agent presents results to user in chat

**Entry point**: `orchestrator-service` at `POST /api/v1/chat`

### 6.1 Intent Resolution Flow

**Flow: Processing Natural Language Intent**

1. System receives customer intent
2. Intent Resolver (Module 4) processes:

  - Extracts entities
  - Identifies requirements
  - Builds Graph of Needs

3. Queries Scout Engine for products
4. Applies ranking boost
5. Returns curated results
6. Presents to customer

### 6.2 Time-Chain Calculation Flow

**Flow: Multi-Leg Journey Optimization**

1. System receives order request
2. Time-Chain Resolver (Module 5) calculates:

  - Identifies all legs
  - Calculates travel times
  - Accounts for processing times
  - Synchronizes arrivals

3. Verifies deadline feasibility
4. If feasible: Proceeds
5. If not: Suggests alternatives

### 6.3 Autonomous Re-Sourcing Flow (MVP Critical: Live Demo)

**Flow: Live Demo of Autonomous Recovery**

1. **User Request**: Customer requests change to placed order:

  - Example: "I want pink flowers instead of red"
  - Order already placed with red flowers from Vendor A

2. **Partner Communication**: System sends change request via Omnichannel Broker (Module 24):

  - WhatsApp message to partner: "Customer requested change: Pink flowers instead of red. Can you fulfill? [Yes] [No]"

3. **Partner Rejection**: Partner rejects request:

  - Partner replies: "No, we don't have pink flowers"
  - System receives rejection via webhook

4. **Autonomous Recovery Triggers (Module 6)** - **No Human Intervention**:

  - **Step 1**: Cancel original order leg
  - Cancels red flowers order from Vendor A
  - Releases escrow (Module 16)
  - Updates order status
  - **Step 2**: Find alternative using Scout Engine (Module 1)
  - Searches for "pink flowers" from other vendors
  - Excludes Vendor A
  - Filters by price range, location, availability
  - Ranks by trust score, proximity, price similarity
  - **Step 3**: Update bundle
  - Removes red flowers leg
  - Adds pink flowers leg from Vendor B
  - Updates bundle composition
  - **Step 4**: Recalculate Time-Chain (Module 5)
  - Recalculates timeline with new vendor location
  - Checks for conflicts with other legs
  - Calculates new arrival times
  - **Step 5**: Notify user with Status Narrator (Module 14)
  - Generates status update with agent reasoning
  - Shows timeline comparison (if changed)
  - Adaptive Card: "I've found pink flowers from a different vendor. Your timeline shows a 5-minute delay. Should I proceed?"

5. **User Approval**: Customer approves:

  - User: "Yes, proceed"
  - System confirms new order
  - Updates bundle
  - Processes payment for new item

6. **Result**:

  - Order successfully updated
  - New timeline communicated
  - **No human intervention required**
  - Seamless recovery experience

**Flow: Automatic Substitution (General Case)**

1. System detects issue:

  - Item unavailable
  - Item damaged at hub
  - Vendor unable to fulfill

2. Autonomous Re-Sourcing (Module 6) triggers:

  - Re-scouts for alternatives
  - Finds local substitutes
  - Verifies compatibility

3. System automatically:

  - Updates order
  - Notifies customer
  - Adjusts Time-Chain

4. No human intervention required

### 6.4 Status Narration Flow

**Flow: Generating Human-Readable Updates**

1. System detects status change
2. Status Narrator (Module 14) processes:

  - Translates logistics data
  - Generates empathetic message
  - Example: "We found a scratch on the cap, so we're getting you a fresh one from a nearby store—still arriving today!"
  - **Extracts Agent Reasoning**: "I'm still waiting to buy the flowers because the forecast for Thursday just changed to 'Rainy'—monitoring for a clear window."

3. Sends update via:

  - Web dashboard
  - WhatsApp (if opted in)
  - Email

4. Customer receives update

### 6.5 Hybrid Response Logic Flow

**Flow: AI vs Human Escalation**

1. Customer sends message
2. Hybrid Response Logic (Module 13) evaluates:

  - Routine question? → AI responds
  - Complex issue? → Escalate to human
  - Dispute? → Human-in-the-loop
  - Physical damage? → Human-in-the-loop

3. Appropriate response channel activated
4. If human: Support agent notified
5. If AI: Automated response sent

### 6.6 Omnichannel Negotiation Flow (Module 24)

**Flow: Two-Way Negotiation Orchestration**

1. System receives negotiation request from user
2. Negotiation Orchestrator (Durable Functions) starts:

  - Creates Negotiation Object
  - Checks partner's communication preference
  - Links to user's primary AI thread

3. System sends message to partner:

  - Routes to partner's preferred channel (WhatsApp/SMS/Email/API)
  - Formats message for channel
  - Includes interactive buttons (if supported)

4. System waits for partner reply:

  - Durable Functions waits for external event
  - Timeout: 15 min (JIT) or 60 min (standard)

5. Partner replies:

  - Via WhatsApp/SMS/Email/API
  - Webhook receives reply
  - Triggers external event to orchestrator

6. System processes reply:

  - NLP re-processing (Module 4)
  - Sentiment analysis
  - Counter-offer extraction
  - Vision AI (if photo)

7. If counter-offer:

  - Enriches with metadata (Module 1)
  - Generates Adaptive Card
  - Pushes to user's AI thread
  - Updates status to "awaiting_user_approval"

8. User approves/rejects:

  - System receives approval event
  - Completes negotiation
  - Updates order

**Flow: Escalation Trigger**

1. System detects escalation trigger:

  - **Timeout**: No reply within timeout period
  - **Sentiment**: Frustration detected ("I already told you no pink!")
  - **Deadlock**: 3+ counter-offers without resolution
  - **Urgency**: Time-Chain leg < 2 hours from execution

2. System triggers escalation:

  - Creates escalation record
  - Adds to Admin Intervention Queue
  - Notifies admin dashboard
  - Pauses AI responses

3. Admin intervenes:

  - Views negotiation context
  - Joins conversation
  - Resolves issue

4. Negotiation completes with admin assistance

### 6.7 Standing Intent Orchestration Flow (Module 23)

**Flow: Durable Orchestration Execution**

1. Client Function receives standing intent request
2. Starts Durable Orchestration:

  - Creates orchestration instance
  - Returns instance ID for tracking
  - Orchestrator begins execution

3. Orchestrator coordinates workflow:

  - **Step 1**: Calls Vendor Scout Activity
  - Queries Scout Engine for products
  - Returns vendor options
  - **Step 2**: Logs progress via Status Narrator Activity
  - Writes to Progress Ledger
  - Updates user: "Found your flowers! Waiting for sunny Thursday."
  - **Step 3**: Yields (pauses) waiting for external event
  - Intent Watcher Activity checks conditions periodically
  - When condition met: Sends "IntentConditionMet" event
  - **Step 4**: If approval required, yields for "UserApproval" event
  - Waits up to timeout period
  - Based on trust level: Auto-proceeds or cancels
  - **Step 5**: Calls Atomic Checkout Activity
  - Executes purchase
  - Completes orchestration

4. **Cost Efficiency**:

  - Waiting state: $0 (orchestrator sleeps)
  - Activity execution: Pay only for seconds of execution
  - Example: 7-day wait = ~168 seconds execution = ~$0.0001

**Flow: Intent Watcher Activity**

1. Timer-triggered function runs periodically (every hour)
2. Checks all active standing intents:

  - Weather conditions (API call)
  - Calendar conditions (day of week, date)
  - Inventory conditions (stock availability)
  - Price conditions (price drops)

3. When condition met:

  - Sends external event to orchestrator instance
  - Orchestrator resumes execution

4. Updates condition check log

**Flow: External Event Handling**

1. External event received (UserApproval, IntentConditionMet, etc.)
2. Event stored in external_events table
3. Durable Functions processes event:

  - Routes to correct orchestration instance
  - Orchestrator resumes from checkpoint
  - Continues workflow

4. Progress logged to Progress Ledger

---

## Cross-Persona Flows

### Multi-Party Communication Flow

**Flow: Unified Conversation Thread**

1. Any participant (Customer, Vendor, Hub, Worker) sends message
2. Message appears in Support Hub (Module 12)
3. All participants see message in real-time:

  - Web chat
  - WhatsApp (if opted in)

4. Message routing:

  - Product question → Relevant vendor
  - Delivery question → Hub or worker
  - General → AI or support

5. All responses visible to all parties

### Order Lifecycle Flow (All Personas)

**Flow: Complete Order Journey**

1. **Customer**: Places order via intent
2. **AI Orchestrator**: Resolves intent, discovers products, calculates Time-Chain
3. **Vendors**: Receive order, process, update status
4. **Hub**: Receives items, assembles, coordinates
5. **Gig Worker**: Picks up, delivers
6. **AI Orchestrator**: Tracks progress, sends updates
7. **Customer**: Receives delivery, confirms
8. **Escrow Manager**: Releases payments to all parties
9. **All Parties**: Can communicate via Support Hub throughout

---

## Flow Categories Summary

### Authentication Flows

- Customer: Passkey, Social Login, Agentic Handoff
- Partner: Business Verification, Skill-Based RBAC
- Hub: Capability-Based Access
- Gig Worker: QR-Handshake, Adaptive MFA
- Admin: Hardware-Bound Security, JIT Access

### Order Management Flows

- Customer: Intent → Discovery → Customization → Checkout → Tracking
- Partner: Order Receipt → Processing → Status Updates → Payment
- Hub: Task Receipt → Assembly → Coordination → Handoff
- Gig Worker: Task Acceptance → Pickup → Delivery → Confirmation

### Communication Flows

- All: Multi-Party Support Hub
- Customer: WhatsApp Integration
- All: Real-time Chat Features

### Financial Flows

- Customer: Atomic Multi-Checkout
- All: Escrow Management
- Partner/Hub/Worker: Payment Receipt

### Administrative Flows

- Superadmin: Global Configuration
- Ops Admin: Intervention, Monitoring
- All Admins: Curation, Promotion, Visibility Management

### System Automation Flows

- Intent Resolution
- Time-Chain Calculation
- Autonomous Re-Sourcing
- Status Narration
- Hybrid Response Logic
- Standing Intent Orchestration (Module 23)
- Omnichannel Negotiation (Module 24)
