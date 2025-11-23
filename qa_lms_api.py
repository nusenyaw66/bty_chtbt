import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Import functions from qa_lms_chatbot.py
from qa_lms_chatbot import (
    vector_store,
    count_tokens,
    truncate_content,
    retrieve_documents,
    generate_answer,
    openai_client,
    model_name
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app (API only, no templates)
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS for all routes (needed for cross-origin requests from NAS)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize chat history storage (in-memory, per session)
# In production, consider using Redis or database for persistence
chat_histories = {}

def get_chat_history():
    """Get or create chat history for current session."""
    session_id = session.get('session_id')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    
    return chat_histories[session_id]

def generate_qa_prompt_with_history(query, retrieved_docs, chat_history):
    """Generate QA prompt with provided chat history (modified from qa_lms_chatbot.py)."""
    # Base prompt template without content
    base_prompt = f"""你是一個繁體中文問答聊天機器人。請根據以下上下文、對話歷史或你的知識回答使用者的問題。如果上下文和歷史無相關資訊，根據你的知識提供答案；若仍不知道，說不知道。

Context:
{{context}}

Chat History:
{{history_context}}

User Question: {query}

Answer: """
    
    # Format retrieved documents
    context = "\n".join([f"Q: {doc.metadata['question']}\nA: {doc.page_content}" for doc in retrieved_docs])
    
    # Format recent chat history (limit to last 3 interactions)
    history_context = ""
    for past_query, past_answer in chat_history[-3:]:
        history_context += f"Previous Q: {past_query}\nPrevious A: {past_answer}\n"
    
    # Calculate token counts
    base_tokens = count_tokens(base_prompt.format(context="", history_context=""))
    query_tokens = count_tokens(query)
    context_tokens = count_tokens(context)
    history_tokens = count_tokens(history_context)
    
    # Target max tokens for content (leaving buffer for base prompt and query)
    max_content_tokens = 900 - base_tokens - query_tokens
    
    # Truncate if necessary
    if context_tokens + history_tokens > max_content_tokens:
        # Allocate half to context, half to history
        target_context_tokens = max_content_tokens // 2
        target_history_tokens = max_content_tokens - target_context_tokens
        
        context = truncate_content(context, target_context_tokens, keep_start=True)
        history_context = truncate_content(history_context, target_history_tokens, keep_start=False)
    
    # Generate final prompt
    prompt = base_prompt.format(context=context, history_context=history_context)
    
    prompt_tokens = count_tokens(prompt)
    logger.info(f"QA Prompt token count: {prompt_tokens}")
    if prompt_tokens > 1000:
        logger.warning("Prompt still exceeds 1000 tokens after truncation.")
    
    return prompt

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """API endpoint for chat messages."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        query = data.get('message', '').strip()
        
        if not query:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get chat history for this session
        chat_history = get_chat_history()
        
        # Retrieve relevant documents
        retrieved_docs = retrieve_documents(query, k=3)
        logger.info(f"Retrieved {len(retrieved_docs)} documents for query: {query}")
        
        # Generate QA prompt with chat history
        prompt = generate_qa_prompt_with_history(query, retrieved_docs, chat_history)
        
        # Generate answer
        answer = generate_answer(prompt)
        
        # Save to chat history (limit to last 10 conversations)
        chat_history.append((query, answer))
        if len(chat_history) > 10:
            chat_history.pop(0)
        
        return jsonify({
            'response': answer,
            'query': query
        })
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '抱歉，無法處理您的請求，請稍後再試。'}), 500

@app.route('/api/clear', methods=['POST', 'OPTIONS'])
def clear_history():
    """Clear chat history for current session."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        session_id = session.get('session_id')
        if session_id and session_id in chat_histories:
            chat_histories[session_id] = []
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'error': '無法清除歷史記錄'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        logger.info(f"Health check requested from {request.remote_addr}")
        return jsonify({
            'status': 'OK',
            'model': model_name,
            'vector_store_loaded': vector_store is not None
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'ERROR', 'error': str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint - API info."""
    return jsonify({
        'service': 'Chatbot API',
        'version': '1.0',
        'endpoints': {
            'chat': '/api/chat',
            'clear': '/api/clear',
            'health': '/api/health'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5566))
    host = os.environ.get('HOST', '0.0.0.0')
    logger.info(f"Starting Flask API server on {host}:{port}")
    logger.info(f"API will be accessible at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

