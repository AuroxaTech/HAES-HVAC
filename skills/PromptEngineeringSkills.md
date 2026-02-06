# Prompt Engineering Skills (Portable)

Use this doc when editing **system prompts** or **knowledge base** content for AI assistants (e.g. Vapi, voice agents, chatbots). Copy this file into any project or reference it so prompts stay minimal and effective.

---

## 1. Keep the system prompt minimal (Target: ~800 tokens max)

- Put only **non-negotiable rules** and **role/tone** in the main system prompt.
- Long procedures, FAQs, and policies belong in the **Knowledge Base** (or tool descriptions), not in the prompt.
- A short prompt performs better: less dilution, less truncation risk, more capacity for tools and KB at runtime.
- **Target:** Aim for 600-800 tokens maximum for voice agents.

---

## 2. Critical rules first

- Place the most important rules at the **top** of the prompt (e.g. STOP rule, prohibited phrases, safety).
- Use **short bullets**, one idea per rule. Avoid long paragraphs.
- If the model must never do X, state it clearly and early.

---

## 3. Prefer KB for SOPs and reference content

- **System prompt:** Say *when* to use the KB (e.g. "Search the knowledge base for policies, procedures, and FAQs; follow the retrieved content").
- **Knowledge Base:** Hold full SOPs, step-by-step flows, policies, and long reference text.
- Do **not** duplicate KB content in the prompt. Reference it; don't repeat it.

---

## 4. Tool-centric behavior

- The prompt should define **when** to use which tool and **tone**; detailed "how" can live in **tool names/descriptions** and the KB.
- Keep tool-usage instructions concise. Let tool schemas and KB carry procedure detail.

---

## 5. Avoid bloat when adding behavior

When adding new behavior (e.g. a new question, flow, or rule):

1. **First:** Can it live in the KB? If yes, add it there and add one short line in the prompt (e.g. "Before closing, ask how they heard about us and tag in CRM").
2. **Second:** Can it live in a tool description? If yes, update the tool schema; prompt only says when to call the tool.
3. **Last:** Only if it's a critical, non-negotiable rule that must never be forgotten, add a short bullet to the system prompt.

---

## 6. Few-shot examples

- Use 1–2 examples only where they materially change behavior.
- Keep examples short. In voice, long examples consume tokens and can hurt consistency.

---

## 6.5. Voice-specific guidance

- **Keep responses brief:** Under 3 sentences unless customer asks for detail. Voice loses attention faster than text.
- **Speak naturally:** Use contractions ("I'll" not "I will"), casual tone, avoid robotic phrases.
- **Handle interruptions gracefully:** If customer interrupts, acknowledge and adjust to their new topic.
- **Confirm before finalizing:** Repeat key details back (name, phone, date) before completing actions.

---

## 7. Checklist before shipping prompt changes

- [ ] No long procedures pasted into the prompt; they're in KB or tool descriptions.
- [ ] Critical rules (safety, prohibited phrases, STOP rule) are at the top and concise.
- [ ] One idea per bullet; no dense paragraphs.
- [ ] New behavior added via KB or tool first; prompt only references or gives a single short instruction.
- [ ] Prompt is under 800 tokens (check with token counter).
- [ ] No duplicate content between prompt and KB.
- [ ] Voice-specific guidance applied (brevity, natural language).

---

## 7.5. Red flags (prompt is too long)

- More than 1,000 tokens total
- Duplicate content from KB
- Step-by-step procedures in prompt
- Lists of data (pricing, hours, service areas)
- Long examples (>5 lines each)
- "Instructions" for every possible scenario

---

## Reuse across projects

- Copy this file into `skills/` or `doc/` in any repo, or keep it in a shared folder (e.g. `~/Developer/skills/`).
- In Cursor, reference it when working on prompts (e.g. open the file or @-mention it), or add a per-project rule that says: "When editing system prompts or KB, follow the guidelines in `skills/PromptEngineeringSkills.md`."