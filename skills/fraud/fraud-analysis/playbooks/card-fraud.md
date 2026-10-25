# Playbook: card fraud (card-not-present, skimming or counterfeit, friendly fraud)

## Indicators
- **Card-not-present:** online or phone purchases the customer doesn't
  recognise, often several small test charges followed by large ones.
- **Skimming or counterfeit:** card-present charges in a place the customer
  wasn't, while the card is still in their possession. A recent ATM or
  fuel-pump visit is a common origin.
- **Friendly fraud:** the customer or a household member made the charge, for
  example a forgotten subscription or a child's in-app purchase. Consider this
  before concluding a third party was involved, but never accuse the customer.

## Tactical actions
1. Block the affected card and decline pending authorizations from the same
   merchants (owner: card_services, immediate).
2. File a dispute or chargeback for each unauthorized transaction, listing
   the amounts (owner: card_services, within_24_hours).
3. Order a replacement card with a new number and expiry date (owner:
   card_services, within_24_hours).
4. For skimming, report the suspected compromise point so the card network
   can investigate it (owner: fraud_ops, within_24_hours).

## Permanent fixes
- **Customer account:** a new card number, transaction alerts, card controls
  in the app (online or international on/off), and virtual card numbers for
  online shopping.
- **Bank controls (when there's a gap):**
  - card-testing velocity rules (many small authorizations from one merchant
    category);
  - 3-D Secure step-up for high-risk card-not-present merchants;
  - linking common-point-of-purchase analysis to proactive card reissue.
