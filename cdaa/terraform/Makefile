VARFILE := terraform.tfvars.localstack

TARGETS := \
  -target=aws_dynamodb_table.access_requests \
  -target=aws_lambda_function.slack_access_request_handler \
  -target=aws_lambda_function.daily_reconciliation \
  -target=aws_lambda_function.audit_log_ctl_forwarder \
  -target=aws_ssm_parameter.slack_signing_secret \
  -target=aws_ssm_parameter.slack_bot_token \
  -target=aws_ssm_parameter.config_allowed_durations \
  -target=aws_ssm_parameter.config_customer_data \
  -target=aws_ssm_parameter.config_whitelist_db_users \
  -target=aws_ssm_parameter.config_whitelist_s3_actors \
  -target=aws_ssm_parameter.config_jira_reporting_enabled \
  -target=aws_iam_role.lambda_role

.PHONY: init apply plan destroy

init:
	terraform init

plan:
	terraform plan -var-file=$(VARFILE) $(TARGETS)

apply:
	terraform apply -auto-approve -var-file=$(VARFILE) $(TARGETS)

destroy:
	terraform destroy -var-file=$(VARFILE) $(TARGETS)
