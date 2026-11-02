# Database Restore Runbook — `psql-invoice-trac-harb`

Covers the Azure Database for PostgreSQL Flexible Server defined in
`terraform/main.tf` (resource group `rg-invoice-tracker`, region `uksouth`,
PostgreSQL 16, `B_Standard_B1ms`, 32 GB).

## Backup configuration

| Setting | Value |
|---|---|
| Automated backups | Enabled (Azure-managed, daily snapshots + continuous WAL) |
| Retention | 30 days (`backup_retention_days = 30`) |
| Geo-redundant backup | Enabled (`geo_redundant_backup_enabled = true`) — copies stored in the paired region (UK West) |
| Point-in-time recovery | Native to Flexible Server; any second within the 30-day window |

## Important: enabling geo-redundant backup on an existing server

`geo_redundant_backup_enabled` **can only be set when a server is created**.
It cannot be toggled in place, and Terraform will plan a destroy/recreate if
it is changed on an existing server. **Do not apply that plan against a live
server.** If a server already exists without geo-redundant backup:

1. Provision a **new** server with `geo_redundant_backup_enabled = true`
   (e.g. temporarily set `server_name` to a new name), **or** restore the
   existing server to a new server with geo-redundant backup enabled:
   ```sh
   az postgres flexible-server restore \
     --resource-group rg-invoice-tracker \
     --name <new-server-name> \
     --source-server psql-invoice-trac-harb \
     --geo-redundant-backup Enabled
   ```
2. Alternatively migrate the data with `pg_dump`/`pg_restore`:
   ```sh
   pg_dump -Fc -h <old-fqdn> -U <admin> -d invoice_tracker -f invoice_tracker.dump
   pg_restore -h <new-fqdn> -U <admin> -d invoice_tracker --no-owner invoice_tracker.dump
   ```
3. Repoint the backend (`POSTGRES_HOST`) to the new server, verify, then
   decommission the old server and import the new one into Terraform state.

## Point-in-time restore (PITR)

Restores always create a **new** server; the source is left untouched.

1. Pick the target time (UTC, ISO 8601) within the last 30 days.
2. Restore:
   ```sh
   az postgres flexible-server restore \
     --resource-group rg-invoice-tracker \
     --name psql-invoice-trac-harb-restore \
     --source-server psql-invoice-trac-harb \
     --restore-time "2026-11-01T10:00:00Z"
   ```
3. Re-apply networking/firewall rules and server parameters to the restored
   server if needed (these are not all carried over).

## Geo-restore (regional outage)

If `uksouth` is unavailable, restore from the geo-redundant copy into the
paired region:
```sh
az postgres flexible-server geo-restore \
  --resource-group rg-invoice-tracker \
  --name psql-invoice-trac-harb-geo \
  --source-server <source-server-resource-id> \
  --location ukwest
```
Geo-restore recovers to the latest available geo-replicated backup (RPO is
typically under 1 hour).

## Verification after any restore

1. Connect: `psql "host=<restored-fqdn> dbname=invoice_tracker user=<admin> sslmode=require"`.
2. Check data: `SELECT count(*) FROM django_migrations;` and spot-check row
   counts of the application tables against expectations for the restore time.
3. Point a staging backend at the restored server (`POSTGRES_HOST=<restored-fqdn>`)
   and run `python manage.py migrate --check` and a smoke test of the API.
4. For a real recovery, switch the production backend's `POSTGRES_HOST`
   to the restored server and restart the Container App.

## Restore test (required before go-live, then periodically)

Perform a PITR to a temporary server using the steps above, complete the
verification checklist, then delete the temporary server:
```sh
az postgres flexible-server delete --resource-group rg-invoice-tracker \
  --name psql-invoice-trac-harb-restore --yes
```

Record each test:

| Date | Performed by | Restore type | Target time | Duration | Result |
|---|---|---|---|---|---|
| _pending — complete before go-live_ | | | | | |
