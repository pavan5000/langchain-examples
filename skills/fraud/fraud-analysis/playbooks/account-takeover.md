# Playbook: account takeover (ATO) and SIM swap

## Indicators
- A login from a new device or location, often followed within minutes by a
  password or contact-detail change.
- New payees, or a raised transfer limit, shortly after the login.
- High-value card-not-present purchases or P2P transfers made out of the
  customer's normal pattern.
- **SIM swap:** the customer suddenly loses mobile service, then SMS one-time
  codes arrive at the fraudster's phone.

## Tactical actions (in this order)
1. Hold, cancel or recall pending outbound payments, starting with the
   largest P2P or wire. If a payment has settled, send a recovery request to
   the receiving bank right away (owner: fraud_ops, immediate).
2. Revoke all active sessions, tokens and newly registered devices, and lock
   digital access (owner: digital_banking, immediate).
3. Block any card used in the fraudulent transactions and order a
   replacement (owner: card_services, immediate).
4. Verify the customer out-of-band, using contact details on file *before*
   the takeover. Never use details that changed during the incident (owner:
   fraud_ops, within_1_hour).
5. Reverse any unauthorized changes to contact details, payees and limits
   (owner: digital_banking, within_1_hour).
6. Preserve logs and investigate the payee for mule activity (owner:
   financial_crimes, within_24_hours).

## Permanent fixes
- **Customer account:** phishing-resistant MFA (passkey or authenticator app
  instead of SMS), trusted-device binding, a new card number, and a review of
  recovery contact details.
- **Bank controls (when there's a gap):**
  - step-up authentication for any payment within 24 hours of a password
    reset or new-device login;
  - a hold period on new payees;
  - geo-velocity rules;
  - alerts to the *old* contact details when contact details change;
  - a carrier SIM-swap signal check before trusting SMS codes.
