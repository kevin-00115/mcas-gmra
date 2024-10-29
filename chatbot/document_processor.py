from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
import pinecone
import os
from dotenv import load_dotenv

class DocumentProcessor:
    def __init__(self, docs_dir="documents"):
        self.docs_dir = docs_dir
        self.embeddings = OpenAIEmbeddings()
        
        # Load environment variables
        load_dotenv()
        
        # Initialize Pinecone
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment=os.getenv("PINECONE_ENVIRONMENT")
        )
        
        # Create documents directory if it doesn't exist
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)
        
        # Set index name
        self.index_name = "chatbot-index"
        
        # Create Pinecone index if it doesn't exist
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=self.index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine"
            )

    def process_documents(self):
        # Load documents from the documents directory
        loader = DirectoryLoader(self.docs_dir, glob="**/*.txt")
        documents = loader.load()
        
        # Split documents into chunks
        text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separator="\n"
        )
        texts = text_splitter.split_documents(documents)
        
        # Create vector store using Pinecone
        vectorstore = Pinecone.from_documents(
            documents=texts,
            embedding=self.embeddings,
            index_name=self.index_name
        )
        
        return vectorstore

    def query_documents(self, vectorstore, query, k=3):
        # Search for relevant documents
        docs = vectorstore.similarity_search(query, k=k)
        context = "\n".join([doc.page_content for doc in docs])
        return context

    def clear_vector_store(self):
        # Delete all vectors in the index
        if self.index_name in pinecone.list_indexes():
            pinecone.delete_index(self.index_name)
