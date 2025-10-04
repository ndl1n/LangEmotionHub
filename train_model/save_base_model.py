from transformers import AutoTokenizer, AutoModelForCausalLM

model_name = 'taide/TAIDE-LX-7B-Chat'

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

local_model_path = './saved-taide-model'
tokenizer.save_pretrained(local_model_path)
model.save_pretrained(local_model_path)

print(f"模型已保存到 {local_model_path}")