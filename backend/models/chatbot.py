from datetime import datetime
from utils.document_processor import DocumentProcessor
from utils.vector_store import VectorStore
from utils.rag_pipeline import RAGPipeline
from utils.insight_generator import InsightGenerator
import logging

class DocumentChatbot:
    def __init__(self, session_id):
        self.session_id = session_id
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore(session_id)
        self.rag_pipeline = RAGPipeline(self.vector_store)
        self.insight_generator = InsightGenerator(self.vector_store)
        self.documents = []
        
    def process_document(self, file_path, filename):
        """Process uploaded document and add to vector store"""
        try:
            # Process document
            success, data = self.document_processor.process_file(file_path, filename)
            
            if not success:
                return False, data  # data contains error message
            
            texts = data  # data contains processed text chunks
            
            # Add to vector store
            self.vector_store.add_documents(texts)
            
            # Generate document insights
            doc_insights = self.insight_generator.generate_document_insights(texts, filename)
            
            # Store document info with insights
            doc_info = {
                'filename': filename,
                'chunks': len(texts),
                'upload_time': datetime.now().isoformat(),
                'insights': doc_insights
            }
            self.documents.append(doc_info)
            
            return True, {
                'message': f"Successfully processed {filename} into {len(texts)} chunks",
                'insights': doc_insights
            }
            
        except Exception as e:
            logging.error(f"Error processing document: {str(e)}")
            return False, f"Error processing document: {str(e)}"
    
    def ask_question(self, question):
        """Ask a question about the uploaded documents with enhanced insights"""
        if not self.vector_store.has_documents():
            return "No documents have been uploaded yet. Please upload a document first."
        
        try:
            # Get basic RAG response
            rag_response = self.rag_pipeline.query(question)
            
            # Generate contextual insights based on the question
            insights = self.insight_generator.generate_contextual_insights(question)
            
            # Combine response with insights
            if isinstance(rag_response, dict):
                rag_response['insights'] = insights
                return rag_response
            else:
                return {
                    'answer': rag_response,
                    'insights': insights,
                    'sources': []
                }
                
        except Exception as e:
            logging.error(f"Error answering question: {str(e)}")
            return f"Error answering question: {str(e)}"
    
    def get_document_summary(self, filename=None):
        """Get comprehensive summary of document(s)"""
        try:
            return self.insight_generator.generate_document_summary(filename)
        except Exception as e:
            logging.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
    
    def get_documents(self):
        """Get list of uploaded documents"""
        return self.documents
    
    def cleanup(self):
        """Clean up resources"""
        self.vector_store.cleanup()
        self.documents.clear()