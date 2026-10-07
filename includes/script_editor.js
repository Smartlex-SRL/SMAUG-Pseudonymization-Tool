/* Funzione di sanitize ad uso generale */
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* Aggiusta i livelli per evitare che i box non permettano l'editing dell'eventuale testo interno */
function adjustZIndexInPages() {
  const pages = document.querySelectorAll("div.page");
  pages.forEach(page => {
    const allElements = page.querySelectorAll("*");
    allElements.forEach(el => {
      const style = el.style;
      if (style.position === "absolute") {
        if (el.tagName === "DIV") {
          style.zIndex = "0";
        } else if (el.tagName === "SPAN") {
          style.zIndex = "10";
        }
      }
    });
  });
}

/* Funzione di pulizia preliminare del dom da testo con doppi spazi */
function normalizeTextSpacesInPages() {
  const pages = document.querySelectorAll("div.page");
  pages.forEach(page => {
    const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, null, false);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentNode.closest("#popup") && node.nodeValue.includes("  ")) {
        node.nodeValue = node.nodeValue.replace(/\s{2,}/g, ' ');
      }
    }
  });
}

/* Funzione di rimozione bordo pagina extra inserito dal convertitore */
function removeExtraPageBorder() {
  const pages = document.querySelectorAll("div.page");
  pages.forEach(page => {
    const spans = page.querySelectorAll("span");
    for (const span of spans) {
      const style = span.style;
      if (
        style.position === "absolute" &&
        style.left === "0px" &&
        style.top === "50px"
      ) {
        span.remove();
        break;
      }
    }
  });
}

/* Funzione di riduzione font globale di un unità */
function decreaseFontSizeInPages() {
  const pages = document.querySelectorAll("div.page");
  pages.forEach(page => {
    const elements = page.querySelectorAll("*");
    elements.forEach(el => {
      const fontSizeStr = el.style.fontSize;
      if (fontSizeStr && fontSizeStr.endsWith("px")) {
        const currentSize = parseFloat(fontSizeStr);
        if (!isNaN(currentSize) && currentSize > 1) {
          el.style.fontSize = `${currentSize - 1}px`;
        }
      }
    });
  });
}

/* Anonimizzazione iniziali in fase di caricamento */
window.addEventListener("load", function () {
  removeExtraPageBorder();
  adjustZIndexInPages();
  /*normalizeTextSpacesInPages();
  decreaseFontSizeInPages();
  
  Object.keys(doc).forEach(entity => {
    const sortedEntries = doc[entity]
    .slice()
    .sort((a, b) => b.text.length - a.text.length);
    sortedEntries.forEach(entry => {
      const rawText = entry.text.trim();
      const excludeTexts = ["in", ".", ". ", " .", " . "];
      if (excludeTexts.includes(rawText)) return;
      const label = `${entity[0]}.${entry.index}`;
      const text = entry.text.replace(/\s+/g, ' ').trim();
      const pageDivs = document.querySelectorAll("div.page");
      pageDivs.forEach(page => {
        const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, {
          acceptNode: function (node) {
            const normalized = node.nodeValue.replace(/\s+/g, ' ');
            const pattern = new RegExp(`\\b${escapeRegExp(text)}[.,;:!?]?\\b`, 'i');
            if (!pattern.test(normalized)) return NodeFilter.FILTER_SKIP;
            if (node.parentNode.closest("#popup")) return NodeFilter.FILTER_REJECT;
            if (!["DIV", "SPAN", "P", "LI"].includes(node.parentNode.tagName)) return NodeFilter.FILTER_SKIP;
            return NodeFilter.FILTER_ACCEPT;
          }
        });
        const nodesToReplace = [];
        while (walker.nextNode()) {
          nodesToReplace.push(walker.currentNode);
        }
        nodesToReplace.forEach(node => {
          markText(node.parentNode, node, text, label, entity, entry.entity_index);
        });
      });
      replaceSplitAcrossBrs(text, label);
      replaceSplitAcrossNodes(selectedText, label);
    });
  });*/

  populateSelect();
  createDynamicStyles();
  initAreaDeletion();
  initMovableEditable();  

  bindEntityMarkTooltip();
  bindMarkClick();

});

