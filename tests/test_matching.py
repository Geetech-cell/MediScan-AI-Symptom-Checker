import pytest
from streamlit_app import _find_disease_info


@pytest.mark.parametrize(
    "input_name, expect_present",
    [
        ("Influenza", True),
        ("flu-like illness", True),
        ("COVID", True),
        ("covid-19 infection", True),
        ("Migraine headache", True),
        ("appendix pain", True),
        ("heartburn and reflux", True),
        ("earache (otitis)", True),
        ("", False),
        ("nonsense-symptom-xyz", False),
    ],
)
def test_find_disease_info_various(input_name, expect_present):
    info = _find_disease_info(input_name)
    if expect_present:
        assert info is not None, f"Expected a match for '{input_name}'"
        assert isinstance(info.get("desc"), str) and info.get("desc"), "Missing description"
    else:
        assert info is None


def test_find_disease_info_keyword_match():
    # Keywords provided in the DISEASE_INFO should match
    info = _find_disease_info("wheezing and cough")
    assert info is not None
    assert isinstance(info.get("emoji"), str) and info.get("emoji")


def test_find_disease_info_substring():
    info = _find_disease_info("covid pneumonia co-infection")
    assert info is not None
    # either covid-19 or pneumonia info should be returned
    assert isinstance(info.get("desc"), str) and info.get("desc")
