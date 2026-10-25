# Playbook: lost or stolen card

## Indicators
- The customer says they lost the card or it was stolen. Note where and when.
- Transactions made after the loss time are presumed unauthorized. Ones made
  before it are presumed the customer's own unless they say otherwise.
- If a wallet or phone was stolen, other cards, ID documents and the banking
  app may be exposed too.

## Tactical actions
1. Block the card immediately. Use a permanent block for stolen cards; a
   temporary lock is enough if the customer may still find a lost one (owner:
   card_services, immediate).
2. Review transactions since the loss time, and dispute any the customer
   doesn't recognise (owner: card_services, within_1_hour).
3. If a phone was stolen, revoke that device's banking session and digital
   wallet tokens (owner: digital_banking, immediate).
4. Order a replacement card, with expedited delivery if the customer has no
   other way to pay (owner: card_services, within_24_hours).

## Permanent fixes
- **Customer account:** a new card number, refreshed digital wallet tokens,
  and in-app card lock so the customer can act faster next time.
- **Bank controls (when there's a gap):** self-service instant card lock if
  the customer had to wait for an agent; automatic token revocation when a
  card is reported stolen.
