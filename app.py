"""
Course-material RAG Web application using Sakura AI Engine

This file is the Flask server. Its responsibilities are:

1. Return the HTML screen to the browser
2. Receive the question (JSON) sent from JavaScript
3. Validate the input values
4. Get the account token from an environment variable
5. Call Sakura AI Engine's RAG API using requests
   (doing in Python what you previously did with curl)
6. Clean up AI Engine's response and return it to the browser

The core thing to understand is this flow:
    Browser -> JavaScript -> Flask -> requests -> AI Engine -> Flask -> Browser
"""

import os
import time

from flask import Flask, jsonify, render_template, request
import requests


# =====================================================================
# Fixed settings
#   Keeping these together here makes them easy to change later.
# =====================================================================

# AI Engine's RAG chat endpoint
AI_ENGINE_URL = "https://api.ai.sakura.ad.jp/v1/documents/chat/"

# Embedding model (vectorizes the question text and documents)
EMBEDDING_MODEL = "multilingual-e5-large"

# Answer-generation model (produces a natural-language answer from the search results)
CHAT_MODEL = "gpt-oss-120b"

# Distance metric (how vector closeness is calculated)
DISTANCE_TYPE = "cosine"

# Fixed tag(s) used to limit what gets searched.
#   - Register the class documents with this tag attached.
#   - An empty list [] means no tag filtering is applied
#     (every registered document becomes searchable).
RAG_TAGS = []

# Name of the environment variable that holds the account token
TOKEN_ENV_NAME = "AI_ENGINE_TOKEN"

# Timeout, in seconds, for calling AI Engine
REQUEST_TIMEOUT = 60

# Maximum length of the question text
MAX_QUERY_LENGTH = 1000

# Allowed range for top_k
TOP_K_MIN = 1
TOP_K_MAX = 10

# Allowed range for threshold
THRESHOLD_MIN = 0.0
THRESHOLD_MAX = 1.0


app = Flask(__name__)


# =====================================================================
# Routing
# =====================================================================

@app.route("/", methods=["GET"])
def index():
    """Return the top screen (HTML)."""
    return render_template("index.html")