/* Variabili globali usate per contenere il testo selezionato da sostiture */
let selectedText = "";
let selectionRange = null;
let selectedContent;

/* Chiude il popop di sostituzione testo */
function closePopup() {
  document.getElementById("popup").style.display = "none";
}

/* Data una label (Person,Location,Company,Date,ID) calcola l'indice da usare per l'eventuale entity da aggiungere */
function getNextEntityIndexForEntity(entity) {
  const items = doc[entity];
  if (!items || items.length === 0) return 1;
  return Math.max(...items.map(i => i.entity_index || 0)) + 1;
}

/* Popola la dropdown di selezione label */
function populateSelect() {
  const select = document.getElementById("entity-select");
  select.innerHTML = `<option value="">-- Select --</option>`;
  const predefinedEntities = ["ID", "Person", "Location", "Company", "Date"];
  predefinedEntities.forEach(key => {
    if (!doc[key]) {
      doc[key] = [];
    }
    const nextEntityIndex = getNextEntityIndexForEntity(key);
    const option = document.createElement("option");
    option.value = key;
    option.textContent = `${key}`;
    option.dataset.entity_index = nextEntityIndex;
    select.appendChild(option);
  });
}

/* Funzione per l'esclusione del nodo html del popup */
function isInsidePopup(node) {
  return node.closest && node.closest("#popup");
}

/* Funzione di sostituzione effettiva del occorrenza singola nel nodo */
function markText(parent, textNode, match, label, entity, entity_index) {
  const parts = textNode.nodeValue.split(match);
  parts.forEach((part, i) => {
    if (part) parent.insertBefore(document.createTextNode(part), textNode);
    if (i < parts.length - 1) {
      const mark = document.createElement("mark");
      mark.className = strategy.toLowerCase();
      mark.contentEditable = "true";
      mark.textContent = label;
      mark.dataset.entity = entity;
      mark.dataset.entity_index = entity_index;
      mark.dataset.original = match;
      parent.insertBefore(mark, textNode);
    }
  });
  parent.removeChild(textNode);
}

