# Database Backup & Restore Runbook — `psql-invoice-trac-harb`

Owner: Platform / on-call engineer
Applies to: Azure Database for PostgreSQL Flexible Server `psql-invoice-trac-harb`
(resource group `rg-invoice-tracker`, region `uksouth`, PostgreSQL 16, `B_Standard_B1ms`, 32 GB).
Infrastructure definition: [`terraform/main.tf`](../terraform/main.tf).

## 1. Backup configuration

| Setting | Value | Notes |
|---|---|---|
| Automated backups | Enabled (always on for Flexible Server) | Daily snapshots + continuous WAL archiving |
| `backup_retention_days` | **30** | Restore to any point in the last 30 days |
| `geo_redundant_backup_enabled` | **true** | Backups replicated to the paired region (`ukwest`), separate from the primary |
| Point-in-time recovery (PITR) | Native | Any second within the retention window |

Verify the live configuration:

```bash
az postgres flexible-server show \
  --resource-group rg-invoice-tracker \
  --name psql-invoice-trac-harb \
  --query "{retention:backup.backupRetentionDays, geo:backup.geoRedundantBackup, earliest:backup.earliestRestoreDate}"
```

Expected: `retention = 30`, `geo = "Enabled"`.

## 2. Enabling geo-redundant backup on an existing server (one-time migration)

`geo_redundant_backup_enabled` **can only be set when a server is created**. It cannot be
toggled in place on an existing server, and Terraform will plan a replacement if it is
changed. If the current `psql-invoice-trac-harb` was provisioned without geo-redundant
backup, it must be migrated to a **new** server — not updated in place:

1. Provision the new server from `terraform/main.tf` with a new name (server names are
   globally unique), e.g.:
   ```bash
   export TF_VAR_admin_login=<POSTGRES_USER>
   export TF_VAR_admin_password="$(az keyvault secret show --vault-name kv-invoice-trac-harb --name <postgres-password-secret> --query value -o tsv)"
   cd terraform
   terraform init
   terraform apply -var server_name=psql-invoice-trac-harb-geo
   ```
2. Schedule a short maintenance window and stop writes (scale the
   `invoice-trac-harb-backend-api` Container App to 0 replicas).
3. Copy the data using **one** of:
   - **pg_dump / pg_restore**:
     ```bash
     pg_dump  -h psql-invoice-trac-harb.postgres.database.azure.com -U <user> -d invoice_tracker -Fc -f invoice_tracker.dump
     createdb -h psql-invoice-trac-harb-geo.postgres.database.azure.com -U <user> invoice_tracker
     pg_restore -h psql-invoice-trac-harb-geo.postgres.database.azure.com -U <user> -d invoice_tracker --no-owner invoice_tracker.dump
     ```
   - **Azure point-in-time restore to a new server** (`az postgres flexible-server restore`,
     see §3) with `--geo-redundant-backup Enabled --backup-retention 30` added, then verify with
     the `az ... show` command in §1 and `terraform import` the restored server instead of
     running step 1.
4. Run smoke checks (§5), then update `POSTGRES_HOST` on the Container App to the new FQDN
   and scale the backend back up.
5. Import the new server into Terraform state, keep the old server for at least 7 days as a
   fallback, then decommission it.

## 3. Point-in-time restore (PITR) — same region

Use for data corruption, accidental deletes, or bad migrations. A restore **always creates a
new server**; the source server is untouched.

```bash
# Restore time must be within the 30-day window, in UTC (ISO 8601).
az postgres flexible-server restore \
  --resource-group rg-invoice-tracker \
  --name psql-invoice-trac-harb-restore-$(date +%Y%m%d%H%M) \
  --source-server psql-invoice-trac-harb \
  --restore-time "2026-11-01T09:30:00Z"
```

Then:
1. Re-apply firewall / networking rules to the restored server if required.
2. Validate data (§5).
3. Either point the backend at the restored server (update `POSTGRES_HOST` on the
   `invoice-trac-harb-backend-api` Container App and restart), or `pg_dump` the affected
   tables from the restored server and load them into the primary.

## 4. Geo-restore — regional outage

Use if `uksouth` is unavailable. Restores from the geo-redundant backup copy into the paired
region.

```bash
az postgres flexible-server geo-restore \
  --resource-group rg-invoice-tracker \
  --name psql-invoice-trac-harb-ukwest \
  --source-server /subscriptions/<subscription-id>/resourceGroups/rg-invoice-tracker/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-invoice-trac-harb \
  --location ukwest
```

Expect an RPO of up to ~1 hour (geo-replicated backup lag). Update `POSTGRES_HOST` on the
backend and validate (§5).

## 5. Post-restore validation

```bash
psql "host=<restored-fqdn> dbname=invoice_tracker user=<user> sslmode=require" \
  -c "SELECT count(*) FROM django_migrations;" \
  -c "SELECT max(applied) FROM django_migrations;"
```

- Row counts of key application tables match expectations for the restore time.
- `python manage.py migrate --check` against the restored server reports no pending migrations.
- Backend health check and login through the frontend succeed.

## 6. Restore test (required before go-live, then at least quarterly)

1. Perform a PITR (§3) to a throwaway server with a restore time ~1 hour in the past.
2. Run the validation in §5.
3. Record the result below, then delete the throwaway server:
   ```bash
   az postgres flexible-server delete --resource-group rg-invoice-tracker --name <throwaway-server> --yes
   ```

| Date (UTC) | Performed by | Type (PITR / geo) | Restore point | Time to restore | Result | Notes |
|---|---|---|---|---|---|---|
| _pending — must be completed before go-live_ | | | | | | |
