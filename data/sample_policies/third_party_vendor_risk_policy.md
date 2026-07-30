# Third-Party Vendor Risk Policy

> **SYNTHETIC / FICTIONAL DOCUMENT.** Written for the fictional company
> "Northbridge Financial Group" to power a portfolio RAG demo. Illustrative
> internal policy language only; not a representation of any real
> institution's actual policy or a real regulatory requirement.

**Document ID:** TPRM-POL-003
**Owner:** Third-Party Risk Management
**Effective Date:** 2025-01-20 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose and Scope

This policy governs the identification, assessment, and ongoing oversight of
risk introduced by third parties, including vendors, subcontractors, and
hosted or managed AI/ML service providers, that provide products or services
to Northbridge Financial Group.

## Section 2: Third-Party Risk Tiering

Third parties are tiered at onboarding based on:

- Access to confidential customer or company data
- Criticality of the service to core business operations
- Whether the third party performs a function on Northbridge's behalf that
  is subject to regulatory oversight ("regulated activity outsourcing")
- Whether the third party hosts, trains, or fine-tunes AI/ML models using
  Northbridge data

Critical third parties (Tier 1) require enhanced due diligence, executive
sponsor sign-off, and inclusion in the enterprise Third-Party Inventory.

## Section 3: Data Handling Requirements for Hosted AI Services

Where a proposed third party is a hosted or managed large language model or
agentic AI platform, the engagement review must additionally document:

1. Whether prompts, retrieved documents, or customer data leave Northbridge's
   network boundary, and if so, under what data processing agreement
2. Whether the third party retains, logs, or uses submitted data for model
   training absent explicit opt-out
3. An assessment of whether a self-hosted or in-network alternative (e.g.,
   an on-premises open-weight model, or a self-hosted retrieval pipeline)
   is feasible for the use case, particularly where source documents are
   confidential policy, customer, or supervisory content
4. Incident notification SLAs in the event of a data exposure at the vendor

Business units are encouraged to prefer architectures where sensitive
document content does not need to leave the Northbridge network boundary
when an in-network alternative meets functional requirements at reasonable
cost.

## Section 4: Ongoing Monitoring

Tier 1 and Tier 2 third parties are subject to at least annual reassessment,
including review of the vendor's own security attestations (e.g., SOC 2
Type II or equivalent), incident history, and financial viability.

## Section 5: Termination and Offboarding

Contracts with third parties handling confidential data must include a
data return or certified destruction clause exercisable at contract
termination, and offboarding procedures must confirm revocation of all
system access and API credentials within five business days of termination.
