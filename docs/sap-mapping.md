# SAP S/4HANA and ECC mapping

`pipelines/sap_erp.yml` rewrites the vendor-neutral ERP schema in
[erp-log-schema.md](erp-log-schema.md) into SAP table and field names. It is a
pySigma processing pipeline. Pass it after `pipelines/finance_scope.yml`:

```bash
sigma convert -t splunk -p pipelines/finance_scope.yml -p pipelines/sap_erp.yml \
  rules/erp_vendor_payment/erp_vendor_bank_details_changed.yml
```

Nothing in this repository has been executed against a live SAP system. The
checks are local: `scripts/check_sap_pipeline.py` asserts the converted text,
and `tests/test_sap_pipeline.py` runs the SQLite conversion over JSON fixtures
shaped like change-document rows. Where a mapping is uncertain, this page says
so. Do not treat an uncertain row as a field that was confirmed in a system.

Do not pass this pipeline when converting a correlation rule. pySigma applies a
logsource condition to a correlation when any referenced rule has that
logsource, so a single rename would hit both sides of a join. `vendor_id` is
`OBJECTID` on change documents and `LIFNR` on the payment tables. The pipeline
therefore does not rename `vendor_id` or `user`. Alias those in the SIEM, per
source. Hand-written correlation queries stay on the SigmaFin field names and
are documented in [handwritten-correlations.md](handwritten-correlations.md).

## What the pipeline changes

| SigmaFin field or value | SAP predicate the pipeline emits | Confidence |
|---|---|---|
| `action: vendor_updated` on `vendor_master` | `TCODE` in `FK02`, `XK02`, `MK02`, `BP` | High for FK02 and XK02. MK02 is the purchasing equivalent of the same vendor object and is included for that reason. BP is the S/4HANA Business Partner transaction; see the S/4 note below. |
| `action: vendor_created` on `vendor_master` | `TCODE` in `FK01`, `XK01`, `MK01`, `BP` | Same split as the update row. MK01 is the purchasing create transaction. |
| `action: payment_released` on `payments` | `TCODE` = `F110` and not `XVORL` = `X` | Medium. F110 is the automatic payment transaction. `XVORL` = `X` marks a proposal run on `REGUH` and `REGUP`; a blank `XVORL` is an executed run. "Released" is not an SAP status word. |
| `action: role_assigned` on `user_admin` | `TCODE` in `SU01`, `PFCG` | Medium. Both transactions write user-to-role assignments. Mass maintenance (SU10 and friends) is not included. |
| `action: payment_approved`, `payment_run_modified`, `emergency_access_started` | Left as the SigmaFin value | Not mapped. There is no single SAP field these values correspond to. See the per-rule section. |
| `status: success` on product `erp` | Dropped | Change documents and `REGUH`/`REGUP` rows are written for a committed change. They have no success/failure column. A failed attempt is absent, not a row with another status. |
| `field_changed: bank_account_number` | `FNAME` = `BANKN` | High for ECC vendor bank details (`LFBK`). Key-field caveat below. |
| `field_changed: bank_routing_number` | `FNAME` = `BANKL` | Medium. `BANKL` is the SAP bank key, not always a national routing number. |
| `field_changed: bank_country` | `FNAME` = `BANKS` | High for `LFBK`. Same key-field caveat. |
| `field_changed: iban`, `swift_bic`, `bank_name` | Removed from the query | Not columns of `LFBK`. See below. Dropping them is deliberate so the query does not pretend to match those changes. |
| vendor update, any of the bank fields | `OBJECTCLAS` = `KRED`, `TABNAME` = `LFBK`, `CHANGE_IND` = `U` | High for object class `KRED` and table `LFBK` on ECC. `CHANGE_IND` is the header indicator on `CDHDR` (`U` = update). |
| vendor create | `OBJECTCLAS` = `KRED`, `TABNAME` in `LFA1`, `LFB1`, `CHANGE_IND` = `I` | High for `LFA1` (general) and `LFB1` (company code) as tables of object `KRED`. `I` is insert. |
| role assignment | `OBJECTCLAS` = `PFCG`, `TABNAME` = `AGR_USERS` | Medium. Public practitioner guidance reads role-assignment change documents with object class `PFCG`. Confirm in the customer system (transaction SCDO, or one test assignment). |
| `role_name` | `AGR_NAME` | Medium, and only after the SIEM has parsed the role out of the change document. Raw `CDPOS` often keeps the role inside `TABKEY`. |
| `approval_status` | Not renamed | SAP standard `AGR_USERS` has no approval column. |
| `outside_business_hours` | Not renamed | Not an SAP field. The enrichment note in the schema doc still applies. |
| `vendor_id` | Not renamed by the pipeline | Change documents: `CDHDR-OBJECTID`. Payments: `REGUH-LIFNR` / `REGUP-LIFNR`. Alias per source. |
| `user` | Not renamed by the pipeline | Change documents: `CDHDR-USERNAME`. Payment tables do not carry the user who started F110. Security audit log: `SLGUSER`. |

