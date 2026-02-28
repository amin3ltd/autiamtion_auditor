"""
LLM Provider Module for Automaton Auditor

Supports multiple LLM providers:
- LM Studio (local)
- OpenAI
- Anthropic (Claude)
- Google Gemini
- Ollama
- Azure OpenAI
- Cohere
- Hugging Face

Each provider has specific configuration options.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import os
import logging


class LLMProvider(Enum):
    """Supported LLM providers."""
    LM_STUDIO = "lm_studio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE = "azure"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    requires_api_key: bool
    requires_base_url: bool
    supports_vision: bool
    supports_streaming: bool
    default_model: str
    models: List[str]


# Provider configurations
PROVIDER_CONFIGS: Dict[LLMProvider, ProviderConfig] = {
    LLMProvider.LM_STUDIO: ProviderConfig(
        name="LM Studio (Local)",
        requires_api_key=False,
        requires_base_url=True,
        supports_vision=False,
        supports_streaming=True,
        default_model="llama3.2:latest",
        models=["llama3.2:latest", "llama3.1:latest", "mistral:latest", 
                "gemma-3-4b:latest", "phi3:latest", "qwen2.5:latest"]
    ),
    LLMProvider.OPENAI: ProviderConfig(
        name="OpenAI",
        requires_api_key=True,
        requires_base_url=False,
        supports_vision=True,
        supports_streaming=True,
        default_model="gpt-4o",
        models=["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"]
    ),
    LLMProvider.ANTHROPIC: ProviderConfig(
        name="Anthropic (Claude)",
        requires_api_key=True,
        requires_base_url=False,
        supports_vision=True,
        supports_streaming=True,
        default_model="claude-sonnet-4-20250514",
        models=["claude-sonnet-4-20250514", "claude-opus-4-20250514", 
                "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
    ),
    LLMProvider.GOOGLE: ProviderConfig(
        name="Google Gemini",
        requires_api_key=True,
        requires_base_url=False,
        supports_vision=True,
        supports_streaming=True,
        default_model="gemini-2.0-flash-exp",
        models=["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", 
                "gemini-1.5-flash-8b"]
    ),
    LLMProvider.OLLAMA: ProviderConfig(
        name="Ollama (Local)",
        requires_api_key=False,
        requires_base_url=True,
        supports_vision=False,
        supports_streaming=True,
        default_model="llama3.2",
        models=["llama3.2", "llama3.1", "mistral", "phi3", "qwen2.5", 
                "codellama", "orca-mini", "neural-chat"]
    ),
    LLMProvider.AZURE: ProviderConfig(
        name="Azure OpenAI",
        requires_api_key=True,
        requires_base_url=True,
        supports_vision=True,
        supports_streaming=True,
        default_model="gpt-4",
        models=["gpt-4", "gpt-4-turbo", "gpt-35-turbo"]
    ),
    LLMProvider.COHERE: ProviderConfig(
        name="Cohere",
        requires_api_key=True,
        requires_base_url=False,
        supports_vision=False,
        supports_streaming=True,
        default_model="command-r-plus",
        models=["command-r-plus", "command-r", "command", "c4ai--command-r-plus"]
    ),
    LLMProvider.HUGGINGFACE: ProviderConfig(
        name="Hugging Face",
        requires_api_key=True,
        requires_base_url=False,
        supports_vision=False,
        supports_streaming=False,
        default_model="meta-llama/Llama-3.2-3B-Instruct",
        models=["meta-llama/Llama-3.2-3B-Instruct", "meta-llama/Llama-3.2-1B-Instruct",
                "microsoft/Phi-3-mini-128k-instruct", "mistralai/Mistral-7B-Instruct-v0.2"]
    ),
}


def create_llm(
    provider: LLMProvider,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
):
    """
    Create an LLM instance for the specified provider.
    
    Args:
        provider: The LLM provider to use
        model: Model name (uses default if not specified)
        api_key: API key for the provider
        base_url: Custom base URL (required for local providers)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        **kwargs: Additional provider-specific arguments
    
    Returns:
        LangChain ChatModel instance
    """
    config = PROVIDER_CONFIGS[provider]
    model = model or config.default_model
    
    # Get API key from environment if not provided
    if config.requires_api_key and not api_key:
        env_key_map = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.AZURE: "AZURE_OPENAI_API_KEY",
            LLMProvider.COHERE: "COHERE_API_KEY",
            LLMProvider.HUGGINGFACE: "HUGGINGFACE_API_KEY",
        }
        env_key = env_key_map.get(provider)
        if env_key:
            api_key = os.getenv(env_key)
    
    # Validate API key is available if required
    if config.requires_api_key and not api_key:
        raise ValueError(
            f"API key is required for {config.name}. "
            f"Set the appropriate environment variable or pass it directly."
        )
    
    # Get base URL from environment if not provided
    if config.requires_base_url and not base_url:
        url_map = {
            LLMProvider.LM_STUDIO: os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
            LLMProvider.OLLAMA: os.getenv("OLLAMA_URL", "http://localhost:11434/v1"),
        }
        base_url = url_map.get(provider)
    
    # Create the appropriate LLM
    if provider == LLMProvider.LM_STUDIO:
        return _create_lm_studio(model, base_url, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.OPENAI:
        return _create_openai(model, api_key, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.ANTHROPIC:
        return _create_anthropic(model, api_key, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.GOOGLE:
        return _create_google(model, api_key, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.OLLAMA:
        return _create_ollama(model, base_url, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.AZURE:
        return _create_azure(model, api_key, base_url, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.COHERE:
        return _create_cohere(model, api_key, temperature, max_tokens, **kwargs)
    elif provider == LLMProvider.HUGGINGFACE:
        return _create_huggingface(model, api_key, temperature, max_tokens, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _create_lm_studio(model: str, base_url: str, temperature: float, 
                      max_tokens: Optional[int], **kwargs):
    """Create LM Studio LLM."""
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key="not-needed",
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=kwargs.get("streaming", False)
    )


def _create_openai(model: str, api_key: Optional[str], temperature: float,
                   max_tokens: Optional[int], **kwargs):
    """Create OpenAI LLM."""
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=kwargs.get("streaming", False)
    )


def _create_anthropic(model: str, api_key: Optional[str], temperature: float,
                      max_tokens: Optional[int], **kwargs):
    """Create Anthropic Claude LLM."""
    from langchain_anthropic import ChatAnthropic
    
    return ChatAnthropic(
        model=model,
        anthropic_api_key=api_key,
        temperature=temperature,
        max_tokens_to_sample=max_tokens or 4096,
        streaming=kwargs.get("streaming", False)
    )


def _create_google(model: str, api_key: Optional[str], temperature: float,
                   max_tokens: Optional[int], **kwargs):
    """Create Google Gemini LLM."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
        convert_system_message_to_human=True
    )


