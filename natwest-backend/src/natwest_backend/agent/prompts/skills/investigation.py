"""Prompts for the case investigation workflow.

Steps 7-9 are LLM reasoning steps. Steps 7 and 8 must return citation-aware
findings (see CitedFinding in investigation_workflow.py) so every risk
indicator and evidence gap is traceable to a specific record, date, or
value in the gathered data.
"""

RISK_INDICATORS_PROMPT = """\
You are analysing a NatWest investigation case.

Using ONLY the data below, identify risk indicators. Every risk indicator
MUST cite the specific record, date, or value it came from. Never state a
risk indicator without a citation, and never invent or reformat an
identifier, date, or confidence score — use only what literally appears
in the data below.

Categories to look for:
- Active vulnerability signals (cite the vulnerability_register entry; if it has a nested source_record, cite its source_system, source_ref, confidence_score, and generated_at)
- Pattern of related cases — 3+ same-type cases in 90 days (cite the specific case_refs from related_cases_data)
- Disputed amount of £1000 or more (cite the disputed_amount and merchant_name from case_data)
- KYC expired or last review more than 3 years ago (cite the kyc_last_reviewed date from customer_data)
- Consumer Duty flag set on this case (cite the case_ref)
- Case open longer than its SLA — P1 > 24h, P2 > 3 days, P3 > 7 days, P4 > 14 days (cite opened_date and priority)
- System alerts in the timeline with a confidence score above 80% (cite the nested source_record's source_ref, source_system, and confidence_score)

## Case
{case_data}

## Customer Profile (includes vulnerability register)
{customer_data}

## Customer Accounts
{accounts_data}

## Other Cases For This Customer
{related_cases_data}

## Case Timeline
{timeline_data}

## Outstanding Next Actions
{next_actions_data}

Return a JSON array of objects, each with exactly these keys:
{{
  "finding": "concise description of the risk",
  "source_type": "one of: vulnerability_register, source_system_record, case_attribute, related_case, timeline_event, next_actions",
  "source_id": "the specific record id/ref this came from (e.g. a source_ref, case_ref, or register entry id), or null",
  "source_system": "the source system name (fraud_engine, transaction_monitoring, or kyc_monitoring), or null",
  "confidence": "the confidence score as it appears in the data (e.g. '91.00' or '91%'), or null",
  "detected_at": "the ISO date string this was detected or generated, or null",
  "explanation": "why this matters in this specific case"
}}

Example shape (do not copy these values — use the real data provided above):
[{{"finding": "Active life_event vulnerability signal", "source_type": "vulnerability_register", "source_id": "KYC-2026-3310", "source_system": "kyc_monitoring", "confidence": "91.00", "detected_at": "2026-07-15T00:00:00+00:00", "explanation": "Customer has an active bereavement-related vulnerability requiring sensitive handling."}}]

If there are no risk indicators, return: []\
"""

EVIDENCE_GAPS_PROMPT = """\
You are analysing a NatWest investigation case.

Using ONLY the data below, spot what is *missing* that a good decision
would need. Every evidence gap MUST cite the specific record that
highlights the gap — either something that exists without a matching
follow-up, or a case attribute. Never invent or reformat an identifier,
date, or confidence score — use only what literally appears in the data
below.

Categories to look for:
- Vulnerability flag set but no specialist referral in next_actions or timeline (cite the vulnerability_register entry)
- Fraud case but no fraud team involvement in the timeline (cite case_type and the timeline)
- Disputed transaction but no request_documents action (cite disputed_amount and next_actions)
- KYC expired but no kyc_refresh action (cite kyc_status/kyc_last_reviewed and next_actions)
- Case escalated but no case events explaining why (cite the case status and timeline)
- No customer contact recorded despite the case being open (cite opened_date and the timeline)

## Case
{case_data}

## Customer Profile (includes vulnerability register)
{customer_data}

## Customer Accounts
{accounts_data}

## Other Cases For This Customer
{related_cases_data}

## Case Timeline
{timeline_data}

## Outstanding Next Actions
{next_actions_data}

Return a JSON array of objects, each with exactly these keys:
{{
  "finding": "concise description of what is missing",
  "source_type": "one of: vulnerability_register, source_system_record, case_attribute, related_case, timeline_event, next_actions",
  "source_id": "the specific record id/ref that highlights this gap, or null",
  "source_system": "the source system name if relevant, or null",
  "confidence": "a confidence score if relevant, or null",
  "detected_at": "an ISO date string if relevant, or null",
  "explanation": "what specifically is missing and why it matters"
}}

Example shape (do not copy these values — use the real data provided above):
[{{"finding": "No specialist referral despite an active vulnerability signal", "source_type": "vulnerability_register", "source_id": "KYC-2026-3310", "source_system": null, "confidence": null, "detected_at": null, "explanation": "Active vulnerability signal requires an escalate_vulnerability action, but none exists in next_actions."}}]

If there are no evidence gaps, return: []\
"""

RECOMMENDATION_PROMPT = """\
You are completing a NatWest case investigation report.

Given the case data, customer profile, and the cited risk indicators and
evidence gaps below, recommend ONE next action. The action type must be
one of: contact_customer, request_documents, issue_refund, escalate_fraud,
escalate_vulnerability, kyc_refresh, add_case_note

Write narrative sections that reference specific findings by their source
system, source ref, date, or confidence score — never write generic
statements. For example, vulnerability_context should read like:
"One active life_event signal — flagged by kyc_monitoring on 15 Jul 2026
(KYC-2026-3310, 91% confidence)." rather than "Active vulnerability signal
present."

## Case
{case_data}

## Customer Profile (includes vulnerability register)
{customer_data}

## Risk Indicators (with citations)
{risk_indicators}

## Evidence Gaps (with citations)
{evidence_gaps}

Return ONLY a JSON object with exactly these keys:
{{
  "case_summary": "2-3 sentences on what the case is about",
  "customer_context": "2-3 sentences on who the customer is",
  "vulnerability_context": "summary naming specific vulnerability signals with their source system, date, ref, and confidence, or null if none",
  "recommended_action": "one sentence describing the recommendation, referencing the specific finding(s) driving it",
  "recommended_action_type": "one of the allowed action types, or null",
  "reasoning": "short justification citing the specific findings (by source id) that drove this recommendation"
}}\
"""
