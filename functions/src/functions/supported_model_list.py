MODELS_WITH_STREAMING_SUPPORT = [
    # Amazon Nova & Titan (available in eu-central-1)
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0",
    "amazon.titan-text-express-v1:0:8k",
    "amazon.titan-text-express-v1",
    "amazon.titan-text-lite-v1:0:4k", 
    "amazon.titan-text-lite-v1",
    
    # Anthropic Claude (available in eu-central-1)
    "anthropic.claude-sonnet-4-20250514-v1:0",          # Claude Sonnet 4 (latest)
    "arn:aws:bedrock:eu-central-1:037708943013:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0",        # Claude 3.7 Sonnet  
    "anthropic.claude-3-5-sonnet-20240620-v1:0",        # Claude 3.5 Sonnet
    "anthropic.claude-3-sonnet-20240229-v1:0",          # Claude 3 Sonnet
    "anthropic.claude-3-haiku-20240307-v1:0",           # Claude 3 Haiku
    
    # Legacy Anthropic models
    "anthropic.claude-v2:1:200k",
    "anthropic.claude-v2:1:18k",
    "anthropic.claude-v2:1",
    "anthropic.claude-v2",
    "anthropic.claude-instant-v1",
    
    # Mistral AI (available in eu-central-1)
    "mistral.pixtral-large-2502-v1:0",
    
    # Meta Llama (available in eu-central-1) 
    "meta.llama3-2-3b-instruct-v1:0",
    "meta.llama3-2-1b-instruct-v1:0"
]