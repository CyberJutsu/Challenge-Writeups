resource "azurerm_api_management_api_policy" "real_ip_policy" {
  api_name            = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name

  xml_content = <<XML
<policies>
  <inbound>
    <base />
    <set-variable name="client-ip" value="@{
      string xForwardedFor = context.Request.Headers.GetValueOrDefault("X-Forwarded-For", "");
      if (!string.IsNullOrEmpty(xForwardedFor)) {
        return xForwardedFor.Split(',')[0].Trim();
      }
      return context.Request.Headers.GetValueOrDefault("X-Real-IP", context.Request.IpAddress);
    }" />
    <set-variable name="user-agent" value="@(context.Request.Headers.GetValueOrDefault("User-Agent", ""))" />
    <set-variable name="custom-telemetry" value="@{
      return new JObject(
        new JProperty("timestamp", DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")),
        new JProperty("clientIP", (string)context.Variables["client-ip"]),
        new JProperty("userAgent", (string)context.Variables["user-agent"]),
        new JProperty("method", context.Request.Method),
        new JProperty("url", context.Request.Url.ToString()),
        new JProperty("requestId", context.RequestId)
      ).ToString();
    }" />
    <trace source="custom-telemetry">
      <message>@((string)context.Variables["custom-telemetry"])</message>
    </trace>
  </inbound>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
XML

  depends_on = [azurerm_api_management_api.api]
}