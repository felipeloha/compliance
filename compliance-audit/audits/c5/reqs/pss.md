# PSS - Product and Service Security

## PSS-01 Guidelines and recommendations for cloud customers
The cloud provider makes guidelines and recommendations for the secure use of the provided cloud service available to cloud customers. The information contained therein is suitable for supporting cloud customers in the secure configuration, installation, and use of the cloud service, insofar as this is applicable to the cloud service and is the responsibility of the cloud customer.

The type and scope of the information provided are based on the needs of the cloud customer's expert personnel who establish information security requirements, implement them, or monitor their implementation (e.g., IT, compliance, internal audit). The information in the guidelines and recommendations for the secure use of the provided cloud service specifically addresses the following aspects, insofar as they are applicable to the cloud service:

- Instructions regarding secure configuration
- Information sources on known vulnerabilities and update mechanisms
- Error handling and logging mechanisms
- Authentication mechanisms
- Role and rights concept, including risky combinations
- Services and functions for administering the cloud service by privileged users

The information is maintained in such a way that it is applicable to the provided cloud service in the version intended for productive use.

## PSS-02 Identification of vulnerabilities in the cloud service
The cloud provider uses appropriate procedures to check the cloud service for vulnerabilities that may be introduced into the cloud service through the software development process.

The procedures for identifying such vulnerabilities are part of the software development process and, depending on the risk assessment, include the following activities:

- Static code analysis
- Dynamic code analysis
- Code reviews by qualified personnel of the cloud provider
- Obtaining information about confirmed vulnerabilities in software libraries provided by third parties and used in the cloud service

The severity of identified vulnerabilities is assessed according to defined criteria, and measures are initiated for timely remediation or mitigation.

## PSS-03 Online register of known vulnerabilities
The cloud provider maintains or refers to a daily updated online register of known vulnerabilities affecting the cloud service provided and assets provided by the cloud provider that cloud customers must install, deploy, or operate themselves within their area of responsibility.

## PSS-04 Error handling and logging mechanisms
The provided cloud service is equipped with error handling and logging mechanisms. These enable cloud customers to retrieve security-relevant information about the security status of the cloud service as well as the data, services, or functions it provides.

The information is sufficiently detailed to allow cloud customers to review the following aspects, as far as they are applicable to the cloud service:

- Which data, services, or functions are available to the cloud customer in the cloud service, when, and by whom they were accessed
- Errors in the processing of automatic or manual actions
- Changes to security-relevant configuration parameters, error handling and logging mechanisms, user authentication, action authorization, cryptography, and communication security

The logged information is protected from unauthorized access and modification and can be deleted by the cloud customer.

If the cloud customer is responsible for activating or determining the type and scope of logging, the cloud provider will provide suitable logging functions.

## PSS-05 Authentication mechanisms
The provided cloud service offers authentication mechanisms that can be used to enforce strong authentication (e.g., two- or multi-factor authentication) for users, IT components, or applications under the responsibility of the cloud customer.

These authentication mechanisms are implemented at all access points that enable users, IT components, or applications to interact with the cloud service.

These authentication mechanisms are enforced for privileged users, IT components, or applications.

## PSS-06 Session Management
To protect confidentiality, availability, integrity, and authenticity during interactions with the cloud service, appropriate session management is used, which at least corresponds to the state of the art and is protected against known attacks. Mechanisms are implemented that invalidate a session if it detects inactivity.

## PSS-07 Confidentiality of authentication information
If passwords are used as authentication information for the cloud service, their confidentiality is ensured by the following procedures:

- Users can initially create the password themselves or must change an initially predefined password upon first logging into the cloud service. An initially predefined password expires after a maximum of 14 days.
- When creating passwords, compliance with the length and complexity requirements of the cloud provider (see IDM-09) or the cloud customer is technically enforced.
- The user is informed about changing or resetting the password.
- Server-side storage is carried out using cryptographically strong hash functions that correspond to the state of the art, in combination with salt values.

## PSS-08 Roles and rights concept
The cloud provider provides cloud customers with a role and rights concept for managing access authorizations. This framework describes rights profiles for the functions provided by the cloud service.

The rights profiles are designed to enable cloud customers to manage access authorizations according to the principle of least privilege and as necessary for the performance of their tasks, as well as to implement the principle of separation of duties between operational and supervisory functions.

## PSS-09 Authorization mechanisms
Access to the functions provided by the cloud service is restricted by access controls (authorization mechanisms) that verify whether users, IT components, or applications are authorized to perform certain actions.

The cloud provider validates the functionality of the authorization mechanisms before new functions are made available to cloud customers, as well as when changes are made to the authorization mechanisms of existing functions (see DEV-06). The severity of identified vulnerabilities is assessed according to defined criteria based on industry-standard metrics, and measures are initiated for timely remediation or mitigation.

## PSS-10 Software-defined Networking
If the cloud service offers software-defined networking (SDN) capabilities, the confidentiality of the cloud customer's data is ensured through appropriate SDN procedures.

The cloud provider validates the functionality of the SDN capabilities before providing new SDN capabilities to the cloud customer or modifying existing SDN capabilities. Identified deficiencies are assessed and remedied in a risk-oriented manner.

## PSS-11 Images for virtual machines and containers
To the extent that cloud customers operate virtual machines or containers with the cloud service, the cloud provider must ensure the following aspects:

- The cloud customer can restrict the selection of virtual machine or container images according to its specifications, so that users of this cloud customer can only launch images or containers approved in accordance with these restrictions
- If the cloud provider makes virtual machine or container images available to the cloud customer, it will inform the cloud customer about the changes made compared to the previous version
- The images provided by the cloud provider are hardened according to generally accepted industry standards

## PSS-12 Locations of data processing and storage
The cloud customer is able to determine the locations (city/country) for data processing and storage, including data backups, according to the contractually available options. This must be ensured by the cloud architecture.
