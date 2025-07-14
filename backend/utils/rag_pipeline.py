from langchain_openai import OpenAI
from langchain.chains import RetrievalQA
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import logging

class RAGPipeline:
    def __init__(self, vector_store, temperature=0.7):
        self.vector_store = vector_store
        self.llm = OpenAI(temperature=temperature)
        
    def query(self, question, k=3):
        """Query the RAG pipeline with a question"""
        if not self.vector_store.has_documents():
            return "No documents available for querying."
        
        try:
            # Get retriever
            retriever = self.vector_store.get_retriever(search_kwargs={"k": k})
            
            if retriever is None:
                return "Unable to retrieve documents."
            
            # Create QA chain with invoke method
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            # Get answer using invoke method
            result = qa_chain.invoke({"query": question})
            
            # Format response with sources
            sources = []
            for doc in result.get('source_documents', []):
                sources.append({
                    'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    'source': doc.metadata.get('source', 'Unknown'),
                    'page': doc.metadata.get('page', 'N/A')
                })
            
            return {
                'answer': result['result'],
                'sources': sources,
                'question': question
            }
            
        except Exception as e:
            logging.error(f"Error in RAG pipeline: {str(e)}")
            return f"Error processing question: {str(e)}"
    
    def get_relevant_documents(self, query, k=3):
        """Get relevant documents without generating answer"""
        if not self.vector_store.has_documents():
            return []
        
        try:
            return self.vector_store.search(query, k=k)
        except Exception as e:
            logging.error(f"Error retrieving documents: {str(e)}")
            return []