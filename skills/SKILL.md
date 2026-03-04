---
name: voice-ai-prompt-engineer
description: Build, structure, and optimize prompts for VAPI voice agents and chat assistants. Use this skill when creating a new assistant prompt, updating an existing one, improving conversation flows, fixing unnatural responses, or optimizing a prompt for caching. Applies to all VAPI agent types including healthcare, HVAC, beauty, water delivery, sales, and inbound/outbound voice agents.
---

This skill defines how to write, structure, and optimize prompts for voice AI assistants and chat agents built on VAPI. Apply it as the reference standard when building or optimizing any voice or chat agent prompt. It covers structure, formatting conventions, prompt caching optimization, and best practices drawn from real-world voice agent development.

---

## When to Apply This Skill

Apply this skill automatically whenever the user:
- Creates a new VAPI voice agent or chat assistant prompt
- Updates or optimizes an existing assistant prompt
- Reports unnatural responses, wrong routing, or broken flows
- Sets up a new assistant in the VAPI dashboard
- Asks to improve response quality, latency, or cost efficiency
- Mentions words like "prompt", "agent", "voice agent", "system prompt", "VAPI", "chat widget"

---

## The Process

Follow this sequence for every prompt build or update:

1. **Design** — Craft the initial prompt with clear structure, business logic, and conversation flows.
2. **Cache Optimize** — Restructure so static content is at the top and all dynamic variables are at the bottom.
3. **Test** — Run through real and simulated calls. Evaluate whether responses match expectations.
4. **Refine** — Adjust wording, add missing logic, remove redundancy, fix edge cases.
5. **Repeat** — Iterate until the success rate meets the target. Each cycle should produce measurable improvement.

Success rate = percentage of calls the agent handles end-to-end without needing a human. Track this across iterations.

---

## Prompt Structure

Use a two-tier hierarchy to organize all prompts:

- **XML tags** for top-level sections (e.g., `<Identity>`, `<Business Details>`, `<Call Paths>`)
- **Bracketed headers** for sub-sections within those containers (e.g., `[Hours of Operation]`, `[Style]`)

This creates clear separation of concerns — the agent locates and processes each section independently without instructions bleeding into one another.

### Required Sections

| Section | Purpose | Cache Position |
|---------|---------|----------------|
| `<Identity>` | Agent persona, name, role, identity handling | STATIC — top |
| `<Business Details>` | Location, phone, hours, services, rules | STATIC — top |
| `<Language Settings>` | Supported languages and matching behavior | STATIC — top |
| `<Context and Rules>` | Goals, style, guidelines, error handling | STATIC — top |
| `<Call Paths>` or `<Chat Paths>` | Conversation flows by intent (A, B, C, D) | STATIC — top |
| `<Transfer Rules>` | When and how to transfer, override logic | STATIC — top |
| `<Call Closing>` or `<Chat Closing>` | How to end the conversation cleanly | STATIC — top |
| `<Current Time>` | ⚠️ Dynamic timestamp — ALWAYS last | DYNAMIC — bottom |
| `<Prospect Data>` | ⚠️ All {{variables}} — ALWAYS last | DYNAMIC — bottom |

### Standard Skeleton

```
<!-- ======= STATIC SECTION (FULLY CACHED) ======= -->

<Identity>
You are [Name], a [tone] digital assistant for [Business Name].

[AI Identity Handling]
- If asked who or what you are, say: "I'm [Name], a digital assistant for [Business]. I can help [primary capabilities]."
</Identity>

<Business Details>
[Location & Phone]
[Address]
Phone: [number spelled out digit by digit]

[Hours of Operation]
Monday: [hours spelled out in words]
...

[Services]
- [List of offered services]
- [Explicitly excluded services]
</Business Details>

<Language Settings>
[Language matching rules]
</Language Settings>

<Context and Rules>
[Context]
[Style]
[Response Guidelines]
[After-Hours Rules]
[Error Handling]
</Context and Rules>

<Call Paths>
A) CALL START
[Caller Intent]

B) TOPIC-SPECIFIC FLOWS

C) APPOINTMENT BOOKING

D) MESSAGE FLOW
</Call Paths>

<Transfer Rules>
[Business Hours Transfers]
[After-Hours Transfers]
</Transfer Rules>

<Call Closing>
[End-of-call behavior]
</Call Closing>

<!-- ======= DYNAMIC SECTION - DO NOT MOVE ABOVE THIS LINE ======= -->

<Current Time>
The current date and time is: {{"now" | date: "%A, %B %d, %Y at %I:%M %p", "America/Los_Angeles"}}
Current year: {{"now" | date: "%Y", "America/Los_Angeles"}}
</Current Time>

<Prospect Data>
- Name: {{customer.name}} — use first name only
- Email: {{customer.email}} — confirm before booking
- Any other {{variables}} go here
</Prospect Data>
```