`MK02` and `MK01` are not in the smallest set of transactions (FK02, XK02, BP for a change). They are included because they maintain the same vendor master through purchasing. A system that never uses them is unaffected, because the predicate is an OR.

## Change documents (CDHDR / CDPOS)

Vendor master changes on ECC are change documents. The header table is `CDHDR`, the line table is `CDPOS`. Join them on `OBJECTCLAS`, `OBJECTID` and `CHANGENR`, and land one SIEM event per `CDPOS` line with the header columns copied onto it. The pipeline assumes that shape.

Header columns used here:

| Column | Role |
|---|---|
| `OBJECTCLAS` | Change-document object. `KRED` is the vendor (creditor) master. `LFBK` is one of its tables; `BNKA` (bank master) is not. |
| `OBJECTID` | Object key. For vendor general data this is the vendor number (`LIFNR`), usually with leading zeros. Company-code segments and bank lines also put key fields in `CDPOS-TABKEY`. Confirm the layout with one extracted row before joining to `REGUH-LIFNR`. |
| `USERNAME` | User who saved the change. |
| `UDATE`, `UTIME` | SAP system date and time of the save, not UTC. Build the SIEM timestamp from both, in the system's time zone. |
| `TCODE` | Transaction. Blank or unexpected when the change came from a BAPI, LSMW, `MASS` or `XK99`. Those paths are not in the pipeline, so they will not match. |
| `CHANGE_IND` | Header change type. `U` update, `I` insert. Deletes use other indicators. The line-level column on `CDPOS` is `CHNGIND`, a different name. |

Line columns used here: `TABNAME`, `FNAME`, `CHNGIND`, `VALUE_OLD`, `VALUE_NEW`, `TABKEY`.

The bank rule does not read old and new values. It only asks which field changed. Two caveats, both from public reports rather than from a system checked for this repo:

- Bank country, bank key and bank account are key fields of `LFBK`. The public symptom text of SAP Note 2518878 says updates to `BANKS`, `BANKL` and `BANKN` can be missing from the old/new value columns of the change log. Practitioners also report the previous key showing up in `TABKEY` (a delete of the old line plus an insert of the new one) rather than in `VALUE_OLD` / `VALUE_NEW`. If a test change in the customer system leaves `FNAME` empty and only sets `CHNGIND` to insert or delete on `TABNAME` = `LFBK`, the pipeline's `FNAME` predicate will miss it. Widen the search to the table and the change indicator in that case.
- SAP Note 3683201's public title describes a report for the vendor bank-account change log (`LFBK`, `CDHDR`, `CDPOS`) on S/4HANA. That supports `LFBK` still being the vendor bank table to ask for. It does not prove every S/4 system writes object `KRED` for a Business Partner change.

### Fields that are not on LFBK

