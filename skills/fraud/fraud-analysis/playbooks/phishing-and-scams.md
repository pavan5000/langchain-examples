# Playbook: phishing, social engineering, and authorized push payment (APP) scams

## Indicators
- **Phishing:** the customer clicked a link, entered credentials on a fake
  site, shared a one-time code, or gave details to someone posing as the bank.
  Account takeover often follows, so check that playbook too.
- **APP scam:** the customer sent the money themselves, under false pretences
  such as an investment, romance, fake invoice, impersonated official, or
  "safe account". The payment was authorized but obtained by deception.
- Urgency or secrecy pressure ("don't tell the bank") is a strong signal.

## Tactical actions
1. Hold or recall the scam payment. For P2P transfers and wires, contact the
   receiving institution immediately; speed decides whether the money is
   recovered (owner: fraud_ops, immediate).
2. If credentials or codes were shared, reset them and revoke sessions
   (owner: digital_banking, immediate).
3. Contact the customer through a verified channel. Check whether the
   scammer is still in touch and coaching them, and whether more payments
   are planned (owner: fraud_ops, within_1_hour).
4. Report the phishing domain or phone number for takedown (owner:
   cyber_security, within_24_hours).

## Permanent fixes
- **Customer account:** phishing-resistant MFA, a cooling-off period on new
  payees, and scam-awareness guidance specific to the scam type.
- **Bank controls (when there's a gap):**
  - confirmation-of-payee (name matching) on outbound transfers;
  - dynamic scam warnings at payment time, tailored to the stated purpose;
  - extra friction for first payments to high-risk payees;
  - monitoring of the payee account for mule activity.
