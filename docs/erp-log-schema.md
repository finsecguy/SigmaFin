# Vendor-neutral ERP audit log schema

SigmaFin rules for ERP activity use a custom, vendor-neutral logsource:

```yaml
logsource:
    product: erp
    service: vendor_master   # or payments, user_admin, and later system_audit, reporting
```

This schema is something you map your ERP audit data into. It is not the native format of any ERP product, and no
vendor-specific parser or mapping has been tested. All sample events in `tests/` are synthetic.

## Common fields (every service)

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO 8601 UTC string | Event time, for example `2026-03-02T09:00:00Z`. Required. The test harness rejects samples SQLite cannot parse. |
| `event_id` | string | Unique event identifier. |
| `source_system` | string | Name of the ERP instance. |
| `user` | string | Account that performed the action. |
| `action` | string | Normalized action name. Allowed values are listed per service below. |
| `status` | `success` or `failure` | Outcome of the action. |
| `channel` | `ui`, `api`, `batch` or `import` | How the action was performed. |
| `source_ip` | string | Client address when the ERP records it. Optional. |
| `outside_business_hours` | `true` or `false` | Enrichment field. See below. Optional. |

### Assumption: `outside_business_hours`

Sigma has no time-of-day condition. Rules that need one read a precomputed boolean, `outside_business_hours`. Your
ingestion or enrichment step must compute it from the event time, the ERP's time zone, your working calendar and your
holidays. SigmaFin does not compute it, and a rule that uses it is only as good as that enrichment. Rules that depend
on it say so in their description.

## Service `vendor_master`

Changes to vendor (supplier) master data.

`action` values: `vendor_created`, `vendor_updated`, `vendor_blocked`, `vendor_unblocked`, `vendor_deleted`.

| Field | Description |
|---|---|
| `vendor_id` | Vendor identifier. The correlation key for vendor rules. |
| `vendor_name` | Vendor name. Optional. |
| `field_changed` | For `vendor_updated`, the field that changed, one event per field. |
| `old_value_masked`, `new_value_masked` | Previous and new value, masked. Never log full account numbers. |
| `approval_status` | `approved`, `pending` or `not_required`. |
| `change_reference` | Change request or ticket identifier. Optional. |

`field_changed` vocabulary used by current rules: `bank_account_number`, `iban`, `bank_routing_number`, `swift_bic`,
`bank_name`, `bank_country`. Other values (`payment_terms`, `address_line1`, and so on) are valid and are ignored by
the bank rules.

## Service `payments`

Payment proposals, runs and releases.

`action` values: `payment_proposed`, `payment_approved`, `payment_released`, `payment_run_modified`.

| Field | Description |
|---|---|
| `payment_id` | Payment identifier. |
| `payment_run_id` | Payment run (batch) identifier. |
| `vendor_id` | Vendor paid. Matches `vendor_master.vendor_id`. |
| `amount`, `currency` | Amount as a decimal string and ISO 4217 currency code. |
| `initiator`, `approver` | Accounts that created and approved the payment. Optional. |

## Service `user_admin`

Account and access administration inside the ERP.

`action` values used by current rules: `emergency_access_started`, `role_assigned`. Other values (for example
`user_created`, `role_removed`) are reserved for later rules.

| Field | Description |
|---|---|
| `target_user` | Account that receives the role or the emergency access. Optional for emergency access. |
| `role_name` | Role assigned, for `role_assigned`. |
| `approval_status` | State of the access request behind the change: `approved`, `pending` or `not_required`. Assumed to be recorded by the ERP or joined in by ingestion. |
| `access_id` | Emergency access identifier (the elevated ID that was checked out), for `emergency_access_started`. |
| `ticket_reference` | Incident or change ticket quoted for the emergency access. Optional. |

## Planned services

`system_audit` and `reporting` are reserved. Their fields will be documented here in the same commit as
the first rule that uses them, so reserved services never list fields that no rule or test exercises.

Some fields and values in the services above are defined ahead of use by later rules (`initiator`, `approver`).
Current rules use `action`, `status`, `vendor_id`, `field_changed`, `outside_business_hours`, `role_name` and
`approval_status`. `access_id`, `ticket_reference` and `target_user` are documented for analysts and appear in
samples, but no rule reads them.

## How this relates to real ERP audit data

Real ERPs usually record master data changes as field-level change records (an object, a field, an old value and a
new value) and payments in separate transaction tables. The schema follows that shape on purpose, so a mapping layer
can be thin. That is a design intent, not tested support: SigmaFin has not been run against any ERP's audit data.

## Using the schema with a backend

`pipelines/sigmafin_splunk.yml` maps each service to a Splunk sourcetype (made-up names that you should change). To
rename fields to your ERP's column names, add `field_name_mapping` transformations conditioned on the logsource. The
file contains a commented, untested example of the shape.
