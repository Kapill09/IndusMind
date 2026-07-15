COLLECTION_NAME = "industrial_knowledge"

# ── Embedding ─────────────────────────────────────────────────────────
# Must match the model actually loaded by EmbeddingService.
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

# ── Vector Store ──────────────────────────────────────────────────────
CHROMA_PATH = "./data/chroma"

# ── Reranker ──────────────────────────────────────────────────────────
ENABLE_RERANKER = True
RERANK_TOP_N = 30          # Candidates fed to cross-encoder
FINAL_TOP_K = 8            # Chunks returned after reranking
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"
MIN_RERANKER_SCORE = -4.0  # Floor: discard chunks below this cross-encoder score
RERANKER_GUARANTEED_STRUCTURED_SLOTS = 2  # Reserve top slots for exact metadata matches

# ── BM25 ──────────────────────────────────────────────────────────────
ENABLE_BM25 = True
BM25_INDEX_PATH = "./data/bm25"
BM25_TOP_K = 50            # Candidates from sparse retrieval

# ── Reciprocal Rank Fusion ────────────────────────────────────────────
RRF_K = 60                 # Standard RRF constant

# ── MMR Diversification ──────────────────────────────────────────────
ENABLE_MMR = True
MMR_LAMBDA = 0.7           # Relevance vs. diversity trade-off (1.0 = pure relevance)

# ── Intent Classification ─────────────────────────────────────────────
ENABLE_INTENT_CLASSIFIER = True
INTENT_CLASSIFIER_TIMEOUT_S = 3.0  # Max seconds for LLM-based classification

# ── Retrieval ─────────────────────────────────────────────────────────
SEMANTIC_CANDIDATE_MULTIPLIER = 4
MAX_SEMANTIC_CANDIDATES = 50

# ── Grounding ─────────────────────────────────────────────────────────
MIN_CONFIDENCE_THRESHOLD = 35  # 0-100 scale
