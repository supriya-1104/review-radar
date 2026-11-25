"""The aspects a review can be about (spec 02).

Drafted from 60 real reviews of the 3 Bengaluru places and approved on
2026-11-25. All three places are restaurants/cafes (D2), so there is no
separate non-food list yet. Change a definition here and re-run tagging; the
LLM cache is keyed on the prompt, so changed definitions are re-tagged.
"""

ASPECTS: dict[str, str] = {
    "food_taste": "Flavour and how much they liked the food or drink: tasty, bland, "
                  "best biryani, too spicy, great coffee.",
    "food_quality": "Freshness, oiliness, temperature, hygiene of the food itself, "
                    "getting sick: stale, cold, too oily, food poisoning, hair in food.",
    "portion_value": "Quantity and value for money: small portions, fewer pieces, "
                     "overpriced, worth the price, costly.",
    "wait_time": "Waiting for a table, to order, for food or the bill: 40 min wait, "
                 "slow service, quick service, long queue.",
    "staff": "Staff behaviour and skill: rude, courteous, untrained, helpful, "
             "ignored us, shouting.",
    "order_accuracy": "Wrong, missing or unavailable items: got chicken in veg biryani, "
                      "item missing from order, half the menu not available.",
    "cleanliness": "Cleanliness of the place, tables, cutlery, cups, washroom.",
    "ambience": "Atmosphere and comfort: noise, AC, crowding, seating, vibe, music, "
                "good for working, wifi.",
    "location_parking": "Location, access and parking: easy to find, no parking, "
                        "central location.",
    "billing_policies": "Bills and rules: minimum order to sit, cash only, wrong bill, "
                        "service charge, opening hours not kept.",
    "hype": "Expectations vs reality: overhyped, not as good as social media says, "
            "lives up to the hype.",
}

LABELS: dict[str, str] = {
    "food_taste": "Food taste",
    "food_quality": "Food quality & safety",
    "portion_value": "Portion & value",
    "wait_time": "Wait time",
    "staff": "Staff behaviour",
    "order_accuracy": "Order accuracy",
    "cleanliness": "Cleanliness",
    "ambience": "Ambience & comfort",
    "location_parking": "Location & parking",
    "billing_policies": "Billing & policies",
    "hype": "Hype vs reality",
}

SENTIMENTS = ["pos", "neg", "neutral"]

# The owner's words, used on the dashboard (spec 03: "Slow service", not
# "Wait time"). Problems and praise read differently for the same aspect.
PROBLEM_LABELS: dict[str, str] = {
    "food_taste": "Taste",
    "food_quality": "Food quality & safety",
    "portion_value": "Price vs portion size",
    "wait_time": "Slow service & waiting",
    "staff": "Staff behaviour",
    "order_accuracy": "Wrong or missing items",
    "cleanliness": "Cleanliness",
    "ambience": "Crowding, noise & comfort",
    "location_parking": "Location & parking",
    "billing_policies": "Billing & rules",
    "hype": "Not living up to the hype",
}

PRAISE_LABELS: dict[str, str] = {
    "food_taste": "Taste of the food",
    "food_quality": "Fresh, good-quality food",
    "portion_value": "Good value for money",
    "wait_time": "Quick service",
    "staff": "Friendly, helpful staff",
    "order_accuracy": "Orders served right",
    "cleanliness": "Clean place",
    "ambience": "Ambience & comfort",
    "location_parking": "Convenient location",
    "billing_policies": "Fair billing",
    "hype": "Lives up to the hype",
}
