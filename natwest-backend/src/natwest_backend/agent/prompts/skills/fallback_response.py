DATA_FALLBACK_RESPONSE_PROMPT = """\
You are preparing a user-facing response for a failed or incomplete data lookup.

You will receive the original user request and a structured error payload.

Rules:
- Explain clearly what happened.
- Do not invent customers, issues, IDs, or statuses.
- If exact data was not found, say that explicitly.
- Give 1-3 concrete next steps the user can take.
- Prefer actions such as: verify spelling, provide a more exact name, share an issue reference, share a customer ID, or ask to list available records when relevant.
- If the failure is due to tool limits or bad source data, explain that plainly and suggest a practical next step.
- Keep the answer concise and professional.
- Return only the final user-facing response.

Original request:
{user_message}

Structured error:
{error_payload}
"""
