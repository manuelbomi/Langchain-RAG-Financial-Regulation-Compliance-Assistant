# Data Classification Standard

> **SYNTHETIC / FICTIONAL DOCUMENT.** Written for the fictional company
> "Northbridge Financial Group" to power a portfolio RAG demo. Illustrative
> internal policy language only.

**Document ID:** DCS-STD-004
**Owner:** Data Governance Office
**Effective Date:** 2025-01-10 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose

This standard defines the classification tiers applied to all data assets
created, processed, or stored by Northbridge Financial Group, and the
minimum handling controls required for each tier.

## Section 2: Classification Tiers

| Tier | Label | Description |
|------|-------|-------------|
| 1 | Public | Approved for unrestricted external release |
| 2 | Internal | General business information not intended for external release |
| 3 | Confidential | Customer, employee, or proprietary business data |
| 4 | Restricted | Highly sensitive data (e.g., authentication secrets, regulatory examination material, undisclosed M&A information) |

## Section 3: Handling Requirements by Tier

Confidential (Tier 3) and Restricted (Tier 4) data:

1. Must be encrypted at rest and in transit using approved algorithms
2. Must not be submitted to any external system, including third-party AI
   or productivity tools, unless that system has completed Third-Party Risk
   review per the Third-Party Vendor Risk Policy (TPRM-POL-003) and is
   explicitly approved for that data tier
3. Must be access-controlled on a least-privilege, need-to-know basis per
   the Information Security Access Control Policy (ISEC-POL-005)
4. May only be used to train, fine-tune, or ground (via retrieval) an AI
   system if that system operates within the Northbridge network boundary
   or under an approved data processing agreement

## Section 4: Internal Policy and Procedure Documents

Internal policy, standard, and procedure documents themselves (such as this
one) are classified Internal (Tier 2) unless they reference Restricted
information, in which case the more restrictive tier applies to the
document as a whole.

## Section 5: Retrieval-Augmented AI Systems

Any system that indexes Confidential or Restricted documents for retrieval
(for example, a policy question-answering assistant) must:

- Maintain the source document's classification tier as retrievable
  metadata on each indexed chunk
- Restrict end-user query access based on the requester's entitlement to
  that classification tier
- Log every query and the classification tier of any document surfaced in
  the response, for audit purposes

## Section 6: Declassification and Review

Data classification must be reviewed whenever a document is materially
revised, and at minimum every 24 months, to confirm the assigned tier
remains appropriate.
