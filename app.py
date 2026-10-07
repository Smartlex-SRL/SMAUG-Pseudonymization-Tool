import io
from datetime import datetime

import streamlit as st
from modules.anonymizer import anonymize
from modules.ner import load_models, ner_anonyzer_html_post_beautifier, visualize_ner
from modules.pdf_utils import add_editor, beautifyCodeWithoutEntities, convert_pdf2html, pre_process, text_from_pdf
from spacy.tokens import Span

# Aggiunge dei campi custom al modello Spacy: strategia e indice interno della ricorrenza. Serve per realizzare P.1, P.2 ecc.
if not Span.has_extension("internal_index"):
    Span.set_extension("internal_index", default=None)
if not Span.has_extension("strategy"):
    Span.set_extension("strategy", default=None)


# Imposta la pagina Streamlit
st.set_page_config(page_title="PT — Pseudonymization Tool", layout="centered")
st.title("🔐 PT — Pseudonymization Tool")

# Carica i modelli e popola la dropdown dell'elenco dei modelli (bert/electra)
models = load_models()
model_name = st.sidebar.selectbox("NER Model", options=list(models.keys()))

# Imposta il modello basandosi sulla selezione della dropdown dell'elenco dei modelli
model = models[model_name]

# Casella di testo per inserimento eventuale testo da anonimizzare
text_input = st.text_area("Enter the text to pseudonymize:", "Mario Rossi lives in Milan and works at Enel.")

# Caricamento del file PDF
uploaded_file = st.file_uploader("Or upload a PDF", type=["pdf"])

# Quando si carica un file PDF, viene estratto il testo e pre-processato solo per l'anteprima
if uploaded_file:
    raw_bytes = uploaded_file.read()
    text = text_from_pdf(io.BytesIO(raw_bytes))
    text_input = pre_process(text)
# Elaborazione del testo (Proveniente dalla casella di testo o da file PDF pre-processato)
if text_input:
    # Viene applicato il modello scelto al testo (recupero di tutte le label, entities, occorrenze)
    doc = model(text_input)

    st.markdown("---")
    st.subheader("🔧 Select strategy")

    # Elenco completo delle strategie
    ALL_STRATEGIES = [
        "No",  # Nessuna anonimizzazione
        "OMISSIS",
        "Initials",
        "Tagging",
        "Tagging-CP",
        "Tagging-Gen",
        "Random-CP",
    ]

    # Popola la dropdown per la scelta della strategia di anonimizzazion
    strategy = st.selectbox("Pseudonymization strategy", ALL_STRATEGIES)

    # Recupera le label disponibili nel modello e popola la casella di selezione (ID,Person,Location,Company,Date)
    labels = model.get_pipe("ner").labels
    selected_labels = st.sidebar.multiselect("Entity labels", options=labels, default=list(labels))

    if strategy != "No":
        # Anonimizzazione del testo (Mostra anteprima non formattata con entities in grassetto).
        result = anonymize(doc, strategy=strategy, selected_ner_label=selected_labels)
        st.subheader("📄 Pseudonymized text")
        st.markdown(result)

    else:
        # Visualizzazione del testo (Mostra anteprima non formattata con entities in formato TAG)
        visualize_ner(doc, labels=selected_labels)

else:
    st.info("Enter some text or upload a PDF to get started.")

if uploaded_file is not None:
    # Anonimizzazione PDF

    # Genera un timestamp per salvare i documenti in modo univoco e non creare conflitti: es. "20230409_193045_123456"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # Converte il PDF in Html (conversione esatta: uno span per ogni carattere)
    html = convert_pdf2html(io.BytesIO(raw_bytes))
    # Raggruppamento SPAN per riga e per colonna
    html = beautifyCodeWithoutEntities(html)
    html_originale = html
    # Applica anonimizzazione all'html
    html = ner_anonyzer_html_post_beautifier(html, model, selected_labels, strategy)

    # Aggiunge editor in javascript
    html = add_editor(html, f"processed_{timestamp}", doc, strategy, True)

    # Scrive su file la versione originale e quella anonimizzata
    original_filename = f"static/output/original_{timestamp}.html"
    processed_filename = f"static/output/processed_{timestamp}.html"

    with open(original_filename, "w") as f:
        f.write(html_originale)

    with open(processed_filename, "w") as f:
        f.write(html)

    # URL esposti dallo static file serving di Streamlit
    original_url = f"app/static/output/original_{timestamp}.html"
    processed_url = f"app/static/output/processed_{timestamp}.html"

    st.markdown(f"[ORIGINAL]({original_url})")
    st.markdown(f"[PSEUDONYMIZED]({processed_url})")