---

## Prompt Caching Optimization (OpenAI + VAPI)

### Why It Matters

OpenAI automatically caches the beginning (prefix) of prompts over 1024 tokens. When the same prefix is reused, OpenAI routes the request to the same server — resulting in up to 80% lower latency and 50% cheaper input token costs. This directly improves response speed in chat widgets and reduces client costs at scale.

### The Golden Rule

```
STATIC content (never changes per user) → TOP of prompt → CACHED ✅
DYNAMIC content (changes per user/session) → BOTTOM of prompt → NEVER CACHED ⚠️
```

Never place any `{{variable}}` or LiquidJS expression anywhere in the static section.

### What Goes Where

**STATIC — always at top, fully cached:**
- Identity, persona, tone
- Business details (company info, offers, contacts)
- Context and rules (goals, style, guidelines)
- Conversation flows (Call Paths / Chat Paths)
- Transfer rules
- Knowledge base references
- Objection handling rules
- Error handling

**DYNAMIC — always at bottom, never cached:**
- Current time → `{{"now" | date: ...}}`
- User/prospect data → `{{customer.name}}`, `{{customer.email}}`
- CRM IDs → `{{hubspot_contact_id}}`
- Any session-specific `{{variable}}`

### What Breaks Caching

- Placing `{{"now" | date}}` anywhere above the dynamic divider
- Putting `{{customer.name}}` inside `<Identity>` block
- Any `{{variable}}` appearing in the static section
- Changing the Prompt Cache Key without bumping the version number
- Modifying the beginning of the prompt without updating the cache key version

### VAPI Dashboard Settings

| Setting | Voice Agent | Chat Agent |
|---|---|---|
| Max Tokens | 150–250 | 500–800 |
| Temperature | 0.1–0.3 | 0.1 |
| Prompt Cache Retention | 24h | 24h |
| Prompt Cache Key | client-agent-v1 | client-agent-v1 |

Always use **24h** retention — the default "In Memory" only lasts 5–10 minutes and loses the cache between conversations.

### Cache Key Naming Convention

Format: `{client}-{agentname}-v{version}`

Examples:
- `merit-ava-v1`
- `scval-hvac-v1`
- `fontis-water-v1`
- `onemed-coordinator-v1`
- `browlady-pmu-v1`

Only bump the version number (v1 → v2) when the prompt content actually changes. Never change the key mid-deployment without a corresponding prompt update.

---

## Core Principles

### 1. One Topic at a Time

Voice conversations are linear. Address one question, collect one piece of information, or handle one routing decision before moving on. Never stack multiple questions in a single turn.

### 2. Control Response Timing

Use `~wait for user response~` markers after every question or prompt that requires input. This prevents the agent from racing ahead before the caller has answered.

```
1. Ask: "What time were you thinking of coming in?"
   ~wait for user response~
2. Confirm their choice before proceeding.
```

### 3. Break Down Complex Tasks

Use numbered steps with conditional branching. Each step should clearly state what to say, what to listen for, and where to route based on the response.

```
1. Ask: "Would you like to schedule an appointment or speak with someone?"
   ~wait for user response~
   → If scheduling: Proceed to 'Appointment Booking'
   → If live person: Proceed to 'Transfer Flow'
```

### 4. Use Arrow Notation for Routing

Use `→` for all routing decisions within conversation flows:

```
→ If they agree: Proceed to 'Appointment Booking'
→ If they decline: Proceed to <Call Closing>
```

### 5. Silent Tool Usage

