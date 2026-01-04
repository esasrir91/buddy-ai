"""
Buddy CLI Train Commands

Training commands for creating and managing local LLMs.
"""

import typer
from pathlib import Path
from typing import Optional
import json

from buddy.train.trainer import ModelTrainer
from buddy.train.data_processor import DataProcessor
from buddy.train.model_manager import ModelManager
from buddy.train import list_available_models, get_available_models
from buddy.utils.log import logger

train_cli = typer.Typer(
    help="Train your own local LLMs with custom data",
    no_args_is_help=True,
    add_completion=False,
)


@train_cli.command("data")
def process_data(
    data_path: str = typer.Argument(..., help="Path to directory containing training data"),
    output_path: str = typer.Option("./processed_data.json", "-o", "--output", help="Output path for processed data"),
    min_length: int = typer.Option(10, "--min-length", help="Minimum text length to include"),
    max_length: int = typer.Option(10000, "--max-length", help="Maximum text length per chunk"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging"),
):
    """
    Process training data from a directory.
    
    Traverses the directory recursively and processes all readable files,
    attempting multiple encodings to maximize data extraction.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        processor = DataProcessor(
            min_text_length=min_length,
            max_text_length=max_length
        )
        
        typer.echo(f"Processing data from: {data_path}")
        processed_data = processor.process_directory(data_path)
        
        # Save processed data
        processor.save_processed_data(processed_data, output_path)
        
        # Display statistics
        stats = processed_data.stats
        typer.echo(f"\n📊 Processing Statistics:")
        typer.echo(f"  Files found: {stats['total_files_found']}")
        typer.echo(f"  Files processed: {stats['processed_files']}")
        typer.echo(f"  Files skipped: {stats['skipped_files']}")
        typer.echo(f"  Total text chunks: {stats['total_texts']}")
        typer.echo(f"  Total characters: {stats['total_characters']:,}")
        typer.echo(f"  Average text length: {stats['avg_text_length']:.1f}")
        
        if stats.get('encoding_stats'):
            typer.echo(f"\n📝 Encodings used:")
            for encoding, count in stats['encoding_stats'].items():
                typer.echo(f"  {encoding}: {count} files")
        
        if stats.get('file_type_stats'):
            typer.echo(f"\n📄 File types processed:")
            for file_type, count in stats['file_type_stats'].items():
                typer.echo(f"  {file_type}: {count} files")
        
        typer.echo(f"\n✅ Data processed successfully! Output saved to: {output_path}")
        
    except Exception as e:
        typer.echo(f"❌ Error processing data: {e}", err=True)
        raise typer.Exit(1)


@train_cli.command("model")
def train_model(
    data_path: str = typer.Argument(..., help="Path to processed data file (.json)"),
    name: str = typer.Option(..., "-n", "--name", help="Custom name for the trained model (required)"),
    base_model: str = typer.Option("microsoft/DialoGPT-small", "-b", "--base-model", help="Base model to fine-tune (use aliases like 'mistral-7b', 'llama3-8b', 'phi-2' or full HuggingFace IDs)"),
    output_dir: str = typer.Option("./trained_models", "-o", "--output", help="Output directory for trained model"),
    epochs: int = typer.Option(3, "--epochs", help="Number of training epochs"),
    batch_size: int = typer.Option(4, "--batch-size", help="Training batch size"),
    learning_rate: float = typer.Option(5e-5, "--learning-rate", help="Learning rate"),
    max_length: int = typer.Option(512, "--max-length", help="Maximum sequence length"),
    save_steps: int = typer.Option(500, "--save-steps", help="Save model every N steps"),
    eval_steps: int = typer.Option(500, "--eval-steps", help="Evaluate model every N steps"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging"),
):
    """
    Train a language model on processed data.
    
    Uses the processed data to fine-tune a base language model.
    All training is done locally without requiring external API calls.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Load processed data
        if not Path(data_path).exists():
            typer.echo(f"❌ Data file not found: {data_path}", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"🚀 Starting model training...")
        typer.echo(f"  Data: {data_path}")
        typer.echo(f"  Base model: {base_model}")
        typer.echo(f"  Output: {output_dir}")
        
        # Initialize trainer
        trainer = ModelTrainer(
            base_model=base_model,
            output_dir=Path(output_dir) / name
        )
        
        # Training configuration
        config = {
            'num_epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate,
            'max_length': max_length,
            'save_steps': save_steps,
            'eval_steps': eval_steps,
        }
        
        # Start training
        results = trainer.train_from_processed_data(data_path, config)
        
        typer.echo(f"\n✅ Training completed successfully!")
        typer.echo(f"  Model saved to: {trainer.output_dir}")
        typer.echo(f"  Training loss: {results.get('final_loss', 'N/A')}")
        typer.echo(f"  Training steps: {results.get('global_step', 'N/A')}")
        
    except Exception as e:
        typer.echo(f"❌ Error training model: {e}", err=True)
        logger.error(f"Training failed: {e}", exc_info=True)
        raise typer.Exit(1)


@train_cli.command("quick")
def quick_train(
    data_path: str = typer.Argument(..., help="Path to directory containing training data"),
    name: str = typer.Option(..., "-n", "--name", help="Custom name for the trained model (required)"),
    base_model: str = typer.Option("microsoft/DialoGPT-small", "-b", "--base-model", help="Base model to fine-tune (use aliases like 'mistral-7b', 'llama3-8b', 'phi-2' or full HuggingFace IDs)"),
    output_dir: str = typer.Option("./trained_models", "-o", "--output", help="Output directory for trained model"),
    epochs: int = typer.Option(1, "--epochs", help="Number of training epochs"),
    batch_size: int = typer.Option(2, "--batch-size", help="Training batch size"),
    max_length: int = typer.Option(256, "--max-length", help="Maximum sequence length"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging"),
):
    """
    Quick training pipeline: process data and train model in one command.
    
    This command processes the data directory and immediately trains a model,
    using smaller default settings for faster training.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Step 1: Process data
        typer.echo(f"📁 Step 1: Processing data from {data_path}...")
        
        processor = DataProcessor(
            min_text_length=10,
            max_text_length=max_length
        )
        
        processed_data = processor.process_directory(data_path)
        
        # Save processed data temporarily
        temp_data_file = f"./temp_processed_data_{name}.json"
        processor.save_processed_data(processed_data, temp_data_file)
        
        typer.echo(f"  ✅ Processed {processed_data.stats['processed_files']} files")
        typer.echo(f"  ✅ Generated {processed_data.stats['total_texts']} text chunks")
        
        # Step 2: Train model
        typer.echo(f"\n🚀 Step 2: Training model...")
        
        trainer = ModelTrainer(
            base_model=base_model,
            output_dir=Path(output_dir) / name
        )
        
        config = {
            'num_epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': 5e-5,
            'max_length': max_length,
            'save_steps': 100,
            'eval_steps': 100,
        }
        
        results = trainer.train_from_processed_data(temp_data_file, config)
        
        # Clean up temporary file
        try:
            Path(temp_data_file).unlink()
        except:
            pass
        
        typer.echo(f"\n🎉 Quick training completed!")
        typer.echo(f"  Model: {name}")
        typer.echo(f"  Location: {trainer.output_dir}")
        typer.echo(f"  Training loss: {results.get('final_loss', 'N/A')}")
        
    except Exception as e:
        typer.echo(f"❌ Error in quick training: {e}", err=True)
        logger.error(f"Quick training failed: {e}", exc_info=True)
        raise typer.Exit(1)


@train_cli.command("list")
def list_models(
    models_dir: str = typer.Option("./trained_models", "-d", "--dir", help="Directory containing trained models"),
):
    """
    List all trained models in the specified directory.
    """
    models_path = Path(models_dir)
    
    if not models_path.exists():
        typer.echo(f"❌ Models directory not found: {models_dir}")
        return
    
    # Find model directories (contain config.json or tokenizer.json)
    model_dirs = []
    for item in models_path.iterdir():
        if item.is_dir():
            if (item / "config.json").exists() or (item / "tokenizer.json").exists():
                model_dirs.append(item)
    
    if not model_dirs:
        typer.echo(f"No trained models found in {models_dir}")
        return
    
    typer.echo(f"📋 Trained models in {models_dir}:")
    for model_dir in sorted(model_dirs):
        model_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
        model_size_mb = model_size / (1024 * 1024)
        
        # Try to get model info
        config_file = model_dir / "config.json"
        model_type = "Unknown"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                    model_type = config.get("model_type", "Unknown")
            except:
                pass
        
        typer.echo(f"  📁 {model_dir.name}")
        typer.echo(f"     Type: {model_type}")
        typer.echo(f"     Size: {model_size_mb:.1f} MB")
        typer.echo(f"     Path: {model_dir}")


@train_cli.command("test")
def test_model(
    model_path: str = typer.Argument(..., help="Path to trained model directory"),
    prompt: str = typer.Option("Hello, how are you?", "-p", "--prompt", help="Test prompt"),
    max_length: int = typer.Option(100, "--max-length", help="Maximum generation length"),
    temperature: float = typer.Option(0.7, "--temperature", help="Generation temperature"),
):
    """
    Test a trained model with a sample prompt.
    """
    try:
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            typer.echo(f"❌ Model not found: {model_path}")
            raise typer.Exit(1)
        
        typer.echo(f"🧪 Testing model: {model_path}")
        typer.echo(f"📝 Prompt: {prompt}")
        
        # Initialize model manager for testing
        manager = ModelManager()
        
        # Load the model
        typer.echo(f"⏳ Loading model...")
        result = manager.load_model(str(model_path_obj))
        
        if "error" in result.lower():
            typer.echo(f"❌ Failed to load model: {result}")
            raise typer.Exit(1)
        
        # Generate text
        typer.echo(f"⏳ Generating text...")
        generation_result = manager.generate_text(
            prompt=prompt,
            max_length=max_length,
            temperature=temperature
        )
        
        if "error" in generation_result.lower():
            typer.echo(f"❌ Generation failed: {generation_result}")
            raise typer.Exit(1)
        
        # Parse and display result
        try:
            result_data = json.loads(generation_result)
            generated_text = result_data.get('generated_texts', [''])[0]
            
            typer.echo(f"\n🤖 Generated text:")
            typer.echo(f"{'='*50}")
            typer.echo(generated_text)
            typer.echo(f"{'='*50}")
            
        except json.JSONDecodeError:
            typer.echo(f"\n🤖 Generated text:")
            typer.echo(generation_result)
        
    except Exception as e:
        typer.echo(f"❌ Error testing model: {e}", err=True)
        raise typer.Exit(1)


@train_cli.command("install-deps")
def install_dependencies(
    gpu: bool = typer.Option(False, "--gpu", help="Install GPU support (CUDA)"),
):
    """
    Install training dependencies.
    
    Installs the required packages for training local models.
    """
    try:
        import subprocess
        import sys
        
        packages = [
            "transformers>=4.30.0",
            "datasets>=2.10.0",
            "accelerate>=0.20.0",
            "chardet>=5.0.0",
            "python-docx>=0.8.11",
            "PyPDF2>=3.0.0",
            "pdfplumber>=0.9.0",
        ]
        
        if gpu:
            packages.extend([
                "torch>=2.0.0",
                "torchaudio>=2.0.0",
                "torchvision>=0.15.0",
            ])
        else:
            packages.extend([
                "torch>=2.0.0+cpu",
                "torchaudio>=2.0.0+cpu",
                "torchvision>=0.15.0+cpu",
            ])
        
        typer.echo("📦 Installing training dependencies...")
        
        for package in packages:
            typer.echo(f"  Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                typer.echo(f"❌ Failed to install {package}")
                typer.echo(result.stderr)
            else:
                typer.echo(f"✅ Installed {package}")
        
        typer.echo("\n🎉 All dependencies installed successfully!")
        
    except Exception as e:
        typer.echo(f"❌ Error installing dependencies: {e}", err=True)
        raise typer.Exit(1)


@train_cli.command("list")
def list_models(
    models_dir: str = typer.Option("./trained_models", "-d", "--dir", help="Directory containing trained models"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed model information"),
):
    """
    List all trained models in the models directory.
    
    Shows model names, creation dates, and basic information about each trained model.
    """
    try:
        models_path = Path(models_dir)
        
        if not models_path.exists():
            typer.echo(f"📁 Models directory not found: {models_dir}")
            typer.echo("No trained models found.")
            return
        
        # Find model directories
        model_dirs = []
        for item in models_path.iterdir():
            if item.is_dir() and (item / "config.json").exists():
                model_dirs.append(item)
        
        if not model_dirs:
            typer.echo(f"📭 No trained models found in: {models_dir}")
            return
        
        typer.echo(f"📋 Trained Models in {models_dir}:")
        typer.echo("=" * 60)
        
        for model_dir in sorted(model_dirs):
            model_name = model_dir.name
            
            # Get model info if available
            info_file = model_dir / "model_info.json"
            created_at = "Unknown"
            base_model = "Unknown"
            data_files = "Unknown"
            
            if info_file.exists():
                try:
                    with open(info_file) as f:
                        info = json.load(f)
                        created_at = info.get('created_at', 'Unknown')
                        base_model = info.get('base_model', 'Unknown')
                        
                        # Format datetime
                        if created_at != 'Unknown':
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                created_at = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                        
                        # Get data stats
                        data_stats = info.get('data_stats', {})
                        if data_stats:
                            data_files = f"{data_stats.get('processed_files', 0)} files"
                except:
                    pass
            
            # Get model size
            try:
                model_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                model_size_mb = model_size / (1024 * 1024)
            except:
                model_size_mb = 0
            
            typer.echo(f"🤖 {model_name}")
            typer.echo(f"   📅 Created: {created_at}")
            typer.echo(f"   🧠 Base: {base_model}")
            typer.echo(f"   📊 Data: {data_files}")
            typer.echo(f"   💾 Size: {model_size_mb:.1f} MB")
            
            if verbose:
                typer.echo(f"   📂 Path: {model_dir}")
                
                # Check for additional files
                config_file = model_dir / "config.json"
                if config_file.exists():
                    typer.echo(f"   ✅ Config available")
                
                pytorch_file = model_dir / "pytorch_model.bin"
                safetensors_file = model_dir / "model.safetensors"
                if pytorch_file.exists() or safetensors_file.exists():
                    typer.echo(f"   ✅ Model weights available")
                
                tokenizer_file = model_dir / "tokenizer.json"
                if tokenizer_file.exists():
                    typer.echo(f"   ✅ Tokenizer available")
            
            typer.echo()
        
        typer.echo(f"Total: {len(model_dirs)} trained models")
        
    except Exception as e:
        typer.echo(f"❌ Error listing models: {e}", err=True)
        raise typer.Exit(1)


@train_cli.command("models")
def list_models_cmd():
    """
    List all available open source models for training.
    
    Shows supported model aliases and their HuggingFace identifiers.
    """
    try:
        list_available_models()
    except Exception as e:
        typer.echo(f"❌ Error listing models: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    train_cli()