| SigmaFin value | Where it actually lives | Why the pipeline drops it |
|---|---|---|
| `iban` | ECC stores IBAN on `TIBAN`, not on `LFBK`. S/4HANA Business Partner bank details are on `BUT0BK`, which has its own IBAN column. Whether `TIBAN` or `BUT0BK` is written under object `KRED` was not confirmed. | An `FNAME` = `IBAN` predicate ANDed with `TABNAME` = `LFBK` would never match. A separate search is required, and only after a test change shows which object class and table the system uses. |
| `swift_bic` | `BNKA-SWIFT`, the bank master. Object `KRED` does not include `BNKA`. Changing a vendor's bank key points at a different `BNKA` row; it does not change `SWIFT`. | A vendor change document is the wrong source. A SWIFT change is a bank-master change (transactions such as FI02). |
| `bank_name` | `BNKA-BANKA`. Same object-class gap as SWIFT. | Same as SWIFT. |

`tests/sap_pipeline/` includes a fixture with `TABNAME` = `TIBAN` and `FNAME` = `IBAN`. The converted bank rule does not match it. That is the gap, locked in as a negative sample.

### S/4HANA Business Partner

Transaction `BP` is in the `TCODE` list because S/4HANA maintains vendors as business partners. The pipeline still requires `OBJECTCLAS` = `KRED`. On many S/4 systems a `BP` save is change-document object `BUPA_BUP` (business partner) with bank data on `BUT0BK`, and a `KRED` document is written only if customer/vendor integration posts one. That combination was not confirmed here. `OBJECTCLAS` = `KRED` together with `TCODE` = `BP` can miss the change.

Before relying on the BP branch, save a vendor bank change in a test client and read `CDHDR` for that user and time. If the object class is `BUPA_BUP`, add it to the pipeline and point `TABNAME` at the table the test row actually uses. Do not add `BUPA_BUP` blindly: it is a wider object than vendor bank details.

## Payment run (F110, REGUH / REGUP)

`REGUH` is the payment header from the payment program. `REGUP` is the cleared items. `REGUV` is control data for the run. These are application tables, not an audit log. They are updated as the run moves from proposal to payment, so a SIEM needs a periodic extract or a change capture, not a one-time snapshot.

Public descriptions of the tables agree on:

| Column | Meaning |
|---|---|
| `XVORL` | `X` means proposal only. Blank means the run was executed. |
| `VBLNR` | Payment document number. Blank on a proposal and on proposal exceptions. |
| `LIFNR` | Vendor. This is the join key to the vendor number, not `OBJECTID`, unless the collector copies one into the other. |
| `LAUFD`, `LAUFI` | Run date and identification. Together they are the payment run id. |

The pipeline maps `payment_released` to `TCODE` = `F110` and not `XVORL` = `X`. It does not require `VBLNR` to be filled. Rows with a blank `XVORL` and a blank `VBLNR` are exceptions that were not paid, and they still match. Add `VBLNR` not empty in the SIEM if that noise matters. Confidence is medium because "payment released" in the Sigma rule is the moment money is sent, while an F110 execution only proves the payment program posted a document. A later approval in Bank Communication Management, or a release in a bank portal, is a different system and is not mapped.

`payment_approved` is not mapped. Classic F110 has no approval column on `REGUH`. An approval, when it exists, is a workflow or Bank Communication Management step in other tables. Inventing a status field would be worse than leaving `action` = `payment_approved` in the query, which is what the pipeline does. The segregation-of-duties correlation needs the approving user. That user is not a column of `REGUH` or `REGUP`. The F110 user is in the job log (SM37) or the application log. The correlation cannot be built from the payment tables alone.

`payment_run_modified` is not mapped. Parameter edits for a run are not standard change documents. The Security Audit Log message AU3 ("Transaction started", message id `AU3` in the event list published by Frank Buchholz from table `TSL1D`) can show that someone started F110. That is not evidence the run was modified. `outside_business_hours` stays an enrichment field.

## Security audit log and role assignment

Display transactions are SM20 and, on newer basis releases, RSAU_READ_LOG. Configuration is SM19 or RSAU_CONFIG. The log is a file (directory from `DIR_AUDIT`) or, on newer releases, database storage the RSAU transactions read. A connector has to export it. ABAP itself is not a supported reader of those files; SAP's own guidance is to keep the directory protected.

Message ids below are the `AU` area plus the one-character sub-id, as listed by Frank Buchholz from `TSL1D` (the public SAP Community post linked at the bottom). Later releases add ids. This is not a full catalog.

