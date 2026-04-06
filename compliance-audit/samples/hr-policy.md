# Human Resources Security Policy
**Version:** 1.8
**Last reviewed:** 2024-10-01
**Owner:** Head of Human Resources / Head of Information Security (joint ownership)
**Status:** Approved

---

## 1. Purpose and Scope

This policy establishes information security requirements for the human resources lifecycle
at Acme Cloud Services, covering employees, contractors, and third-party personnel who have
access to production systems or cloud customer data.

---

## 2. Pre-Employment Verification (HR-01)

### 2.1 Background checks

All candidates for roles with access to production systems or customer data are subject
to pre-employment screening before receiving access. To the extent permitted by applicable
law, screening includes:

- Identity verification via government-issued ID
- Employment history and resume verification
- Verification of relevant academic qualifications
- Criminal record check (where legally permissible in the candidate's jurisdiction)

Third-party contractors and contingent workers are subject to equivalent screening by
their employer. Acme Cloud Services requires written confirmation of completed screening
before granting production access.

### 2.2 Roles requiring enhanced screening

Roles with privileged access to production infrastructure undergo enhanced screening,
including additional reference checks. Enhanced screening completion is a prerequisite
for access provisioning (see IDM-06).

---

## 3. Employment and Contractual Obligations (HR-02)

### 3.1 Information security obligations

All employees and contractors must sign the Information Security Acknowledgment as part
of their onboarding documentation. This acknowledgment confirms that they have read,
understood, and agree to comply with:

- The Information Security Policy
- The Acceptable Use Policy
- The Data Handling Standard
- Applicable confidentiality obligations

Signing is required before access to production systems or customer data is granted.

### 3.2 Contractors and service providers

Third-party personnel receive contractual information security obligations equivalent to
employee obligations through their service agreements and, where applicable, supplementary
non-disclosure agreements.

---

## 4. Security Training and Awareness (HR-03)

### 4.1 Mandatory training

All employees and contractors with production access must complete the following training:

| Training | Frequency | Delivery |
|----------|-----------|---------|
| Security Awareness Fundamentals | Annual | Online (LMS) |
| Phishing Simulation | Quarterly | Simulated attack |
| Incident Response Procedures | Annual | Workshop or online |
| Data Handling and Classification | Annual | Online (LMS) |

Training completion is tracked in the Learning Management System (LMS) and reviewed
quarterly by the Information Security team.

### 4.2 Role-specific training

Employees in technical roles (development, operations, security) complete additional
role-specific training:

- Secure development practices (DEV team): annual
- Privileged access responsibilities (system administrators): bi-annual
- Incident response exercises (SRE/security team): semi-annual

### 4.3 Training currency

Training completion data is reviewed against the active employee roster monthly.
Employees more than 30 days overdue on mandatory training have their access to
non-essential systems suspended pending completion.

---

## 5. Disciplinary Process (HR-04)

### 5.1 Process

Violations of information security policies are investigated and addressed through a
documented disciplinary process:

1. Investigation: the Information Security team and HR jointly assess whether a violation
   occurred and its nature and severity.
2. Determination: findings are documented, including evidence reviewed and conclusions.
3. Outcome: proportionate to the severity of the violation, ranging from written warning
   to termination, in accordance with applicable employment law.

Employees are informed in writing of the potential disciplinary outcomes at the start of
the investigation.

### 5.2 Documentation

Disciplinary proceedings are documented in the HR system with restricted access.
Investigation reports are retained for 5 years from case closure.

---

## 6. Termination and Change of Responsibilities (HR-05)

### 6.1 Ongoing obligations

Employees and contractors are formally notified, at termination and in their initial
employment agreement, that the following obligations survive employment:

- Confidentiality obligations (duration specified in the NDA/employment contract)
- Prohibition on retaining or disclosing proprietary information
- Obligation to report any discovered security incidents involving company data

Notification is acknowledged in writing at termination.

### 6.2 Access revocation on termination

Access revocation is governed by the Identity Management Policy (see IDM-04).
The HR team notifies the Identity and Access Management team on the employee's
last working day. All access must be revoked within 24 hours of notification.

---

## 7. Confidentiality Agreements (HR-06)

### 7.1 Scope

Non-disclosure or confidentiality agreements (NDAs) are concluded with:

- All employees: signed before production access is granted
- All contractors and consultants: signed before work commences
- External service providers and suppliers with access to confidential data: signed
  before the service engagement begins

### 7.2 Review cycle

Confidentiality agreements are reviewed at least annually by Legal and Information
Security to ensure they remain adequate for current data protection requirements.

Updated agreements are issued to all parties. Execution of the updated NDA is required
within 30 days of issue.

### 7.3 Scope of confidentiality obligations

NDAs cover at minimum:

- Cloud customer data and metadata
- Proprietary software, algorithms, and architecture
- Security controls and vulnerability information
- Business strategies and financial information not in the public domain

---

## 8. Exceptions

Exceptions to this policy require approval by both the Head of Human Resources and
the Head of Information Security. Exceptions are documented in the risk register with
a defined review date.

---

## 9. References

- Information Security Policy (v2.0, 2024-08-01)
- Identity Management Policy (v1.5, 2024-07-15)
- Acceptable Use Policy (v2.2, 2024-09-15)
- Data Handling Standard (v1.4, 2024-06-01)
