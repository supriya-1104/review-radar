"""Names reviewers write about themselves are hidden; everything else stays."""

from src.privacy import HIDDEN, hide_names


def test_self_introductions_hidden():
    assert hide_names("Hello, this is KRISHNA I visited today") == f"Hello, this is {HIDDEN} I visited today"
    assert hide_names("My name is Priya Sharma and I loved it") == f"My name is {HIDDEN} and I loved it"
    assert hide_names("Myself Rahul, regular here") == f"Myself {HIDDEN}, regular here"


def test_sign_offs_hidden():
    assert hide_names("Great biryani.\nRegards, Anil") == f"Great biryani.\nRegards, {HIDDEN}"
    assert hide_names("Loved it - Meera") == f"Loved it - {HIDDEN}"


def test_ordinary_words_and_staff_names_kept():
    for text in ["I am very disappointed", "This is The best place", "I am Happy with the food",
                 "The waiter, Sandeep was great", "Thanks to Sandeep for the service, will come again",
                 "This is Meghana's best branch", "biryani was ok", ""]:
        assert hide_names(text) == text


def test_place_name_not_hidden():
    assert hide_names("This is Meghana at its best", exclude_words="Meghana Foods") == \
        "This is Meghana at its best"
