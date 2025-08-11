import openai
import os
import time

openai.api_key = os.getenv("OPENAI_API_KEY")

def gpt_validate_setfile(row):
    prompt = f"Validate this EA setfile based on these stats:\n{row}"
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            if attempt < 2:
                time.sleep(60)
                continue
            return f"GPT error: Rate limit exceeded"
        except Exception as e:
            return f"GPT error: {e}"

def score_equity_curve(filename):
    prompt = f"Evaluate the durability of this EA based on equity curve HTML report name: {filename}. Score for robustness, stability, and drawdown resilience."
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            if attempt < 2:
                time.sleep(60)
                continue
            return f"GPT error: Rate limit exceeded"
        except Exception as e:
            return f"GPT error: {e}"