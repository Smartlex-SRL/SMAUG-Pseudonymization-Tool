# modules/anonymizer.py

from collections import Counter
from datetime import date, timedelta
from random import randint
import random
import string
from typing import List

def anonymize(doc, strategy: str, selected_ner_label: List[str]) -> str:
    """
    Anonimizza un Doc di spaCy in base alla strategia specificata.
    
    :param doc: oggetto Doc di spaCy
    :param strategy: stringa che indica la strategia (es. 'OMISSIS', 'Initials', 'Tagging', ...)
    :param selected_ner_label: lista (o set) di label NER da anonimizzare
    :return: testo anonimizzato come stringa
    """
    text = ""

    
    if strategy == 'Tagging':
        # Sostituisce l'entità con il nome dell'etichetta (es: **PERSON**)
        # ma solo se ent.label_ è nelle selected_ner_label
        # e se ent è 'B' (begin), ignora la parte 'I'
        func = lambda t: "" if t.ent_iob_ == 'I' else f'**{t.ent_type_}**'
        text = " ".join(
            t.text if (not t.ent_type_ or t.ent_type_ not in selected_ner_label)
            else func(t)
            for t in doc
        )

    elif strategy == 'OMISSIS':
        # Rimpiazza con **OMISSIS** l'entità (solo sul token B),
        # lasciando vuoto il token I
        func = lambda t: "" if t.ent_iob_ == 'I' else "**OMISSIS**"
        text = " ".join(
            t.text if (not t.ent_type_ or t.ent_type_ not in selected_ner_label)
            else func(t)
            for t in doc
        )

    elif strategy == 'Initials':
        # Rimpiazza con le iniziali es: "Mario Rossi" -> "M.R."
        # Per i token I, mettiamo vuoto.
        text = " ".join(
            t.text if (not t.ent_type_ or t.ent_type_ not in selected_ner_label)
            else (
                "" if t.ent_iob_ == 'I'
                else f'**{"".join([w[0]+"." for w in str(t).split(" ")])}**'
            )
            for t in doc
        )

    elif strategy == 'Tagging-CP':
        # Context-preserving: sostituisce ogni entità con <label>_<numero>
        # Esempio: "Mario" (PERSON) -> PERSON_0
        # Usa un Counter per contare quante volte compare la label
        c = Counter(selected_ner_label)  # Oppure: Counter([ent.label_ for ent in doc.ents])
        dict_replace = {}
        end_prev_ent = 0
        ret = ""

        for e in doc.ents:
            if e.label_ not in selected_ner_label:
                ret += str(doc[end_prev_ent:e.end]) + " "
            else:
                ent_text = str(e)
                if ent_text not in dict_replace:
                    dict_replace[ent_text] = f"{e.label_}_{c[e.label_]}"
                    e._.internal_index=c[e.label_]
                    e._.strategy=strategy
                    c[e.label_] += 1

                ret += str(doc[end_prev_ent:e.start]) + f' **{dict_replace[ent_text]}** '
            end_prev_ent = e.end

        ret += str(doc[end_prev_ent:])
        text = ret

    elif strategy == 'Random-CP':
        # Sostituisce l'entità con un valore random fra un set predefinito,
        # differenziato per label (Person, Location, Company, Date, ID).
        ramdom_dict = {
            'Person': [
                'Marco', 'Alessandro', 'Giuseppe', 'Flavio', 'Luca', 'Giovanni', 
                'Roberto', 'Andrea', 'Stefano', 'Angelo', 'Francesco', 'Mario', 
                'Luigi', 'Anna', 'Maria', 'Sara', 'Laura', 'Aurora', 'Valentina', 
                'Giulia', 'Rosa', 'Gianna', 'Giuseppina', 'Angela', 'Giovanna', 
                'Sofia', 'Stella'
            ],
            'Location': [
                'Milano', 'Napoli', 'Torino', 'Palermo', 'Bologna', 'Firenze', 
                'Bari', 'Catania', 'Venezia', 'Trieste', 'Brescia', 'Verona'
            ],
            'Company': [
                'Enel', 'Assicurazioni Generali', 'Eni', 'GSE', 'Poste italiane', 
                'MSC', 'Techint', 'Unipol Group', 'Telecom', 'UniCredit', 
                'Intesa Sanpaolo', 'Coop', 'Cassa Depositi e Prestiti', 'Conad', 
                'Leonardo', 'Edison', 'Selex', 'Ferrero', 'Saipem', 'Luxottica', 
                'TotalErg', 'Esselung'
            ],
            'Date': [
                (date.today() - timedelta(days=randint(10, 40000))).strftime("%d/%m/%Y")
                for _ in range(20)
            ],
            'ID': [
                ''.join(random.choice(string.ascii_uppercase) for _ in range(5))
                for _ in range(20)
            ]
        }

        dict_replace = {}
        end_prev_ent = 0
        ret = ""

        for e in doc.ents:
            if e.label_ not in selected_ner_label:
                ret += str(doc[end_prev_ent:e.end]) + " "
            else:
                ent_text = str(e)
                # Se non ancora sostituita, assegnagli un valore random
                if ent_text not in dict_replace:
                    # Se la label non è in ramdom_dict, default: "XXXX"
                    if e.label_ not in ramdom_dict:
                        dict_replace[ent_text] = "XXXX"
                    else:
                        dict_replace[ent_text] = random.choice(ramdom_dict[e.label_])

                ret += str(doc[end_prev_ent:e.start]) + f' **{dict_replace[ent_text]}** '
            end_prev_ent = e.end

        ret += str(doc[end_prev_ent:])
        text = ret

    elif strategy == 'Tagging-Gen':
        # Variante "Tagging" che prova a gestire multi-word entità
        # mantenendo un contatore <label>_n
        dict_ents_multiwords = {}
        for e in doc.ents:
            if len(e.as_doc()) > 1:  # multiword
                if e.label_ not in dict_ents_multiwords:
                    dict_ents_multiwords[e.label_] = set()
                dict_ents_multiwords[e.label_].add(str(e).lower())

        def isin_mw(ent):
            """
            Verifica se la stringa dell'entità è presente
            in un set di multiwords, e in tal caso restituisce quella multiword.
            """
            if ent.label_ in dict_ents_multiwords:
                for mw in dict_ents_multiwords[ent.label_]:
                    # se la combinazione di token corrisponde
                    if set(str(ent).lower().split()) == set(mw.split()):
                        return mw
                    elif str(ent).lower() in mw.split():
                        return mw
            return str(ent).lower()

        c = Counter(selected_ner_label)
        dict_replace = {}
        end_prev_ent = 0
        ret = ""

        for e in doc.ents:
            mw_key = isin_mw(e)
            if mw_key not in dict_replace:
                dict_replace[mw_key] = f"{e.label_}_{c[e.label_]}"
                e._.internal_index=c[e.label_]
                c[e.label_] += 1
            else:
                # estrai l'indice già assegnato precedentemente
                e._.internal_index = int(dict_replace[mw_key].split("_")[-1])
            e._.strategy=strategy
            if e.label_ not in selected_ner_label:
                ret += str(doc[end_prev_ent:e.end]) + " "
            else:
                ret += str(doc[end_prev_ent:e.start]) + f' **{dict_replace[mw_key]}** '
            end_prev_ent = e.end

        ret += str(doc[end_prev_ent:])
        text = ret
    else:
        # Se la strategia è "No" o sconosciuta, restituiamo il testo originale
        text = str(doc)
    return text
