COLLECTION_NAME = "industrial_knowledge"

EMBEDDING_MODEL = "text-embedding-3-small"

CHROMA_PATH = "./data/chroma"

# Reranker Configuration
ENABLE_RERANKER = False
RERANK_TOP_N = 20
FINAL_TOP_K = 5
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
