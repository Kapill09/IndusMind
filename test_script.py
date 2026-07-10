import asyncio
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService

def main():
    vdb = VectorDBService()
    print(f'Collection name: {vdb.collection_name}')
    print(f'Collection count: {vdb.count_documents()}')

    emb = EmbeddingService()
    q_emb = emb.generate_embedding('How often should a centrifugal pump be lubricated?')
    print(f'Query embedding dim: {len(q_emb)}')

    res = vdb.search(query_embedding=q_emb, top_k=5)
    print(f'Number of retrieved chunks: {len(res)}')
    if res:
        print(f'Retrieved metadata: {res[0].get("metadata")}')
    else:
        print('No results')

if __name__ == "__main__":
    main()
