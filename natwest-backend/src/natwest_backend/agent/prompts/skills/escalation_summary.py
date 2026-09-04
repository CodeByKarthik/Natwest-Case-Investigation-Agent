CUSTOMER_NAME_EXTRACTION_PROMPT = """\
Extract the customer or company name from the following user message.
Return ONLY the customer name. Nothing else.
If no customer name is found, return exactly: UNKNOWN

User message: {message}\
"""

ESCALATION_SUMMARY_PROMPT = """\
You are preparing an executive escalation summary for a customer account.

Analyse the following operational data and produce a structured summary.

---

## Customer Profile
{customer_data}

## Open Issues ({issue_count} total)
{issues_data}

## Issue Timeline & Updates
{updates_data}

## Pending Next Actions
{actions_data}

---

Produce your response in EXACTLY this format:

### Executive Summary
Write 2-3 paragraphs covering: who the customer is, their current health, \
what the active issues are, how severe the situation is, and what the \
business impact could be if unresolved.

### Risk Level
State one of: **Low** / **Medium** / **High** / **Critical**
Follow with a one-sentence justification based on issue priority, count, \
customer tier, and health status.

### Recommended Next Actions
Provide a numbered list of 3-5 specific, actionable recommendations. \
Each should name a responsible party or role and include a timeframe.

### Missing Information
List any gaps in the data that would be needed for a complete assessment \
(e.g. missing SLA terms, no recent customer communication, unassigned issues).\
"""
