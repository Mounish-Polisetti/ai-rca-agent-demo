"""
app/rag_retriever.py
---------------------
Uses LangChain + FAISS to find similar past incidents.

HOW RAG WORKS HERE:
  1. Load all Markdown incident files from data/incidents/
  2. Split them into chunks (LangChain TextSplitter)
  3. Convert chunks to vectors using Google Gemini embeddings
     (each chunk becomes a list of ~768 numbers representing its meaning)
  4. Store vectors in a FAISS index (persisted on disk in vector_store/)
  5. At query time: convert the query to a vector, find the nearest neighbours
  6. Return the top-K most similar incident chunks as context for the LLM

WHY FAISS?
  FAISS (Facebook AI Similarity Search) is a fast, local vector database.
  No cloud account needed. Runs entirely on your laptop.
  In production you'd use Pinecone, Weaviate, or pgvector instead.

WHY GEMINI EMBEDDINGS?
  We already have a Gemini API key. Google's embedding model converts
  text → 768-dimensional vectors that capture semantic meaning.
  "battery null values" and "missing feature data" map to similar vectors.
"""

import os
from langchain_community.document_loaders  import DirectoryLoader, TextLoader
from langchain.text_splitter               import RecursiveCharacterTextSplitter
from langchain_community.vectorstores      import FAISS
from langchain_google_genai                import GoogleGenerativeAIEmbeddings

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCIDENTS_DIR = os.path.join(BASE_DIR, "data", "incidents")
VECTOR_STORE  = os.path.join(BASE_DIR, "vector_store", "faiss_index")


def build_or_load_vectorstore(gemini_api_key: str):
    """
    Build the FAISS index from incident files (first run) or load it from disk.

    First run:  reads .md files → creates embeddings → saves FAISS index
    Later runs: loads the saved index (much faster)

    Returns:
        FAISS retriever object
    """
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=gemini_api_key,
    )

    # ── Load existing index if available ──────────────────────────────────
    # NOTE: if you change the embedding model, delete vector_store/faiss_index/
    # first — old index was built with a different model and won't work.
    if os.path.exists(VECTOR_STORE):
        print("[RAG] Loading existing FAISS index from disk...")
        db = FAISS.load_local(
            VECTOR_STORE,
            embeddings,
            allow_dangerous_deserialization=True,   # safe: we wrote this file
        )
        print("[RAG] ✓ FAISS index loaded.")
        return db.as_retriever(search_kwargs={"k": 2})

    # ── Build index from incident markdown files ───────────────────────────
    print("[RAG] Building FAISS index from incident files (first run)...")

    # Load all .md files in the incidents directory
    loader = DirectoryLoader(
        INCIDENTS_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents = loader.load()

    if not documents:
        raise FileNotFoundError(
            f"No .md files found in {INCIDENTS_DIR}. "
            "Make sure incident_001_battery_nulls.md and incident_002_api_latency.md exist."
        )

    print(f"[RAG] Loaded {len(documents)} incident document(s).")

    # Split documents into smaller chunks for better retrieval
    # chunk_size=500: each chunk is ~500 characters
    # chunk_overlap=50: chunks share 50 chars at the edges for context continuity
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks   = splitter.split_documents(documents)
    print(f"[RAG] Split into {len(chunks)} chunks.")

    # Create embeddings and build FAISS index
    # This calls the Gemini API once per chunk — uses your API quota
    print("[RAG] Creating embeddings via Gemini API (may take 10-20 seconds)...")
    db = FAISS.from_documents(chunks, embeddings)

    # Save to disk so we don't rebuild every time
    os.makedirs(os.path.dirname(VECTOR_STORE), exist_ok=True)
    db.save_local(VECTOR_STORE)
    print(f"[RAG] ✓ FAISS index built and saved to {VECTOR_STORE}")

    return db.as_retriever(search_kwargs={"k": 2})


def retrieve_similar_incidents(query: str, gemini_api_key: str) -> str:
    """
    Find the most similar past incidents to the given query.

    Args:
        query:           Free-text description of the current incident.
        gemini_api_key:  Your Gemini API key (from .env).

    Returns:
        String containing the most relevant incident text (injected into LLM prompt).
    """
    if not gemini_api_key:
        return "[RAG] Skipped — GEMINI_API_KEY not set."

    try:
        retriever = build_or_load_vectorstore(gemini_api_key)
        docs      = retriever.invoke(query)

        if not docs:
            return "No similar past incidents found in knowledge base."

        # Format retrieved chunks into a readable string
        parts = []
        for i, doc in enumerate(docs, 1):
            source = os.path.basename(doc.metadata.get("source", f"incident_{i}"))
            parts.append(
                f"--- RETRIEVED INCIDENT #{i} [{source}] ---\n"
                f"{doc.page_content.strip()}"
            )
            print(f"[RAG] ✓ Retrieved: {source}")

        return "\n\n".join(parts)

    except Exception as e:
        msg = f"[RAG] Error during retrieval: {e}"
        print(msg)
        return msg
