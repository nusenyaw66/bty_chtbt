import os

from dotenv import load_dotenv
import pandas as pd
# from langchain_chroma import Chroma
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from anthropic import Anthropic
import tiktoken
from google.cloud import storage
from google.api_core.exceptions import NotFound, PermissionDenied

# Load environment variables from .env
load_dotenv()

# Set TOKENIZERS_PARALLELISM to false to avoid warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Define the persistent directory for local versin only
# current_dir = os.path.dirname(os.path.abspath(__file__))
# db_name = "hugging_face_FAISS_with_metadata"
# vector_store_path = os.path.join(current_dir, "db", db_name)

# GCS configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
VECTOR_STORE_GCS_PREFIX = "hugging_face_FAISS_with_metadata"  # Path in GCS bucket
LOCAL_VECTOR_STORE_PATH = "/tmp/db/hugging_face_FAISS_with_metadata"  

# Downloaded vector_store to /tmp/ for Runtime Downloads
def download_vector_store():
    """Download FAISS vector store from GCS to local temp storage if not already present."""
    if os.path.exists(LOCAL_VECTOR_STORE_PATH) and os.listdir(LOCAL_VECTOR_STORE_PATH):
        print("Vector store already downloaded locally. Skipping download.")
        return

    if not BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME is not set in environment variables.")

    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        # Check if bucket exists
        bucket.reload()
    except NotFound:
        raise ValueError(f"GCS bucket '{BUCKET_NAME}' not found.")
    except PermissionDenied:
        raise PermissionDenied("Insufficient permissions to access GCS bucket.")
    except Exception as e:
        raise RuntimeError(f"Error accessing GCS: {e}")

    # Download all files under the prefix
    blobs = bucket.list_blobs(prefix=VECTOR_STORE_GCS_PREFIX)
    os.makedirs(LOCAL_VECTOR_STORE_PATH, exist_ok=True)
    downloaded = False
    for blob in blobs:
        if blob.name.endswith('/'):  # Skip directory markers
            continue
        # Preserve relative path structure
        relative_path = blob.name[len(VECTOR_STORE_GCS_PREFIX):]
        # Remove leading slash if present to avoid absolute path issues
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
        local_path = os.path.join(LOCAL_VECTOR_STORE_PATH, relative_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)
        print(f"Downloaded {blob.name} to {local_path}")
        downloaded = True

    if not downloaded:
        raise ValueError("No files found under GCS prefix. Ensure vector store is uploaded correctly.")

# Initialize HuggingFace embeddings optimized for Traditional Chinese
# Keep the multilingual model for better Chinese text processing
embedding_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(
    model_name=embedding_model_name,
    model_kwargs={'device': 'cpu'},  # Force CPU usage to save memory
    encode_kwargs={'normalize_embeddings': True}  # Normalize for better performance
)

# Global variables for lazy initialization
vector_store = None
anthropic_client = None
chat_history = []

