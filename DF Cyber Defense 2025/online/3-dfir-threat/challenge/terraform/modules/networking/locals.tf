locals {
  vnet_name      = "${var.project_name}-vnet"
  subnet_name    = "default"
  public_ip_name = "${var.project_name}-appgw-pip"
}