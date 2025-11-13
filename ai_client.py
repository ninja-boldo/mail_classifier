import json
import subprocess
from groq import Groq

class client:
    def __init__(self, model_local="qwen3:4b", model_cloud="moonshotai/kimi-k2-instruct-0905") -> None:
        self.client = Groq()
        self.model_cloud = model_cloud
        self.model_local = model_local
    def classify_groq(self, text: str, classes: list[str]) -> str:
        result = ""
        
        # Build the prompt with classification instructions
        prompt = f"""Classify the following text into exactly ONE of these classes: {', '.join(classes)}
                    Text to classify: {text}
                    Important:
                    - Return ONLY the class name, nothing else
                    - Choose exactly one class from the provided list
                    - Use the exact class name format as provided
                    Classification:"""
                        
        completion = self.client.chat.completions.create(
            model=self.model_cloud,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=300,
            top_p=1,
            stream=True,
            stop=None
        )
        
        for chunk in completion:
            result += chunk.choices[0].delta.content or ""
        
        # Clean up the result to ensure consistent format
        result = result.strip()
        
        return result
    
    def classify_local(self, text: str, classes: list[str]):
        """
        Classifies text into one of the provided classes using a local model (Ollama).
        Forces JSON schema output for reliable parsing.
        """
        system_prompt = f"""You are a strict text classifier. Only respond in JSON with this schema:
                        {{
                        "class": "<one of: {', '.join(classes)}>"
                        }}
                        If unsure, pick the closest match.
                        """
        
        user_prompt = f"Classify the following text: {text!r}"
        
        result = subprocess.run(
            ["ollama", "run", self.model_local, "--json"],
            input=(system_prompt + "\n" + user_prompt).encode(),
            capture_output=True,
        )
        
        # Find and parse the last valid JSON in the model output
        output_text = result.stdout.decode()
        try:
            parsed = json.loads(output_text.strip().split("\n")[-1])
            return parsed["class"]
        except Exception:
            print("⚠️ Model output was not valid JSON:\n", output_text)
            return None