"""
LM Studio Helper Module

Provides functions to create LLM instances using LM Studio's local server.
LM Studio provides an OpenAI-compatible API at http://localhost:1234/v1

Usage:
    1. Download and install LM Studio from https://lmstudio.ai/
    2. Load a model (e.g., gemma-3-4b, llama3, mistral)
    3. Click "Start Server" in LM Studio
    4. Use this module to connect:
    
    from src.lm_studio import create_lm_studio_llm
    
    llm = create_lm_studio_llm(model_name="gemma-3-4b")
"""

from typing import Optional
import os


def create_lm_studio_llm(
    model_name: str = "gemma-3-4b",
    base_url: str = "http://localhost:1234/v1",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
    ):
    """
    Create an LLM instance connected to LM Studio.
    
    Args:
        model_name: Name of the model loaded in LM Studio
                   (e.g., "gemma-3-4b", "llama3", "mistral")
        base_url: LM Studio server URL (default: http://localhost:1234/v1)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
    
    Returns:
        LangChain ChatOpenAI instance connected to LM Studio
    """
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key="not-needed",  # LM Studio doesn't require API key
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=False
    )
    
    return llm


def create_llm_from_env():
    """
    Create an LLM based on environment variables.
    
    Set either:
    - LM_STUDIO_URL and LM_MODEL for LM Studio
    - OPENAI_API_KEY for OpenAI
    
    Returns:
        LLM instance
    """
    # Check for LM Studio first
    lm_url = os.getenv("LM_STUDIO_URL")
    lm_model = os.getenv("LM_MODEL")
    
    if lm_url and lm_model:
        return create_lm_studio_llm(
            model_name=lm_model,
            base_url=lm_url
        )
    
    # Fall back to OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4",
            temperature=0.7
        )
    
    raise ValueError(
        "No LLM configured. Set LM_STUDIO_URL and LM_MODEL, "
        "or OPENAI_API_KEY in environment."
    )


# Example usage
if __name__ == "__main__":
    # Test connection to LM Studio
    print("Testing LM Studio connection...")
    print("Make sure LM Studio is running and a model is loaded!")
    print("Start the server in LM Studio, then run this script.\n")
    
    try:
        # Try to create an LLM - will fail if LM Studio isn't running
        llm = create_lm_studio_llm("gemma-3-4b")
        response = llm.invoke("Hello, how are you?")
        print(f"LM Studio connected successfully!")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Could not connect to LM Studio: {e}")
        print("\nTo fix:")
        print("1. Open LM Studio")
        print("2. Search and download a model (e.g., gemma-3-4b)")
        print("3. Click 'Start Server' in LM Studio")
