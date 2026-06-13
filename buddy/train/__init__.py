"""
Buddy Train - Super Simple Local LLM Training

Train your own language models in just one line of code!
Everything runs locally, uses only open-source models, and is completely free.

🚀 SUPER SIMPLE USAGE:
    from buddy.train import train_model, test_model, list_models
    
    # Train a model (that's it!)
    train_model("/path/to/data", "my-awesome-model")
    
    # Test your model
    test_model("my-awesome-model", "Hello, how are you?")
    
    # List all your models
    models = list_models()

✨ CLI Usage (even simpler!):
    buddy train /path/to/data --name my-model
    buddy train test my-model
    buddy train list
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from buddy.train.data_processor import DataProcessor
from buddy.train.trainer import ModelTrainer
from buddy.train.model_manager import ModelManager
from buddy.train.integration import BuddyTrainedModel, create_trained_model

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hardcoded sensible defaults - users don't need to worry about these!
DEFAULT_MODEL = "microsoft/DialoGPT-small"  # Fast, small, good for training
DEFAULT_MAX_EPOCHS = 3
DEFAULT_BATCH_SIZE = 4
DEFAULT_LEARNING_RATE = 5e-5
DEFAULT_MAX_LENGTH = 512
DEFAULT_MODELS_DIR = os.path.join(os.path.expanduser("~"), ".buddy", "trained_models")

# Popular open source models for training
OPEN_SOURCE_TRAINING_MODELS = {
    # Small models for fast training (FREE - no auth required)
    "distilbert": "distilbert-base-uncased",
    "distilgpt2": "distilgpt2", 
    "dialogpt-small": "microsoft/DialoGPT-small",
    "dialogpt-medium": "microsoft/DialoGPT-medium",
    
    # Microsoft Phi models (FREE - no auth required)
    "phi-1": "microsoft/phi-1",
    "phi-1_5": "microsoft/phi-1_5", 
    "phi-2": "microsoft/phi-2",
    "phi-3-mini": "microsoft/Phi-3-mini-4k-instruct",
    
    # EleutherAI GPT models (FREE - no auth required)
    "gpt-neo-125m": "EleutherAI/gpt-neo-125M",
    "gpt-neo-1.3b": "EleutherAI/gpt-neo-1.3B", 
    "gpt-neo-2.7b": "EleutherAI/gpt-neo-2.7B",
    "gpt-j-6b": "EleutherAI/gpt-j-6B",
    
    # BigScience BLOOM (FREE - no auth required)
    "bloom-560m": "bigscience/bloom-560m",
    "bloom-1b1": "bigscience/bloom-1b1", 
    "bloom-3b": "bigscience/bloom-3b",
    "bloom-7b1": "bigscience/bloom-7b1",
    
    # Salesforce CodeGen (FREE - no auth required)
    "codegen-350m": "Salesforce/codegen-350M-mono",
    "codegen-2b": "Salesforce/codegen-2B-mono",
    "codegen-6b": "Salesforce/codegen-6B-mono",
    
    # Technology Innovation Institute Falcon (FREE - no auth required)
    "falcon-7b": "tiiuae/falcon-7b",
    "falcon-7b-instruct": "tiiuae/falcon-7b-instruct",
    "falcon-40b": "tiiuae/falcon-40b",
    
    # OpenLM Research OpenLlama (FREE - no auth required)
    "open-llama-3b": "openlm-research/open_llama_3b",
    "open-llama-7b": "openlm-research/open_llama_7b", 
    "open-llama-13b": "openlm-research/open_llama_13b",
    
    # Databricks Dolly (FREE - no auth required)
    "dolly-v2-3b": "databricks/dolly-v2-3b",
    "dolly-v2-7b": "databricks/dolly-v2-7b",
    "dolly-v2-12b": "databricks/dolly-v2-12b",
    
    # Meta Llama models (requires HuggingFace auth & model approval)
    "llama2-7b-chat": "meta-llama/Llama-2-7b-chat-hf",
    "llama2-13b-chat": "meta-llama/Llama-2-13b-chat-hf", 
    "llama3-8b": "meta-llama/Meta-Llama-3-8B",
    "llama3-8b-instruct": "meta-llama/Meta-Llama-3-8B-Instruct",
    
    # Mistral models (requires HuggingFace auth)
    "mistral-7b": "mistralai/Mistral-7B-v0.1",
    "mistral-7b-instruct": "mistralai/Mistral-7B-Instruct-v0.2",
    "mixtral-8x7b": "mistralai/Mixtral-8x7B-v0.1",
    
    # Google Gemma models (requires HuggingFace auth)
    "gemma-2b": "google/gemma-2b",
    "gemma-2b-it": "google/gemma-2b-it",
    "gemma-7b": "google/gemma-7b", 
    "gemma-7b-it": "google/gemma-7b-it",
}

def get_available_models() -> Dict[str, str]:
    """
    Get all available open source models for training.
    
    Returns:
        Dict[str, str]: Dictionary mapping model names to their HuggingFace identifiers
    """
    return OPEN_SOURCE_TRAINING_MODELS.copy()

def list_available_models() -> None:
    """
    Print all available open source models for training.
    """
    print("🤖 Available Open Source Models for Training:")
    print("=" * 50)
    
    categories = {
        "🟢 FREE Models (No Auth Required)": {
            "Small & Fast": ["distilbert", "distilgpt2", "dialogpt-small", "gpt-neo-125m"],
            "Microsoft Phi": ["phi-1", "phi-1_5", "phi-2", "phi-3-mini"],
            "EleutherAI Models": ["gpt-neo-125m", "gpt-neo-1.3b", "gpt-neo-2.7b", "gpt-j-6b"],
            "BigScience BLOOM": ["bloom-560m", "bloom-1b1", "bloom-3b", "bloom-7b1"],
            "Salesforce CodeGen": ["codegen-350m", "codegen-2b", "codegen-6b"],
            "Falcon Models": ["falcon-7b", "falcon-7b-instruct", "falcon-40b"],
            "OpenLlama": ["open-llama-3b", "open-llama-7b", "open-llama-13b"],
            "Databricks Dolly": ["dolly-v2-3b", "dolly-v2-7b", "dolly-v2-12b"],
        },
        "🔐 Gated Models (Requires HuggingFace Auth)": {
            "Meta Llama": ["llama2-7b-chat", "llama2-13b-chat", "llama3-8b", "llama3-8b-instruct"],
            "Mistral": ["mistral-7b", "mistral-7b-instruct", "mixtral-8x7b"],
            "Google Gemma": ["gemma-2b", "gemma-2b-it", "gemma-7b", "gemma-7b-it"],
        }
    }
    
    for main_category, subcategories in categories.items():
        print(f"\n{main_category}:")
        for category, models in subcategories.items():
            print(f"\n📂 {category}:")
            for model_key in models:
                if model_key in OPEN_SOURCE_TRAINING_MODELS:
                    print(f"   • {model_key} -> {OPEN_SOURCE_TRAINING_MODELS[model_key]}")
    
    print(f"\n💡 Usage: train_model('/path/to/data', 'my-model', model='phi-2')")
    print(f"💡 Or use HuggingFace model ID directly: model='microsoft/phi-2'")
    print(f"\n🚀 Recommended for beginners: 'distilgpt2', 'phi-2', 'gpt-neo-125m'")
    print(f"🔐 For gated models, run: huggingface-cli login")

def resolve_model_name(model: str) -> str:
    """
    Resolve a model name to its HuggingFace identifier.
    
    Args:
        model: Model name (can be alias or full HuggingFace ID)
        
    Returns:
        str: HuggingFace model identifier
    """
    if model in OPEN_SOURCE_TRAINING_MODELS:
        return OPEN_SOURCE_TRAINING_MODELS[model]
    return model

def train_model(
    data_path: str,
    name: str,
    model: Optional[str] = None,
    epochs: Optional[int] = None,
    description: Optional[str] = None,
    force: bool = False
) -> str:
    """
    🚀 Train a language model on your data - SUPER SIMPLE!
    
    This function does EVERYTHING for you:
    ✅ Processes your data (any file type)
    ✅ Validates and cleans the data
    ✅ Sets up training with optimal parameters
    ✅ Trains the model locally
    ✅ Saves and manages the model
    
    Args:
        data_path: Path to your data (file or directory)
        name: Name for your trained model
        model: Base model - use aliases like 'mistral-7b', 'llama3-8b', 'phi-2' or full HuggingFace IDs
        epochs: Training epochs (optional - we use 3)
        description: Description for your model (optional)
        force: Overwrite existing model (optional)
        
    Returns:
        Path to your trained model
        
    Examples:
        >>> # Basic usage with default model
        >>> model_path = train_model("/my/documents", "my-smart-bot")
        
        >>> # Using open source models
        >>> train_model("/my/data", "chitti", model="mistral-7b")
        >>> train_model("/my/data", "assistant", model="llama3-8b-instruct")
        >>> train_model("/my/data", "coder", model="phi-3-mini")
        
        >>> # See all available models
        >>> list_available_models()
    """
    try:
        print(f"🚀 Starting Buddy Train for '{name}'...")
        print("📋 We'll handle everything for you - just sit back and relax!")
        
        # Resolve model name to HuggingFace identifier
        model = resolve_model_name(model or DEFAULT_MODEL)
        epochs = epochs or DEFAULT_MAX_EPOCHS
        
        print(f"🤖 Using base model: {model}")
        
        # Create models directory
        os.makedirs(DEFAULT_MODELS_DIR, exist_ok=True)
        output_dir = os.path.join(DEFAULT_MODELS_DIR, name)
        
        # Check if model already exists
        if os.path.exists(output_dir) and not force:
            print(f"❌ Model '{name}' already exists. Use force=True to overwrite.")
            return output_dir
            
        print(f"📁 Processing data from: {data_path}")
        print("🔍 Reading all files with multiple encoding attempts...")
        
        # Step 1: Process data automatically (handles EVERYTHING)
        processor = DataProcessor()
        processed_data = processor.process_directory(data_path)
        
        if not processed_data.texts:
            raise ValueError("No valid data found in the provided path")
            
        total_chars = sum(len(text) for text in processed_data.texts)
        print(f"✅ Processed {processed_data.stats['processed_files']} files ({total_chars:,} characters)")
        
        # Step 2: Train the model automatically (optimal settings)
        print(f"🔥 Training model '{name}' with optimal settings...")
        print("⏰ This may take 5-30 minutes depending on your data size...")
        
        trainer = ModelTrainer(
            base_model=model,
            output_dir=output_dir
        )
        
        # Create training config with our optimal settings
        training_config = {
            'num_epochs': epochs,
            'batch_size': DEFAULT_BATCH_SIZE,
            'learning_rate': DEFAULT_LEARNING_RATE,
            'max_length': DEFAULT_MAX_LENGTH
        }
        
        trainer.train_from_data(processed_data, training_config)
        
        # Step 3: Save metadata automatically
        import json
        from datetime import datetime
        
        metadata = {
            "name": name,
            "description": description or f"Model trained on {data_path}",
            "base_model": model,
            "epochs": epochs,
            "data_path": data_path,
            "num_files": processed_data.stats['processed_files'],
            "total_characters": total_chars,
            "created_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(output_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
            
        print(f"🎉 Model '{name}' trained successfully!")
        print(f"📍 Saved to: {output_dir}")
        print(f"💡 Test it with: test_model('{name}')")
        
        return output_dir
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        print(f"❌ Training failed: {e}")
        raise


def test_model(name: str, prompt: Optional[str] = None, max_length: int = 100) -> str:
    """
    🧪 Test a trained model - SUPER SIMPLE!
    
    Args:
        name: Name of your trained model
        prompt: What to ask your model (optional - we'll use a default)
        max_length: Response length (optional - default is 100)
        
    Returns:
        Your model's response
        
    Example:
        >>> response = test_model("my-smart-bot", "Hello!")
        >>> print(response)
    """
    try:
        model_path = os.path.join(DEFAULT_MODELS_DIR, name)
        
        if not os.path.exists(model_path):
            available = [m['name'] for m in list_models()]
            raise ValueError(f"Model '{name}' not found. Available: {available}")
            
        print(f"🧪 Testing model '{name}'...")
        
        # Load and test
        manager = ModelManager()
        manager.load_model(model_path)
        
        test_prompt = prompt or "Hello, how can I help you today?"
        print(f"📝 Prompt: {test_prompt}")
        
        response = manager.generate_text(test_prompt, max_length=max_length)
        print(f"🤖 Response: {response}")
        
        return response
        
    except Exception as e:
        logger.error(f"Testing failed: {e}")
        print(f"❌ Testing failed: {e}")
        raise


def list_models() -> List[Dict[str, Any]]:
    """
    📋 List all your trained models - SUPER SIMPLE!
    
    Returns:
        List of your models with details
        
    Example:
        >>> models = list_models()
        >>> for model in models:
        ...     print(f"📦 {model['name']} - {model['description']}")
    """
    try:
        if not os.path.exists(DEFAULT_MODELS_DIR):
            print("📂 No models directory found. Train your first model!")
            return []
            
        models = []
        for model_name in os.listdir(DEFAULT_MODELS_DIR):
            model_path = os.path.join(DEFAULT_MODELS_DIR, model_name)
            metadata_path = os.path.join(model_path, "metadata.json")
            
            if os.path.isdir(model_path):
                if os.path.exists(metadata_path):
                    import json
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    models.append(metadata)
                else:
                    # Fallback for models without metadata
                    models.append({
                        "name": model_name,
                        "description": "Legacy model (no description)",
                        "created_at": "Unknown"
                    })
        
        if models:
            print(f"📦 Found {len(models)} trained models:")
            for model in models:
                print(f"   • {model['name']} - {model.get('description', 'No description')}")
        else:
            print("📂 No trained models found. Train your first model!")
                    
        return models
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return []


def delete_model(name: str) -> bool:
    """
    🗑️ Delete a trained model - SUPER SIMPLE!
    
    Args:
        name: Name of the model to delete
        
    Returns:
        True if deleted successfully
    """
    try:
        model_path = os.path.join(DEFAULT_MODELS_DIR, name)
        
        if not os.path.exists(model_path):
            print(f"❌ Model '{name}' not found")
            return False
            
        import shutil
        shutil.rmtree(model_path)
        print(f"🗑️ Model '{name}' deleted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return False


def use_with_agent(model_name: str, agent_name: str = "My Custom Agent", instructions: str = None):
    """
    🤖 Use your trained model with a Buddy Agent - SUPER SIMPLE!
    
    This creates a complete AI agent powered by your custom trained model.
    
    Args:
        model_name: Name of your trained model
        agent_name: Name for your agent (optional)
        instructions: Instructions for your agent (optional)
        
    Returns:
        Configured Buddy agent ready to use
        
    Example:
        >>> agent = use_with_agent("my-smart-bot")
        >>> response = agent.run("Hello, how are you?")
        >>> print(response.content)
    """
    try:
        model_path = os.path.join(DEFAULT_MODELS_DIR, model_name)
        
        if not os.path.exists(model_path):
            available = [m['name'] for m in list_models()]
            raise ValueError(f"Model '{model_name}' not found. Available: {available}")
        
        # Import here to avoid circular imports
        from buddy.train.integration import create_trained_model
        from buddy import Agent
        
        # Create the trained model
        trained_model = create_trained_model(
            model_path=model_path,
            model_name=f"Trained Model: {model_name}"
        )
        
        # Create the agent
        default_instructions = f"You are a helpful AI assistant powered by a custom trained model named '{model_name}'. You were trained on specific data to be helpful and informative."
        
        agent = Agent(
            name=agent_name,
            model=trained_model,
            instructions=instructions or default_instructions
        )
        
        print(f"🤖 Created agent '{agent_name}' with trained model '{model_name}'")
        print(f"💡 Usage: response = agent.run('your message')")
        
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        print(f"❌ Failed to create agent: {e}")
        raise


# Version info
__version__ = "26.1"

# Export the simple API that users actually want
__all__ = [
    # 🌟 SIMPLE API - This is what users will use!
    "train_model",     # Train a model in one line
    "test_model",      # Test a model in one line  
    "list_models",     # List all models
    "delete_model",    # Delete a model
    "use_with_agent",  # Use model with buddy agent - SUPER SIMPLE!
    
    # 🔧 ADVANCED API - For power users who want control
    "DataProcessor",
    "ModelTrainer", 
    "ModelManager",
    "BuddyTrainedModel",
    "create_trained_model"
]
