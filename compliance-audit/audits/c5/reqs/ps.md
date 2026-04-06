# PS - Physical Security

## PS-01 Safety requirements for premises and buildings
Security requirements for premises and buildings related to the provided cloud service are derived from the security objectives of the information security policy, the identified protection needs for the cloud service, and the assessment of physical and environmental security risks. The security requirements are documented, communicated, and provided in a policy or concept in accordance with SP-01.

The security requirements for data centers are based on criteria that comply with recognized engineering practices. They are suitable for addressing the following threats in accordance with applicable legal and contractual requirements:

- Faulty planning
- Unauthorized access
- Inadequate monitoring
- Inadequate air conditioning
- Fire and smoke
- Water
- Power failure
- Contamination

If the cloud provider uses premises or buildings operated by third parties to provide the cloud service, this document describes the security requirements the cloud provider imposes on these third parties. Appropriate and effective verification of implementation is carried out in accordance with the criteria for managing and monitoring subcontractors (see SSO-01, SSO-02).

## PS-02 Redundancy model
The cloud service is provided from two locations that provide mutual redundancy. The locations comply with the cloud provider's security requirements (see PS-01) and are sufficiently spaced apart to achieve operational redundancy. Operational redundancy is designed to meet the availability requirements contained in the service level agreement.

The functionality of the redundancy is verified at least annually through appropriate tests and exercises (see BCM-04).

## PS-03 Perimeter protection
The structural envelope of rooms and buildings related to the provided cloud service is physically sound and protected by appropriate security measures that comply with the cloud provider's security requirements (see PS-01).

The security measures are suitable for detecting and preventing unauthorized access in a timely manner so that it does not compromise the information security of the cloud service in question.

The external doors, windows, and other structural elements meet a level of security appropriate to the requirements and can withstand a break-in attempt for at least 10 minutes. The surrounding wall structures and locking devices meet the associated requirements.

## PS-04 Access control
Physical access controls are installed at entrances to rooms and buildings related to the provided cloud service in accordance with the cloud provider's security requirements (see PS-01) to prevent unauthorized access.

Access controls are managed by an access control system.

The requirements for the access control system are documented, communicated, and provided in a policy or concept in accordance with SP-01 and include the following aspects:

- Regulated procedures for granting and revoking access authorizations (see IDM-02) based on the principle of least privilege
- Automatic blocking of access authorizations if they have not been used for a period of two months
- Automatic revocation of access authorizations if they have not been used for a period of six months
- Two-factor authentication for access to areas that house system components used to process cloud customer information
- Visitors and external personnel are individually recorded by the access control system during all work in the premises and buildings and identified as such, and supervised during their stay
- Existence and nature of an access log, which enables the cloud provider to verify whether only defined persons have entered the premises and buildings

## PS-05 Protection against fire and smoke
Rooms and buildings related to the provided cloud service are protected from fire and smoke by structural, technical, and organizational measures that comply with the cloud provider's safety requirements (see PS-01) and include the following aspects:

Structural measures: Establishment of fire compartments with a fire resistance of at least 90 minutes for all room-forming components.

Technical measures:
- Early fire detection with automatic power disconnection
- Extinguishing system or oxygen reduction system
- Fire alarm system with notification to the local fire department

Organizational measures:
- Regular fire safety inspections to verify compliance with fire safety regulations
- Regular fire drills

## PS-06 Protection against utility failure
Failure prevention measures for the technical utilities required for the operation of system components used to process cloud customer information are documented and implemented in accordance with the cloud provider's security requirements (see PS-01) with regard to the following aspects:

- Operational redundancy (N+1) in the power and cooling supply
- Use of appropriately dimensioned uninterruptible power supplies (UPS) and emergency power systems (EPS) designed to ensure that all data remains intact in the event of a power failure. The functionality of UPSs and EPSs is verified at least annually
- Maintenance of the utilities in accordance with the manufacturer's recommendations
- Protection of power and telecommunications lines against interruption, malfunction, damage, and eavesdropping. The protection is checked regularly, at least every two years

## PS-07 Monitoring of operating and environmental parameters
Operating parameters of the technical utilities (see PS-06) as well as the environmental parameters of the premises and buildings related to the provided cloud service are monitored and controlled in accordance with the cloud provider's security requirements (see PS-01). If the permissible control range is exceeded, the cloud provider's expert personnel or authorized system components are automatically notified in order to immediately initiate the necessary measures to return to the control range.
