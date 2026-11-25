"""Tagging tests on fake AI answers: no Gemini calls, no cost."""

from src import tag


def test_clean_text_removes_google_html():
    assert tag.clean_text("Great food.<br><br>Slow &amp; rude staff") == "Great food.\n\nSlow & rude staff"
    assert tag.clean_text(None) == ""


def test_quote_check_catches_made_up_quotes():
    text = "Food was amazing but we waited 45 minutes. Didn’t like it"
    assert tag.quote_found("waited 45  Minutes", text)       # spacing/case ignored
    assert tag.quote_found("Didn't like it", text)           # curly vs straight '
    assert not tag.quote_found("the waiter was rude", text)   # not in the review
    assert not tag.quote_found("", text)


BATCH = [("r1", "Biryani was cold and we waited 40 mins"), ("r2", "nice place")]


def test_validate_keeps_good_tags_and_drops_bad_ones():
    answer = {"reviews": [
        {"id": "r1",
         "aspects": [
             {"aspect": "wait_time", "sentiment": "neg", "quote": "waited 40 mins"},
             {"aspect": "staff", "sentiment": "neg", "quote": "the staff was rude"},   # made up
             {"aspect": "parking", "sentiment": "neg", "quote": "Biryani"},           # not an aspect
         ],
         "dishes": [{"dish_raw": "Biryani", "sentiment": "neg",
                     "aspect": "food_quality", "quote": "Biryani was cold"}]},
        {"id": "r2", "aspects": [], "dishes": []},
        {"id": "r99", "aspects": [], "dishes": []},                                  # unknown id
    ]}
    result, stats = tag.validate(answer, BATCH)
    assert [a["aspect"] for a in result["r1"]["aspects"]] == ["wait_time"]
    assert result["r1"]["dishes"][0]["dish_raw"] == "Biryani"
    assert result["r2"] == {"aspects": [], "dishes": []}
    assert stats["quote_not_found"] == 1 and stats["invalid_tag"] == 1
    assert stats["unknown_id"] == 1 and stats["missing_id"] == 0


def test_generic_words_are_not_dishes():
    batch = [("r1", "Coffee was cold but the filter coffee was great")]
    answer = {"reviews": [{"id": "r1", "aspects": [], "dishes": [
        {"dish_raw": "Coffee", "sentiment": "neg", "aspect": "food_quality", "quote": "Coffee was cold"},
        {"dish_raw": "filter coffee", "sentiment": "pos", "aspect": "food_taste",
         "quote": "filter coffee was great"}]}]}
    result, stats = tag.validate(answer, batch)
    assert [d["dish_raw"] for d in result["r1"]["dishes"]] == ["filter coffee"]
    assert stats["generic_dish_dropped"] == 1


def test_dish_spelling_variants_share_one_key():
    keys = {tag.dish_key(n) for n in ["Biriyani", "biryani", "briyani", "biriyanis", "Biryani"]}
    assert keys == {"biryani"}
    assert tag.dish_key("Meghna Spl Biriyani") == tag.dish_key("Meghana's special biryani")
    assert tag.dish_key("Chiken biryani") == "chicken biryani"
    assert tag.dish_key("mutton biryani") != tag.dish_key("chicken biryani")


def test_failed_batch_counts_every_review_as_missing():
    result, stats = tag.validate(None, BATCH)
    assert result == {} and stats["batch_failed"] == 1 and stats["missing_id"] == 2


def test_prompt_lists_every_aspect():
    prompt = tag.tag_prompt(BATCH)
    for key in tag.ASPECTS:
        assert key in prompt
