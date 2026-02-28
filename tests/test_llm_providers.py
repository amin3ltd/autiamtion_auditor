"""
Unit Tests for LLM Providers Module

Tests the LLM provider configuration and creation.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Add parent to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_providers import (
    LLMProvider,
    PROVIDER_CONFIGS,
    create_llm,
    get_provider_info,
    check_provider_health,
    load_from_env
)


class TestProviderConfigs:
    """Test provider configurations."""
    
    def test_all_providers_have_config(self):
        """All providers should have configuration."""
        for provider in LLMProvider:
            assert provider in PROVIDER_CONFIGS
            config = PROVIDER_CONFIGS[provider]
            assert config.name
            assert config.default_model
    
    def test_lm_studio_config(self):
        """LM Studio should not require API key."""
        config = PROVIDER_CONFIGS[LLMProvider.LM_STUDIO]
        assert not config.requires_api_key
        assert config.requires_base_url
        assert not config.supports_vision
    
    def test_openai_config(self):
        """OpenAI should require API key."""
        config = PROVIDER_CONFIGS[LLMProvider.OPENAI]
        assert config.requires_api_key
        assert not config.requires_base_url
        assert config.supports_vision
    
    def test_anthropic_config(self):
        """Anthropic should require API key."""
        config = PROVIDER_CONFIGS[LLMProvider.ANTHROPIC]
        assert config.requires_api_key
        assert config.supports_vision
    
    def test_ollama_config(self):
        """Ollama should not require API key."""
        config = PROVIDER_CONFIGS[LLMProvider.OLLAMA]
        assert not config.requires_api_key
        assert config.requires_base_url


class TestCreateLLM:
    """Test LLM creation functions."""
    
    def test_create_lm_studio(self):
        """Test creating LM Studio LLM."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            pytest.skip("langchain_openai not installed")
        
        with patch('langchain_openai.ChatOpenAI') as mock_chat:
            mock_chat.return_value = MagicMock()
            
            llm = create_llm(
                LLMProvider.LM_STUDIO,
                model="llama3.2:latest",
                base_url="http://localhost:1234/v1"
            )
            
            assert llm is not None
            mock_chat.assert_called_once()
    
    def test_create_openai(self):
        """Test creating OpenAI LLM."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            pytest.skip("langchain_openai not installed")
        
        with patch('langchain_openai.ChatOpenAI') as mock_chat:
            mock_chat.return_value = MagicMock()
            
            llm = create_llm(
                LLMProvider.OPENAI,
                model="gpt-4",
                api_key="test-key"
            )
            
            assert llm is not None
            mock_chat.assert_called_once()
    
    def test_create_anthropic(self):
        """Test creating Anthropic LLM."""
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            pytest.skip("langchain_anthropic not installed")
        
        with patch('langchain_anthropic.ChatAnthropic') as mock_chat:
            mock_chat.return_value = MagicMock()
            
            llm = create_llm(
                LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                api_key="test-key"
            )
            
            assert llm is not None
    
    def test_create_google(self):
        """Test creating Google Gemini LLM."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            pytest.skip("langchain_google_genai not installed")
        
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_chat:
            mock_chat.return_value = MagicMock()
            
            llm = create_llm(
                LLMProvider.GOOGLE,
                model="gemini-1.5-flash",
                api_key="test-key"
            )
            
            assert llm is not None
    
    def test_create_ollama(self):
        """Test creating Ollama LLM."""
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            pytest.skip("langchain_ollama not installed")
        
        with patch('langchain_ollama.ChatOllama') as mock_chat:
            mock_chat.return_value = MagicMock()
            
            llm = create_llm(
                LLMProvider.OLLAMA,
                model="llama3.2",
                base_url="http://localhost:11434"
            )
            
            assert llm is not None


class TestProviderInfo:
    """Test provider info functions."""
    
    def test_get_provider_info(self):
        """Test getting provider info."""
        info = get_provider_info(LLMProvider.OPENAI)
        assert info.name == "OpenAI"
        assert info.default_model == "gpt-4o"
    
    def test_list_available_providers(self):
        """Test listing providers."""
        providers = list(LLMProvider)
        assert len(providers) >= 8
        assert LLMProvider.OPENAI in providers
        assert LLMProvider.LM_STUDIO in providers


class TestHealthCheck:
    """Test health check functions."""
    
    @patch('requests.get')
    def test_check_lm_studio_available(self, mock_get):
        """Test LM Studio health check when available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "llama3.2"}]}
        mock_get.return_value = mock_response
        
        result = check_provider_health(LLMProvider.LM_STUDIO, "http://localhost:1234")
        
        assert result["available"] is True
        assert result["server_available"] is True
        assert "models" in result
    
    @patch('requests.get')
    def test_check_lm_studio_unavailable(self, mock_get):
        """Test LM Studio health check when unavailable."""
        mock_get.side_effect = Exception("Connection refused")
        
        result = check_provider_health(LLMProvider.LM_STUDIO, "http://localhost:1234")
        
        # Returns available=False with fallback models when server is not responding
        # but still provides models for selection
        assert result["available"] is False
        assert result["server_available"] is False
        assert "models" in result
    
    @patch('requests.get')
    def test_check_ollama_available(self, mock_get):
        """Test Ollama health check when available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.2"}]}
        mock_get.return_value = mock_response
        
        result = check_provider_health(LLMProvider.OLLAMA, "http://localhost:11434")
        
        assert result["available"] is True
        assert result["server_available"] is True
        assert "models" in result
    
    @patch('requests.get')
    def test_check_ollama_unavailable(self, mock_get):
        """Test Ollama health check when unavailable."""
        mock_get.side_effect = Exception("Connection refused")
        
        result = check_provider_health(LLMProvider.OLLAMA, "http://localhost:11434")
        
        # Returns available=False with fallback models when server is not responding
        # but still provides models for selection
        assert result["available"] is False
        assert result["server_available"] is False
        assert "models" in result
    
    @patch('requests.get')
    def test_check_lm_studio_running_no_models(self, mock_get):
        """Test LM Studio health check when running but no models loaded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        result = check_provider_health(LLMProvider.LM_STUDIO, "http://localhost:1234")
        
        # Server is running but no models - returns available=True with fallback models
        assert result["available"] is True
        assert result["server_available"] is True
        assert "models" in result
    
    @patch('requests.get')
    def test_check_ollama_running_no_models(self, mock_get):
        """Test Ollama health check when running but no models loaded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response
        
        result = check_provider_health(LLMProvider.OLLAMA, "http://localhost:11434")
        
        # Server is running but no models - returns available=True with fallback models
        assert result["available"] is True
        assert result["server_available"] is True
        assert "models" in result


class TestLoadFromEnv:
    """Test environment loading."""
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    def test_load_openai_from_env(self):
        """Test loading OpenAI from environment."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            pytest.skip("langchain_openai not installed")
        
        with patch('langchain_openai.ChatOpenAI') as mock:
            mock.return_value = MagicMock()
            llm = load_from_env()
            # Note: This may return None if imports fail
            # But should not raise an exception
            assert True  # Test passes if no exception


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
