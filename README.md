# Math Word Problem Solver (LLM Mini Project – PS 26)

Students struggle with word problems. This app takes a word problem in plain English, asks an LLM to
**solve it step by step**, and then **re-computes the arithmetic with Python (sympy)** to confirm the final answer.

## Features
- Step-by-step explanation in simple words, final answer on the last line
- Arithmetic verification with sympy (shows MATCH / DO NOT match)
- Works with Gemini, Groq, OpenAI or a local model via Ollama
- Streamlit UI with example problems

## How to run
```bash
pip install -r requirements.txt
cp .env.example .env        # add your free API key (Gemini or Groq)
streamlit run app.py
```
Run the tests (no API key needed): `python -m unittest discover -s tests -v`

## How it works
1. Prompt: "think step by step" + fixed format (`Step n:`, `CHECK:`, `FINAL ANSWER:` on the last line)
2. `solver.py` parses the reply and extracts the CHECK expression and final answer
3. The CHECK expression is evaluated safely with sympy (only digits and `+ - * / ( ) ^` allowed)
4. The computed value is compared with the LLM's final answer and shown in the UI

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `solver.py` | Prompt, LLM call, parsing, sympy verification |
| `tests/test_solver.py` | Unit tests for parsing and verification |

## Screenshots
<img width="1917" height="971" alt="Screenshot 2026-11-22 103230" src="https://github.com/user-attachments/assets/cbff2929-d31e-4f3f-8b72-33a644c0df23" />
<img width="1912" height="972" alt="Screenshot 2026-11-22 103312" src="https://github.com/user-attachments/assets/eb9d37a2-7531-4d49-b333-9b1b4d5f114b" />
<img width="1911" height="892" alt="Screenshot 2026-11-22 103353" src="https://github.com/user-attachments/assets/ad07bd30-0550-4d70-84bb-e2af3f7eacba" />
<img width="1912" height="867" alt="Screenshot 2026-11-22 103411" src="https://github.com/user-attachments/assets/a3bcfdaa-a9a6-4481-bb99-206294970d31" />




