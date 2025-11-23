import os

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import tiktoken
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Set TOKENIZERS_PARALLELISM to false to avoid warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Define the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
db_name = "hugging_face_FAISS_with_metadata"
vector_store_path = os.path.join(current_dir, "db", db_name)

# Model configuration for LM Studio
model_name = "qwen2.5-7b-instruct-mlx"

# Initialize OpenAI client for LM Studio local server
openai_client = OpenAI(
    base_url="http://10.20.11.199:1234/v1",  # LM Studio local server URL with /v1 endpoint
    api_key="not-needed",  # LM Studio doesn't require an API key
    timeout=60  # Optional: Set a timeout for requests
)

# Initialize HuggingFace embeddings
embedding_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(
    model_name=embedding_model_name,
    model_kwargs={'device': 'cpu'},  # Force CPU usage to save memory
    encode_kwargs={'normalize_embeddings': True}  # Normalize for better performance
)

# Load the FAISS vector store
vector_store = FAISS.load_local(
            folder_path=vector_store_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
# Initialize chat history
chat_history = []

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

# Function to retrieve relevant documents
def retrieve_documents(query, k=3):
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

# Function to generate answer using LM Studio local server
def generate_answer(prompt):
    try:
        response = openai_client.chat.completions.create(
            model=model_name,  # Use qwen2.5-7b-instruct-mlx model on LM Studio
            messages=[
                {"role": "system", "content": "你是您是一位負責回答中文問題的醫美助理。 請使用以下提供的相關內容和對話歷史來回答問題。 如果你不知道答案， 請直接說你不知道。 請在3句話內回答並保持答案簡潔。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.9,
        )
        
        # Debug: Print response structure
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")
        
        # Safely extract the answer with proper None checks
        if response is None:
            print("Error: Response is None")
            return "無法取得回應內容。回應為空。"
        
        if not hasattr(response, 'choices') or response.choices is None:
            print("Error: Response has no 'choices' attribute or it is None")
            return "無法取得回應內容。回應結構錯誤。"
        
        if len(response.choices) == 0:
            print("Error: Response.choices is empty")
            return "無法取得回應內容。沒有可用的選擇。"
        
        if not hasattr(response.choices[0], 'message') or response.choices[0].message is None:
            print("Error: Response.choices[0] has no 'message' attribute or it is None")
            return "無法取得回應內容。訊息結構錯誤。"
        
        content = response.choices[0].message.content
        answer = content.strip() if content is not None else "無法取得回應內容。"
        print(f"Raw API response: {answer}")
        return answer
    except Exception as e:
        print(f"Error generating answer: {e}")
        import traceback
        traceback.print_exc()
        return "抱歉，無法生成回答，請稍後再試。"

# Function for continuous chatbot interaction
def qa_chatbot():
    print("Welcome to the QA Chatbot! Enter your question or type 'exit' to quit.")
    global chat_history
    while True:
        query_input = input("Your question: ")
        query = query_input.strip() if query_input is not None else ""
        if query.lower() == "exit":
            print("Goodbye!")
            break
        if not query:
            print("Please enter a valid question.")
            continue
        
        # Retrieve relevant documents
        retrieved_docs = retrieve_documents(query)
        
        # Generate QA prompt
        prompt = generate_qa_prompt(query, retrieved_docs)
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