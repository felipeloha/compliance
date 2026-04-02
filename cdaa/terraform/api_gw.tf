resource "aws_apigatewayv2_api" "slack_api" {
  name          = "${local.name_prefix}-slack-api"
  protocol_type = "HTTP"
  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "slack_integration" {
  api_id                 = aws_apigatewayv2_api.slack_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.slack_access_request_handler.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "slack_route" {
  api_id    = aws_apigatewayv2_api.slack_api.id
  route_key = "POST ${var.api_path}"
  target    = "integrations/${aws_apigatewayv2_integration.slack_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.slack_api.id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvokeSlack"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_access_request_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack_api.execution_arn}/*/*"
}
