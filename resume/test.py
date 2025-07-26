from transformers import T5Tokenizer, T5ForConditionalGeneration

def load_model_and_tokenizer(model_path):
    """
    Load the tokenizer and model from the specified path.
    """
    tokenizer = T5Tokenizer.from_pretrained("google-t5/t5-base")
    model = T5ForConditionalGeneration.from_pretrained(model_path)
    return tokenizer, model

def generate_text(prompt, tokenizer, model):
    """
    Generate text using the model based on the given prompt.
    """
    # Encode the input prompt to get the tensor
    input_ids = tokenizer(prompt, return_tensors="pt", padding=True).input_ids

    # Generate the output using the model
    outputs = model.generate(input_ids, max_length=512, num_return_sequences=1)

    # Decode the output tensor to human-readable text
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return generated_text

def main():
    model_path = "nakamoto-yama/t5-resume-generation"
    print(f"Loading model and tokenizer from {model_path}")
    tokenizer, model = load_model_and_tokenizer(model_path)
    
    # Test the model with a prompt
    while True:
        prompt = input("Enter a job description or title: ")
        if prompt.lower() == 'exit':
            break
        response = generate_text(f"generate resume JSON for the following job: {prompt}", tokenizer, model)
        response = response.replace("LB>", "{").replace("RB>", "}")
        print(f"Generated Response: {response}")

if __name__ == "__main__":
    main()
