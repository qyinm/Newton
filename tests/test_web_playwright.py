from newton.backends.web_playwright import selector_description


def test_selector_description_prefers_role_name():
    assert selector_description({"role": "button", "name": "Log in"}) == "role=button[name=Log in]"


def test_selector_description_accepts_test_id():
    assert selector_description({"test_id": "submit"}) == "test_id=submit"


def test_selector_description_accepts_text():
    assert selector_description({"text": "Dashboard"}) == "text=Dashboard"
