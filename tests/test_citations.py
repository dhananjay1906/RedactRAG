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
