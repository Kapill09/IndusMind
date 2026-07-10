from backend.services.vectordb_service import VectorDBService

db = VectorDBService()

print("Collection Name:", db.collection.name)
print("Document Count:", db.collection.count())