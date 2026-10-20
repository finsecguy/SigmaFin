# Microsoft 365 field assumptions

Rules with `product: m365` use the field names of the Microsoft 365 unified audit log and Exchange admin audit
(`Operation`, `UserId`, `ClientIP`) with one normalization.

## Flattened `Parameters`

In Exchange admin audit records, `Parameters` is a list of name and value pairs. Sigma cannot match inside a list of
objects, and a domain check needs the value of one parameter, not a serialized blob. Rules therefore expect each
parameter as its own field named `Parameters.<Name>`:

```json
{
  "Operation": "New-InboxRule",
  "UserId": "ap@finance.example.com",
  "Parameters.ForwardTo": "audit-desk@mail.example.net"
}
```

Flatten at ingestion (for example with a Splunk field extraction or an ingestion pipeline). SigmaFin does not ship
this normalization. SigmaHQ M365 rules solve the same problem differently, by matching the serialized list with
`Parameters|contains`, which cannot express an external domain check.

Known limitation: when one parameter holds several recipients, the rules judge only the end of the value against the
internal domains. Normalizing to one event per recipient removes the limitation.

## Finance scoping

Audit and sign-in logs do not contain department or group membership. Finance rules scope with a placeholder list,
`finance_mailboxes`, expanded by `|expand` from `pipelines/finance_scope.yml`. Edit that file with your own finance
user principal names and shared mailboxes (AP, treasury, payroll) before converting. An enrichment field would also
work, but SigmaFin does not assume one exists.

The `UserId` field is the account that performed the action. A rule an administrator creates on a finance mailbox
shows the administrator in `UserId`, so it is outside this scope.