def initialize_components():
    """Initialize heavy components only when needed."""
    global vector_store, anthropic_client
    
    if vector_store is None:
        print("Initializing vector store...")
        # Load the vector store from GCS with memory optimization
        download_vector_store()

        # Load FAISS with memory-efficient settings
        vector_store = FAISS.load_local(
            folder_path=LOCAL_VECTOR_STORE_PATH,
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Force garbage collection after loading heavy objects
        import gc
        gc.collect()
        print("Vector store initialized successfully")
    
    if anthropic_client is None:
        print("Initializing Anthropic client...")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables. Please set it in your .env file or environment.")
        anthropic_client = Anthropic(api_key=api_key)
        print("Anthropic client initialized successfully")

# Initialize tiktoken encoder for token counting (using cl100k_base for general token counting)
tokenizer = tiktoken.get_encoding("cl100k_base")

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

# Function to retrieve relevant documents with memory optimization
def retrieve_documents(query, k=2):  # Reduced from 3 to 2 to save memory
    if vector_store is None:
        raise RuntimeError("Vector store not initialized. Call initialize_components() first.")
    results = vector_store.similarity_search(query, k=k)
    return results

# Function to generate QA prompt with chat history
def generate_qa_prompt(query, retrieved_docs):
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
    print(f"QA Prompt token count: {prompt_tokens}")
    if prompt_tokens > 1000:
        print("Warning: Prompt still exceeds 1000 tokens after truncation.")
    
    return prompt


# Function to generate answer using Claude API
def generate_answer(prompt):
    if anthropic_client is None:
        raise RuntimeError("Anthropic client not initialized. Call initialize_components() first.")
    
    try:
        # Combine system message and user prompt for Claude
        system_message = "你是您是一位負責回答中文問題的醫美助理。 請使用以下提供的相關內容來回答問題。 如果你不知道答案， 請先不要回答。 請在3句話內回答並保持答案簡潔。"
        full_prompt = f"{system_message}\n\n{prompt}"
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Use Claude 3.5 Sonnet
            max_tokens=500,  # Adjust based on desired output length
            temperature=0.9,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        
        # Safely extract the answer from the response
        content = response.content[0]
        # Some Claude SDKs return a dict, some return an object; handle both
        answer = getattr(content, 'text', None)
        if answer is None:
            # Try to get 'text' if content is a dict
            answer = content.get('text') if isinstance(content, dict) else None
        if answer is None:
            # Fallback: use string representation
            answer = str(content)
        answer = answer.strip() if isinstance(answer, str) else ""
        
        if not answer:
            answer = "無法取得回應內容。"
        # # Debug: Print response details
        # print(f"Raw API response: {answer}")
        return answer
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating answer: {error_msg}")
        # Check for authentication errors specifically
        if "401" in error_msg or "authentication" in error_msg.lower() or "api-key" in error_msg.lower():
            print("Authentication error detected. Please check your ANTHROPIC_API_KEY environment variable.")
        return "抱歉，無法生成回答，請稍後再試。"
    
# Function for Line messenger interaction
def qa_line_chatbot(query):
    import gc
    try:
        # Initialize components if not already done
        initialize_components()
        
        # Retrieve relevant documents
        retrieved_docs = retrieve_documents(query)
            
        prompt = generate_qa_prompt(query, retrieved_docs)
        answer = generate_answer(prompt)

        # Save to chat history (limit to last 10 conversations to save memory)
        chat_history.append((query, answer))
        if len(chat_history) > 10:
            chat_history.pop(0)

        # Force garbage collection to free memory
        gc.collect()

        return answer
    except Exception as e:
        print(f"Error in qa_line_chatbot: {e}")
        gc.collect()  # Clean up on error too
        return "抱歉，無法處理您的請求，請稍後再試。"

# Function for continuous chatbot interaction
def qa_chatbot():

    # Initialize components if not already done
    initialize_components()

    # print("Welcome to the QA Chatbot! Enter your question or type 'exit' to quit.")
    while True:
        query = input("Your question: ").strip()
        if query.lower() == "exit":
            print("Goodbye!")
            break
        if not query:
            print("Please enter a valid question.")
            continue
        
        # Retrieve relevant documents
        retrieved_docs = retrieve_documents(query)
        # Debug: Print retrieved documents
        print("Retrieved documents:")
        for doc in retrieved_docs:
            print(f"Metadata: {doc.metadata}, Content: {doc.page_content}")
        
        # Generate QA prompt
        prompt = generate_qa_prompt(query, retrieved_docs)
        # Debug: Print prompt details
        print(f"Prompt text: {prompt}")
        
        # Generate answer
        answer = generate_answer(prompt)

        # Save to chat history
        chat_history.append((query, answer))

        print(f"Query: {query}")
        print(f"Answer: {answer}\n")

# Run the chatbot
if __name__ == "__main__":
    qa_chatbot()