import json
from pathlib import Path
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", "CREDIT_CARD",
            "CASE_NUMBER", "BOOKING_ID"]

# Known staff names (stand-in for the HR staff directory); spaCy NER misses some of them.
# Must NOT be loaded from data/policies/manifest.json: that file is the leak test's answer key.
_STAFF_DIRECTORY = Path(__file__).parent.parent / "config" / "staff_directory.json"
STAFF_NAMES = json.loads(_STAFF_DIRECTORY.read_text(encoding="utf-8"))

CUSTOM_RECOGNIZERS = [
    # Presidio compiles these case-insensitively, so "prb-..." and "bk..." also match.
    # Separator after the prefix may be "-", a space or nothing. A bare number is only
    # matched right after a label ("Case #", "Booking:"); the lookbehinds keep the label
    # out of the span and stop every 7-digit number from being masked.
    PatternRecognizer(supported_entity="CASE_NUMBER",
        patterns=[Pattern("case", r"\bPRB[-\s]?\d{4}[-\s]\d{6}\b", 0.9),
                  Pattern("case_labeled",
                          r"(?:(?<=case\s#)|(?<=case#)|(?<=case\s)|(?<=docket\s))\d{4}-\d{6}\b", 0.8)],
        context=["case", "docket", "file"]),
    PatternRecognizer(supported_entity="BOOKING_ID",
        patterns=[Pattern("booking", r"\bBK[-\s]?\d{7}\b", 0.9),
                  Pattern("booking_labeled",
                          r"(?:(?<=booking:\s)|(?<=booking\s)|(?<=booking#)|(?<=booking\s#))\d{7}\b", 0.8)],
        context=["booking"]),
    PatternRecognizer(supported_entity="PHONE_NUMBER", name="ExtendedPhoneRecognizer",
        patterns=[Pattern("us_phone_ext",
            r"(?:\+?1[-.\s]?|001[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?:\s?(?:x|ext\.?)\s?\d{1,5})?", 0.7)],
        context=["phone", "contact", "reach", "call"]),
    # Presidio's built-in email recognizer rejects non-real TLDs (e.g. .example)
    PatternRecognizer(supported_entity="EMAIL_ADDRESS", name="AnyTldEmailRecognizer",
        patterns=[Pattern("email_any_tld", r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", 0.8)]),
    PatternRecognizer(supported_entity="PERSON", name="StaffNameRecognizer",
        deny_list=STAFF_NAMES),
]

nlp = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]}).create_engine()
base_analyzer = AnalyzerEngine(nlp_engine=nlp)
custom_analyzer = AnalyzerEngine(nlp_engine=nlp)
for rec in CUSTOM_RECOGNIZERS:
    custom_analyzer.registry.add_recognizer(rec)
anonymizer = AnonymizerEngine()

def analyze(text: str, custom: bool = True):
    a = custom_analyzer if custom else base_analyzer
    return a.analyze(text=text, language="en", entities=ENTITIES)

def mask(text: str, custom: bool = True) -> str:
    return anonymizer.anonymize(text=text, analyzer_results=analyze(text, custom)).text