When the agent triggers a tool or transfer, it executes silently — no announcement. Never say "I'm going to transfer you now" or "I'm calling a function." Just do it.

### 6. Never Narrate Internal Actions

The caller should never hear the words "function," "tool," "API," or any backend operation name.

### 7. Spell Out Numbers for Natural Speech

All numbers must be written as spoken words to prevent robotic TTS output:

- Prices: "forty four ninety nine" not "$44.99"
- Times: "Four Thirty PM" not "4:30 PM"
- Phone numbers: digit-by-digit — "five seven five, six one three, eight zero four two"
- Dates: "January Twenty Four" — never include years unless explicitly needed
- Vehicle models: "Ford F One Fifty" not "Ford F-150"

### 8. Progressive Disclosure

Don't volunteer information the caller hasn't asked for. Don't announce hours unless asked. Don't mention the store is closed unless directly relevant to the caller's request.

### 9. Accept and Reuse Partial Information

If the caller provides their name, time preference, or other details during natural conversation, capture and reuse it. Never re-ask for something already given.

### 10. Preserve the Caller's Words

Do not modify, correct, or reinterpret caller input. Pass their exact words into any tool call. If they say "two-ish," work with "two-ish."

---

## Section-Specific Guidelines

### Identity

Keep tight. Define the agent's name, tone, and role in one to two sentences. Include an `[AI Identity Handling]` sub-section with the exact scripted response for "who are you?" or "are you a robot?" questions. Never place any `{{variables}}` here — move them to `<Prospect Data>` at the bottom.

```
<Identity>
You are Jordan, a friendly, upbeat, and professional digital assistant for Big O Tires – Taos, New Mexico.

[AI Identity Handling]
- If asked who or what you are, say: "I'm Jordan, a digital assistant for Big O Tires. I can help schedule a time for you to come in or take a message for the team."
</Identity>
```

### Business Details

Organize with bracketed sub-sections. Place behavioral rules directly alongside the data they apply to. Spell out all hours in spoken-word format. List services offered AND services explicitly not offered to prevent the agent from improvising.

### Context and Rules

The behavioral core of the prompt. Use bracketed sub-sections:

- **[Context]** — The primary goal of every call
- **[Style]** — Tone, pacing, and interaction style
- **[Response Guidelines]** — Formatting requirements, prohibited language, guardrails
- **[After-Hours Rules]** — Time-conditional behavior that overrides default flows
- **[Error Handling]** — Fallback behavior for unclear input, tool failures, dead ends

### Call Paths / Chat Paths

Use lettered sections (A, B, C, D) for distinct flows. Use numbered steps for sequential logic and `→` arrows for conditional routing.

Start every prompt with a `[Caller Intent]` or `[Chat Intent]` routing block:

```
A) CALL START
[Caller Intent]
Listen fully without interrupting, then route based on intent:
- If caller wants to schedule: Proceed to 'Appointment Booking'
- If caller asks about pricing: Proceed to 'Pricing Questions'
- If caller requests a real person: Proceed to 'Transfer Flow'
- If caller wants to leave a message: Proceed to 'Message Flow'
```

Each sub-flow must be self-contained with its own entry point, steps, and exit routing.

### Transfer Rules

Dedicate a standalone section. Define:

- **Override conditions** — When to transfer immediately regardless of current flow
- **Business hours behavior** — Which tool to trigger
- **After-hours behavior** — What to say instead, where to route next
- **Post-booking exception** — Never transfer immediately after booking unless caller explicitly asks

### Call Closing / Chat Closing

Keep minimal. Its job is to trigger the end function when conversation is complete.

```
<Call Closing>
- Use this flow when the caller's request has been fulfilled.
- NEVER trigger the endCall function during the middle of the call.
→ When the call has been completed: trigger the endCall function
</Call Closing>
```

---

## Chat Agent Differences (VAPI Chat Widget)

When building for the VAPI chat widget instead of voice calls, apply these adjustments:

