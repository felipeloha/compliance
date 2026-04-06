# OPS - Operations Security

## OPS-01 Capacity management - planning
Capacity and resource planning (personnel and IT resources) follows an established process to avoid potential capacity bottlenecks. These processes include forecasting future capacity requirements to identify usage trends and manage the risks of system overload.

Cloud providers take appropriate measures to ensure that, in the event of capacity bottlenecks or outages of personnel and IT resources, they continue to meet the requirements agreed with cloud customers for the provision of the cloud service.

## OPS-02 Capacity management - monitoring and scaling
Technical and organizational measures for monitoring and provisioning or deprovisioning cloud services are defined. This ensures that the cloud provider ensures that resources are provided or services are rendered in accordance with the contractual agreements and that compliance with service level agreements is ensured.

## OPS-03 Capacity management - cloud customer controls
Depending on the capabilities of the respective service model, the cloud customer is able to control and monitor the allocation of the system resources allocated to it for administration/use in order to avoid over-allocation of resources and achieve sufficient performance.

## OPS-04 Protection against malware - concept
Policies and instructions with specifications for protection against malware are documented, communicated, and provided in accordance with SP-01 with regard to the following aspects:

- Use of system-specific protection mechanisms
- Operation of protection programs on system components under the cloud provider's responsibility that are used to provide the cloud service in the production environment
- Operation of protection programs for employee end devices

## OPS-05 Protection against malware - implementation
System components under the cloud provider's responsibility that are used to provide the cloud service in the production environment are protected according to the specifications defined in the malware protection policies and instructions.

If protection programs with signature- and/or behavior-based malware detection and removal are in place, these protection programs are updated at least daily.

## OPS-06 Data backup and recovery requirements - concept
Policies and instructions with specifications for data backup and recovery are documented, communicated, and provided in accordance with SP-01 regarding the following aspects:

- The scope and frequency of data backups, as well as the retention period, correspond to the contractual agreements with the cloud customers and the cloud provider's operational continuity requirements regarding maximum tolerable downtime (RTO) and maximum permissible data loss (RPO)
- Data backups are encrypted and state-of-the-art
- Access to the backed-up data and recovery operations are permitted only by authorized personnel
- Recovery procedures are tested (see OPS-08)

## OPS-07 Data backup and recovery - monitoring
The cloud provider monitors the implementation of data backups using technical and organizational measures. Any disruptions are investigated and promptly resolved by qualified cloud provider employees to ensure compliance with contractual obligations to cloud customers or the cloud provider's business requirements.

## OPS-08 Data backup and recovery - regular testing
Recovery procedures are tested regularly by the cloud provider, at least annually. These tests allow an assessment of whether contractual agreements and the specifications regarding the maximum tolerable downtime (RTO) and the maximum permissible data loss (RPO) are being adhered to (see BCM-02).

Deviations from the specifications are reported to the responsible personnel or system components at the cloud provider so that they can promptly assess the deviations and initiate the necessary measures.

## OPS-09 Data backup and recovery - retention
The cloud provider transfers the data to be backed up to a remote location or transports it to a remote location on backup media. If the data backup is transferred to the remote location over a network, the data backup or transfer takes place in an encrypted format that complies with the state of the art. The distance from the main location is selected after careful consideration of recovery times and the impact of disasters on both locations. The physical and environmental security measures at the remote location correspond to the level at the main location.

## OPS-10 Logging and monitoring concept
The cloud provider has established policies and instructions governing the logging and monitoring of events on system components under its responsibility. These policies and instructions are documented, communicated, and provided in accordance with SP-01 with regard to the following aspects:

- Definition of events that could lead to a violation of the protection objectives
- Specifications for activating, stopping, and pausing the various logging processes
- Information regarding the purpose and retention period of the logging
- Definition of roles and responsibilities for setting up and monitoring logging
- Time synchronization of system components
- Compliance with legal and regulatory frameworks

## OPS-11 Logging and monitoring - concept for handling metadata
Policies and instructions with specifications for the secure handling of metadata (usage data) are documented, communicated, and provided in accordance with SP-01 with regard to the following aspects:

- Metadata is collected and used exclusively for billing purposes, for troubleshooting faults and errors, and for handling security incidents
- Only anonymized metadata is used to provide and improve the cloud service
- No commercial use
- Storage for a specified period of time reasonably related to the purposes of collection
- Immediate deletion when the purposes of collection have been fulfilled
- Provision to cloud customers in accordance with the contractual agreements

