# Asset Management Policy
**Version:** 2.1
**Last reviewed:** 2024-11-15
**Owner:** Head of Information Security
**Status:** Approved

---

## 1. Purpose and Scope

This policy establishes requirements for the identification, classification, and lifecycle
management of information assets at Acme Cloud Services. It applies to all hardware,
software, data, and services used in the production environment.

---

## 2. Asset Inventory (AM-01)

### 2.1 Inventory requirements

All assets used in the provision of cloud services must be registered in the asset
management system within 24 hours of commissioning. The inventory is maintained
automatically via infrastructure tooling (IaC scanning, cloud provider APIs) and
supplemented by manual records for physical hardware.

Asset records must include:

- Asset identifier
- Asset type (hardware, software, SaaS, data repository)
- Owner (individual or team)
- Environment (production, staging, development)
- Data classification
- Commissioning date
- Decommissioning date (when applicable)

### 2.2 Inventory reviews

The asset inventory is reviewed quarterly by asset owners and validated annually by the
Information Security team. Discrepancies must be resolved within 14 days of discovery.

### 2.3 Change logging

All changes to the inventory (creation, modification, decommissioning) are logged with
timestamp and responsible individual or automated process. Logs are retained for 24 months.

---

## 3. Acceptable Use and Safe Handling (AM-02)

### 3.1 Acquisition and commissioning

New assets must be approved by an authorized manager before procurement. Commissioning
requires verification of:

- Secure baseline configuration
- Malware protection enabled
- Authentication and authorization mechanisms configured
- Encrypted storage (where applicable)
- Registration in the asset inventory

### 3.2 Software and patch management

All software assets must run supported versions with available security updates.
Software for which vendor support has ended must be identified in the risk register and
replaced within 90 days, or a compensating control documented with risk owner sign-off.

### 3.3 Decommissioning

Assets must be securely decommissioned following the data deletion procedure (see Section 6).
Data on decommissioned storage must be cryptographically wiped or physically destroyed.
Decommissioning must be documented in the asset inventory.

---

## 4. Hardware Commissioning (AM-03)

All hardware deployed in the production environment undergoes a commissioning review:

1. Risk identification for the intended use case
2. Secure configuration verification against the applicable hardening baseline
3. Approval by an authorized reviewer before production deployment

Hardware commissioning records are retained for the asset's operational lifetime plus
24 months.

---

## 5. Hardware Decommissioning (AM-04)

Decommissioning of production hardware requires:

1. Approval from an authorized manager
2. Data deletion: all storage media wiped using NIST 800-88 Rev1 compliant methods,
   or physical destruction if wiping is not feasible
3. Removal from the asset inventory with decommissioning date and method recorded

---

## 6. Employee Asset Responsibilities (AM-05)

Employees who are issued assets (laptops, mobile devices, access tokens) must:

1. Acknowledge the Acceptable Use Policy before receiving the asset
2. Complete security awareness training covering asset handling within 30 days of issuance
3. Return all assets within 2 business days of employment termination

Asset acknowledgment records are maintained in the HR system and auditable.

---

## 7. Asset Classification and Labeling (AM-06)

### 7.1 Classification schema

All assets are classified according to the protection requirements of the information
they process, store, or transmit:

| Level | Confidentiality | Integrity | Availability |
|-------|----------------|-----------|--------------|
| Public | None | Low | Low |
| Internal | Medium | Medium | Medium |
| Confidential | High | High | High |
| Restricted | Highest | Highest | Highest |

### 7.2 Labeling

Digital assets are labeled via metadata tags in the asset management system and, where
technically feasible, via file system or storage tags. Physical assets are labeled with
a tamper-evident classification sticker.

### 7.3 Handling by classification

Handling requirements for each classification level are defined in the Data Classification
Standard and enforced through technical controls (encryption, access controls) and
procedural controls (clean desk, secure disposal).

---

## 8. Exceptions

Exceptions to this policy require written approval from the Head of Information Security
and must be entered in the risk register with an accepted residual risk documented by
the risk owner. All exceptions are reviewed at least annually.

---

## 9. References

- Data Classification Standard (v1.4, 2024-09-01)
- Secure Configuration Baseline (v3.0, 2024-06-15)
- Data Deletion Procedure (v2.0, 2024-03-20)
- Risk Management Policy (v1.2, 2024-01-10)
