# Business Continuity Policy

> **SYNTHETIC / FICTIONAL DOCUMENT.** Written for the fictional company
> "Northbridge Financial Group" to power a portfolio RAG demo. Illustrative
> internal policy language only.

**Document ID:** BCP-POL-006
**Owner:** Operational Resilience Office
**Effective Date:** 2025-02-10 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose

This policy establishes the requirements for business continuity and
disaster recovery planning across Northbridge Financial Group, to ensure
critical business functions can continue or be restored within acceptable
timeframes following a disruption.

## Section 2: Business Impact Analysis

Each business unit must maintain a Business Impact Analysis (BIA) that
identifies critical processes and assigns:

- **Recovery Time Objective (RTO):** maximum tolerable downtime
- **Recovery Point Objective (RPO):** maximum tolerable data loss window

Processes supporting customer-facing financial transactions or regulatory
reporting are generally designated Tier 1 (RTO of 4 hours or less).

## Section 3: AI and Automated System Resilience

Where an AI-based system (including a retrieval-augmented generation
assistant, autonomous agent, or model-backed decision system) supports a
Tier 1 or Tier 2 process, the BIA must additionally document:

1. A defined fallback procedure if the AI system is unavailable or is
   returning low-confidence or refused responses at an abnormal rate
2. Whether the system's dependencies (vector index, model endpoint,
   orchestration layer) are hosted in-network or by a third party, and the
   corresponding recovery dependencies
3. A manual override or human-in-the-loop fallback for any AI system
   that would otherwise be a single point of failure in a critical process

## Section 4: Testing Requirements

Business continuity plans must be tested at least annually, via tabletop
exercise at minimum and full failover testing for Tier 1 processes at least
every two years. Test results and remediation items must be documented and
tracked to closure.

## Section 5: Communication Plan

Each business continuity plan must include a communication plan identifying
who notifies customers, regulators, and internal stakeholders in the event
of a significant disruption, and the escalation thresholds that trigger
each notification.

## Section 6: Plan Maintenance

Business continuity plans must be reviewed and re-approved annually, and
immediately following any material change to the supported process,
technology stack, or organizational structure.
