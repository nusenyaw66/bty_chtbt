# Chat Model Documents: https://python.langchain.com/v0.2/docs/integrations/chat/
# OpenAI Chat Model Documents: https://python.langchain.com/v0.2/docs/integrations/chat/openai/

from dotenv import load_dotenv
#from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Load environment variables from .env
load_dotenv()

# Create an instance of the LLM
# model = ChatOpenAI(model="gpt-4o")
# model = ChatXAI(
#     # xai_api_key="YOUR_API_KEY",
#     model="grok-beta",
# )

import os

model = ChatGoogleGenerativeAI(
    model="gemini-pro",  # Choose the desired Gemini model
    # google_api_key=llm_api_key,  # Your Google API key
)

# # Invoke the model with a message
result = model.invoke("What is 81 divided by 9?")
print("Full result:")
print(result)
print("Content only:")
print(result.content)

# Define a prompt template
# prompt_template = """
# Translate the following English sentence to Spanish:

# {text}
# """
# prompt = PromptTemplate(
#     template=prompt_template,
#     input_variables=["text"]
# )

# # Create an LLMChain
# llm_chain = LLMChain(prompt=prompt, llm=model)

# # Run the chain with input text
# text = "I love to learn new things."
# output = llm_chain.run(text=text)

# print(output)