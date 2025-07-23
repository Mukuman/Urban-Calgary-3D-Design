import requests
import os
import json
import re
from huggingface_hub import InferenceClient
from dotenv import load_dotenv


load_dotenv()



# -----------------------------------------------------------------------------
# LLM Integration: parse natural language into filter JSON
# -----------------------------------------------------------------------------


HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
MODEL_ID = "moonshotai/Kimi-K2-Instruct" 

client = InferenceClient(
    model = MODEL_ID,
    api_key = HUGGINGFACE_API_KEY,
)


def parse_query_with_llm(user_query):
    """
    Send prompt to Hugging Face Inference API to extract filter.
    Expected LLM output: a JSON object {"attribute":...,"operator":...,"value":...}
    """
    if not HUGGINGFACE_API_KEY:
        raise EnvironmentError("HUGGINGFACE_API_KEY is not set in environment")
    
    prompt = (
    f"Extract a structured filter from this natural language query: \"{user_query}\".\n"
    "Return only a JSON object with the keys 'attribute', 'operator', and 'value'.\n"
    "'attribute' must match a known column like 'height', 'stage', or 'year'.\n"
    "'operator' should be a comparison operator like '=', '>', or '<'.\n"
    "'value' can be a number or a string depending on the attribute.\n"
    "Use domain knowledge — for example, if the user asks for 'new' buildings, interpret that as buildings with 'stage' = 'NEW'.\n"
    "Use the same for if the user asks for constructed buildings"
    "Do not include any explanation or extra text."
    )
     # Call the model with a single user message for chat completion
    messages = [{"role": "user", "content": prompt}]
    
    response = client.chat_completion(messages, max_tokens=100)
    text = response.choices[0].message.content

    # Extract JSON substring from model output
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError('Could not extract JSON filter from LLM response')
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        raise ValueError(f"LLM returned invalid JSON: {text}")
    # headers = {
    #     'Authorization': f'Bearer {HUGGINGFACE_API_KEY}',
    #     'Content-Type': 'application/json'
    # }
    # payload = { 'inputs': prompt }
    # resp = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)
    # resp.raise_for_status()
    # result = resp.json()
    # # For text-generation models, result is a list with 'generated_text'
    # text = result[0].get('generated_text', '') if isinstance(result, list) else result.get('generated_text', '')
    # # Extract JSON substring
    # match = re.search(r'\{.*\}', text, re.DOTALL)
    # if not match:
    #     raise ValueError('Could not extract JSON filter from LLM response')
    # return json.loads(match.group(0))
