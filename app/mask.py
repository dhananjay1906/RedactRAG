import json
from pathlib import Path
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", "CREDIT_CARD",
            "CASE_NUMBER", "BOOKING_ID"]

# Staff names from the policy "Contacts" sections; spaCy NER misses some of them
_MANIFEST = Path(__file__).parent.parent / "data" / "policies" / "manifest.json"
STAFF_NAMES = [d["pii"]["PERSON"] for d in json.loads(_MANIFEST.read_text(encoding="utf-8"))
               if "PERSON" in d["pii"]]

CUSTOM_RECOGNIZERS = [
    PatternRecognizer(supported_entity="CASE_NUMBER",
        patterns=[Pattern("case", r"\bPRB-\d{4}-\d{6}\b", 0.9)],
        context=["case", "docket", "file"]),
    PatternRecognizer(supported_entity="BOOKING_ID",
        patterns=[Pattern("booking", r"\bBK\d{7}\b", 0.9)],
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
