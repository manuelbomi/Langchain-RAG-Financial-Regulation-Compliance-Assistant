# Model Risk Management Policy

> **SYNTHETIC / FICTIONAL DOCUMENT.** This policy was written for a fictional
> company, "Northbridge Financial Group," solely to power a portfolio demo of
> a retrieval-augmented generation system. It illustrates the *style* of
> internal bank policy language and does not cite, quote, or represent any
> real regulation, supervisory letter, or actual institution's policy. Do not
> treat any statement here as regulatory guidance.

**Document ID:** MRM-POL-001
**Owner:** Model Risk Management Office
**Effective Date:** 2025-01-15 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose and Scope

This policy establishes the framework by which Northbridge Financial Group
identifies, measures, monitors, and controls model risk arising from the
design, development, deployment, and ongoing use of quantitative models,
including statistical models, machine learning models, and generative AI
systems used in decision-making processes.

## Section 2: Model Definition

For purposes of this policy, a "model" is any quantitative method, system, or
approach that applies statistical, economic, financial, or mathematical
theories, techniques, and assumptions to process input data into quantitative
estimates. This definition explicitly includes machine learning classifiers,
large language model-based agents used in customer-facing or decision-support
roles, and rules engines with learned parameters.

## Section 3: Model Risk Tiering

Every model must be assigned a risk tier (Tier 1 - Critical, Tier 2 -
Significant, Tier 3 - Limited) at inception, based on:

- Materiality of financial impact
- Degree of automation (human-in-the-loop vs. fully autonomous decisioning)
- Complexity and explainability of the underlying method
- Regulatory sensitivity of the use case

Tier 1 models, including any autonomous or semi-autonomous AI agent that can
take an action (e.g., approve a transaction, generate customer communication)
without a human review step, require independent validation before
production deployment and at least annual revalidation thereafter.

## Section 4: Independent Validation Requirements

Independent Validation (performed by a team organizationally separate from
model development) must assess, at minimum:

1. Conceptual soundness of the modeling approach
2. Data lineage and input quality
3. Outcome analysis and ongoing monitoring plan
4. Benchmark comparison against a challenger approach where feasible
5. For AI agent systems: evaluation of tool-use boundaries, prompt-injection
   resistance, and failure/refusal behavior under adversarial or
   out-of-distribution inputs

## Section 5: Ongoing Monitoring

Model owners must implement monitoring that detects performance drift,
data drift, and — for generative or agentic systems — an increase in
ungrounded or unverifiable outputs. Any monitoring breach must be logged and
escalated to the Model Risk Committee within five business days.

## Section 6: Model Inventory

All models, including internally built agentic AI systems and third-party
model-backed services, must be registered in the enterprise Model Inventory
prior to production use, with an assigned owner, risk tier, and validation
status.
