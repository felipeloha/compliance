# COS - Communication Security

## COS-01 Technical protective measures
Based on the results of a risk analysis conducted in accordance with OIS-06, the cloud provider has implemented technical protective measures suitable for promptly detecting and responding to network-based attacks based on anomalous inbound or outbound traffic patterns and/or distributed denial-of-service (DDoS) attacks. Data from appropriately implemented technical protective measures is fed into a comprehensive SIEM system so that necessary countermeasures can be initiated for correlating events. The protective measures are documented, communicated, and provided in accordance with SP-01.

## COS-02 Security requirements for connections in the cloud provider's network
Specific security requirements have been designed, published, and provided for establishing connections within the cloud provider's network. The security requirements specify connection controls and protocols for the cloud provider's area of responsibility.

## COS-03 Monitoring connections in the cloud provider's network
A distinction is made between trusted and untrusted networks. These are separated into different security zones for internal and external network areas (and, if applicable, a DMZ) based on a risk assessment.

Physical and virtualized network environments are designed and configured to restrict and monitor established connections to trusted or untrusted networks in accordance with defined security requirements.

The entire design and configuration for monitoring these connections is reviewed in a risk-oriented manner, at least annually, with regard to the resulting security requirements. Identified vulnerabilities and deviations are subjected to a risk assessment in accordance with the risk management procedure (see OIS-06), and mitigation measures are defined and tracked (see OPS-18).

The business justification for the use of all services, protocols, and ports is reviewed at specified intervals. In addition, the review also includes the justifications for compensating measures for the use of protocols deemed insecure.

## COS-04 Cross-network access
Each network perimeter is controlled by security gateways. Cross-network access authorization is based on a security assessment based on cloud customer requirements.

## COS-05 Networks for administration
Separate networks exist for the administrative management of the infrastructure and for the operation of management consoles. These networks are logically or physically separated from the cloud customer network and protected from unauthorized access by multi-factor authentication (see IDM-09). Networks used by the cloud provider for the purpose of migration or creating virtual machines are also physically or logically separated from other networks.

## COS-06 Segregation of data traffic in shared network environments
Cloud customers' traffic in shared network environments is segregated according to a documented network-level segmentation concept to ensure the confidentiality and integrity of the transmitted data.

## COS-07 Documentation of the network
The logical structure of the network used to provide or operate the cloud service is transparent and up-to-date documented to avoid administrative errors during operation and to ensure timely recovery in the event of a disruption in accordance with contractual obligations. The documentation specifically outlines how the subnets are assigned and how the network is zoned and segmented. It also specifies the geographical locations where cloud customers' data is stored.

## COS-08 Data transfer guidelines
Policies and instructions containing technical and organizational measures to protect data transmission from unauthorized interception, manipulation, copying, modification, redirection, or destruction are documented, communicated, and made available in accordance with SP-01. These specifications establish a reference to the classification of information (see AM-06).
