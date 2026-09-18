```markdown
# FileShare-GUI

Local Gradio app for **deduplication, text extraction, FCP classification, human review, and metadata injection**.

It runs on a **single Windows workstation**. After the Hugging Face models are saved on disk, the pipeline can run **offline**. No Ollama and no cloud OCR.

---

## What it does

| Phase | Tab | Purpose |
|-------|-----|---------|
| 0 | Deduplication | Exact / near-duplicate scan, Excel review, optional dry-run then delete |
| 1 | Ingestion | Extract text from Office / PDF / images / txt; export vision images under `extracted_texts/_images` |
| 2 | Classification | Match text to `fcp_CSV-UTF.csv` with **one** local embedder (MiniLM or Qwen3-Embedding-0.6B). Optional image captions via local Qwen2-VL |
| 2b | Review / override | Human picks Function → Sub-Function → Business Process from the FCP list. Official bilingual fields are written back into the **same** MiniLM or Qwen3 workbook. Excerpt columns are cleared |
| 3 | Placeholders | JSON side-cars from that workbook, including Litigation_hold / Archival_value / critical_business_content |
| 4 | Injector | Clone originals into a **per-model** folder; native Office properties when possible; always a JSON side-car |

The Gradio UI also has a Dashboard, a read-only Configuration view, and a Stop button (stop does not undo files already written).

---

## Two embedding models

| Choice | Report | Placeholders / clones |
|--------|--------|------------------------|
| MiniLM (fast) | `classification_results_minilm.xlsx` | `Injected_Metadata\minilm\` |
| Qwen3-Embedding-0.6B | `classification_results_qwen3.xlsx` | `Injected_Metadata\qwen3\` |

Only **one** embedder is loaded at a time. Caches live under `classification_results\embedding_cache\minilm\` and `...\qwen3_0.6b\`. Do not mix those folders.

---

## Design principles

- **Local-first / offline runtime** — no Ollama, no OCR cloud APIs, no required internet after model download  
- **Independent absolute paths** — source docs, extracts, results and models can each live on different drives or DFS shares  
- **One config file** — set paths in `project_config.py` once per machine, then restart the app  
- **Human review** — classification and dedup produce Excel workbooks; selected columns (e.g. litigation hold) can be edited before placeholders/injection  
- **Managed-device friendly** — no admin install required if Python/conda is already available; distribute as a GitHub ZIP  

---

## Requirements

- **OS:** Windows recommended (Office metadata injection via `pywin32` is Windows-only). Core pipeline works on other OS without native Office inject.  
- **Python:** 3.10+ (3.11 tested in development)  
- **Optional:** Microsoft Office (licensed) for native Word/Excel property injection  
- **Disk:** space for models (embedder is small; Qwen2-VL-2B is larger) and document working folders  
- **GPU (optional):** helps vision; CPU works more slowly  

---

## Repository layout (high level)

```text
FileShare-GUI/
├── app.py                 # Gradio UI
├── project_config.py      # ALL absolute paths (edit on each machine)
├── requirements.txt
├── backend/               # runners, job control, dashboard status
├── Classification/
├── Ingestion/
├── DeDuplication/
├── Metadata_Placeholder/
├── Metadata_Injector/
└── Resources-Sources/     # fcp_CSV-UTF.csv, dictionaries, RegEx, etc.
```

**Not in Git (keep local):** virtualenv, model weight folders, live document corpora, classification outputs, indexes.

---

## 1. Get the code

### Option A — ZIP (recommended for end users)

1. Open the GitHub repo: `https://github.com/ssc-dsai/FileShare-GUI-python`  
2. **Code → Download ZIP**  
3. Extract to a **user-writable** folder, e.g.  
   `C:\FileShare-GUI`  
   Do **not** copy under `Program Files`.

### Option B — Git clone

```bash
git clone https://github.com/ssc-dsai/FileShare-GUI-python.git
cd FileShare-GUI-python
```

---

## 2. Create a Python environment

**venv:**

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**or conda / miniconda:**

```bash
conda create -n FileShare-GUI python=3.11 -y
conda activate FileShare-GUI
python -m pip install -r requirements.txt
```

