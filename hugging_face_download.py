from transformers import DistilBertTokenizer, DistilBertModel

# Download the tokenizer
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

# Download the model
model = DistilBertModel.from_pretrained('distilbert-base-uncased')

# Save them if you want to use them offline
tokenizer.save_pretrained("./distilbert_base_uncased_tokenizer")
model.save_pretrained("./distilbert_base_uncased_model")