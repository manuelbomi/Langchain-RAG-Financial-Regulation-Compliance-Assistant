# Incident Response Policy

> **SYNTHETIC / FICTIONAL DOCUMENT.** Written for the fictional company
> "Northbridge Financial Group" to power a portfolio RAG demo. Illustrative
> internal policy language only.

**Document ID:** IR-POL-008
**Owner:** Information Security Office
**Effective Date:** 2025-02-15 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose

This policy defines how Northbridge Financial Group detects, triages,
contains, and reports information security incidents, including incidents
involving AI systems and agent tooling.

## Section 2: Incident Severity Classification

| Severity | Description | Initial Response SLA |
|----------|--------------|----------------------|
| SEV-1 | Confirmed data exfiltration, or an autonomous system taking an unauthorized consequential action | 15 minutes |
| SEV-2 | Suspected data exposure or repeated AI system guardrail bypass | 1 hour |
| SEV-3 | Isolated anomaly with no confirmed data or system impact | 1 business day |

## Section 3: AI-Specific Incident Triggers

The following are explicitly in scope as reportable security incidents and
must be triaged under this policy:

1. A prompt-injection attempt that caused a system to disregard its
   operating instructions or to attempt an unauthorized action
2. An AI agent taking a write action (e.g., submitting a transaction,
   sending a communication) outside its approved authorization boundary
3. Discovery that Confidential or Restricted data was submitted to a
   non-approved external AI tool
4. A retrieval-augmented system generating a response with a citation to a
   document that does not exist, or a document classification mismatch
   (e.g., surfacing Restricted content to a requester without entitlement)

## Section 4: Containment and Eradication

Upon confirmation of a SEV-1 or SEV-2 incident involving an AI agent or
automated tool, the on-call responder must have the authority to
immediately revoke the affected system's credentials and disable its
write-capable tools pending investigation, without requiring prior business
approval.

## Section 5: Post-Incident Review

Every SEV-1 and SEV-2 incident requires a documented post-incident review
within 10 business days, including root cause, timeline, and remediation
actions with owners and due dates. Findings relevant to model or agent
behavior must be shared with the Model Risk Management Office for
consideration in the next revalidation cycle.

## Section 6: Regulatory Notification

Where an incident meets the threshold for regulatory notification under
applicable law, Legal and Compliance must be engaged immediately to manage
the notification timeline; this policy's internal SLAs do not supersede
applicable external notification deadlines.
