"""
Buddy Train CLI - Super Simple Local LLM Training

Commands:
    buddy train /path/to/data --name my-model    # Train a model (super simple!)
    buddy train test my-model                    # Test your trained model  
    buddy train list                             # List all your models
    buddy train delete my-model                  # Delete a model
"""

import typer
import os
from typing import Optional
from pathlib import Path

try:
    from buddy.train import train_model, test_model, list_models, delete_model, list_available_models
except ImportError:
    # Handle case where buddy.train is not available
    def train_model(*args, **kwargs):
        raise ImportError("buddy.train module not available")
    def test_model(*args, **kwargs):
        raise ImportError("buddy.train module not available") 
    def list_models(*args, **kwargs):
        raise ImportError("buddy.train module not available")
    def delete_model(*args, **kwargs):
        raise ImportError("buddy.train module not available")
    def list_available_models(*args, **kwargs):
        raise ImportError("buddy.train module not available")

# Import our super simple training functions
from buddy.train import train_model, test_model, list_models, delete_model

app = typer.Typer(help="🚀 Train your own local LLMs with custom data - SUPER SIMPLE!")

@app.command()
def train(
    data_path: str = typer.Argument(..., help="Path to your data (file or directory)"),
    name: str = typer.Option(..., "--name", "-n", help="Name for your trained model"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Base model (use aliases like 'mistral-7b', 'llama3-8b', 'phi-2' or full HuggingFace IDs)"),
    epochs: Optional[int] = typer.Option(None, "--epochs", "-e", help="Training epochs (optional, default is 3)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description for your model"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing model")
):
    """
    🚀 Train a language model on your data - SUPER SIMPLE!
    
    This command does EVERYTHING for you:
    ✅ Processes all files in your path (any format)
    ✅ Handles encoding detection automatically  
    ✅ Sets up optimal training parameters
    ✅ Trains your model locally
    ✅ Saves and manages your model
    
    Example:
        buddy train /my/documents --name my-smart-bot
    """
    try:
        if not os.path.exists(data_path):
            typer.echo(f"❌ Path not found: {data_path}")
            raise typer.Exit(1)
            
        typer.echo(f"🚀 Training model '{name}' on data from: {data_path}")
        typer.echo("📋 We'll handle everything automatically!")
        
        model_path = train_model(
            data_path=data_path,
            name=name,
            model=model,
            epochs=epochs,
            description=description,
            force=force
        )
        
        typer.echo(f"✨ Success! Your model '{name}' is ready!")
        typer.echo(f"💡 Test it with: buddy train test {name}")
        
    except Exception as e:
        typer.echo(f"❌ Training failed: {e}")
        raise typer.Exit(1)


@app.command()
def test(
    name: str = typer.Argument(..., help="Name of your trained model"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Text prompt to test"),
    max_length: int = typer.Option(100, "--max-length", "-l", help="Response length")
):
    """
    🧪 Test your trained model - SUPER SIMPLE!
    
    Example:
        buddy train test my-smart-bot --prompt "Hello, how are you?"
    """
    try:
        typer.echo(f"🧪 Testing model '{name}'...")
        
        response = test_model(name, prompt, max_length)
        typer.echo("✨ Test completed!")
        
    except Exception as e:
        typer.echo(f"❌ Testing failed: {e}")
        raise typer.Exit(1)


@app.command()
def list():
    """
    📋 List all your trained models - SUPER SIMPLE!
    
    Example:
        buddy train list
    """
    try:
        models = list_models()
        
        if not models:
            typer.echo("📂 No trained models found.")
            typer.echo("💡 Train your first model with: buddy train /path/to/data --name my-model")
        else:
            typer.echo(f"📦 Found {len(models)} trained models:")
            typer.echo()
            for model in models:
                typer.echo(f"📦 {model['name']}")
                typer.echo(f"   📝 {model.get('description', 'No description')}")
                typer.echo(f"   📅 Created: {model.get('created_at', 'Unknown')}")
                if 'num_files' in model:
                    typer.echo(f"   📁 Files: {model['num_files']}")
                typer.echo()
                
    except Exception as e:
        typer.echo(f"❌ Failed to list models: {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Name of the model to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """
    🗑️ Delete a trained model - SUPER SIMPLE!
    
    Example:
        buddy train delete old-model
    """
    try:
        if not confirm:
            confirmed = typer.confirm(f"Are you sure you want to delete model '{name}'?")
            if not confirmed:
                typer.echo("❌ Cancelled")
                return
                
        success = delete_model(name)
        if success:
            typer.echo(f"✨ Model '{name}' deleted successfully!")
        else:
            typer.echo(f"❌ Failed to delete model '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"❌ Delete failed: {e}")
        raise typer.Exit(1)


@app.command()
def install_deps():
    """
    📦 Install training dependencies
    
    This installs the required packages for training:
    - transformers
    - torch
    - datasets
    """
    import subprocess
    import sys
    
    typer.echo("📦 Installing training dependencies...")
    
    packages = [
        "transformers>=4.20.0",
        "torch>=1.12.0", 
        "datasets>=2.0.0",
        "accelerate>=0.20.0"
    ]
    
    for package in packages:
        typer.echo(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to install {package}: {e}")
            raise typer.Exit(1)
            
    typer.echo("✅ All dependencies installed successfully!")
    typer.echo("🚀 You're ready to train models!")


@app.command()
def models():
    """List all available open source models for training"""
    try:
        list_available_models()
    except Exception as e:
        typer.echo(f"❌ Error listing models: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
