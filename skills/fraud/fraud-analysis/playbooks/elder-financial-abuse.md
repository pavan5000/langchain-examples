# Playbook: elder or vulnerable-customer financial abuse

## Indicators
- The customer is flagged as vulnerable, or mentions age, cognitive decline,
  illness or dependence on a carer.
- A third party (a relative, carer or new "friend") is directing transactions,
  or has recently been added to the account.
- Sudden large withdrawals, changes in spending pattern, or new beneficiaries.

## Tactical actions
1. Hold suspicious outbound payments pending verification (owner: fraud_ops,
   immediate).
2. Speak to the customer directly and privately, not through the third party,
   using a specialist vulnerable-customer team (owner: fraud_ops,
   within_1_hour).
3. Review recently added authorized users, powers of attorney and payees
   (owner: fraud_ops, within_24_hours).
4. Escalate to financial crimes; adult protective services may need to be
   notified, according to policy (owner: financial_crimes, within_24_hours).

## Permanent fixes
- **Customer account:** a trusted contact person on file, lower limits by
  agreement, and alerts to the trusted contact.
- **Bank controls (when there's a gap):** vulnerability flags that trigger
  extra checks on large or unusual payments, and staff training on spotting
  coercion.

State in `analyst_summary` that a specialist must handle the case, since it
needs sensitive, person-to-person contact.
