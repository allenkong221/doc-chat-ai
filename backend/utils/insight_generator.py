from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
import logging
import re
from collections import Counter

class InsightGenerator:
    def __init__(self, vector_store, temperature=0.3):
        self.vector_store = vector_store
        self.llm = OpenAI(temperature=temperature)
        
        # Prompt templates for different types of insights
        self.document_analysis_prompt = PromptTemplate.from_template(
            """Analyze the following document content and provide key insights:

            Document: {filename}
            Content: {content}
            
            Please provide:
            1. Main topics and themes (3-5 key points)
            2. Document type and purpose
            3. Key findings or important information
            4. Potential questions someone might ask about this document
            
            Keep your analysis concise and actionable.
            
            Analysis:"""
        )
        
        self.contextual_insights_prompt = PromptTemplate.from_template(
            """Based on the user's question and the document content, provide contextual insights:

            User Question: {question}
            Relevant Content: {content}
            
            Please provide:
            1. How this question relates to the document's main themes
            2. Additional context or background information
            3. Related concepts or areas the user might want to explore
            4. Potential follow-up questions
            
            Insights:"""
        )
        
        self.summary_prompt = PromptTemplate.from_template(
            """Create a comprehensive summary of the document(s):

            Content: {content}
            
            Please provide:
            1. Executive Summary (2-3 sentences)
            2. Key Points (5-7 bullet points)
            3. Important Details or Data
            4. Conclusions or Recommendations (if any)
            
            Summary:"""
        )
    
    def generate_document_insights(self, texts, filename):
        """Generate insights when a document is first uploaded"""
        try:
            # Combine first few chunks for analysis
            sample_content = "\n".join([text.page_content for text in texts[:3]])
            
            # Generate basic statistics
            stats = self._generate_document_stats(texts)
            
            # Generate AI insights
            ai_insights = self.llm.invoke(
                self.document_analysis_prompt.format(
                    filename=filename,
                    content=sample_content[:3000]  # Limit content length
                )
            )
            
            return {
                'statistics': stats,
                'ai_analysis': ai_insights,
                'suggested_questions': self._generate_suggested_questions(texts)
            }
            
        except Exception as e:
            logging.error(f"Error generating document insights: {str(e)}")
            return {
                'statistics': {'error': 'Unable to generate statistics'},
                'ai_analysis': 'Unable to generate AI analysis',
                'suggested_questions': []
            }
    
    def generate_contextual_insights(self, question):
        """Generate insights based on user's question"""
        try:
            # Get relevant documents for the question
            relevant_docs = self.vector_store.search(question, k=3)
            
            if not relevant_docs:
                return {'message': 'No relevant content found for contextual insights'}
            
            # Combine relevant content
            relevant_content = "\n".join([doc.page_content for doc in relevant_docs])
            
            # Generate contextual insights
            insights = self.llm.invoke(
                self.contextual_insights_prompt.format(
                    question=question,
                    content=relevant_content[:2000]  # Limit content length
                )
            )
            
            # Generate question classification
            question_type = self._classify_question(question)
            
            return {
                'contextual_analysis': insights,
                'question_type': question_type,
                'related_content_found': len(relevant_docs),
                'suggested_follow_ups': self._generate_follow_up_questions(question, relevant_docs)
            }
            
        except Exception as e:
            logging.error(f"Error generating contextual insights: {str(e)}")
            return {'error': f'Unable to generate contextual insights: {str(e)}'}
    
    def generate_document_summary(self, filename=None):
        """Generate comprehensive document summary"""
        try:
            # Get all documents or specific document
            if filename:
                # Search for specific document chunks
                all_chunks = self.vector_store.search(f"source:{filename}", k=10)
            else:
                # Get sample from all documents
                all_chunks = self.vector_store.search("", k=10)
            
            if not all_chunks:
                return "No documents available for summary"
            
            # Combine content
            combined_content = "\n".join([chunk.page_content for chunk in all_chunks])
            
            # Generate summary
            summary = self.llm.invoke(
                self.summary_prompt.format(
                    content=combined_content[:4000]  # Limit content length
                )
            )
            
            return {
                'summary': summary,
                'chunks_analyzed': len(all_chunks),
                'document_scope': filename if filename else 'All documents'
            }
            
        except Exception as e:
            logging.error(f"Error generating document summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
    
    def _generate_document_stats(self, texts):
        """Generate basic document statistics"""
        try:
            total_chars = sum(len(text.page_content) for text in texts)
            total_words = sum(len(text.page_content.split()) for text in texts)
            
            # Extract all text for analysis
            all_text = " ".join([text.page_content for text in texts])
            
            # Count sentences (rough estimate)
            sentences = len(re.findall(r'[.!?]+', all_text))
            
            # Most common words (simple analysis)
            words = re.findall(r'\b\w+\b', all_text.lower())
            common_words = Counter(words).most_common(10)
            # Filter out common stop words
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'a', 'an', 'this', 'that', 'these', 'those'}
            filtered_words = [(word, count) for word, count in common_words if word not in stop_words]
            
            return {
                'total_chunks': len(texts),
                'total_characters': total_chars,
                'total_words': total_words,
                'estimated_sentences': sentences,
                'avg_words_per_chunk': total_words // len(texts) if texts else 0,
                'top_keywords': filtered_words[:5]
            }
            
        except Exception as e:
            logging.error(f"Error generating document stats: {str(e)}")
            return {'error': 'Unable to generate statistics'}
    
    def _classify_question(self, question):
        """Classify the type of question being asked"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['what', 'define', 'explain', 'describe']):
            return 'Definitional/Explanatory'
        elif any(word in question_lower for word in ['how', 'process', 'method', 'way']):
            return 'Process/Method'
        elif any(word in question_lower for word in ['why', 'reason', 'cause', 'because']):
            return 'Causal/Reasoning'
        elif any(word in question_lower for word in ['when', 'time', 'date', 'period']):
            return 'Temporal'
        elif any(word in question_lower for word in ['where', 'location', 'place']):
            return 'Location-based'
        elif any(word in question_lower for word in ['who', 'person', 'people', 'author']):
            return 'Person/Entity'
        elif any(word in question_lower for word in ['compare', 'difference', 'similar', 'versus']):
            return 'Comparative'
        elif any(word in question_lower for word in ['list', 'examples', 'types', 'kinds']):
            return 'Listing/Examples'
        else:
            return 'General Inquiry'
    
    def _generate_suggested_questions(self, texts):
        """Generate suggested questions based on document content"""
        try:
            # Sample content from document
            sample_content = "\n".join([text.page_content for text in texts[:2]])
            
            # Simple keyword-based question generation
            questions = []
            
            # Look for common patterns that suggest questions
            if 'process' in sample_content.lower() or 'method' in sample_content.lower():
                questions.append("How does this process work?")
            
            if 'result' in sample_content.lower() or 'conclusion' in sample_content.lower():
                questions.append("What are the main results or conclusions?")
            
            if 'problem' in sample_content.lower() or 'issue' in sample_content.lower():
                questions.append("What problems or issues are discussed?")
            
            if 'recommendation' in sample_content.lower() or 'suggest' in sample_content.lower():
                questions.append("What are the key recommendations?")
            
            # Always include generic useful questions
            questions.extend([
                "What is the main purpose of this document?",
                "What are the key takeaways?",
                "Can you summarize the main points?"
            ])
            
            return questions[:5]  # Return top 5 questions
            
        except Exception as e:
            logging.error(f"Error generating suggested questions: {str(e)}")
            return ["What is this document about?", "Can you summarize the main points?"]
    
    def _generate_follow_up_questions(self, original_question, relevant_docs):
        """Generate follow-up questions based on the original question and relevant content"""
        try:
            question_type = self._classify_question(original_question)
            
            # Basic follow-up questions based on question type
            follow_ups = []
            
            if question_type == 'Definitional/Explanatory':
                follow_ups = [
                    "Can you provide more details about this?",
                    "What are some examples of this?",
                    "How does this relate to other concepts?"
                ]
            elif question_type == 'Process/Method':
                follow_ups = [
                    "What are the steps involved?",
                    "What tools or resources are needed?",
                    "What are common challenges in this process?"
                ]
            elif question_type == 'Causal/Reasoning':
                follow_ups = [
                    "What are the implications of this?",
                    "Are there alternative explanations?",
                    "What evidence supports this reasoning?"
                ]
            else:
                follow_ups = [
                    "Can you elaborate on this topic?",
                    "What additional context is available?",
                    "Are there related topics I should explore?"
                ]
            
            return follow_ups[:3]
            
        except Exception as e:
            logging.error(f"Error generating follow-up questions: {str(e)}")
            return ["Can you provide more details?", "What else should I know about this?"]