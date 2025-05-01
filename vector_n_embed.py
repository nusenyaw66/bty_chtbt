import os
import glob
import pandas as pd
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# Define the directory containing the text files and the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
books_dir = os.path.join(current_dir, "books")
db_dir = os.path.join(current_dir, "db")
db_name = "hugging_face_with_metadata"

print(f"Books directory: {books_dir}")
print(f"DB directory: {db_dir}")

# make embeddings a global variable
# embeddings = None

def load_csvs_to_documents(csv_directory):
    """
    Load multiple Q&A CSV files and convert them to LangChain Document objects.
    """
    documents = []
    # Get all CSV files in the directory
    csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
    
    if not csv_files:
        raise ValueError(f"No CSV files found in {csv_directory}")
    
    for csv_file in csv_files:
        try:
            print(f"Processing {csv_file}...")
            # Load CSV
            df = pd.read_csv(csv_file)
            
            # Validate required columns
            required_columns = ["Question", "Answer"]
            if not all(col in df.columns for col in required_columns):
                print(f"Skipping {csv_file}: Missing required columns {required_columns}")
                continue
            
            # Convert rows to Document objects
            for _, row in df.iterrows():
                doc = Document(
                    page_content=str(row["Question"]),  # Embed the question
                    metadata={
                        "index": str(row["ID"]),  # Ensure ID is a string
                        "answer": str(row["Answer"]),
                        "category": str(row.get("Category", "")),  # Handle optional columns
                        "source_file": os.path.basename(csv_file)  # Track source file
                    }
                )
                documents.append(doc)
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
    
    if not documents:
        raise ValueError("No valid documents created from CSV files")
    
    print(f"Created {len(documents)} documents from {len(csv_files)} CSV files")
    return documents

# Function to create and persist vector store
def create_vector_store(docs, store_name, embeddings):
    persistent_db = os.path.join(db_dir, store_name)
    if not os.path.exists(persistent_db):
        print(f"\n--- Creating vector store {store_name} ---")

        # Create vector store with FAISS
        vector_store = FAISS.from_documents(
        documents=docs,
        embedding=embeddings
        )

        # Save vector store to disk
        vector_store.save_local(persistent_db)

        print(f"--- Finished creating vector store {store_name} ---")
    else:
        print(
            f"Vector store {store_name} already exists. No need to initialize.")

def main():
    # Check if the Chroma vector store already exists， if not, create it
    persistent_directory = os.path.join(db_dir, db_name)

    if not os.path.exists(persistent_directory):
        print("Persistent directory does not exist. Initializing vector store...")

        # Step 1: Load and prepare CSV files
        # Ensure the books directory exists
        if not os.path.exists(books_dir):
            raise FileNotFoundError(
                f"The directory {books_dir} does not exist. Please check the path."
            )
        else:
            documents = load_csvs_to_documents(books_dir)

        # Step 2: Initialize HuggingFaceEmbeddings
        print("\n--- Using Hugging Face Transformers ---")
        embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",  # Fast, effective for semantic similarity
        model_kwargs={"device": "cpu"}   # Use GPU if available: "cuda"
        )
        print("\n--- Finished creating embeddings with Hugging Face.---")
        
        # Step 3: Create the vector store and persist it
        create_vector_store(documents, db_name, embeddings)

    else:
        print("Vector store already exists. No need to initialize.")


if __name__ == "__main__":
    main()        