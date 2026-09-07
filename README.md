# RAG Q&A App (Sakura AI Engine Course Material)

This is a course-material Web app where you ask a question against
registered documents, and Sakura AI Engine's RAG API (`documents_chat`)
returns an answer along with its sources.

The core thing to understand is this flow:

```
Browser → JavaScript → Flask → requests → AI Engine → Flask → Browser
```

The API you used to call with curl is now called from behind a Web
screen, using Python (`requests`).

## Directory Structure

```
04_rag-web-app/
├── app.py                The Flask server. Validation, token management, API calls, formatting
├── requirements.txt      Required Python packages
├── templates/
│   └── index.html        The Web screen's HTML
└── static/
    ├── style.css         The screen's design
    └── app.js            Gets input, sends it to Flask, displays the result
```

## Startup (WSL / Ubuntu)

```bash
# 1. Move to the working directory
cd 04_rag-web-app

# 2. Create the virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Install the packages
pip install -r requirements.txt

# 5. Set the account token as an environment variable
#    Set the whole <UUID>:<secret> shown when it was issued
export AI_ENGINE_TOKEN="<your issued account token>"

# 6. Start it
python app.py
```

Open the following URL in Chrome.

```
http://127.0.0.1:5000
```

## Prerequisites

- The RAG documents for the class are already registered with AI
  Engine, and their status is `available`.

## Things to Check When Verifying It Works

### What you'll see in Chrome DevTools (Network tab)

This is the Browser ↔ Flask traffic. You can check the JSON sent to
`/api/rag-chat` (`query` / `top_k` / `threshold`), the JSON Flask
returned, and the status code.

### What you'll see in Flask's terminal

This is the Flask ↔ AI Engine traffic. The question and parameters
received, along with AI Engine's status and processing time, are
logged (the token is never logged).

```
[RAG request]
query: What should I be careful about when handling personal information?
top_k: 3
threshold: 0.3

[AI Engine response]
status: 200
elapsed: 2.35 sec
```

## Where to Make Changes (all near the top of app.py)

- **Model names**: `EMBEDDING_MODEL` / `CHAT_MODEL`
- **Distance metric**: `DISTANCE_TYPE = "cosine"`
- **Timeout**: `REQUEST_TIMEOUT = 60`

## Implementation Notes (for turning this into course material)

- In AI Engine's actual response, the sources come back nested
  (e.g. `sources[i]["document"]["name"]`). `app.py`'s `format_result()`
  repacks this into a flat shape that's easy for the screen to work
  with.
- The answer (`answer`) comes back with some Markdown mixed in (like
  `-` for bullet points). For safety, it's displayed with `textContent`,
  and line breaks are handled with CSS `white-space: pre-wrap`. Symbols
  are shown as plain characters.
- distance is only rounded to 4 decimal places for display; the
  underlying value is left untouched.

## Security Notes

- The account token is only ever read from an environment variable —
  it never appears in the code, HTML, JS, or logs.
- JavaScript never calls AI Engine directly; it always goes through
  Flask.
- Strings received from the API are displayed with `textContent`,
  never inserted into `innerHTML`.
- This is for local use (127.0.0.1) only. Do not expose it to the
  internet.