| Id | Text in that list | Use |
|---|---|---|
| AU3 | Transaction started | Someone ran a transaction. Weak signal for F110, SU01 or PFCG. Not a field-level change. |
| AU7 | User created | User master, not vendor master. |
| AUB | Authorizations for user changed | SU01 changed authorizations. The role name is not a structured column; it is inside the message data (`SLGDATA`) if it is there at all. |
| AUD | User master record changed | Same limitation. |
| AUC | User logoff | Not a user-master change. Easy to misread from the id alone. |

The pipeline does not emit these ids. AUB and AUD cannot answer "which privileged role was granted", which is what `erp_privileged_role_assigned_without_approval` asks.

Role assignment is a change document on `AGR_USERS` (columns include `AGR_NAME` for the role and `UNAME` for the user) or a `CDPOS` line with `TABNAME` = `AGR_USERS`. The pipeline asks for `OBJECTCLAS` = `PFCG`, `TABNAME` = `AGR_USERS`, `TCODE` in `SU01` or `PFCG`, and `AGR_NAME` in the privileged-role list from `pipelines/finance_scope.yml`. The list is synthetic. Replace it.

Uncertainty to confirm with one assignment in the customer client:

- Object class `PFCG` is what public guidance uses to read `AGR_USERS` changes, including removals. Some systems record the same assignment on the user object instead. If a test assignment does not produce `PFCG`, the rule will not fire.
- A public description of the SUIM view that reads these changes derives the role and the user from `CDPOS-TABKEY`, not from `VALUE_NEW`. `AGR_NAME` in the converted query assumes the collector has already parsed that key into a column. If the SIEM stores raw `TABKEY` only, the query matches nothing.
- `approval_status` is not on `AGR_USERS` and not on the change document. GRC Access Control access requests store approvals in GRC tables, which this pipeline does not map. The Sigma rule alerts when `approval_status` is anything other than `approved`, including missing. On a raw SAP extract the field is missing, so every privileged assignment alerts. That is the same behaviour the rule already documents. Do not deploy it until the field is joined from the request workflow or the noise is accepted.

### Emergency access

There is no Security Audit Log message whose meaning is "emergency access started" or "firefighter session started". The SigmaFin value `emergency_access_started` is left unchanged so the gap stays visible in the query.

Firefighter (emergency access) in SAP GRC Access Control is application data, not the security audit log. Access Control 10 and 12 store session logs in GRC tables; the name commonly cited is `GRACFFLOG`. The older Virsa product used different tables. Column names differ by release, so this pipeline does not rename the SigmaFin fields onto them. A customer with GRC can map `emergency_access_started` onto the firefighter logon row after checking their release's table. A customer without GRC has no standard source for this rule. A logon of a known firefighter user id in the security audit log (successful dialog logon) is only an approximation, and only if those ids are a list the SIEM already has.

## Which rules are fully mappable

| Rule | Result |
|---|---|
| `erp_vendor_bank_details_changed` | Partial. Account number, bank key and bank country on `LFBK` under object `KRED` are mapped. IBAN, SWIFT and bank name are dropped. S/4 `BP` may not write object `KRED`. BAPI and mass changes are not in the `TCODE` list. Key-field changes may sit in `TABKEY` rather than `FNAME`. |
| `erp_new_vendor_created_event` (and the mirrored copies) | Largely mapped for an ECC create through FK01, XK01 or MK01: object `KRED`, tables `LFA1` and `LFB1`, header indicator `I`. The same S/4 and BAPI gaps apply. |
| `erp_vendor_payment_released` (and the mirrored copies) | Partial. Executed F110 run (`XVORL` not `X`). Does not prove a bank release, and does not exclude exceptions with a blank `VBLNR`. |
| `erp_privileged_role_assigned_without_approval` | Partial. `PFCG` / `AGR_USERS` / `SU01` / `PFCG` are emitted, with `AGR_NAME` taken from the placeholder list. Approval state is not an SAP column. Object class and `TABKEY` parsing need a test assignment. |
| `erp_payment_run_modified_outside_hours` | Not mapped, apart from dropping `status`. No standard change document for an F110 parameter edit. `outside_business_hours` is still enrichment. |
| `erp_sod_payment_approved_event` | Not mapped, apart from dropping `status`. No approval field on `REGUH`. |
| `erp_emergency_access_started` | Not mapped, apart from dropping `status`. No security-audit-log message. GRC firefighter logs are a different source and are version-specific. |
| `erp_vendor_bank_change_then_payment`, `erp_new_vendor_paid_quickly`, `erp_vendor_created_and_payment_approved_by_same_user` | Do not convert these with this pipeline. Each one joins two sources that do not share field names. Use the hand-written queries, and substitute the SAP columns from this page per source. |

