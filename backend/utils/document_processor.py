from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
import logging

class DocumentProcessor:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
    def process_file(self, file_path, filename):
        """Process a file and return text chunks"""
        try:
            # Load document based on file type
            if filename.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif filename.endswith('.txt'):
                loader = TextLoader(file_path)
            else:
                return False, f"Unsupported file type: {filename}"
            
            # Load and split document
            documents = loader.load()
            texts = self.text_splitter.split_documents(documents)
            
            # Add metadata
            for text in texts:
                text.metadata['source'] = filename
                text.metadata['upload_time'] = datetime.now().isoformat()
            
            return True, texts
            
        except Exception as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
            return False, f"Error processing file: {str(e)}"
    
    def get_supported_extensions(self):
        """Get list of supported file extensions"""
        return ['txt', 'pdf', 'docx']