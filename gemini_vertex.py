from pathlib import Path

from google import genai
from google.genai.types import Part

client = genai.Client(
    vertexai=True,
    project="redhat-ai-analysis",
    location="global",
)

MODEL = "gemini-3.1-flash-lite"

# --- Tool calling (Flash-Lite) ---
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Tool

get_weather = FunctionDeclaration(
    name="get_weather",
    description="Get the current weather for a given city.",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'San Francisco'"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"},
        },
        "required": ["city"],
    },
)

search_restaurants = FunctionDeclaration(
    name="search_restaurants",
    description="Search for restaurants near a location.",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "Location to search near"},
            "cuisine": {"type": "string", "description": "Type of cuisine, e.g. 'italian'"},
        },
        "required": ["location"],
    },
)

tools = [Tool(function_declarations=[get_weather, search_restaurants])]

response = client.models.generate_content(
    model=MODEL,
    contents="What's the weather in Tokyo in celsius, and find me some good ramen places nearby?",
    config=GenerateContentConfig(tools=tools),
)

print("\n=== Tool calling (Flash-Lite) ===")
for part in response.candidates[0].content.parts:
    if part.function_call:
        fc = part.function_call
        print(f"Function: {fc.name}")
        print(f"Args: {fc.args}")
        print()
