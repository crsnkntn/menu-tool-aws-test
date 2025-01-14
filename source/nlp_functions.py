import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key from .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

gpt_model = "gpt-4o-mini"

class InformedDeletionIndices(BaseModel):
    keep_these: List[int]


def informed_deletion(
    uncleaned: List[str], 
    topic: str,
    strictness: str
) -> List[str]:
    # Construct the prompt for GPT to decide which indices to keep
    uncleaned = [string[:30] for string in uncleaned]
    prompt_template = (
        "Here is a list of strings. I am interested in strings related to {topic}. Identify and return the indices of strings {strictness}ly related to this! Thank you."
        "The output should be a JSON object in the format provided, a list of strings in a json object:"
        "Strings:\n{strings}"
    )

    # Safely format strings by escaping problematic characters
    formatted_strings = "\n".join([f"{i}: {repr(s)}" for i, s in enumerate(uncleaned)])
    prompt = prompt_template.format(strings=formatted_strings, topic=topic, strictness=strictness)

    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=InformedDeletionIndices,
        )

        kept_indices = response.choices[0].message.parsed.keep_these
        return [uncleaned[i] for i in kept_indices]

    except Exception as e:
        print(f"Error processing prompt: {e}")
        return []

