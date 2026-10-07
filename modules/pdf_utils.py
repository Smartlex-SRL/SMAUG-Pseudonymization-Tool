# modules/pdf_utils.py

import re
import io
import os
import fitz  # PyMuPDF
from pathlib import Path
import warnings
from typing import Optional

# pdfminer (per la conversione in HTML)
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.converter import HTMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

import re
from collections import defaultdict
from typing import Optional
from bs4 import BeautifulSoup, Tag


# Sopprime i messaggi di avviso di pdfminer
warnings.filterwarnings("ignore", category=UserWarning, module='pdfminer')

# La tengo giusto per avere un anteprima di anonimizzazione nella pagina. Non serve un granché, anche perche' e' buggata
def text_from_pdf(file_like) -> str:
    """
    Estrae tutto il testo da un PDF usando PyMuPDF.
    'file_like' è un oggetto tipo BytesIO o un file aperto in modalità 'rb'.
    """
    # Riposizioniamo il cursore all'inizio
    file_like.seek(0)
    doc = fitz.open(stream=file_like.read(), filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return text

# Rimuove qualche intestazione, ma in realtà non serve a un granché. Solo per l'anteprima testuale
def remove_page_headers(text: str) -> str:
    """
    Esempio di rimozione di intestazioni ripetute, es. 'REPUBBLICA ITALIANA'.
    Puoi modificare il pattern a seconda dei tuoi casi d'uso.
    """
    pattern = r"(?im)^.{0,20}REPUBBLICA ITALIANA.*\n"
    return re.sub(pattern, "", text)

# Rimuove spazi multipli e richiama un altra funzione. Come per le precedenti, serve solo per l'anteprima buggata del testo
def pre_process(text: str) -> str:
    """
    Pulisce il testo da ritorni a capo e whitespace extra,
    poi rimuove eventuali intestazioni ripetute.
    """
    text = re.sub(r"\s+", " ", text)
    text = remove_page_headers(text)
    return text.strip()

# Conversione da PDF ad HTML
def convert_pdf2html(file_like, scale=1.0, layoutmode="exact", password="") -> str:
    """
    Converte un PDF in HTML usando pdfminer. Restituisce una stringa con il contenuto HTML.

    Parametri:
    - file_like:  oggetto stile file (BytesIO o file aperto in 'rb').
    - scale:      fattore di scala per i caratteri/grafica.
    - layoutmode: 'exact' (mantiene la posizione) o 'normal'.
    - password:   se il PDF è protetto, altrimenti stringa vuota.
    """
    # Riposizioniamo il cursore
    file_like.seek(0)

    # L'output di pdfminer va in un buffer binario
    outfp = io.BytesIO()

    # Resource manager e parametri di layout
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()

    # Inizializziamo HTMLConverter
    device = HTMLConverter(
        rsrcmgr,
        outfp,
        laparams=laparams,
        scale=scale,
        layoutmode=layoutmode,
        codec='utf-8',   # fondamentale se scriviamo in un BytesIO
    )

    # Interprete delle pagine
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    # Pagine
    converted_pages = []
    close_file = False

    try:
        # Legge e processa le pagine
        # Dal momento che pdfminer ti restituisce il codice come se fossero piu' pagine html,
        # rimuovo tutto cià che non è necessario in modo tale che risulti un unica pagina html

        for page_num, page in enumerate(PDFPage.get_pages(file_like, 
                                                          maxpages=0, 
                                                          password="", 
                                                          caching=True, 
                                                          check_extractable=True), start=1):
            outfp = io.BytesIO()
            device = HTMLConverter(
                rsrcmgr,
                outfp,
                laparams=laparams,
                scale=scale,
                layoutmode=layoutmode,
                codec='utf-8'
            )
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            interpreter.process_page(page)
            device.close()
            
            html_page = outfp.getvalue().decode("utf-8", errors="replace")
            outfp.close()

            # Rimozione tag html superflui
            html_page = html_page.replace('<html>', '')
            html_page = html_page.replace('</html>', '')
            html_page = html_page.replace('<head>', '')
            html_page = html_page.replace('</head>', '')
            html_page = html_page.replace('<body>', '')
            html_page = html_page.replace('</body>', '')
            html_page = html_page.replace('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">','')
            # Rimozione bordino pagina sfasato
            html_page = html_page.replace('<span style="position:absolute; border: gray 1px solid; left:0px; top:50px; width:612px; height:792px;"></span>','')
            # Rimozione numero di pagina extra del sistema di navigazione della libreria
            html_page = html_page.replace('<div style="position:absolute; top:0px;">Page: <a href="#1">1</a></div>','')
            # Rimozione etichette di pagina del sistema di navigazione della libreria
            html_page = html_page.replace('<div style="position:absolute; top:50px;"><a name="1">Page 1</a></div>','')
            html_page = html_page.replace('<div style="position:absolute; top:50px;"><a name="1">Page 1</a></div>','')

            # Aggiunta carriage-return
            html_page = html_page.replace('</div><span', '</div>\n<span')
            html_page = html_page.replace('</div><div', '</div>\n<div')
            
            # Aggiunta spazio per i <span> vuoti
            html_page = html_page.replace('></span>', '> </span>')

            # Wrap del contenuto della pagina dentro div di classe "page"
            wrapped_page = (
                f'<div class="page" id="page-{page_num}" '
                f'style="margin: 0 auto; position:relative; width:660px; height:940px; '
                f'box-shadow: 0 0 10px rgba(0, 0, 0, 0.2); background-color: white;">\n'
                f'{html_page}\n</div>'
            )
            # Raggruppamento pagine
            converted_pages.append(wrapped_page)
    finally:
        if close_file:
            file_like.close()

    body_content = "\n".join(converted_pages)
    
    # Pulizia eventuali span superflui
    body_content = _cleanup_spans(body_content)

    # Apertura file di stile CSS da applicare alla pagina e iniettare come stringa
    css_path = os.path.join("includes", "style.css")

    # Lettura del contenuto del file CSS
    with open(css_path, "r", encoding="utf-8") as file:
        css_content = file.read() 
    
    # Composizione del documento HTML finale
    html_content = f"""
    <html lang="it">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title></title>
            <style>{css_content}</style>
        </head>
        <body>
            <div id="custom-tooltip"></div>
            <div id="popup">
                <div id="popup-header">
                    <span>Replace the text with:</span>
                    <span class="close" onclick="closePopup()">×</span>
                </div>
                <div id="selected-text"></div>
                <select id="entity-select" onchange="onEntityChange()">
                    <option value="">-- Select --</option>
                </select>
                <select id="existing-text-select">
                    <option value="">-- New text --</option>
                </select>
                <button onclick="handleReplacement()">Apply</button>
            </div>
            <div id="mark-popup">
                <!-- Header con X di chiusura stile esistente -->
                <div id="mark-popup-header">
                    <span>Selected entity:</span>
                    <span class="close" onclick="document.getElementById('mark-popup').style.display='none'">×</span>
                </div>
                <div style="margin-bottom: 1em;">
                    <strong>Entity:</strong> <span id="mark-popup-entity"></span>
                </div>
                <div style="margin-bottom: .5em;">
                    <strong>Original text:</strong> <span id="mark-popup-original"></span>
                </div>
                <div style="text-align: right;">
                    <button id="mark-popup-restore">Restore original text</button>
                </div>
            </div>
            <div id="header" style="text-align: center; position:fixed; z-index: 999; width: 100%; height: 60px; background-color: lightgray;">
                <button onclick="window.print()">Print</button><button id="cancella_area">Clear area</button>
            </div>
            <div id="spacer" style="height: 60px;"></div>
            <div id="pages-container">
            {body_content}
            </div>
        </body>
        <script></script>
    </html>
    """
    return html_content


def _cleanup_spans(html_text: str) -> str:
    """
    Funzione di utilità (privata) per pulire eventuali <span> vuoti o
    consecutivi in eccesso. Puoi modificarla o eliminarla in base alle
    tue esigenze di layout.
    """
    lines = html_text.split('\n')
    clean_text = ""
    n_ws = 0
    span_seq = []

    for line in lines:
        # Se contiene <span> apparentemente vuoto
        if '> </span>' in line:
            n_ws += 1
            span_seq.append(line)
        else:
            # Se ci sono più di 1 <span> vuoti consecutivi,
            # tieni solo l'ultimo (o il primo, a scelta)
            if n_ws > 1:
                clean_text += span_seq[-1] + "\n"
            else:
                for sp in span_seq:
                    clean_text += sp + "\n"

            span_seq.clear()
            n_ws = 0
            clean_text += line + "\n"

    # Se rimane qualcosa in span_seq, aggiungilo
    if span_seq:
        clean_text += "\n".join(span_seq)

    return clean_text

# Aggiunge al documento html, lo script di gestione dell'aggiunta manuale di entity al documento
def add_editor(html, filename: str, doc, strategy, anonymize: bool):
    html_content = html
    if anonymize:
        script_path = os.path.join("includes", "script_editor.js")
        with open(script_path, "r", encoding="utf-8") as file:
            js_editor = file.read()
        html_content = html_content.replace('</body>',f'<script>{js_editor}</script></body>')
    return html_content

_STYLE_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")

def _parse_style(style: str) -> dict[str, str]:
    """Restituisce un dizionario {proprietà_css: valore} a partire da uno
    `style` inline."""
    return {prop.lower(): val.strip() for prop, val in _STYLE_RE.findall(style)}

def _number(px: str | None) -> Optional[float]:
    """Converte '12.4px' → 12.4   |   None/'' → None"""
    if not px:
        return None
    try:
        return float(px.rstrip("px"))
    except ValueError:
        return None

def _style_to_string(styles: dict[str, str]) -> str:
    """Serializza il dizionario di stili in una stringa style inline."""
    return "; ".join(f"{k}: {v}" for k, v in styles.items())

def beautifyCodeWithoutEntities(html: str) -> str:
    """
    Unisce gli <span> generati “uno per lettera” in righe (stesso *top*) e
    successivamente in colonne (stesso *left* + stesso font) all’interno di
    ciascun <div class="page">.

    Parameters
    ---------- 
    html : str
        Codice HTML sorgente.

    Returns
    -------
    str
        HTML ottimizzato.
    """
    soup = BeautifulSoup(html, "html.parser")

    # -- FUSIONE ORIZZONTALE (stesso top) con distanza tra gli span controllata -----
    DISTANZA_MAX = 2  # distanza massima in pixel tra gli span per fonderli

    for page in soup.select("div.page"):
        rows: dict[int, list[Tag]] = defaultdict(list)

        for span in page.find_all("span"):
            styles = _parse_style(span.get("style", ""))
            top = _number(styles.get("top"))
            if top is None:
                continue
            rows[round(top)].append(span)

        for spans in rows.values():
            if len(spans) < 2:
                continue

            # Ordine crescente di "left"
            spans.sort(
                key=lambda s: _number(_parse_style(s.get("style", "")).get("left")) or 0
            )

            # Raggruppiamo gli span che sono vicini tra loro
            gruppi = []
            gruppo_corrente = [spans[0]]

            for i in range(1, len(spans)):
                left_corrente = _number(_parse_style(spans[i-1].get("style", "")).get("left"))
                left_successivo = _number(_parse_style(spans[i].get("style", "")).get("left"))
                font_size_precedente = _number(_parse_style(spans[i-1].get("style", "")).get("font-size"))
                font_size_successivo = _number(_parse_style(spans[i].get("style", "")).get("font-size"))
                distanza = left_successivo - left_corrente
                #max_font_size=max(font_size_precedente,font_size_successivo)
                if font_size_precedente is None:
                    font_size_precedente = 10
                if font_size_successivo is None:
                    font_size_successivo = 10

                max_font_size = max(font_size_precedente, font_size_successivo)

                # Se la distanza tra gli span è inferiore alla distanza massima, li aggiungiamo allo stesso gruppo
                if distanza <= max_font_size*DISTANZA_MAX:
                    gruppo_corrente.append(spans[i])
                else:
                    # Altrimenti, iniziamo un nuovo gruppo
                    gruppi.append(gruppo_corrente)
                    gruppo_corrente = [spans[i]]

            # Aggiungiamo l'ultimo gruppo
            gruppi.append(gruppo_corrente)

            # Fonderemo gli span in ciascun gruppo
            for gruppo in gruppi:
                if len(gruppo) < 2:
                    continue

                anchor = gruppo[0]
                # Costruiamo l'HTML da inserire nell'ancora
                parts: list[str] = []
                for s in gruppo:
                    text = s.get_text("", strip=False)
                    parts.append(text)
                anchor.clear()  # Rimuove il contenuto precedente
                # Inseriamo HTML “vivo”, non solo testo
                anchor.append(BeautifulSoup("".join(parts), "html.parser"))

                # Rimuove gli span fusi (dal secondo in poi)
                for extra in gruppo[1:]:
                    extra.decompose()
   # -- FUSIONE VERTICALE (stesso left + stesso font + distanza tra gli span controllata) --
    DISTANZA_MAX_VERTICALE = 10  # distanza massima in pixel tra gli span per fonderli verticalmente

    for page in soup.select("div.page"):
        current_left = None
        current_size = None
        current_family = None
        current_top = None
        anchor_span: Tag | None = None

        # Ci serve l'elenco *attuale* degli span (dopo la fusione orizzontale)
        for span in page.find_all("span"):
            styles = _parse_style(span.get("style", ""))
            
            left = _number(styles.get("left"))
            if left is None:
                continue
            left = round(left)

            size = round(_number(styles.get("font-size")) or 0)
            family = styles.get("font-family", "").strip().lower()

            top = round(_number(styles.get("top")) or 0)

            if anchor_span is None:
                # Primo span della pagina / reset
                current_left, current_size, current_family, current_top = left, size, family, top
                anchor_span = span
                continue

            same_column = left == current_left
            same_font = size == current_size and family == current_family

            # Calcoliamo la distanza verticale tra gli span
            distanza_vert = top - current_top

            if same_column and same_font and distanza_vert <= DISTANZA_MAX_VERTICALE:
                # Fusione verticale: aggiungiamo un <br/> per separare il testo
                anchor_span.append(BeautifulSoup("<br/>", "html.parser"))
                # Manteniamo eventuale markup interno
                anchor_span.append(BeautifulSoup(span.decode_contents(), "html.parser"))
                span.decompose()
            else:
                # Nuova colonna o font differente → reset
                current_left, current_size, current_family, current_top = left, size, family, top
                anchor_span = span

    for span in soup.select("div.page span"):
        span["contenteditable"] = "true"

        styles = _parse_style(span.get("style", ""))
        styles["z-index"] = "10"
        span["style"] = _style_to_string(styles)

    for inner_div in soup.select("div.page div"):
        styles = _parse_style(inner_div.get("style", ""))
        styles["z-index"] = "0"
        inner_div["style"] = _style_to_string(styles)

    return str(soup)