### spaCy language models (once per environment)

```bash
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
```
### Option B — if admin rights prevent you to downloading spaCy
```bash
Navigate to: https://spacy.io/models/en#en_core_web_sm
- Click on the Download Link and download to to your machine
Navigate to: https://spacy.io/models/fr#fr_core_news_sm
- Click on the Download Link and download to to your machine
Move both "en_core_web_sm-3.8.0-py3-none-any.whl" and "fr_core_news_sm-3.8.0-py3-none-any.whl" from the downloads folder to C:\FileShare-GUI
```

### Windows only (native Office injection)

```bash
python -m pip install pywin32
```

If COM injection fails, the app still writes **`.metadata.json` side-cars**.

---

## 3. Download models from Hugging Face (one-time, needs network)

Runtime is offline; **first-time download requires internet**.

Create a models root (example):

```text
C:\FileShare-GUI\models
```

### Embedding model (required for classification vectors)

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

```bash
python -c "from sentence_transformers import SentenceTransformer; from pathlib import Path; d=Path(r'C:\FileShare-GUI\models\paraphrase-multilingual-MiniLM-L12-v2'); d.mkdir(parents=True, exist_ok=True); m=SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); m.save(str(d)); print('Done', d)"
python -c "from sentence_transformers import SentenceTransformer; from pathlib import Path; d=Path(r'C:\FileShare-GUI\models\Qwen2-VL-2B-Instruct'); d.mkdir(parents=True, exist_ok=True); m=SentenceTransformer('sentence-transformers/Qwen2-VL-2B-Instruct'); m.save(str(d)); print('Done', d)"
python -c "from sentence_transformers import SentenceTransformer; from pathlib import Path; d=Path(r'C:\FileShare-GUI\models\Qwen3-Embeddings-0.6B'); d.mkdir(parents=True, exist_ok=True); m=SentenceTransformer('sentence-transformers/Qwen3-Embeddings-0.6B'); m.save(str(d)); print('Done', d)"
```
### Option B — if admin rights prevent you to downloading HuggingFace models
```bash
From the Command Line, type the following once your in th project directory

cd C:\FileShare-GUI\models

git -c http.sslVerify=false clone https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
git -c http.sslVerify=false clone https://huggingface.co/sentence-transformers/paraphrase-MiniLM-L12-v2
git -c http.sslVerify=false clone https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
```

### Vision model (required for image-flagged documents)

`Qwen/Qwen2-VL-2B-Instruct`

Download with the same approach you used in development (Hugging Face `snapshot_download` / transformers save into):

```text
C:\FileShare-GUI\models\Qwen2-VL-2B-Instruct
```

Point `project_config.py` at these folders (see below).

After download, by default the offline-friendly environment variables are preset when starting the app:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

---

## 4. Configure paths (only place to set them)

Edit **`project_config.py`** on the machine. Set each absolute path to real folders on that PC or DFS share.

Typical entries:

| Setting | Meaning |
|---------|---------|
| `SOURCE_DOCS_DIR` | Incoming documents to process |
| `EXTRACTED_TEXTS_DIR` | Extracted `.txt` + `_images` |
| `CLASSIFICATION_RESULTS_DIR` | Excel/CSV + embedding cache |
| `DEDUPS_DIR` | Deduplication reports |
| `INJECTED_METADATA_DIR` | Clones + placeholders |
| `MODELS_DIR` / `EMBEDDING_MODEL_PATH` / `VISION_MODEL_PATH` | Local model folders |
| `RESOURCES` paths | `fcp_CSV-UTF.csv`, dictionaries, RegEx, trivial subjects |

**Rules:**

- Paths are **independent** (no single required data root).  
- **Restart** the Gradio app after any path change.  
- Do not put live data only inside the folder you overwrite when installing a new ZIP.

Ensure `Resources-Sources` files ship with the repo (FCP CSV, `Doc_Type_Dictionary.txt`, `RegEx-db.csv`, `trivial_subjects.txt`).

---

## 5. Start the application

