import os 
from openai import OpenAI
from pinecone import Pinecone
from typing import List, Dict 
import tiktoken 
from datetime import datetime
import json
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()

class DocumentProcessor:
    def __init__(self):
        # Initialize OpenAI 
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize logger 
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Constants
        self.embedding_model = "text-embedding-ada-002"
        self.completion_model = "gpt-4-turbo-preview"
        self.index_name = "therapy-chatbot"
        self.context_window = 10

        # Initialize Pinecone
        try:
            self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            
            if not any(index.name == self.index_name for index in existing_indexes):
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # dimensionality of text-embedding-ada-002
                    metric="cosine",
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-west-2"
                        }
                    }
                )
                self.logger.info(f"Created new Pinecone index: {self.index_name}")
            
            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            self.logger.info("Pinecone initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Pinecone: {e}")
            raise

        # Load documents into Pinecone index
        self.load_documents()

    def setup_logging(self):
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler('document_processor.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error getting embedding: {e}")
            raise

    def read_file_content(self, file_path):
        """
        Reads the content of a PDF file using PyPDFLoader.
        """
        try:
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                # Combine all page contents into a single string
                content = " ".join([doc.page_content for doc in documents])
                return content
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.error(f"Unsupported file format: {file_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
        
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into smaller chunks"""
        chunks = []
        sentences = text.split('.')
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence = sentence.strip() + '.'
            sentence_size = len(sentence)

            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_size

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def load_documents(self):
        """Load documents into Pinecone"""
        try:
            # Check if documents are already loaded
            stats = self.index.describe_index_stats()
            if stats.total_vector_count > 0:
                self.logger.info("Documents already loaded in Pinecone")
                return

            documents_dir = 'documents'
            for filename in os.listdir(documents_dir):
                file_path = os.path.join(documents_dir, filename)
                if not (filename.endswith('.txt') or filename.endswith('.pdf')):
                    continue

                # Read and process the document
                content = self.read_file_content(file_path)
                if not content:
                    self.logger.error(f"No content found in {file_path}")
                    continue

                # Split into chunks
                chunks = self.split_text_into_chunks(content)
                
                # Process chunks in batches
                batch_size = 50
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    
                    # Generate IDs and get embeddings
                    ids = [f"{filename}-chunk-{j}" for j in range(i, i + len(batch))]
                    embeddings = [self.get_embedding(text) for text in batch]
                    
                    # Create metadata
                    metadata = [{'text': text, 'source': filename} for text in batch]
                    
                    # Create vectors
                    vectors = list(zip(ids, embeddings, metadata))
                    
                    # Upsert to Pinecone
                    self.index.upsert(vectors=vectors)
                
                self.logger.info(f"Loaded {filename} into Pinecone")

            self.logger.info(f"Successfully loaded documents into Pinecone")

        except Exception as e:
            self.logger.error(f"Error loading documents: {e}")
            raise

    def query_relevant_context(self, query: str, chat_history: List[Dict[str, str]] = None) -> str:
        """Get relevant context for a query"""
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)

            # Search Pinecone
            search_results = self.index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True
            )

            # Extract relevant texts and sources
            relevant_texts = [match.metadata['text'] for match in search_results.matches]
            sources = [match.metadata['source'] for match in search_results.matches]
            
            # log the query and relevant texts
            self.logger.info(f"Query: {query}, Relevant texts: {relevant_texts}, Sources: {sources}")
            # Combine with chat history if available
            if chat_history:
                if not isinstance(chat_history, list):
                    chat_history = list(chat_history)
                recent_history = chat_history[-self.context_window:]
                history_context = " ".join([msg['message'] + " " + msg['response'] for msg in recent_history])
                return f"{history_context}\n\nRelevant context:\n\n" + "\n\n".join(relevant_texts)

            return "\n\n".join(relevant_texts)

        except Exception as e:
            self.logger.error(f"Error querying relevant context: {e}")
            return ""
