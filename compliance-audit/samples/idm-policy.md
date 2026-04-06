# Identity and Access Management Policy
**Version:** 2.3
**Last reviewed:** 2024-09-20
**Owner:** Head of Information Security
**Status:** Approved

---

## 1. Purpose and Scope

This policy governs the management of identities, access rights, and authentication
mechanisms at Acme Cloud Services. It applies to all human users (employees, contractors,
service accounts) and system components that access production systems or cloud customer data.

---

## 2. Access and Permissions Policy (IDM-01)

### 2.1 Role and rights concept

All access to production systems is governed by a role and rights concept.
Access is granted on the principles of least privilege (only the minimum access required
for the task) and need-to-know (access granted only where required to perform the job function).

The role catalog is maintained by the Information Security team and reviewed annually.

### 2.2 Unique identifiers

Every user and service account is assigned a unique identifier. Shared accounts are
prohibited in production environments. Service accounts are named to identify the
owning team and purpose.

### 2.3 Separation of duties

The following duties are separated to prevent conflict of interest:

- Development vs. production deployment approval
- Access rights management vs. access rights review
- Incident response vs. audit logging

Where technical separation is not feasible, compensating controls (additional logging,
dual-approval workflows) are documented in the risk register.

---

## 3. Access Provisioning and Modification (IDM-02)

### 3.1 New access

Access requests must be submitted via the access request system with:

- Business justification
- Requested role or resource
- Manager approval
- Duration (temporary or permanent)

Requests are reviewed by the system owner or delegate. Access is provisioned only
after approval is recorded in the system.

### 3.2 Modification

Access modifications follow the same approval workflow as new access.
Role changes are processed within 2 business days of the approved request.

---

## 4. Access Blocking and Revocation for Inactivity (IDM-03)

User accounts and service accounts are monitored for activity:

- Accounts with no authentication events for **60 days** are automatically suspended.
  Reactivation requires a new approval from the account owner's manager.
- Accounts suspended for **180 days** are automatically revoked.
  Reactivation requires the full provisioning process (see IDM-02).

Service accounts used by automated pipelines are exempt from suspension if they are
configured in an approved scheduled job with a documented owner.

---

## 5. Access Revocation on Role Change (IDM-04)

### 5.1 Privileged access

Changes to roles that involve privileged access are processed within **48 hours** of the
effective date of the change. The previous role's privileged entitlements are revoked
regardless of whether new access has been provisioned.

### 5.2 All other access

All other access entitlements are reviewed and adjusted within **14 days** of the effective
date of a role change. The IAM team is notified by HR of role changes on the effective date.

---

## 6. Access Reviews (IDM-05)

### 6.1 Schedule

All access entitlements are subject to a formal review at least annually:

| Access type | Review frequency | Reviewer |
|-------------|-----------------|---------|
| Privileged access | Every 6 months | System owner + Security |
| Production system access | Annual | Manager + System owner |
| Standard application access | Annual | Manager |

### 6.2 Process

Access reviews are conducted in the access governance platform. Reviewers certify
each entitlement as appropriate, require modification, or revoke it.

Identified deviations (entitlements that should be removed or modified) are resolved
within **7 days** of the review completion date.

---

## 7. Privileged Access Management (IDM-06)

### 7.1 Privileged account policy

Privileged access (administrative, root, or equivalent) is managed separately from
standard access:

- Privileged accounts are personalized (no shared admin accounts)
- Access is time-limited: administrative access is requested per-session or per-task
  via a privileged access management (PAM) solution
- Privileged sessions are recorded and logs retained for 12 months
- Technical service accounts with privileged access are assigned to a named human owner

### 7.2 Monitoring

Privileged access activity is monitored via the SIEM. Alerts are configured for:

- Off-hours privileged access
- Access to systems outside the account's normal scope
- High volume of read/write operations in short time windows

Alerts are reviewed within 4 business hours. Confirmed misuse triggers the incident
response process (see SIM-01) and the disciplinary process (see HR-04).

---

## 8. Access to Cloud Customer Data (IDM-07)

Acme Cloud Services employees do not access cloud customer data without prior customer
authorization, except in the following circumstances:

- Legal obligation (with customer notification unless prohibited by law)
- Customer-requested support case (logged and attributed to a support ticket)
- Emergency response to prevent data loss or service disruption (logged, customer notified within 72 hours)

All access events are logged with timestamp, user, duration, reason, and associated
ticket number. Customers are notified of access events within **72 hours** of occurrence
via the security notification channel specified in their service agreement.

---

## 9. Authentication Information Confidentiality (IDM-08)

Passwords must not be shared, written down in plaintext, or transmitted in cleartext.

- Initial passwords expire after **14 days** if not changed
- Password changes trigger an email notification to the registered address
- Passwords are stored server-side using bcrypt or Argon2 with per-user salt
- Systems that cannot enforce modern hashing are noted in the risk register with
  a remediation timeline

Deviations from password storage requirements are subject to risk assessment and
formal risk acceptance by the Head of Information Security.

---

## 10. Authentication Mechanisms (IDM-09)

### 10.1 Multi-factor authentication

**All production access requires MFA.** This applies to:

- VPN and remote access to the corporate network
- Cloud provider consoles (AWS, GCP, Azure)
- Privileged access via the PAM solution
- CI/CD pipeline approvals with production deployment scope

### 10.2 Password requirements

Passwords used within the production environment must meet:

- Minimum length: 14 characters
- Complexity: at least one uppercase, one lowercase, one digit, one special character
- No reuse of the previous 12 passwords
- Maximum age: 365 days for standard accounts; MFA-enabled accounts have no forced rotation

### 10.3 Certificates

Certificate-based authentication uses digitally signed certificates managed in accordance
with the Key Management Policy (see CRY-01). Certificates expire within 2 years.

---

## 11. Exceptions

Access exceptions (e.g., temporary elevated access, delay in access revocation) require
approval from the Head of Information Security with a documented justification, duration,
and compensating control. All exceptions are reviewed at access review time.

---

## 12. References

- Human Resources Security Policy (v1.8, 2024-10-01)
- Key Management Policy (v1.1, 2024-05-15)
- Privileged Access Management Standard (v1.0, 2024-04-01)
- Security Incident Management Policy (v2.1, 2024-08-30)
