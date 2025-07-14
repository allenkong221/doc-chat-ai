from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from models.chatbot import DocumentChatbot
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global storage for user sessions
user_sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/upload', methods=['POST'])
def upload_document():
    """Upload and process document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    session_id = request.form.get('session_id') or str(uuid.uuid4())
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get or create chatbot instance
    if session_id not in user_sessions:
        user_sessions[session_id] = DocumentChatbot(session_id)
    
    chatbot = user_sessions[session_id]
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
        file.save(file_path)
        
        # Process document
        success, message = chatbot.process_document(file_path, filename)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        if success:
            result = message  # message now contains both message and insights
            return jsonify({
                'message': result['message'],
                'insights': result['insights'],
                'session_id': session_id,
                'documents': chatbot.get_documents()
            })
        else:
            return jsonify({'error': message}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/chat', methods=['POST'])
def chat():
    """Ask question about uploaded documents"""
    data = request.json
    session_id = data.get('session_id')
    question = data.get('question')
    
    if not session_id or not question:
        return jsonify({'error': 'Session ID and question are required'}), 400
    
    if session_id not in user_sessions:
        return jsonify({'error': 'No documents found for this session'}), 404
    
    chatbot = user_sessions[session_id]
    response = chatbot.ask_question(question)
    
    return jsonify({'response': response})

@app.route('/documents/<session_id>', methods=['GET'])
def get_documents(session_id):
    """Get list of uploaded documents"""
    if session_id not in user_sessions:
        return jsonify({'documents': []})
    
    chatbot = user_sessions[session_id]
    return jsonify({'documents': chatbot.get_documents()})

@app.route('/session', methods=['POST'])
def create_session():
    """Create new session"""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = DocumentChatbot(session_id)
    return jsonify({'session_id': session_id})

@app.route('/summary/<session_id>', methods=['GET'])
def get_document_summary(session_id):
    """Get comprehensive document summary"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    chatbot = user_sessions[session_id]
    filename = request.args.get('filename')  # Optional: get summary for specific document
    
    summary = chatbot.get_document_summary(filename)
    return jsonify({'summary': summary})

@app.route('/insights/<session_id>', methods=['POST'])
def get_insights(session_id):
    """Get contextual insights for a specific question"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    chatbot = user_sessions[session_id]
    insights = chatbot.insight_generator.generate_contextual_insights(question)
    
    return jsonify({'insights': insights})

@app.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete session and cleanup resources"""
    if session_id in user_sessions:
        chatbot = user_sessions[session_id]
        chatbot.cleanup()
        del user_sessions[session_id]
        return jsonify({'message': 'Session deleted successfully'})
    return jsonify({'error': 'Session not found'}), 404

if __name__ == '__main__':
    # Set your OpenAI API key here or use environment variable
    # os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
    
    app.run(debug=True, port=5001)