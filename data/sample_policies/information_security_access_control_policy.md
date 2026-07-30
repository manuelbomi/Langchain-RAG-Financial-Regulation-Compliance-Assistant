# Information Security Access Control Policy

> **SYNTHETIC / FICTIONAL DOCUMENT.** Written for the fictional company
> "Northbridge Financial Group" to power a portfolio RAG demo. Illustrative
> internal policy language only.

**Document ID:** ISEC-POL-005
**Owner:** Information Security Office
**Effective Date:** 2025-01-05 (fictional)
**Review Cycle:** Annual

## Section 1: Purpose

This policy establishes minimum requirements for granting, reviewing, and
revoking access to Northbridge Financial Group information systems, in
support of the principle of least privilege.

## Section 2: Access Provisioning

Access to any system processing Confidential or Restricted data (per the
Data Classification Standard, DCS-STD-004) must be:

1. Requested through the approved access management workflow
2. Approved by the resource owner and the requester's manager
3. Granted on a least-privilege basis, scoped to the minimum access
   required to perform the job function
4. Time-bound where the access is for a temporary engagement

## Section 3: Authentication Requirements

- All human users must authenticate with multi-factor authentication (MFA)
  for access to systems processing Confidential or Restricted data
- Service accounts and machine-to-machine credentials (including API keys
  used by internal AI agents and tools) must be rotated at least every 90
  days and must never be embedded in source code or committed to a version
  control repository
- Any AI agent or automated tool that calls internal or external APIs on a
  user's behalf must operate under a scoped service identity with logged,
  attributable actions — never under a shared or generic credential

## Section 4: Periodic Access Review

Access entitlements must be recertified at least every 90 days by the
resource owner. Access not recertified within the review window is
automatically revoked.

## Section 5: Privileged and Automated Access

Privileged access, including elevated access granted to autonomous or
semi-autonomous AI agents capable of taking write actions on production
systems, requires:

- Additional approval from Information Security
- Session logging sufficient to reconstruct every action taken
- A documented "blast radius" limitation (e.g., read-only by default,
  write actions gated behind an explicit human approval step for
  consequential or irreversible actions)

## Section 6: Termination of Access

All access must be revoked within 24 hours of an employee's or contractor's
termination, and within five business days for a vendor engagement
termination, consistent with the Third-Party Vendor Risk Policy
(TPRM-POL-003).
