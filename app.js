/*
  RAG Q&A App frontend logic

  Responsibilities:
    - Read the input values from the Web screen
    - Validate the input values
    - Send JSON to Flask (fetch)
    - Display the answer and sources that come back from Flask
    - Disable the button while submitting, to prevent double submission

  Important:
    - Never call the AI Engine API directly from JavaScript.
      Always go through Flask (so the account token is never exposed
      to the browser).
    - Strings received from the API are never inserted directly into
      innerHTML; they're safely displayed with textContent.
*/

// Start once the HTML has finished loading
document.addEventListener("DOMContentLoaded", function () {

  // ---- Grab the screen elements we need ----
  const queryInput = document.getElementById("query");
  const topKInput = document.getElementById("top-k");
  const thresholdInput = document.getElementById("threshold");
  const thresholdValueLabel = document.getElementById("threshold-value");
  const submitButton = document.getElementById("submit-button");

  const errorArea = document.getElementById("error-area");
  const answerArea = document.getElementById("answer-area");
  const answerText = document.getElementById("answer-text");
  const sourcesArea = document.getElementById("sources-area");
  const sourcesList = document.getElementById("sources-list");

  // ---- Display and update the threshold slider's current value ----
  thresholdInput.addEventListener("input", function () {
    thresholdValueLabel.textContent = thresholdInput.value;
  });

  // ---- Handle the submit button being clicked ----
  submitButton.addEventListener("click", function () {
    sendQuestion();
  });

  /*
    The main routine: sends the question to Flask and displays the
    result. Marked async so it can await the fetch result.
  */
  async function sendQuestion() {
    // Clear any previous error message
    hideError();

    // --- 1. Read the input values ---
    const query = queryInput.value;
    const topK = Number(topKInput.value);
    const threshold = Number(thresholdInput.value);

    // --- 2. Validate the input values (also validated server-side) ---
    const validationError = validateInput(query, topK, threshold);
    if (validationError !== null) {
      showError(validationError);
      return;
    }

    // --- 3. Build the JSON to send to Flask ---
    const requestBody = {
      query: query,
      top_k: topK,
      threshold: threshold
    };

    // --- 4. Switch to the "submitting" state (prevents double submission) ---
    setLoading(true);

    try {
      // --- 5. POST to Flask with fetch ---
      const response = await fetch("/api/rag-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestBody)
      });

      // --- 6. Extract the JSON Flask returned ---
      const data = await response.json();

      // If Flask returned an error (400, 500, 502, 504, etc.)
      if (!response.ok) {
        const message = data.error || "An error occurred.";
        showError(message);
        return;
      }

      // --- 7. Display the answer and its sources ---
      showAnswer(data.__(1)__);   // <- extract the response's "answer" field
      showSources(data.__(2)__);  // <- extract the response's "sources" array

    } catch (e) {
      // The request itself failed (e.g. Flask isn't running)
      showError("Failed to connect to the server.");
    } finally {
      // Restore the button whether this succeeded or failed
      setLoading(false);
    }
  }

  /*
    Validates the input values.
    Returns null if there's no problem, or an error message if there is.
  */
  function validateInput(query, topK, threshold) {
    // Question is empty, or whitespace only
    if (query.trim() === "") {
      return "Please enter a question.";
    }
    // Question is too long
    if (query.length > 1000) {
      return "Please keep your question to 1000 characters or fewer.";
    }
    // top_k is out of range, or not a number
    if (Number.isNaN(topK) || topK < 1 || topK > 10) {
      return "Please set top_k between 1 and 10.";
    }
    // threshold is out of range, or not a number
    if (Number.isNaN(threshold) || threshold < 0 || threshold > 1) {
      return "Please set threshold between 0.0 and 1.0.";
    }
    return null;
  }

  /* Display the answer on screen */
  function showAnswer(answer) {
    // Use textContent, not innerHTML (for safety)
    answerText.textContent = answer;
    answerArea.hidden = false;
  }

  /*
    Display the sources on screen.
    Assumes Flask sends back a sources array shaped like:
      [{ document_name, document_id, chunk_index, distance, content }, ...]
  */
  function showSources(sources) {
    // Clear the display area first
    sourcesList.textContent = "";

    // No sources
    if (!sources || sources.length === 0) {
      const message = document.createElement("p");
      message.className = "no-sources";
      message.textContent = "No sources available.";
      sourcesList.appendChild(message);
      sourcesArea.hidden = false;
      return;
    }

    // Build and add each source one at a time
    sources.forEach(function (source, index) {
      const item = createSourceItem(source, index);
      sourcesList.appendChild(item);
    });

    sourcesArea.hidden = false;
  }

  /*
    Builds the display element for a single source.
    Assembled using only createElement and textContent, so the
    received strings are always displayed safely.
  */
  function createSourceItem(source, index) {
    const wrapper = document.createElement("div");
    wrapper.className = "source-item";

    // Heading (Source 1, Source 2, ...)
    const title = document.createElement("h3");
    title.textContent = "Source " + (index + 1);
    wrapper.appendChild(title);

    // Document name (only if present)
    if (source.document_name) {
      wrapper.appendChild(makeMeta("Document name: " + source.document_name));
    }

    // Chunk number (only if present)
    if (source.chunk_index !== null && source.chunk_index !== undefined) {
      wrapper.appendChild(makeMeta("Chunk number: " + source.chunk_index));
    }

    // distance (only if present; rounded to 4 decimal places for display)
    if (source.distance !== null && source.distance !== undefined) {
      const rounded = Number(source.distance).toFixed(4);
      wrapper.appendChild(makeMeta("distance: " + rounded));
    }

    // Show the details (content and document ID) as a collapsible section
    const hasContent = Boolean(source.content);
    const hasId = Boolean(source.document_id);
    if (hasContent || hasId) {
      const details = document.createElement("details");

      const summary = document.createElement("summary");
      summary.textContent = "Show details";
      details.appendChild(summary);

      // The referenced chunk's content
      if (hasContent) {
        const content = document.createElement("div");
        content.className = "source-content";
        content.textContent = source.content;
        details.appendChild(content);
      }

      // Document ID
      if (hasId) {
        const idLine = document.createElement("div");
        idLine.className = "source-id";
        idLine.textContent = "Document ID: " + source.document_id;
        details.appendChild(idLine);
      }

      wrapper.appendChild(details);
    }

    return wrapper;
  }

  /* Helper that builds one line of source metadata */
  function makeMeta(text) {
    const p = document.createElement("p");
    p.className = "source-meta";
    p.textContent = text;
    return p;
  }

  /* Display an error */
  function showError(message) {
    errorArea.textContent = message;
    errorArea.hidden = false;
  }

  /* Clear the error display */
  function hideError() {
    errorArea.textContent = "";
    errorArea.hidden = true;
  }

  /*
    Toggles the "submitting" state.
    While loading is true, the button is disabled and its label changes.
  */
  function setLoading(loading) {
    if (loading) {
      submitButton.disabled = true;
      submitButton.textContent = "Generating answer";
    } else {
      submitButton.disabled = false;
      submitButton.textContent = "Ask";
    }
  }

});