## OPS-12 Logging and monitoring - access, storage and deletion
The requirements for logging and monitoring events and for the secure handling of metadata are implemented through technically supported procedures with the following restrictions:

- Access only for authorized users and systems
- Storage for the specified period
- Deletion when further storage is no longer necessary for the purpose of collection

## OPS-13 Logging and monitoring - event detection
Log data is automatically monitored for events that could lead to a violation of protection objectives, in accordance with the logging and monitoring guidelines. This includes the detection of relationships between events (event correlation).

Identified events are automatically reported to the responsible personnel or system components of the cloud provider for immediate assessment and the necessary actions.

## OPS-14 Logging and monitoring - retention of logging data
The cloud provider stores the generated logging data, regardless of its source, in a suitable and immutable aggregated manner, enabling centralized, authorized analysis of the data. Logging data is deleted when it is no longer required to achieve its intended purpose.

Authentication takes place between logging servers and the assets being logged to protect the integrity and authenticity of the transmitted and stored information. Transmission occurs using state-of-the-art encryption or via a dedicated administration network (out-of-band management).

## OPS-15 Logging and monitoring - accountability
The generated logging data allows for the unique identification of user access at the tenant level to support forensic analysis in the event of a security incident.

Interfaces are available for conducting forensic analysis and securing infrastructure components and their network communications.

## OPS-16 Logging and monitoring - configuration
Access to system components for logging and monitoring under the cloud provider's responsibility is restricted to authorized users. Configuration changes are made in accordance with applicable policies and instructions (see DEV-03).

## OPS-17 Logging and monitoring - availability of monitoring software
The cloud provider monitors the logging and monitoring systems within its area of responsibility to ensure their continuous availability.

## OPS-18 Dealing with vulnerabilities, disruptions and errors - concept
Policies and instructions containing technical and organizational measures are documented, communicated, and provided in accordance with SP-01 to ensure the timely identification and addressing of vulnerabilities in the system components used to provide the cloud service. These policies and instructions contain specifications for the following aspects:

- Regular identification of vulnerabilities
- Assessing the severity of identified vulnerabilities
- Prioritizing and implementing measures for the timely remediation or mitigation of identified vulnerabilities based on severity and within defined timeframes
- Handling system components for which, based on a risk assessment, no measures for the timely remediation or mitigation of vulnerabilities have been initiated

## OPS-19 Dealing with vulnerabilities - penetration testing
The cloud provider must conduct penetration tests at least annually by qualified internal personnel or external service providers. The penetration tests are conducted according to a documented test methodology and cover the system components relevant to the provision of the cloud service within the cloud provider's area of responsibility.

## OPS-20 Dealing with vulnerabilities - measurements and evaluations
The cloud provider conducts regular measurements, analyses, and evaluations of its vulnerability and incident management procedures to verify their ongoing suitability, appropriateness, and effectiveness. Results are evaluated at least quarterly by responsible cloud provider personnel to initiate continuous improvement measures or verify their effectiveness.

## OPS-21 Involvement of the cloud customer in the event of disruptions
The cloud provider will inform the cloud customer regularly and in an appropriate manner, consistent with the contractual agreements, about the status of incidents affecting the cloud customer and, where appropriate and necessary, involve the customer in their resolution. Once an incident has been resolved from the cloud provider's perspective, the cloud customer will be informed of the measures taken in accordance with the contractual agreements.

## OPS-22 Testing and documentation of open vulnerabilities
System components within the cloud provider's area of responsibility are regularly tested for open vulnerabilities, and these are documented in the vulnerability register (see OPS-18).

## OPS-23 System hardening
System components under the cloud provider's responsibility that are used to deliver the cloud service in the production environment are hardened according to generally accepted industry standards. The hardening requirements applicable to each system component are documented.

If immutable images are used, compliance with the hardening requirements is verified during image creation using a consistent process. Configuration and log files relating to the continuous deployment of these images are retained.

## OPS-24 Separation of data sets in the cloud infrastructure
Cloud customers' data stored and processed on shared virtual and physical resources is securely and strictly separated according to a documented concept based on a risk analysis in accordance with OIS-07 to ensure the confidentiality and integrity of this data.
