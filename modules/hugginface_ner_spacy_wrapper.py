import spacy
from spacy.language import Language
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from spacy.util import filter_spans

model_name = "models/montebovi"

LABEL_MAP = {
    "NOME": "Person",
    "COGNOME": "Person",
    "DATA_NASCITA": "Date",
    "DATA_MORTE": "Date",
    "ETA": "Person",
    "PROFESSIONE": "Person",
    "STATO_CIVILE": "Person",
    "CODICE_FISCALE": "ID",
    "NUMERO_TELEFONO": "ID",
    "EMAIL": "ID",
    "CODICE_POSTALE": "ID",
    "INDIRIZZO": "ID",
    "NUMERO_CARTA": "ID",
    "CVV": "ID",
    "NUMERO_CONTO": "ID",
    "IBAN": "ID",
    "BIC": "ID",
    "P_IVA": "ID",
    "TASSO_MUTUO": "ID",
    "NUM_ASSEGNO_BANCARIO": "ID",
    "RAGIONE_SOCIALE": "Company",
    "TRIBUNALE": "Company",
    "LEGGE": "ID",
    "N_SENTENZA": "ID",
    "N_LICENZA": "ID",
    "AVV_NOTAIO": "Person",
    "REGIME_PATRIMONIALE": "ID",
    "CARTELLA_CLINICA": "ID",
    "MALATTIA": "ID",
    "MEDICINA": "ID",
    "STORIA_CLINICA": "ID",
    "IP": "ID",
    "IPV6_1": "ID",
    "MAC": "ID",
    "USER_AGENT": "ID",
    "IMEI": "ID",
    "STATO": "Location",
    "LUOGO": "Location",
    "ORARIO": "Date",
    "DATA": "Date",
    "NUMERO_DOCUMENTO": "ID",
    "TARGA_VEICOLO": "ID",
    "URL": "ID",
    "PASSWORD": "ID",
    "PIN": "ID",
    "BRAND": "Company",
    "BANCA": "Company"
}

# Carica tokenizer e modello Hugging Face
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)
hf_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

# Crea modello spaCy vuoto
nlp = spacy.blank("it")

# Componente custom come classe (non solo funzione)
class HFNERComponent:
    def __init__(self, pipeline, label_map):
        self.pipeline = pipeline
        self.label_map = label_map
        self.labels = sorted(set(label_map.values()))  # necessario per compatibilità

    def __call__(self, doc):
        entities = self.pipeline(doc.text)
        spans = []
        for ent in entities:
            raw_label = ent['entity_group']
            if raw_label not in self.label_map:
                continue
            mapped_label = self.label_map[raw_label]
            start = doc.text.find(ent['word'])
            end = start + len(ent['word'])
            span = doc.char_span(start, end, label=mapped_label, alignment_mode='expand')
            if span:
                spans.append(span)
        doc.ents = filter_spans(spans)
        return doc

# Factory con protezione
if not Language.has_factory("hf_ner"):
    @Language.factory("hf_ner")
    def create_hf_ner_component(nlp, name):
        return HFNERComponent(hf_pipeline, LABEL_MAP)

# Inserisce nella pipeline come "ner"
nlp.add_pipe("hf_ner", name="ner")

# Funzione da importare
def load_hugginface_model_as_spacy():
    return nlp
