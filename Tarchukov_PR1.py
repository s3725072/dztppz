import os
import re
os.environ["USE_TF"]="0"
from datasets import Dataset
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer,AutoModelForCausalLM, Trainer, TrainingArguments
from trl import SFTTrainer, SFTConfig
from peft import get_peft_model,LoraConfig

with open("rules.txt", "r", encoding="utf-8") as f:
    texts=f.read()
    
dataset = Dataset.from_dict({"text": texts})

model_text=SentenceTransformer("jina-embeddings-v5-text-small",trust_remote_code=True)

embeddings=model_text.encode(dataset["text"]) 


tokenizer=AutoTokenizer.from_pretrained("microsoft/Phi-4-mini-instruct")

model=AutoModelForCausalLM.from_pretrained("microsoft/Phi-4-mini-instruct",load_in_8bit=True)

peft_config = LoraConfig(
    r=16,
    lora_alpha=16,
    lora_dropout=0.1
)

peft_model=get_peft_model(model,peft_config)

args = SFTConfig(
    num_train_epochs=2,  
    per_device_train_batch_size=4,  
    gradient_accumulation_steps=1,  
    gradient_checkpointing=True,  
    learning_rate=2e-4, 
    bf16=True, 
)

trainer=SFTTrainer(
    model=model,
    peft_config=peft_config,
    train_dataset=dataset["text"],
    tokenizer=tokenizer
)

trainer.train()

from trl import setup_chat_format

model = setup_chat_format(model=model)