```bash
cd <project-root>
.venv\Scripts\activate
py app.py
```

Open a browser:

```text
http://127.0.0.1:7860
```

- Use **Stop current job** to cancel a long phase (already-written files are kept; there is no undo).  
- **Dashboard** shows counts and readiness of key artifacts.

---

## 6. Typical end-to-end workflow

1. **Deduplication** analysis → open Excel in DEDUPS_DIR → mark User_Confirmed_Delete → dry-run → uncheck dry-run to delete.
2. **Ingestion** extracts text and images for further processing
3. **Classification** (pick MiniLM or Qwen3). Close the result workbook in Excel first.
4. **Review / override** for rows the model got wrong.
5. **Placeholders** create the metadata labels and space within the document properties
6. **Metadata injector** with the same radio.

- Disposition Authorization: `2021/005`  
- Technical Environment: `Microsoft's Distributed File System (DFS)`

---

## 7. Updating the application

1. Stop the app (Ctrl+C).  
2. Download a new ZIP (or `git pull`).  
3. Replace code files; **preserve** your edited `project_config.py` (or re-apply paths).  
4. Activate env → `pip install -r requirements.txt` if dependencies changed.  
5. Start again.

Data folders and model directories should live **outside** the code tree when possible.

---

## 8. Security notes (local deploy)

- Prefer **localhost** binding; do not use public Gradio share links for sensitive corpora.  
- Keep **model directories** writable only by trusted admins; load only models you downloaded.  
- Treat external PDFs/images as untrusted input (parser DoS possible); keep packages updated via `requirements.txt`.  
- Native Office injection is **best-effort**; JSON side-cars are the reliable metadata record.

---

## 9. Troubleshooting

| Symptom | Check |
|---------|--------|
| App won’t start | Correct venv/conda; `pip install -r requirements.txt` |
| Import / module errors | Run from project root; `PYTHONPATH` / working directory |
| Empty classification hierarchy | FCP CSV path; embedding model path; re-run classification |
| No `_images` for PDFs | Document may have no embedded rasters; standalone PNG/JPG are copied under `_images` when configured |
| Word inject fails | Office COM policy; side-car JSON still written |
| Hugging Face network calls | Models path wrong; set offline env vars; verify local folders |

---

## Quick start (checklist)

- [ ] ZIP or clone into a user-writable folder  
- [ ] Create venv/conda env; install `requirements.txt`  
- [ ] Download MiniLM + Qwen2-VL into local model folders  
- [ ] Edit `project_config.py` paths once  
- [ ] `python app.py` → http://127.0.0.1:7860  
- [ ] Smoke-test Ingestion → Classification on a small folder  
```

## Configure paths (required)

Before the first run, open **project_config.py** and set every absolute
path for this machine (source documents, extracted texts, results and models.
Save the file and restart the app after any change.

# =============================================================================
# PATH CONFIGURATION (REQUIRED ON EACH MACHINE)
# =============================================================================
# Edit the absolute paths below to match this computer or DFS share.
# There is no single data root — each folder can live on a different drive.
# After changing any path, SAVE this file and RESTART the Gradio app
# (stop with Ctrl+C, then: python app.py).
# Do not rely on environment variables for normal use; this file is the
# single place to configure paths.
# =============================================================================

Paths are set only in project_config.py. Change paths there, save, then restart the application.

```

## User interface

### Dashboard
![Dashboard status](docs/images/1_Dashboard.png)

### Configuration of Absolute Paths
![Configuration](docs/images/2_Configuration.png)

### Deduplication
![Deduplication](docs/images/3_DeDuplication.png)

### Deduplication Dry-Run and Deletion
![Deduplication](docs/images/3_DeDuplication2.png)

### Ingestion of Raw Text from Documents
![Ingestion](docs/images/4_Ingestion.png)

### Classification
![Classification](docs/images/5_Classification.png)

### Review and Override
![Classification](docs/images/5_Classification2.png)

### Metadata Placeholder and Injection
![Metadata](docs/images/6_Metadata.png)

### Metadata Placeholder and Injection
![Metadata](docs/images/6_Metadata2.png)

```