/* Handler pulsante Applica Popup - Effettua l'eventuali sostituzioni e chiude il Popup */
function handleReplacement() {
  const select = document.getElementById("entity-select");
  const entity = select.value;
  const existingTextSelect = document.getElementById("existing-text-select");
  const selectedExistingText = existingTextSelect.value;
  if (!["Person", "Location", "ID", "Date", "Company"].includes(entity)) return;
  if (!selectedText) return;
  let finalText = selectedText;
  let entity_index;
  if (selectedExistingText) {
    finalText = selectedExistingText;
    const entry = window.doc[entity]
      .slice()
      .sort((a, b) => b.text.length - a.text.length)
      .find(e => e.text === finalText);
    if (!entry) {
      console.warn(`⚠️ Nessuna entità trovata per "${finalText}"`);
      return;
    }
    entity_index = entry.entity_index;
    console.log(`🔁 Sostituzione con esistente: ${entity[0]}.${entity_index}`);
  } else {
    const existing = window.doc[entity]
      .slice()
      .sort((a, b) => b.text.length - a.text.length)
      .find(e => e.text === selectedText);
    if (existing) {
      entity_index = existing.entity_index;
      console.log(`ℹ️ Trovato esistente: ${entity[0]}.${entity_index}`);
    } else {
      entity_index = getNextEntityIndexForEntity(entity);
      const newEntry = { text: selectedText, entity_index };
      window.doc[entity].push(newEntry);
      console.log(`✅ Aggiunto nuovo:`, newEntry);
    }
  }
  const label = `${entity[0]}.${entity_index}`;
  
  const word = escapeRegExp(selectedText);
  const boundaryRegex = new RegExp(
    `(?<![\\p{L}\\p{N}])${word}(?![\\p{L}\\p{N}])`,
    "gu"
  );

  const pageDivs = document.querySelectorAll("div.page");

  pageDivs.forEach(page => {
    const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        /*if (!node.nodeValue.includes(selectedText)) {*/
        if (!boundaryRegex.test(node.nodeValue)) {
          return NodeFilter.FILTER_SKIP;
        }
        if (isInsidePopup(node.parentElement)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodesToReplace = [];
    while (walker.nextNode()) {
      nodesToReplace.push(walker.currentNode);
    }
    nodesToReplace.forEach(node => {
      markText(node.parentNode, node, selectedText, label, entity, entity_index);
    });
  });
  replaceSplitAcrossBrs(selectedText, label);
  replaceSplitAcrossNodes(selectedText, label);
  closePopup();
  select.value = "";
  resetExistingTextSelect();
  populateSelect();
  bindEntityMarkTooltip();
  bindMarkClick();
}

function replaceSplitAcrossNodes(text, label) {
  /*console.log("Da fare: controllo delle parole tra uno span e l'altro");*/
}

/* Handler rilascio pulsante mouse */
document.addEventListener("mouseup", function(event) {
  const selection = window.getSelection();
  const text = selection.toString().replace(/\s+/g, ' ').trim();
  const popup = document.getElementById("popup");
  const selectedTextDiv = document.getElementById("selected-text");
  if (text.length > 0) {
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    selectedText = text;
    selectionRange = range.cloneRange();
    selectedContent = selection.getRangeAt(0).cloneContents();
    selectedTextDiv.textContent = `"${text}"`;
    popup.style.left = `${rect.left + window.scrollX}px`;
    popup.style.top = `${rect.bottom + window.scrollY}px`;
    popup.style.display = 'block';  
  } else {
    closePopup();
  }
});

/* Handler pulsante premuto fuori dall'area popup */
document.addEventListener("mousedown", function(event) {
  const popup = document.getElementById("popup");
  if (!popup.contains(event.target)) {
    closePopup();
  }
});

/* Effettua la sostituzione nelle casistiche in cui l'entity si trova a cavallo tra due righe (Es: Mario<br>Rossi)*/
function replaceSplitAcrossBrs(text, label) {
  const pages = document.querySelectorAll("div.page");
  const normalizedTarget = text.trim().replace(/\s+/g, ' ');
  pages.forEach(page => {
    const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        if (isInsidePopup(node.parentElement)) return NodeFilter.FILTER_REJECT;
        if (node.nodeValue.trim() === "") return NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    for (let i = 0; i < nodes.length - 1; i++) {
      /*
      DA SISTEMARE
      const current = nodes[i];
      const next = nodes[i + 1];
      const between = current.parentNode.nextSibling;
      if (!between || between.nodeName !== "BR") continue;
      const combinedText = (current.nodeValue + " " + next.nodeValue).replace(/\s+/g, ' ').trim();
      if (combinedText.includes(normalizedTarget)) {
        const parent = current.parentNode;
        const br = between;
        parent.removeChild(current);
        parent.removeChild(br);
        parent.removeChild(next);

        const [entityInitial, entity_index] = label.split(".");
        const span = document.createElement("span");
        span.className = "tagging-cp";
        span.contentEditable = "true";
        span.textContent = label;
        span.dataset.entity = Object.keys(doc).find(key => key[0] === entityInitial) || "";
        span.dataset.entity_index = entity_index;
        span.dataset.original = text;
        parent.appendChild(span);

        const span = document.createElement("span");
        span.className = "tagging-cp";
        span.contentEditable = "true";
        span.textContent = label;
        parent.appendChild(span);

        i++;
      }*/
    }
  });
}

/* Gestione dei tag al passaggio del mouse sulle entities */
function bindEntityMarkTooltip() {
  const marks = document.querySelectorAll("mark");
  const tooltip = document.getElementById("custom-tooltip");
  let timeout;
  marks.forEach(mark => {
    mark.addEventListener("mouseenter", (e) => {
      timeout = setTimeout(() => {
        const type = mark.dataset.entity;
        const entity_index = parseInt(mark.dataset.entity_index, 10);
        const entry = doc[type]?.find(el => el.entity_index === entity_index);
        if (!entry) return;
        tooltip.textContent = entry.text;
        tooltip.style.left = `${e.pageX + 10}px`;
        tooltip.style.top = `${e.pageY + 10}px`;
        tooltip.style.opacity = "1";
        tooltip.style.transform = "translateY(-4px)";
      }, 200);
    });
    mark.addEventListener("mouseleave", () => {
      clearTimeout(timeout);
      tooltip.style.opacity = "0";
      tooltip.style.transform = "translateY(0)";
    });
  });
}

/* Popola la dropdown per la selezione delle entities interne alla label principale */
function populateExistingTextSelect(entity) {
  const select = document.getElementById("existing-text-select");
  select.innerHTML = `<option value="">-- Add new entry --</option>`;
  if (!doc[entity]) return;
  doc[entity].forEach(entry => {
    const option = document.createElement("option");
    option.value = entry.text;
    option.textContent = `${entry.text} (${entity[0]}.${entry.entity_index})`;
    select.appendChild(option);
  });
}

/* Handler selezione label principale */
function onEntityChange() {
  const entity = document.getElementById("entity-select").value;
  populateExistingTextSelect(entity);
}

/* Svuota la dropdown delle entities per popolamenti successivi */
function resetExistingTextSelect() {
  const select = document.getElementById("existing-text-select");
  select.innerHTML = `<option value="">-- New text --</option>`;
}


/* FUNZIONI PER LA CANCELLAZIONE AREA */

function createDynamicStyles() {
  if (document.getElementById("dynamic-selection-styles")) return;
  const style = document.createElement("style");
  style.id = "dynamic-selection-styles";
  style.textContent = `
    /* Rettangolo di selezione area */
    #selection-box{position:fixed;border:2px dashed red;pointer-events:none;z-index:9999;}
    .highlight-span-area{outline:2px solid red;}
    body.no-user-select,*:focus.no-user-select{user-select:none!important;-webkit-user-select:none!important;-moz-user-select:none!important;-ms-user-select:none!important;}

    /* Elemento spostabile & handle/bottoni */
    .movable-elem{position:absolute;}
    .move-elem-btn,.delete-elem-btn{position:absolute;font-size:10px;padding:2px 4px;border:none;border-radius:3px;cursor:pointer;z-index:50;display:none;}
    .move-elem-btn{background:#3399ff;color:#fff;}
    .delete-elem-btn{background:#ff5959;color:#fff;}
    .moving-elem{cursor:move!important;opacity:.85;}
  `;
  document.head.appendChild(style);
}

function initAreaDeletion() {
  const btn = document.getElementById("cancella_area");
  if (!btn) {
    console.warn("Bottone con id 'cancella_area' non trovato. La funzione di cancellazione area non è stata inizializzata.");
    return;
  }
  const pagesContainer = document.getElementById("pages-container");
  if (!pagesContainer) {
    console.warn("Contenitore pagine con id 'pages-container' non trovato. La funzione di cancellazione area non è stata inizializzata.");
    return;
  }

  let selecting = false;
  let startX, startY, box, currentPage, relRect;

  const rectContains = (outer, inner) =>
    inner.left   >= outer.left  &&
    inner.top    >= outer.top   &&
    inner.right  <= outer.right &&
    inner.bottom <= outer.bottom;

  /* 1. Click sul bottone => attivo modalità selezione */
  btn.addEventListener('click', () => {
    document.body.style.cursor = 'crosshair';
    document.body.classList.add('no-user-select'); // blocco selezione testo
    selecting = true;
  });

  /* 2. Mousedown => creo il rettangolo */
  document.addEventListener('mousedown', e => {
    if (!selecting) return;
    startX = e.clientX;
    startY = e.clientY;
    currentPage = e.target.closest('.page');
    if (!currentPage) {
      selecting = false;
      document.body.style.cursor = 'default';
      document.body.classList.remove('no-user-select');
      return;
    }
    box = document.createElement('div');
    box.id = 'selection-box';
    document.body.appendChild(box);
  });

  /* 3. Mousemove => aggiorno il rettangolo */
  document.addEventListener('mousemove', e => {
    if (!box) return;
    const x = Math.min(e.clientX, startX);
    const y = Math.min(e.clientY, startY);
    const w = Math.abs(e.clientX - startX);
    const h = Math.abs(e.clientY - startY);
    Object.assign(box.style, {
      left: x + 'px',
      top: y + 'px',
      width: w + 'px',
      height: h + 'px'
    });
  });

  /* 4. Mouseup => calcolo selezione, conferme ed eliminazioni */
  document.addEventListener('mouseup', () => {
    if (!selecting && !box) return;

    document.body.classList.remove('no-user-select'); // ripristino selezione testo

    if (!box) {
      selecting = false;
      document.body.style.cursor = 'default';
      return;
    }

    const selRect = box.getBoundingClientRect();
    document.body.removeChild(box);
    document.body.style.cursor = 'default';
    box = null;
    selecting = false;

    if (!currentPage) return;

    const candidateSpans = Array.from(currentPage.querySelectorAll('span'));
    const selectedSpans = candidateSpans.filter(sp => rectContains(selRect, sp.getBoundingClientRect()));

    if (selectedSpans.length === 0) return;

    selectedSpans.forEach(sp => sp.classList.add('highlight-span-area'));

    if (!confirm(`Are you sure you want to delete ${selectedSpans.length} items?`)) {
      selectedSpans.forEach(sp => sp.classList.remove('highlight-span-area'));
      return;
    }

    selectedSpans.forEach(sp => sp.remove());

    const pageRect = currentPage.getBoundingClientRect();
    relRect = {
      leftPct:  (selRect.left   - pageRect.left) / pageRect.width,
      topPct:   (selRect.top    - pageRect.top ) / pageRect.height,
      rightPct: (selRect.right  - pageRect.left) / pageRect.width,
      bottomPct:(selRect.bottom - pageRect.top ) / pageRect.height
    };

    if (confirm('Do you want to delete these items from the other pages as well?')) {
      Array.from(pagesContainer.querySelectorAll('.page')).forEach(pg => {
        if (pg === currentPage) return;
        const pgRect = pg.getBoundingClientRect();
        const absRect = {
          left:   pgRect.left + relRect.leftPct   * pgRect.width,
          top:    pgRect.top  + relRect.topPct    * pgRect.height,
          right:  pgRect.left + relRect.rightPct  * pgRect.width,
          bottom: pgRect.top  + relRect.bottomPct * pgRect.height
        };
        Array.from(pg.querySelectorAll('span')).forEach(sp => {
          if (rectContains(absRect, sp.getBoundingClientRect())) sp.remove();
        });
      });
    }
  });
}

/* =========================================================
   SEZIONE 2 –  "DRAG & CANCELLA_RIQUADRO" per elementi contenteditable
   ========================================================= */
   function initMovableEditable(){
    const pages=document.querySelectorAll('#pages-container .page');
    pages.forEach(p=>p.querySelectorAll('[contenteditable="true"]:not(mark)').forEach(makeMovable));

    // Rendi movibili anche quelli aggiunti dinamicamente
    const observer=new MutationObserver(muts=>muts.forEach(m=>m.addedNodes.forEach(n=>{
      if(n.nodeType===1){
        if(n.getAttribute('contenteditable')==='true' && n.tagName !== 'MARK') makeMovable(n);
        n.querySelectorAll?.('[contenteditable="true"]:not(mark)').forEach(makeMovable);
      }
    })));
    observer.observe(document.getElementById('pages-container'),{subtree:true,childList:true});
  }
  
  function makeMovable(el){
    if(el.classList.contains('movable-elem')) return; // già inizializzato
    el.classList.add('movable-elem');
  
    /* ─────  BOTTONI  ───── */
    const moveBtn=document.createElement('button');
    moveBtn.className='move-elem-btn';
    moveBtn.textContent='⤢';
    moveBtn.title = 'Drag to move';
  
    const delBtn=document.createElement('button');
    delBtn.className='delete-elem-btn';
    delBtn.textContent='✕';
    delBtn.title = 'Delete box';
  
    document.body.appendChild(moveBtn);
    document.body.appendChild(delBtn);
  
    const placeButtons=()=>{
      const r=el.getBoundingClientRect();
      const y=r.top+window.scrollY-10;
      moveBtn.style.left=r.right+window.scrollX+20+'px';
      moveBtn.style.top =(y-20)+'px';
      delBtn.style.left=r.right+window.scrollX+40+'px';
      delBtn.style.top =(y-20)+'px';
    };
  
    // Mostra bottoni al focus/click
    const showBtns=()=>{placeButtons();moveBtn.style.display=delBtn.style.display='block';};
    const hideBtns=()=>{moveBtn.style.display=delBtn.style.display='none';};

    el.addEventListener('focus',showBtns);
    el.addEventListener('click',showBtns);

    el.addEventListener('blur', e => {                      
      const to = e.relatedTarget;
      if (moveBtn.contains(to) || delBtn.contains(to)) {
        return;
      }
      hideBtns();
    });


    window.addEventListener('scroll',()=>{if(moveBtn.style.display==='block')placeButtons();});
  
    /* ─────  CANCELLA  ───── */
    delBtn.addEventListener('click',()=>{
      if (confirm('Delete this item?')) {
        el.remove();
        //hideBtns();
        moveBtn.remove();
        delBtn.remove();  
      } else {
        hideBtns();
      }
    });
  
    /* ─────  DRAG CON MANIGLIA  ───── */
    let drag=false,startX=0,startY=0,origLeft=0,origTop=0;

  const onMove=e=>{
    if(!drag) return;
    const dx=e.clientX-startX;
    const dy=e.clientY-startY;
    el.style.left=(origLeft+dx)+"px";
    el.style.top =(origTop +dy)+"px";
    placeButtons();
  };
  const stopDrag=()=>{
    if(!drag) return;
    drag=false;
    el.classList.remove('moving-elem');
    document.removeEventListener('mousemove',onMove);
    document.removeEventListener('mouseup',stopDrag);
  };

  moveBtn.addEventListener('mousedown',e=>{
    e.preventDefault(); showBtns();
    drag=true;
    startX=e.clientX;
    startY=e.clientY;
    // prendi le coordinate iniziali relative al suo posizionatore (offsetParent)
    origLeft=parseFloat(el.style.left)||el.offsetLeft;
    origTop =parseFloat(el.style.top )||el.offsetTop;
    el.classList.add('moving-elem');
    document.addEventListener('mousemove',onMove);
    document.addEventListener('mouseup',stopDrag);
  });
  
  }


  /* SOSTITUZIONE MARK CON TESTO ORIGINALE */

  function bindMarkClick() {
    document.querySelectorAll('mark').forEach(mark => {
      mark.addEventListener('click', onMarkClick);
    });
  }
  
  function onMarkClick(e) {
    e.stopPropagation();
    const mark = e.currentTarget;
    // dati originali
    const original = mark.dataset.original; // MARIO ROSSI
    const entity = mark.dataset.entity;  //Person
    const entity_index = mark.dataset.entity_index; // 1
    const label = `${entity.charAt(0).toUpperCase()}.${entity_index}`;
  
    // popup elements
    const popup = document.getElementById('mark-popup');
    document.getElementById('mark-popup-original').textContent = original;
    document.getElementById('mark-popup-entity').textContent = label;
  
    // posiziona
    const r = mark.getBoundingClientRect();
    popup.style.left = `${r.left + window.scrollX}px`;
    popup.style.top = `${r.bottom + window.scrollY + 5}px`;
    popup.style.display = 'block';
  
    // memorizza contesto
    popup._original = original;
    popup._entity = entity;
    popup._entity_index = entity_index;
    popup._label = label;
    popup._current_mark=mark;
    

  }
  
  // ................................................................
  // 2) HANDLER RESTORE TESTO ORIGINALE
  const restoreBtn = document.getElementById('mark-popup-restore');
  restoreBtn.addEventListener('click', () => {
    const popup = document.getElementById('mark-popup');

    // conferma
    if (!confirm('Restore the original text?')) return;
    applyToAll = confirm('Apply the replacement throughout the entire document?');
    const selector = `mark[data-entity_index="${popup._entity_index}"][data-entity="${popup._entity}"]`;
    const marks = applyToAll
      ? Array.from(document.querySelectorAll(selector))
      : [popup._current_mark];
    
    marks.forEach(m => {
      const txtNode = document.createTextNode(m.dataset.original);
      m.parentNode.replaceChild(txtNode, m);
      // rimuovi da doc JSON se applyToAll
      if (applyToAll) {
        doc[popup._entity] = doc[popup._entity].filter(el => el.entity_index!== popup._entity_index);
      }
    });
    popup.style.display = 'none';
  });