def _create_ollama(model: str, base_url: Optional[str], temperature: float,
                   max_tokens: Optional[int], **kwargs):
    """Create Ollama LLM."""
    from langchain_ollama import ChatOllama
    
    return ChatOllama(
        model=model,
        base_url=base_url or "http://localhost:11434",
        temperature=temperature,
        num_predict=max_tokens
    )


def _create_azure(model: str, api_key: Optional[str], base_url: Optional[str],
                  temperature: float, max_tokens: Optional[int], **kwargs):
    """Create Azure OpenAI LLM."""
    from langchain_openai import AzureChatOpenAI
    
    return AzureChatOpenAI(
        model=model,
        api_key=api_key,
        azure_endpoint=base_url,
        api_version=kwargs.get("api_version", "2024-02-01"),
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=kwargs.get("streaming", False)
    )


def _create_cohere(model: str, api_key: Optional[str], temperature: float,
                   max_tokens: Optional[int], **kwargs):
    """Create Cohere LLM."""
    from langchain_cohere import ChatCohere
    
    return ChatCohere(
        model=model,
        cohere_api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens
    )


def _create_huggingface(model: str, api_key: Optional[str], temperature: float,
                        max_tokens: Optional[int], **kwargs):
    """Create Hugging Face LLM."""
    from langchain_huggingface import HuggingFaceEndpoint
    
    return HuggingFaceEndpoint(
        repo_id=model,
        huggingfacehub_api_token=api_key,
        temperature=temperature,
        max_new_tokens=max_tokens,
        task="text-generation"
    )


def get_provider_info(provider: LLMProvider) -> ProviderConfig:
    """Get configuration info for a provider."""
    return PROVIDER_CONFIGS[provider]


def list_available_providers() -> List[LLMProvider]:
    """List all available providers."""
    return list(LLMProvider)


