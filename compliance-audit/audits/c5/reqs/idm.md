# IDM - Identity and Access Management

## IDM-01 Access and Permissions Policy
A role and rights concept based on the cloud provider's business and security requirements, as well as a policy for managing access authorizations for internal and external employees of the cloud provider, as well as for system components that play a role in the cloud provider's automated authorization processes, are documented, communicated, and provided in accordance with SP-01 with the following specifications:

- Assignment of unique user names
- Assignment and modification of access authorizations based on the principle of least privilege and as necessary for the performance of tasks
- Separation of duties between operational and controlling functions
- Separation of duties in the management of rights profiles, approval, and assignment of access authorizations
- Approval of the assignment or modification by authorized personnel or authorized system components before access to cloud customer data or system components for the provision of the cloud service can be granted
- Regular review of granted access authorizations
- Blocking and revoking access authorizations in the event of inactivity
- Time-based or event-related revocation or adjustment of access authorizations in the event of changes in responsibilities

## IDM-02 Assignment and modification of access and access authorizations
Regulated procedures for the assignment and modification of access and authorization rights for internal and external employees of the cloud provider as well as for system components that play a role in the cloud provider's automated authorization processes ensure compliance with the role and rights concept as well as the policy for managing access and authorization rights.

## IDM-03 Blocking and revocation of access rights in case of inactivity or repeated failed logins
Access authorizations of internal and external employees of the cloud provider, as well as system components that play a role in the cloud provider's automated authorization processes, will be blocked if they have not been used for a period of two months. Unblocking requires approval from an authorized authority.

Blocked access authorizations will be revoked after six months at the latest. After revocation, the process for granting access authorizations (see IDM-02) must be repeated.

## IDM-04 Revocation or adjustment of access rights in the event of changes
Access authorizations will be revoked promptly in the event of changes to the responsibilities of the cloud provider's internal and external employees or system components that play a role in the cloud provider's automated authorization processes. Privileged access authorizations will be adjusted or revoked no later than 48 hours after the change takes effect. All other access authorizations will be adjusted or revoked no later than 14 days. After revocation, the granting process (see IDM-02) must be repeated.

## IDM-05 Regular review of access authorizations
Access authorizations of internal and external employees of the cloud provider, as well as system components that play a role in the cloud provider's automated authorization processes, are reviewed at least annually to determine whether they still correspond to the actual tasks or areas of application. The review is carried out by authorized individuals from the cloud provider's organizational units who, based on their knowledge of the employees' or system components' areas of responsibility, can assess the appropriateness of the granted access authorizations. Identified deviations are addressed promptly, but no later than seven days after their detection, by appropriately changing or revoking access authorizations.

## IDM-06 Privileged access permissions
Privileged access authorizations for internal and external employees and technical users of the cloud provider are granted and modified in accordance with the Access Authorization Management Policy (see IDM-01) or a separate policy.

Privileged access authorizations are personalized and assigned for a limited time based on a risk assessment and as necessary for the performance of the task. Technical users are also assigned to internal or external employees of the cloud provider.

The activities of users with privileged access authorizations are logged to detect any suspected misuse of these authorizations. The logged information is automatically monitored for defined events that may constitute misuse. If such an event is identified, the responsible personnel of the cloud provider are automatically informed so that they can immediately assess whether misuse has occurred and initiate appropriate measures. In the event of proven misuse of privileged access authorizations, disciplinary measures will be initiated in accordance with HR-04.

## IDM-07 Access to cloud customer data
The cloud customer will be informed by the cloud provider of events in which internal or external employees of the cloud provider will have or have had read or write access to the cloud customer's data processed, stored, or transmitted in the cloud service without the cloud customer's prior consent. This information will be provided for each event, provided the cloud customer's data is/was not encrypted, the encryption is/was lifted for access, or the contractual agreements do not explicitly exclude such information. The information will include the reason, time, duration, type, and extent of the access. The information is sufficiently detailed to enable competent persons of the cloud customer to conduct a risk assessment of the access. This information will be provided in accordance with the contractual agreement, but no later than 72 hours after access.

## IDM-08 Confidentiality of authentication information
The allocation of authentication information for access to system components for providing the cloud service to internal and external users of the cloud provider and system components that play a role in the cloud provider's automated authorization processes is carried out in an orderly manner that ensures the confidentiality of the information.

If passwords are used as authentication information, their confidentiality is ensured by the following procedures, to the extent technically feasible:

- Users can initially create the password themselves or must change an initially predefined password when logging into the system component for the first time. An initially predefined password expires after a maximum of 14 days.
- When creating passwords, compliance with the password specifications (see IDM-09) is enforced, to the extent technically feasible.
- The user is informed about password changes or resets.
- Server-side storage is carried out using cryptographically strong password hash functions.

Deviations are assessed through a risk analysis, and mitigating measures derived from this are implemented.

## IDM-09 Authentication mechanisms
System components under the cloud provider's responsibility that are used to provide the cloud service authenticate users of the cloud provider's internal and external employees, as well as system components that play a role in the cloud provider's automated authorization processes. Access to the production environment requires two- or multi-factor authentication. Within the production environment, users are authenticated using passwords, digitally signed certificates, or procedures that achieve at least an equivalent level of security. If digitally signed certificates are used, they are managed in accordance with the key management policy (see CRY-01). The password specifications are derived from a risk assessment and documented, communicated, and provided in a password policy according to SP-01. Compliance with these specifications is enforced by configuring the system components, as far as technically possible.
