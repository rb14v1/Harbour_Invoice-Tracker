# Azure Database for PostgreSQL Flexible Server for invoice_trac_harb.
#
# Backups (requirement rel.backup_configured):
#   - Automated backups are always on for Flexible Server; retention is set to 30 days.
#   - geo_redundant_backup_enabled stores backups in the paired region (uksouth -> ukwest),
#     i.e. separate from the primary server's region.
#   - Point-in-time recovery (PITR) is native to Flexible Server and covers the full
#     retention window.
#
# NOTE: geo_redundant_backup_enabled can only be set at server creation. Applying this to an
# existing server without geo-redundant backup forces a new server. See
# docs/restore-runbook.md for the migration and restore procedure.
#
# Secrets: admin_password is never hardcoded. Supply it via the TF_VAR_admin_password
# environment variable (e.g. populated from Key Vault kv-invoice-trac-harb in CI).

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "resource_group_name" {
  description = "Existing resource group that hosts the database server."
  type        = string
  default     = "rg-invoice-tracker"
}

variable "location" {
  description = "Primary Azure region for the database server."
  type        = string
  default     = "uksouth"
}

variable "server_name" {
  description = "Globally unique name of the PostgreSQL Flexible Server."
  type        = string
  default     = "psql-invoice-trac-harb"
}

variable "admin_login" {
  description = "Administrator login (matches POSTGRES_USER used by the backend). Supply via TF_VAR_admin_login."
  type        = string
}

variable "admin_password" {
  description = "Administrator password (POSTGRES_PASSWORD). Supply via TF_VAR_admin_password or Key Vault; never commit."
  type        = string
  sensitive   = true
}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = var.server_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  # Matches the postgres:16-alpine image used in docker-compose.yml.
  version  = "16"
  sku_name = "B_Standard_B1ms"

  storage_mb = 32768

  administrator_login    = var.admin_login
  administrator_password = var.admin_password

  # Automated backups: 30-day retention, geo-redundant copy in the paired region, PITR native.
  backup_retention_days        = 30
  geo_redundant_backup_enabled = true

  lifecycle {
    # Azure assigns an availability zone at creation; don't fight it on later plans.
    ignore_changes = [zone]

    # Prevent accidental destruction of the primary database (and its backups).
    prevent_destroy = true
  }
}

output "postgresql_server_fqdn" {
  description = "FQDN to use as POSTGRES_HOST for the backend."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgresql_backup_retention_days" {
  value = azurerm_postgresql_flexible_server.main.backup_retention_days
}

output "postgresql_geo_redundant_backup_enabled" {
  value = azurerm_postgresql_flexible_server.main.geo_redundant_backup_enabled
}
