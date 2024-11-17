from document_processor import DocumentProcessor

if __name__ == '__main__':
    doc_processor = DocumentProcessor()
    doc_processor.load_documents()
    print("Documents loaded successfully into Pinecone.")