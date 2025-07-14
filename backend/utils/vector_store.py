from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import tempfile
import shutil
import os
import logging

class VectorStore:
    def __init__(self, session_id):
        self.session_id = session_id
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = None
        self.temp_dir = None
        
    def add_documents(self, texts):
        """Add documents to vector store"""
        try:
            if self.vectorstore is None:
                # Create temporary directory for non-persistent storage
                self.temp_dir = tempfile.mkdtemp(prefix=f"chroma_{self.session_id}_")
                
                # Create vector store with temporary directory
                self.vectorstore = Chroma.from_documents(
                    texts,
                    self.embeddings,
                    persist_directory=self.temp_dir
                )
            else:
                # Add documents to existing vector store
                self.vectorstore.add_documents(texts)
                
            return True
            
        except Exception as e:
            logging.error(f"Error adding documents to vector store: {str(e)}")
            return False
    
    def search(self, query, k=3):
        """Search for similar documents"""
        if self.vectorstore is None:
            return []
        
        try:
            return self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logging.error(f"Error searching vector store: {str(e)}")
            return []
    
    def get_retriever(self, search_kwargs=None):
        """Get retriever for RAG pipeline"""
        if self.vectorstore is None:
            return None
        
        if search_kwargs is None:
            search_kwargs = {"k": 3}
            
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    def has_documents(self):
        """Check if vector store has documents"""
        return self.vectorstore is not None
    
    def cleanup(self):
        """Clean up temporary directory and resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logging.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logging.error(f"Error cleaning up temporary directory: {str(e)}")
        
        self.vectorstore = None
        self.temp_dir = None