- Replace `<Call Paths>` with `<Chat Paths>`
- Replace `<Call Closing>` with `<Chat Closing>`
- Replace `<Transfer Rules>` with escalation or handoff logic
- **Do NOT spell out numbers** — chat users read text, not TTS
- **Allow fuller responses** — chat users can read at their own pace
- **Skip filler phrases** — "Got it." "That makes sense." are fine in chat but remove voice-specific phrases like "on the call," "speaking with," "recording"
- **Multiple questions per turn are acceptable** in chat (unlike voice where one question per turn is strict)
- Use `{{transport.conversationType}}` in the prompt if the same assistant handles both voice and chat

---

## Style and Tone

### Do
- Use warm, natural language
- Use contractions ("we're," "you'll," "I've")
- Use the caller's name once after capturing it
- Restart cleanly if interrupted
- Keep responses short and conversational

### Avoid
- Filler words: "perfect," "awesome," "great question"
- Corporate jargon or overly formal language
- Narrating internal actions
- Volunteering unrequested information
- Stacking multiple questions in one turn (voice only)

---

## Language Support

If the agent supports multiple languages, include a `<Language Settings>` section:

- Automatically detect and match the caller's language
- Switch immediately when language preference is indicated
- Stay in the matched language unless the caller explicitly asks to switch back
- Never ask for language preference — just match it

---

## Voice Realism (Optional)

For agents needing a more human-like quality, add sparingly:

- **Hesitations:** "I was, uh, checking on that for you"
- **Pauses:** "Let me... pull that up for you"
- **Emotional emphasis:** "That's great!"

Use only in conversational agents. Avoid in transactional or professional contexts.

---

## Testing Checklist

After building or optimizing any prompt, verify:

**Structure**
- [ ] All conversation paths have clear entry and exit points
- [ ] Every question includes a `~wait for user response~` marker (voice)
- [ ] Static and dynamic sections are correctly separated
- [ ] Dynamic divider comment is present

**Caching**
- [ ] No `{{variables}}` appear in the static section
- [ ] No LiquidJS date expressions appear above the dynamic divider
- [ ] `<Current Time>` is at the very bottom
- [ ] `<Prospect Data>` is at the very bottom
- [ ] Prompt Cache Key is set in VAPI dashboard
- [ ] Cache Retention is set to 24h
- [ ] Cache Key follows `client-agent-v1` naming convention
- [ ] Max Tokens is appropriate for agent type (150–250 voice, 500–800 chat)

**Behavior**
- [ ] After-hours logic correctly restricts transfers
- [ ] Tool names are never spoken aloud
- [ ] Numbers, dates, times, prices are spelled out (voice only)
- [ ] Agent doesn't re-ask for information already provided
- [ ] Transfer override rules fire correctly
- [ ] Edge cases handled (past-time booking, ambiguous times, closing-time requests)
- [ ] Agent doesn't prematurely end the call
- [ ] Language switching works (if applicable)

---

## Common Issues and Fixes

**Responses feel like a phone call in chat mode?**
The prompt is written for voice. Remove number-spelling rules, allow fuller responses, remove voice-specific language like "on the call." Add `{{transport.conversationType}}` channel awareness.

**Numbers sound robotic?**
Spell out all numbers in spoken-word format. "Forty four ninety nine" not "$44.99."

**Agent sounds too corporate?**
Add personality to `<Identity>` and style constraints to `[Style]`. Use contractions, avoid jargon, keep responses short.

**Agent volunteers too much information?**
Add progressive disclosure rules to `[Response Guidelines]`.

**Agent gets stuck in loops?**
Ensure every conditional branch has an explicit exit path. Add fallback: "If a clear answer cannot be obtained after two attempts, proceed to 'Message Flow'."

**Transfers happen after hours?**
Move the dynamic time variable to the bottom. Add explicit "NEVER transfer after hours" rules in `<Transfer Rules>`.

**Cache not hitting?**
Check that no `{{variable}}` or `{{"now"}}` appears in the static section. Verify the Prompt Cache Key is unchanged and Cache Retention is set to 24h in the VAPI dashboard.

**Name being auto-corrected or corrupted?**
Add a `[Name Handling]` rule inside `<Identity>`: "Always use the name exactly as provided in `{{customer.name}}`. Never auto-correct, phonetically adjust, or alter any spelling." Also consider switching the VAPI model from a voice-optimized model to GPT-4o or Claude for text-native processing.
