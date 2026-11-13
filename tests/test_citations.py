from app.agent import check_citations

CHUNKS = [{"doc": "drug-testing.md", "content": "The fee is $12 per test."}]

def test_supported_answer_passes():
    r = check_citations({"answer": "The fee is $12 [drug-testing.md].", "chunks": CHUNKS})
    assert r["citations"] == ["drug-testing.md"]

def test_made_up_number_is_rejected():
    r = check_citations({"answer": "The fee is $50 [drug-testing.md].", "chunks": CHUNKS})
    assert r["citations"] == []

def test_uncited_file_is_rejected():
    r = check_citations({"answer": "The fee is $12 [other.md].", "chunks": CHUNKS})
    assert r["citations"] == []

# Source for the stricter cases: numbers that are substrings of each other, plus a formatted one.
SRC = [{"doc": "p.md", "content": "The fee is $12 per test. Records are kept for 120 days. "
                                  "Insurance of at least $500,000 and 1200 pages. At least one form."}]

def ok(answer):
    return check_citations({"answer": answer + " [p.md]", "chunks": SRC})["citations"] == ["p.md"]

def test_substring_numbers_are_rejected():
    for wrong in ["The fee is $1.", "The fee is $2.", "The fee is $20.", "Kept for 12 days and 0 hours."]:
        assert not ok(wrong), wrong

def test_formatting_differences_pass():
    for right in ["The fee is $12.00.", "Kept for 120 days.", "Up to 1,200 pages.", "At least $500000."]:
        assert ok(right), right

def test_number_words():
    assert ok("The fee is twelve dollars.")
    assert not ok("The fee is twenty dollars.")
    assert ok("Bring at least one form.")          # "one" is not treated as a number