def check_provider_health(provider: LLMProvider, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a provider is accessible.
    
    Returns:
        Dict with 'available' (bool), 'message' (str), and optionally 'models' (list)
    """
    try:
        if provider == LLMProvider.LM_STUDIO:
            return _check_lm_studio(base_url or "http://localhost:1234")
        elif provider == LLMProvider.OLLAMA:
            return _check_ollama(base_url or "http://localhost:11434")
        else:
            # For cloud providers, just check if we have credentials
            return {
                "available": True,
                "message": f"{provider.value} is configured"
            }
    except Exception as e:
        return {
            "available": False,
            "message": str(e)
        }


def _check_lm_studio(base_url: str) -> Dict[str, Any]:
    """Check LM Studio availability."""
    import requests
    
    # Get the predefined models from config as fallback
    config = PROVIDER_CONFIGS.get(LLMProvider.LM_STUDIO)
    fallback_models = config.models if config and config.models else [
        "llama3.2:latest", "llama3.1:latest", "mistral:latest", 
        "gemma-3-4b:latest", "phi3:latest", "qwen2.5:latest"
    ]
    
    try:
        # Try the /v1/models endpoint (OpenAI compatible)
        response = requests.get(f"{base_url}/models", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Handle OpenAI-compatible response format
            models = []
            if "data" in data and isinstance(data["data"], list):
                models = [m.get("id") for m in data["data"][:10] if m.get("id")]
            
            # Server is responding but may have no models loaded
            if models:
                return {
                    "available": True,
                    "server_available": True,
                    "message": "LM Studio is running",
                    "models": models
                }
            else:
                # Server running but no models loaded - return available with fallback
                return {
                    "available": True,
                    "server_available": True,
                    "message": "LM Studio is running but no models detected. Using default models.",
                    "models": fallback_models
                }
    except Exception as e:
        logging.debug(f"LM Studio health check failed: {e}")
    
    # If API call fails or returns no models, return available=False with fallback models
    # This indicates the server is not running but allows fallback models for selection
    return {
        "available": False,
        "server_available": False,
        "message": "LM Studio is not running. Using default models - ensure server is running before use.",
        "models": fallback_models
    }


def _check_ollama(base_url: str) -> Dict[str, Any]:
    """Check Ollama availability."""
    import requests
    
    # Get the predefined models from config as fallback
    config = PROVIDER_CONFIGS.get(LLMProvider.OLLAMA)
    fallback_models = config.models if config and config.models else [
        "llama3.2", "llama3.1", "mistral", "phi3", "qwen2.5", 
        "codellama", "orca-mini", "neural-chat"
    ]
    
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name") for m in models[:10]]
            
            # Server is responding but may have no models loaded
            if model_names:
                return {
                    "available": True,
                    "server_available": True,
                    "message": "Ollama is running",
                    "models": model_names
                }
            else:
                # Server running but no models loaded - return available with fallback
                return {
                    "available": True,
                    "server_available": True,
                    "message": "Ollama is running but no models detected. Using default models.",
                    "models": fallback_models
                }
    except Exception as e:
        logging.debug(f"Ollama health check failed: {e}")
    
    # If API call fails, return available=False with fallback models
    # This indicates the server is not running but allows fallback models for selection
    return {
        "available": False,
        "server_available": False,
        "message": "Ollama is not running. Using default models - ensure server is running before use.",
        "models": fallback_models
    }


# Environment variable helpers
def load_from_env() -> Optional[Any]:
    """
    Auto-detect and create LLM from environment variables.
    
    Checks in order:
    - LM_STUDIO_URL + LM_MODEL
    - OLLAMA_URL + OLLAMA_MODEL
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    - GOOGLE_API_KEY
    - etc.
    """
    # Check LM Studio
    if os.getenv("LM_STUDIO_URL") and os.getenv("LM_MODEL"):
        return create_llm(
            LLMProvider.LM_STUDIO,
            model=os.getenv("LM_MODEL"),
            base_url=os.getenv("LM_STUDIO_URL")
        )
    
    # Check Ollama
    if os.getenv("OLLAMA_URL") and os.getenv("OLLAMA_MODEL"):
        return create_llm(
            LLMProvider.OLLAMA,
            model=os.getenv("OLLAMA_MODEL"),
            base_url=os.getenv("OLLAMA_URL")
        )
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return create_llm(LLMProvider.OPENAI)
    
    # Check Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        return create_llm(LLMProvider.ANTHROPIC)
    
    # Check Google
    if os.getenv("GOOGLE_API_KEY"):
        return create_llm(LLMProvider.GOOGLE)
    
    return None
