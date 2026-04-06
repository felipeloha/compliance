# DEV - Secure Development

## DEV-01 Guidelines for the development/procurement of information systems
Policies and instructions containing technical and organizational measures for the secure development of the cloud service are documented, communicated, and made available in accordance with SP-01.

The policies and instructions contain specifications throughout the entire lifecycle of the cloud service and are based on recognized standards and methods with regard to the following aspects:

- Security in software development (requirements, design, implementation, testing, and review)
- Security in software deployment
- Security in operations (response to identified errors and vulnerabilities)

## DEV-02 Outsourcing development
If the development of the cloud service (or individual system components) is outsourced, specifications regarding the following aspects must be contractually agreed between the cloud provider and the outsourced development contractor:

- Security in software development (requirements, design, implementation, testing, and verification) in accordance with recognized standards and methods
- Acceptance testing of the quality of the services provided in accordance with the agreed functional and non-functional requirements
- Submission of evidence that sufficient verifications have been performed to rule out the existence of known vulnerabilities

## DEV-03 Guidelines for changing information systems
Policies and instructions containing technical and organizational measures for managing changes (change management) to system components of the cloud service within the framework of software provision are documented, communicated, and provided in accordance with SP-01 with regard to the following aspects:

- Criteria for risk assessment, categorization, and prioritization of changes and associated requirements regarding the type and scope of tests to be performed, as well as the necessary approvals for development/implementation of the change and the releases for deployment in the production environment
- Requirements for the execution and documentation of tests
- Requirements for the separation of duties during development, testing, and release of changes
- Requirements for the appropriate information of cloud customers about the type and scope of the change and the resulting cooperation obligations in accordance with the contractual agreements
- Requirements for the documentation of changes in the system, operational, and user documentation
- Requirements for the execution and documentation of emergency changes, which must meet the same security level as normal changes

## DEV-04 Security training for software delivery
The cloud provider operates a program for regular, targeted security training and awareness-raising among internal and external employees regarding standards and methods for secure software development and deployment, as well as the use of the tools used for this purpose. The program is regularly reviewed and adjusted with regard to the applicable policies and instructions, the assigned roles and responsibilities, and the tools used.

## DEV-05 Risk assessment, categorization and prioritization of changes
Changes are subjected to a risk assessment with regard to potential impacts on the affected system components in accordance with the Change Management Guidelines (see DEV-03) and are categorized and prioritized accordingly.

## DEV-06 Testing the changes
Changes to the cloud service are subjected to appropriate testing as part of the software development and deployment process.

The type and scope of the tests are determined based on the risk assessment. They are performed by appropriately qualified personnel from the cloud provider or by automated testing procedures that comply with recognized standards of technology. Cloud customers are involved in the testing process in accordance with contractual requirements.

The severity of errors and vulnerabilities identified in the tests that are relevant for acceptance are assessed according to defined criteria, and measures are initiated for timely remediation or mitigation.

## DEV-07 Logging changes
System components and tools for source code management and software deployment used to implement changes to system components of the cloud service in the production environment are subject to a role and rights concept in accordance with IDM-01 and authorization mechanisms. They must be configured so that all changes are logged and can thus be traced back to the individuals or system components who made the changes.

## DEV-08 Version control
Version control procedures are in place to track dependencies between individual changes and to restore affected system components to their previous state as a result of errors or identified vulnerabilities.

## DEV-09 Releases for deployment in the production environment
Authorized personnel or system components of the cloud provider release changes to the cloud service based on defined criteria (e.g., test results and required approvals) before they are deployed to cloud customers in the production environment.

Cloud customers are involved in the release process according to contractual requirements.

## DEV-10 Separation of environments
Production environments are physically or logically separated from test or development environments to prevent unauthorized access to cloud customer data, the spread of malware, or changes to system components. Data from production environments is not used in test or development environments to protect their confidentiality.
