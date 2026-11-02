# Azure Database for PostgreSQL Flexible Server for invoice_trac_harb.
# Satisfies rel.backup_configured: 30-day automated backups, geo-redundant
# backup storage (paired region), and native point-in-time restore (PITR).
# Restore procedure: see docs/restore-runbook.md.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "resource_group_name" {
  description = "Resource group containing the PostgreSQL server."
  type        = string
  default     = "rg-invoice-tracker"
}

variable "location" {
  description = "Azure region for the primary server. Geo-redundant backups are stored in the paired region."
  type        = string
  default     = "uksouth"
}

variable "server_name" {
  description = "PostgreSQL Flexible Server name."
  type        = string
  default     = "psql-invoice-trac-harb"
}

variable "database_name" {
  description = "Application database name (matches POSTGRES_DB)."
  type        = string
  default     = "invoice_tracker"
}

variable "admin_login" {
  description = "Administrator login (matches POSTGRES_USER). Note: 'postgres' is reserved on Azure Flexible Server. Supply via TF_VAR_admin_login."
  type        = string
}

variable "admin_password" {
  description = "Administrator password (matches POSTGRES_PASSWORD). Supply via TF_VAR_admin_password or from Key Vault; never commit."
  type        = string
  sensitive   = true
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = var.server_name
  resource_group_name = var.resource_group_name
  location            = var.location

  version    = "16"
  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768

  administrator_login    = var.admin_login
  administrator_password = var.admin_password

  # Automated backups with PITR across the full retention window.
  backup_retention_days = 30

  # Store backups in the paired region (separate from the primary).
  # Cannot be changed on an existing server - see docs/restore-runbook.md.
  geo_redundant_backup_enabled = true

  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

output "postgresql_fqdn" {
  description = "Use as POSTGRES_HOST."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}
