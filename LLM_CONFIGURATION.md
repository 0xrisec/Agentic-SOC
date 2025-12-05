# Multi-LLM Provider Support

The Agentic SOC POC now supports multiple LLM providers. You can easily switch between OpenAI and Google Gemini.

## Supported Providers

- **OpenAI**: GPT-4, GPT-3.5, and other OpenAI models
- **Gemini**: Google's Gemini Pro and other Gemini models

## Configuration

### 1. Set your LLM provider in `.env`

```env
# Choose your provider (openai or gemini)
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-pro
```

### 2. Install the required dependencies

```bash
pip install -r requirements.txt
```

## Switching Between Providers

### Using OpenAI (Default)

1. Set `LLM_PROVIDER=openai` in your `.env` file
2. Add your OpenAI API key: `OPENAI_API_KEY=sk-...`
3. Optionally specify a model: `OPENAI_MODEL=gpt-4-turbo-preview`

### Using Gemini

1. Set `LLM_PROVIDER=gemini` in your `.env` file
2. Add your Gemini API key: `GEMINI_API_KEY=...`
3. Optionally specify a model: `GEMINI_MODEL=gemini-pro`

## Getting API Keys

### OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key and add it to your `.env` file

### Gemini API Key
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add it to your `.env` file

## Available Models

### OpenAI Models
- `gpt-4-turbo-preview` (recommended)
- `gpt-4`
- `gpt-3.5-turbo`
- `gpt-3.5-turbo-16k`

### Gemini Models
- `gemini-pro` (recommended)
- `gemini-pro-vision` (for multimodal tasks)

## Example Configuration

### Production with OpenAI GPT-4
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4-turbo-preview
```

### Cost-Effective with Gemini Pro
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyxxxxx
GEMINI_MODEL=gemini-pro
```

## Architecture

The multi-LLM support is implemented through:

1. **`app/config.py`**: Configuration management for all LLM providers
2. **`app/llm_factory.py`**: Factory pattern to instantiate the appropriate LLM based on configuration
3. **Agent files**: All agents use the `get_llm()` factory function instead of directly instantiating a specific provider

## Troubleshooting

### Error: API key not set
Make sure you've added the correct API key for your chosen provider in the `.env` file.

### Error: Unsupported provider
Check that `LLM_PROVIDER` is set to either `openai` or `gemini` (lowercase).

### Error: Module not found
Run `pip install -r requirements.txt` to install all required dependencies.

## Future Provider Support

To add support for additional LLM providers:

1. Add the provider's LangChain package to `requirements.txt`
2. Add configuration fields to `app/config.py`
3. Update `app/llm_factory.py` to handle the new provider
4. Add environment variables to `.env`
