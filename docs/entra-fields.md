# Microsoft Entra field assumptions

Rules with `product: azure` and `service: signinlogs` use the column names of the `SigninLogs` table of the Azure
Monitor Logs reference (https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/signinlogs).

| Field | Meaning | Used for |
|---|---|---|
| `UserPrincipalName` | UPN of the user who signed in | Scoping to finance users |
| `ResultType` | `0` is success, any other value is a failure | Keeping only successful sign-ins |
| `Location` | Two letter country code of the sign-in | Country allowlist |
| `RiskEventTypes_V2` | List of risk event types as a string, such as `anonymizedIPAddress` | Anonymous IP detection |

The sign-in records in SigmaFin samples are flat and use these column names. A SIEM that stores the same data under
other names (for example the Microsoft Graph `signIn` resource, which has `userPrincipalName` and
`location.countryOrRegion`) needs a field mapping in the conversion pipeline. SigmaFin does not ship one.

`RiskEventTypes_V2` is matched with `contains`, so it works whether your ingestion keeps the list as a JSON string or
joins it with commas. If your ingestion splits the list into separate events or fields, adjust the rule.

Known behaviour: `Location` is a country code only when Entra could resolve one. A successful finance sign-in with
an empty or missing `Location` is not on the allowed list, so `entra_finance_signin_unlisted_country` alerts on it.
Both cases are positive samples and run on SQLite. The Splunk query is `NOT Location IN (...)`, which also matches
a missing field, but that is not executed anywhere yet.

## Finance scoping

Sign-in logs do not contain department or group membership. Finance rules scope with the placeholder lists
`finance_users` and `allowed_countries`, expanded by `|expand` from `pipelines/finance_scope.yml`. Edit that file
before converting. The shipped values are synthetic.
