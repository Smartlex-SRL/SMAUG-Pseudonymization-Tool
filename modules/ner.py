# modules/ner.py
import spacy
import streamlit as st
import pandas as pd
import html
import re
import random
import string
from datetime import date, timedelta, datetime
from spacy import displacy
from typing import Sequence, List, Optional, Tuple
from bs4 import BeautifulSoup, NavigableString
import json
from modules.anonymizer import anonymize
from collections import Counter
from modules.pdf_utils import pre_process
from modules.hugginface_ner_spacy_wrapper import load_hugginface_model_as_spacy



NER_ATTRS = ["text", "label_", "start_char", "end_char"]

@st.cache_resource(show_spinner=False)
def load_models():
    electra_model = spacy.load("models/electra_ner_final")
    bert_model = spacy.load("models/bert_ner_final")
    montebovi_model = load_hugginface_model_as_spacy()
    
    return {
        "electra-ita-ner-final": electra_model,
        "bert-ita-ner-final": bert_model,
        "montebovi": montebovi_model
    }

def get_html(html: str):
    WRAPPER = """<div style='overflow-x: auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem; margin-bottom: 2.5rem'>{}</div>"""
    html = html.replace("\n", " ")
    return WRAPPER.format(html)

def visualize_ner(
    doc: spacy.tokens.Doc,
    *,
    labels: Sequence[str] = tuple(),
    attrs: List[str] = NER_ATTRS,
    show_table: bool = True,
    title: Optional[str] = "Named Entities",
    sidebar_title: Optional[str] = "Named Entities",
    key=None
) -> None:
    if title:
        st.header(title)
    if sidebar_title:
        st.sidebar.header(sidebar_title)

    html = displacy.render(doc, style="ent", options={"ents": labels})
    style = "<style>mark.entity { display: inline-block }</style>"
    st.write(f"{style}{get_html(html)}", unsafe_allow_html=True)

    if show_table:
        data = [
            [str(getattr(ent, attr)) for attr in attrs]
            for ent in doc.ents
            if ent.label_ in labels
        ]
        df = pd.DataFrame(data, columns=attrs)
        st.dataframe(df)

def ner_anonyzer_html_post_beautifier(html_text: str, ner_spacy_model, selected_ner_label: List[str], strategy: str) -> str:
    soup = BeautifulSoup(html_text, 'html.parser')
    pages_container = soup.find('div', id='pages-container')
    pages = pages_container.find_all('div', class_='page') if pages_container else []
    text = ''
    span_positions = []
    position = 0
    for page in pages:
        spans = page.find_all('span')
        for span in spans:
            span_text = span.get_text()
            span_positions.append((span, position))
            text += span_text + ' '
            position += len(span_text) + 1

    doc = ner_spacy_model(text)
    result = anonymize(doc, strategy, selected_ner_label)

    # Random pool per Random-CP
    random_pool = {
        'PERSON': [
            'Marco', 'Alessandro', 'Giuseppe', 'Flavio', 'Luca', 'Giovanni',
            'Roberto', 'Andrea', 'Stefano', 'Angelo', 'Francesco', 'Mario',
            'Luigi', 'Anna', 'Maria', 'Sara', 'Laura', 'Aurora', 'Valentina',
            'Giulia', 'Rosa', 'Gianna', 'Giuseppina', 'Angela', 'Giovanna',
            'Sofia', 'Stella'
        ],
        'LOCATION': [
            'Milano', 'Napoli', 'Torino', 'Palermo', 'Bologna', 'Firenze',
            'Bari', 'Catania', 'Venezia', 'Trieste', 'Brescia', 'Verona'
        ],
        'COMPANY': [
            'Enel', 'Eni', 'GSE', 'Poste italiane', 'MSC', 'Techint', 'Telecom',
            'Unipol Group', 'Coop', 'Ferrero', 'Luxottica', 'Conad'
        ],
        'DATE': [
            (date.today() - timedelta(days=random.randint(10, 40000))).strftime("%d/%m/%Y")
            for _ in range(20)
        ],
        'ID': [
            ''.join(random.choice(string.ascii_uppercase) for _ in range(5))
            for _ in range(20)
        ]
    }
    for span, span_start in span_positions:
        span_text = span.get_text()
        span_end = span_start + len(span_text)
        span_entities = [
            ent for ent in doc.ents
            if ent.label_ in selected_ner_label and span_start <= ent.start_char < span_end
        ]
        if not span_entities:
            continue
        span_entities = sorted(span_entities, key=lambda e: e.start_char, reverse=True)
        for ent in span_entities:
            original_text = ent.text
            strategy_type = ent._.strategy
            replacement = ""
            if strategy_type == "OMISSIS":
                replacement = "OMISSIS"
            elif strategy_type == "Tagging":
                replacement = ent.label_[0]
            elif strategy_type == "Initials":
                replacement = ".".join([w[0].upper() for w in original_text.split() if w]) + "."
            elif strategy_type in {"Tagging-CP", "Tagging-Gen"}:
                replacement = f'{ent.label_[0]}.{ent._.internal_index}'
            elif strategy_type == "Random-CP":
                replacement = random.choice(random_pool.get(ent.label_, ["XXXX"]))
            else:
                replacement = ent.label_
            mark_tag = soup.new_tag("mark",
                                    **{
                                        "data-type": "entity",
                                        "data-original": original_text,
                                        "data-replacement": replacement,
                                        "data-entity_index": ent._.internal_index,
                                        "data-strategy": strategy_type,
                                        "data-entity": ent.label_,
                                        "contenteditable": "false"
                                    })
            if strategy_type is None:
                print("⚠️ Nessuna strategy_type specificata. Uso fallback 'anon'.")
            mark_tag["class"] = (strategy_type or "anon").lower()
           # mark_tag["class"] = strategy_type.lower()
            mark_tag.string = original_text
            internal_start = ent.start_char - span_start
            internal_end = internal_start + len(original_text)
            span_text = (
                span_text[:internal_start] +
                str(mark_tag) +
                span_text[internal_end:]
            )
            span.string=span_text # Tag in forma testuale. Faro' un unescape alla fine di tutto
    nuovo_html=soup.prettify()
    nuovo_html=html.unescape(nuovo_html)
    soup = BeautifulSoup(nuovo_html, 'html.parser') # Faccio il parse con i tag unescapati cosi' vedo i mark come tag

    # Sostituisci visualmente il contenuto dei mark con il replacement (solo testo visibile)
    marks = soup.find_all('mark')
    for mark in marks:
        mark.string = mark["data-replacement"]

    # Genera JSON struttura entità da usare con javascript
    entity_tree = {}
    for ent in doc.ents:
        label = ent.label_
        text_ent = ent.text
        internal_index = ent._.internal_index
        if label not in entity_tree:
            entity_tree[label] = {"items": [], "counter": 1}
        if not any(item["text"] == text_ent for item in entity_tree[label]["items"]):
            idx = entity_tree[label]["counter"]
            entity_tree[label]["items"].append({"text": text_ent, "entity_index": internal_index})
            entity_tree[label]["counter"] += 1

    for label in entity_tree:
        entity_tree[label] = entity_tree[label]["items"]

    json_string = json.dumps(entity_tree, ensure_ascii=False)
    cleaned_html = str(soup).replace("</body>", f'<script>var doc={json_string};var strategy="{strategy}";</script></body>')

    return cleaned_html
