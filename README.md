# PT — Pseudonymization Tool

PT is a Streamlit application developed by SmartLex for the SMAUG project (task T2.2). It identifies candidate personal data in Italian text and PDF documents, then lets users apply a pseudonymization strategy. The tool is designed to preserve useful context while supporting human review before the output is shared or reused.

## Capabilities

- Process free text or upload a PDF.
- Choose between three bundled named-entity recognition (NER) models: `berta-ita-ner-final`, `electra-ita-ner-final`, and `montebovi`.
- Review recognized entities and select which categories to process.
- Apply suppression (`OMISSIS`), initials, tagging, context-preserving tagging, generalized tagging, or context-preserving random substitution.
- Download/view the original and pseudonymized HTML generated for PDF uploads.

The models identify candidate entities; users remain responsible for reviewing the results and choosing the appropriate categories and strategy for their use case.

## Start with Docker

From the project directory, build and run the application:

```powershell
docker build -t pt .
docker run --rm -p 127.0.0.1:8501:8501 pt
```

Open [http://localhost:8501](http://localhost:8501) in a browser. Stop the application with `Ctrl+C`.

## Run locally

Use Python 3.11, matching the version used by the Docker image. From the project directory, create and activate a virtual environment, install the dependencies, create the output directory, and start Streamlit:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force static\output | Out-Null
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501). The `models` directory containing the bundled NER models must be present in the project directory.

PDF processing writes the original and pseudonymized HTML files to `static/output`. Treat both files as potentially sensitive data and manage access and retention accordingly.