## Getting the events into a SIEM

The pipeline names SAP columns. The collector has to present those names, or the pipeline has to be edited.

1. Change documents. Extract `CDHDR` joined to `CDPOS` for object classes `KRED` and, after a test change, whatever `BP` actually writes. One event per line. Copy `USERNAME`, `UDATE`, `UTIME`, `TCODE`, `CHANGE_IND` and `OBJECTID` onto the line. Function module `CHANGEDOCUMENT_READ` is the standard reader. Schedule it. Convert `UDATE` and `UTIME` from the SAP system's time zone into the SIEM timestamp the correlation window uses.
2. Payment runs. Extract `REGUH` and `REGUP`, including `XVORL`, `VBLNR`, `LIFNR`, `LAUFD` and `LAUFI`. Capture repeatedly. The tables change in place when a proposal is executed.
3. Security audit log. Export with the SAP audit-log tooling (SM20, RSAU_READ_LOG, or a supported connector). Keep message id, user (`SLGUSER`), transaction and timestamp. Do not point ABAP at the audit files to scrape them; restrict that directory.
4. Role assignments. Either parse `AGR_USERS` change documents (`TABKEY` into role and user) or take a periodic snapshot of `AGR_USERS` and alert on new rows. A snapshot is current state, not the moment of assignment, so the timestamp is the extract time unless the change document is used.
5. Alias `vendor_id` per index: `OBJECTID` (or the vendor number parsed out of it) for change documents, `LIFNR` for `REGUH`/`REGUP`. The hand-written correlations join on `vendor_id` and assume that alias already happened.

Splunk sourcetypes and KQL table names are not set by this pipeline. `pipelines/sigmafin_splunk.yml` and `pipelines/sigmafin_kusto.yml` still use the placeholder names for the vendor-neutral schema. Point those at the indexes or tables the collector actually fills, or add a `sourcetype` / `query_table` item conditioned on the same logsource.

## Sources

These were used for the field names above. They are not a substitute for a test change in the customer client.

- Change documents for vendor bank details, object `KRED`, table `LFBK` included and `BNKA` not included: [SAP Community, change log for vendor bank details](https://community.sap.com/t5/technology-q-a/change-log-related-help/qaq-p/6416698).
- Key fields of vendor bank data missing from old/new values: public symptom text of SAP Note 2518878.
- S/4HANA vendor bank change log naming `LFBK`, `CDHDR`, `CDPOS`: public title of SAP Note 3683201.
- `REGUH` / `REGUP` / `REGUV`, and `XVORL` = `X` for a proposal: [SAP Community, F110 tables](https://community.sap.com/t5/enterprise-resource-planning-q-a/f110-tables/qaq-p/4496238). `REGUP` columns `XVORL`, `LIFNR` and `VBLNR` are also listed at [leanx.eu REGUP](https://leanx.eu/sap/table/regup/).
- Security audit log message ids (`AU3`, `AU7`, `AUB`, `AUD`, `AUC` as logoff): [Frank Buchholz, recommended SM19/SM20 settings, quoting TSL1D](https://community.sap.com/t5/application-development-and-automation-discussions/recommended-settings-for-the-security-audit-log-sm19-sm20/m-p/9205603).
- `AGR_USERS` change documents read with object class `PFCG`: [SAP Community, timestamp of role assignment changes](https://community.sap.com/t5/application-development-and-automation-discussions/time-stemp-for-change-roles-assigments-to-user/m-p/6010208).