@app.route("/api/rag-chat", methods=["POST"])
def rag_chat():
    """
    Receive the question sent from JavaScript, call AI Engine's RAG
    API, and return the result.
    """

    # --- 1. Extract the JSON sent from the browser ------------------
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "The request format is invalid."}), 400

    query = data.get("query")
    top_k = data.get("top_k")
    threshold = data.get("threshold")

    # --- 2. Validate the input values ---------------------------------
    #   Also validated on the JavaScript side, but always validate on
    #   the server too.
    error_message = validate_input(query, top_k, threshold)
    if error_message is not None:
        return jsonify({"error": error_message}), 400

    # Once validated, fix these as their proper numeric types
    query = query.strip()
    top_k = int(top_k)
    threshold = float(threshold)

    # --- 3. Get the account token from an environment variable ------
    token = os.getenv(TOKEN_ENV_NAME)
    if not token:
        # Don't call AI Engine if there's no token
        return jsonify({"error": "AI_ENGINE_TOKEN is not set."}), 500

    # --- 4. Build the request to send to AI Engine -------------------
    payload = build_payload(query, top_k, threshold)

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # --- 5. Log to the terminal (never log the token) ----------------
    print("[RAG request]")
    print(f"query: {query}")
    print(f"top_k: {top_k}")
    print(f"threshold: {threshold}")
    print(f"tags: {RAG_TAGS}")

    # --- 6. Call AI Engine --------------------------------------------
    #   requests.post() plays the same role curl used to play.
    start_time = time.time()
    try:
        response = requests.post(
            __(4)__,                 # <- curl's destination URL (1st argument)
            headers=headers,
            json=__(5)__,            # <- the body that corresponds to curl's --data (payload)
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        # The response didn't come back in time
        print("[AI Engine response] timeout")
        return jsonify({"error": "The AI Engine API response timed out."}), 504
    except requests.exceptions.RequestException:
        # Any other communication error, e.g. couldn't connect
        print("[AI Engine response] connection error")
        return jsonify({"error": "An error occurred while connecting to AI Engine."}), 502

    elapsed = time.time() - start_time
    print("[AI Engine response]")
    print(f"status: {response.status_code}")
    print(f"elapsed: {elapsed:.2f} sec")

    # --- 7. If AI Engine returned an error -----------------------------
    if response.status_code != 200:
        # Don't return the token or internal details to the browser
        return jsonify({"error": "AI Engine API returned an error."}), 502

    # --- 8. Parse the response as JSON --------------------------------
    try:
        response_data = response.json()
    except ValueError:
        # Couldn't be read as JSON
        return jsonify({"error": "Could not parse AI Engine's response."}), 502

    # --- 9. Clean it up into the shape the browser expects, and return -
    result = format_result(response_data)
    return jsonify(result), 200


# =====================================================================
# Helper functions
#   Split into small pieces to keep things readable.
# =====================================================================

def validate_input(query, top_k, threshold):
    """
    Validate the input values.
    Returns None if there's no problem, or an error message (string)
    if there is.
    """

    # Validate query
    if not isinstance(query, str) or query.strip() == "":
        return "Please enter a question."
    if len(query) > MAX_QUERY_LENGTH:
        return f"Please keep your question to {MAX_QUERY_LENGTH} characters or fewer."

    # Validate top_k (can it be treated as an integer?)
    try:
        top_k_value = int(top_k)
    except (TypeError, ValueError):
        return "Please specify top_k as an integer."
    if top_k_value < TOP_K_MIN or top_k_value > TOP_K_MAX:
        return f"Please set top_k between {TOP_K_MIN} and {TOP_K_MAX}."

    # Validate threshold (can it be treated as a number?)
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return "Please specify threshold as a number."
    if threshold_value < THRESHOLD_MIN or threshold_value > THRESHOLD_MAX:
        return "Please set threshold between 0.0 and 1.0."

    # Everything checks out
    return None


def build_payload(query, top_k, threshold):
    """Build the JSON payload to send to AI Engine."""
    payload = {
        "model": EMBEDDING_MODEL,
        "chat_model": CHAT_MODEL,
        "query": __(1)__,        # <- the question text sent via curl's --data
        "top_k": __(2)__,        # <- top_k from curl's --data (number of references)
        "threshold": __(3)__,    # <- threshold from curl's --data (similarity threshold)
        "distance_type": DISTANCE_TYPE,
    }

    # Only add tags if fixed tags are set.
    #   When RAG_TAGS is an empty list, the tags field itself isn't sent.
    if RAG_TAGS:
        payload["tags"] = RAG_TAGS

    return payload


def format_result(response_data):
    """
    Reshape AI Engine's response into what the screen needs to display.

    In AI Engine's actual response, the source information comes back
    nested:
        sources[i]["document"]["name"]  ... document name
        sources[i]["document"]["id"]    ... document ID
        sources[i]["chunk_index"]       ... chunk number
        sources[i]["distance"]          ... distance
        sources[i]["content"]           ... chunk content
    Here, we repack it into a flat shape that's easy for the screen to
    work with. Uses get() throughout so a missing key never causes a
    crash.
    """

    # Extract the answer text (empty string if missing)
    answer = response_data.get("answer", "")

    # Clean up the source information
    raw_sources = response_data.get("sources", [])
    sources = []
    for item in raw_sources:
        # document is a nested dict; fall back to an empty dict if missing
        document = item.get("document", {}) or {}

        source = {
            "document_name": document.get("name", ""),
            "document_id": document.get("id", ""),
            "chunk_index": item.get("chunk_index"),
            "distance": item.get("distance"),
            "content": item.get("content", ""),
        }
        sources.append(source)

    return {"answer": answer, "sources": sources}


# =====================================================================
# Startup
#   Only run this in a local environment. Do not expose it to the internet.
# =====================================================================

if __name__ == "__main__":
    # Start on 127.0.0.1 (accessible only from your own PC)
    app.run(host="127.0.0.1", port=5000, debug=True)
