import os
from dotenv import load_dotenv
import pandas as pd
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
import tiktoken
from flask import Flask, request, jsonify, render_template
from uuid import uuid4

# Load environment variables from .env
load_dotenv()

# Set TOKENIZERS_PARALLELISM to false to avoid warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize Flask app
app = Flask(__name__, template_folder="templates")

# Define the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
db_name = "hugging_face_chroma_with_metadata"
vector_store_path = os.path.join(current_dir, "db", db_name)

# Retrieve OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

chat_history = []

# Initialize HuggingFace embeddings
embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)

# Load the Chroma vector store
vector_store = Chroma(persist_directory=vector_store_path, embedding_function=embeddings)

# Initialize tiktoken encoder for token counting
tokenizer = tiktoken.encoding_for_model("gpt-4o")

# Function to count tokens
def count_tokens(text):
    return len(tokenizer.encode(text))

# Function to truncate content to fit token limit
def truncate_content(content, max_tokens, keep_start=True):
    tokens = tokenizer.encode(content)
    if len(tokens) <= max_tokens:
        return content
    if keep_start:
        return tokenizer.decode(tokens[:max_tokens])
    return tokenizer.decode(tokens[-max_tokens:])

# Function to retrieve relevant documents
def retrieve_documents(query, k=3):
    results = vector_store.similarity_search(query, k=k)
    return results

# Function to generate QA prompt with chat history
def generate_qa_prompt(query, retrieved_docs):
    base_prompt = f"""你是一個繁體中文問答聊天機器人。請根據以下上下文、對話歷史或你的知識回答使用者的問題。如果上下文和歷史無相關資訊，根據你的知識提供答案；若仍不知道，說不知道。

Context:
{{context}}

Chat History:
{{history_context}}

User Question: {query}

Answer: """
    
    context = "\n".join([f"Q: {doc.metadata['question']}\nA: {doc.page_content}" for doc in retrieved_docs])
    
    history_context = ""
    for past_query, past_answer in chat_history[-3:]:
        history_context += f"Previous Q: {past_query}\nPrevious A: {past_answer}\n"
    
    base_tokens = count_tokens(base_prompt.format(context="", history_context=""))
    query_tokens = count_tokens(query)
    context_tokens = count_tokens(context)
    history_tokens = count_tokens(history_context)
    
    max_content_tokens = 900 - base_tokens - query_tokens
    
    if context_tokens + history_tokens > max_content_tokens:
        target_context_tokens = max_content_tokens // 2
        target_history_tokens = max_content_tokens - target_context_tokens
        
        context = truncate_content(context, target_context_tokens, keep_start=True)
        history_context = truncate_content(history_context, target_history_tokens, keep_start=False)
    
    prompt = base_prompt.format(context=context, history_context=history_context)
    
    prompt_tokens = count_tokens(prompt)
    print(f"QA Prompt token count: {prompt_tokens}")
    if prompt_tokens > 1000:
        print("Warning: Prompt still exceeds 1000 tokens after truncation.")
    
    return prompt

# Function to generate answer using OpenAI API
def generate_answer(prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是您是一位負責回答中文問題的醫美助理。請使用以下提供的相關內容來回答問題。如果你不知道答案，請先不回答。請在3句話內回答並保持答案簡潔。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.9,
        )
        content = response.choices[0].message.content
        answer = content.strip() if content is not None else "無法取得回應內容。"
        return answer
    except Exception as e:
        print(f"Error generating answer: {e}")
        return "抱歉，無法生成回答，請稍後再試。"

# Route for the main web page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle chat queries
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': '請輸入有效的問題。', 'chat_id': str(uuid4())})
    
    if query.lower() == "exit":
        response = {'answer': '聊天機器人即將關閉。感謝您的使用！', 'chat_id': str(uuid4()), 'exit': True}
        # Delay the exit to allow response to be sent
        from threading import Timer
        Timer(1.0, lambda: os._exit(0)).start()
        return jsonify(response)
    
    retrieved_docs = retrieve_documents(query)
    prompt = generate_qa_prompt(query, retrieved_docs)
    answer = generate_answer(prompt)
    
    chat_history.append((query, answer))
    
    return jsonify({
        'query': query,
        'answer': answer,
        'chat_id': str(uuid4())
    })

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5798)