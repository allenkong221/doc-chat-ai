import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import './App.css';

const API_BASE_URL = 'http://localhost:5001';

interface Message {
  type: 'user' | 'bot' | 'system' | 'error';
  content: string | { answer: string; sources?: { source: string; content: string }[] };
  timestamp: string;
}

interface Document {
  filename: string;
  chunks: number;
  upload_time: string;
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [collapsedSources, setCollapsedSources] = useState<{ [key: number]: boolean }>({});
  const [expandedSources, setExpandedSources] = useState<{ [key: string]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    createSession();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '20px';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputMessage(e.target.value);
    adjustTextareaHeight();
  };

  const createSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/session`);
      setSessionId(response.data.session_id);
    } catch (error) {
      console.error('Error creating session:', error);
    }
  };

  const onDrop = async (acceptedFiles: File[]) => {
    if (!sessionId) return;
    
    setIsUploading(true);
    
    for (const file of acceptedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      
      try {
        const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        setDocuments(response.data.documents);
        setMessages(prev => [...prev, {
          type: 'system',
          content: `Document "${file.name}" uploaded successfully!`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        
      } catch (error: any) {
        console.error('Error uploading file:', error);
        setMessages(prev => [...prev, {
          type: 'error',
          content: `Failed to upload "${file.name}": ${error.response?.data?.error || 'Unknown error'}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    }
    
    setIsUploading(false);
    setShowUploadModal(false);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    disabled: isUploading
  });

  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId || isProcessing) return;
    
    const userMessage: Message = {
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toLocaleTimeString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsProcessing(true);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        session_id: sessionId,
        question: inputMessage
      });
      
      const botMessage: Message = {
        type: 'bot',
        content: response.data.response,
        timestamp: new Date().toLocaleTimeString()
      };
      
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error: any) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.response?.data?.error || 'Failed to get response'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
    
    setIsProcessing(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatDocumentTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const toggleSources = (messageIndex: number) => {
    setCollapsedSources(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }));
  };

  const toggleSourceExpansion = (sourceKey: string) => {
    setExpandedSources(prev => ({
      ...prev,
      [sourceKey]: !prev[sourceKey]
    }));
  };

  const truncateText = (text: string, maxLength: number = 150) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const renderMessage = (message: Message, index: number) => {
    if (typeof message.content === 'object') {
      return (
        <div>
          <p>{message.content.answer}</p>
          {message.content.sources && (
            <div className="sources">
              <h4>Sources:</h4>
              {message.content.sources.map((source, i) => (
                <div key={i} className="source">
                  <strong>{source.source}:</strong> {source.content}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    return <p>{message.content}</p>;
  };

  const renderEmptyState = () => (
    <div className="empty-state">
      <div className="empty-state-icon">📄</div>
      <h2>Upload documents to get started</h2>
      <p>Upload your documents and start asking questions. I'll help you find the information you need.</p>
      <button 
        className="empty-state-button"
        onClick={() => setShowUploadModal(true)}
      >
        Upload Documents
      </button>
    </div>
  );

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <h1>Document Chat</h1>
        <div className="documents-info">
          {documents.length > 0 && (
            <span>{documents.length} document{documents.length !== 1 ? 's' : ''} uploaded</span>
          )}
          <button 
            className="upload-button"
            onClick={() => setShowUploadModal(true)}
          >
            Upload
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="container">
        {/* Chat Interface */}
        <div className="chat-container">
          <div className="messages">
            {documents.length === 0 ? renderEmptyState() : (
              <>
                {messages.map((message, index) => (
                  <div key={index} className={`message ${message.type}`}>
                    <div className="message-content">
                      {renderMessage(message)}
                    </div>
                    <div className="message-timestamp">{message.timestamp}</div>
                  </div>
                ))}
                {isProcessing && (
                  <div className="message bot">
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
          
          {/* Input Area */}
          <div className="input-area">
            <div className="input-container">
              <div className="input-wrapper">
                <textarea
                  ref={textareaRef}
                  value={inputMessage}
                  onChange={handleInputChange}
                  onKeyPress={handleKeyPress}
                  placeholder={documents.length === 0 ? "Upload documents to start chatting..." : "Type your message..."}
                  disabled={documents.length === 0 || isProcessing}
                  rows={1}
                  style={{ overflow: 'hidden' }}
                />
              </div>
              <button 
                className="send-button"
                onClick={sendMessage}
                disabled={!inputMessage.trim() || documents.length === 0 || isProcessing}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="upload-modal">
          <div className="upload-modal-content">
            <div className="upload-modal-header">
              <h2>Upload Documents</h2>
              <button 
                className="close-button"
                onClick={() => setShowUploadModal(false)}
              >
                ×
              </button>
            </div>
            
            <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''} ${isUploading ? 'uploading' : ''}`}>
              <input {...getInputProps()} />
              <div className="dropzone-icon">
                {isUploading ? '⏳' : '📁'}
              </div>
              {isUploading ? (
                <p>Uploading and processing documents...</p>
              ) : isDragActive ? (
                <p>Drop the files here...</p>
              ) : (
                <p>Drag & drop documents here, or click to select files</p>
              )}
              <small>Supported formats: PDF, TXT, DOCX</small>
            </div>
            
            {documents.length > 0 && (
              <div className="documents-list">
                <h3>Uploaded Documents</h3>
                {documents.map((doc, index) => (
                  <div key={index} className="document-item">
                    <div className="document-info">
                      <div className="document-name">{doc.filename}</div>
                      <div className="document-meta">
                        {doc.chunks} chunks • {formatDocumentTime(doc.upload_time)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;