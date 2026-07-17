import sys
import os
sys.path.append('d:/Projects/IndusMind')
from backend.services.vectordb_service import VectorDBService
from backend.services.document_service import DocumentService

def main():
    vdb = VectorDBService()
    ds = DocumentService()

    print('=== 1. CHROMA METADATA ===')
    chunks = vdb.get_chunks()
    chroma_docs = {}
    for c in chunks:
        meta = c.get('metadata', {})
        doc_id = meta.get('document_id')
        filename = meta.get('filename')
        if doc_id not in chroma_docs:
            chroma_docs[doc_id] = {'document_id': doc_id, 'filename': filename, 'chunk_count': 1}
        else:
            chroma_docs[doc_id]['chunk_count'] += 1
            
    for d_id, data in chroma_docs.items():
        print(f"document_id: '{d_id}' | filename: '{data['filename']}' | chunks: {data['chunk_count']}")

    print('\n=== 2. FRONTEND IDs (via DocumentService) ===')
    api_docs = ds.list_documents()
    api_doc_ids = [d.get('document_id') for d in api_docs]
    for d in api_docs:
        print(f"document_id: '{d.get('document_id')}' | filename: '{d.get('filename')}'")

    print('\n=== 3. COMPARISON ===')
    chroma_ids = set(chroma_docs.keys())
    frontend_ids = set(api_doc_ids)
    print(f'IDs in Chroma: {len(chroma_ids)}')
    print(f'IDs in Frontend: {len(frontend_ids)}')
    intersection = chroma_ids.intersection(frontend_ids)
    print(f'Matching IDs: {len(intersection)}')

    if len(intersection) != len(frontend_ids):
        print('\nMISMATCH FOUND!')
        print(f'Frontend IDs not in Chroma: {frontend_ids - chroma_ids}')
        print(f'Chroma IDs not in Frontend: {chroma_ids - frontend_ids}')
    else:
        print('\nPerfect Match between Frontend IDs and Chroma IDs.')

if __name__ == "__main__":
    main()
