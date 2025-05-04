import os

from dotenv import load_dotenv
import pandas as pd
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
import tiktoken

# Load environment variables from .env
load_dotenv()

# Set TOKENIZERS_PARALLELISM to false to avoid warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Define the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
db_name = "hugging_face_chroma_with_metadata"
vector_store_path = os.path.join(current_dir, "db", db_name)

# Retrieve OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate API key
# if not OPENAI_API_KEY:
#     raise ValueError("OPENAI_API_KEY is not set. Please ensure it is defined in the .env file or environment variables.")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

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

# Function to retrieve relevant documents
def retrieve_documents(query, k=2):
    results = vector_store.similarity_search(query, k=k)
    return results

# Function to generate QA prompt
def generate_qa_prompt(query, retrieved_docs):
    context = "\n".join([f"Q: {doc.metadata['question']}\nA: {doc.page_content}" for doc in retrieved_docs])
    prompt = f"""你是一個繁體中文問答聊天機器人。請根據以下上下文或你的知識回答使用者的問題。如果上下文無相關資訊，根據你的知識提供答案；若仍不知道，說不知道。


Context:
{context}

User Question: {query}

Answer: """
    prompt_tokens = count_tokens(prompt)
    ## Debug: Print token count
    # print(f"Prompt token count: {prompt_tokens}")
    if prompt_tokens > 1000:
        print("Warning: Prompt exceeds 1000 tokens, may cause issues.")
    return prompt

# Function to generate answer using OpenAI API
def generate_answer(prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o or another model like gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "你是您是一位負責回答中文問題的醫美助理。 請使用以下提供的相關內容來回答問題。 如果你不知道答案， 請直接說你不知道。 請在3句話內回答並保持答案簡潔。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Adjust based on desired output length
            temperature=0.9,
        )
        # Extract the answer
        answer = response.choices[0].message.content.strip()
        # # Debug: Print response details
        # print(f"Raw API response: {answer}")
        # return answer
    except Exception as e:
        print(f"Error generating answer: {e}")
        return "抱歉，無法生成回答，請稍後再試。"

# Function for continuous chatbot interaction
def qa_chatbot():
    print("Welcome to the QA Chatbot! Enter your question or type 'exit' to quit.")
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
        # # Debug: Print retrieved documents
        # print("Retrieved documents:")
        # for doc in retrieved_docs:
        #     print(f"Metadata: {doc.metadata}, Content: {doc.page_content}")
        
        # Generate QA prompt
        prompt = generate_qa_prompt(query, retrieved_docs)
        # Debug: Print prompt details
        print(f"Prompt text: {prompt}")
        
        # Generate answer
        answer = generate_answer(prompt)
        print(f"Query: {query}")
        print(f"Answer: {answer}\n")

# Run the chatbot
if __name__ == "__main__":
    qa_chatbot()