import time
from llama_cpp import Llama

def test_phi2(model_path="phi-2.Q4_K_M.gguf"):
    # Initialize model (optimized for M1/M2)
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=20,      # Balanced GPU offload
        n_threads=4,          # Reserve cores for system
        n_ctx=2048,           # Phi-2's max context
        verbose=False
    )

    # Test cases with expected response characteristics
    test_cases = [
        {
            "name": "Factual QA",
            "prompt": "Question: What is the capital of France?\nAnswer:",
            "min_length": 3,
            "max_length": 40,
            "expected_keywords": ["Paris"]
        },
        {
            "name": "Creative Writing",
            "prompt": "Write a one-sentence story about a robot learning to love:",
            "min_length": 10,
            "max_length": 30,
            "expected_keywords": ["robot", "love"]
        },
        {
            "name": "Code Generation",
            "prompt": "Write Python code to reverse a string:\n```python\n",
            "min_length": 30,
            "max_length": 100,
            "expected_keywords": ["def", "reverse", "[::-1]"]
        }
    ]

    for test in test_cases:
        print(f"\n\033[1m[TEST] {test['name']}\033[0m")
        print(f"Prompt: {test['prompt']}")

        start_time = time.time()
        output = llm(
            prompt=test["prompt"],
            max_tokens=150,
            temperature=0.3,  # More deterministic
            stop=["Question:", "```"]  # Stop sequences
        )
        response = output["choices"][0]["text"]
        latency = time.time() - start_time

        # Calculate tokens/s (approximate)
        tokens = len(response.split())
        tokens_per_sec = tokens / latency if latency > 0 else 0

        # Print results
        print(f"Response: {response}")
        print(f"Latency: {latency:.2f}s | Tokens/s: {tokens_per_sec:.2f}")
        print(f"Length: {len(response)} chars, {tokens} tokens")

        # Validate response
        assert len(response) >= test["min_length"], f"Response too short (min {test['min_length']} chars)"
        assert len(response) <= test["max_length"], f"Response too long (max {test['max_length']} chars)"
        for keyword in test["expected_keywords"]:
            assert keyword.lower() in response.lower(), f"Missing keyword: {keyword}"
        
        print("\033[92m✓ Passed\033[0m")

if __name__ == "__main__":
    test_phi2()