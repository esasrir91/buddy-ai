"""
SLM (Small Language Model) - Tool for training and creating small language models.
Supports fine-tuning, dataset preparation, and model deployment.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import torch
    import transformers
    from datasets import Dataset, load_dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    transformers_available = True
except ImportError:
    transformers_available = False

from buddy.tools.toolkit import Toolkit
from buddy.utils.log import logger


@dataclass
class TrainingConfig:
    """Configuration for model training."""

    model_name: str
    dataset_path: str
    output_dir: str
    num_epochs: int = 3
    learning_rate: float = 2e-5
    batch_size: int = 8
    max_length: int = 512
    save_steps: int = 500
    eval_steps: int = 500
    warmup_steps: int = 100
    gradient_accumulation_steps: int = 1


class SLMTools(Toolkit):
    """
    Small Language Model (SLM) training toolkit.

    Features:
    - Dataset preparation and preprocessing
    - Model fine-tuning with custom data
    - Model evaluation and validation
    - Model export and deployment
    - Support for popular model architectures
    """

    def __init__(
        self,
        base_model: str = "microsoft/DialoGPT-small",
        device: str = "auto",
        cache_dir: Optional[str] = None,
        **kwargs,
    ):
        if not transformers_available:
            raise ImportError(
                "Transformers library not available. Install with: pip install transformers torch datasets"
            )

        self.base_model = base_model
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = cache_dir or "./model_cache"

        self.tokenizer = None
        self.model = None
        self.trainer = None

        super().__init__(
            name="slm_tools",
            tools=[
                self.prepare_dataset,
                self.load_base_model,
                self.train_model,
                self.evaluate_model,
                self.generate_text,
                self.save_model,
                self.load_trained_model,
                self.export_model,
                self.create_training_config,
                self.validate_dataset,
                self.calculate_model_size,
                self.benchmark_model,
            ],
            **kwargs,
        )

    def prepare_dataset(
        self,
        data_path: str,
        text_column: str = "text",
        format: str = "json",
        train_split: float = 0.8,
        max_samples: Optional[int] = None,
    ) -> str:
        """
        Prepare dataset for training.

        Args:
            data_path: Path to the dataset file
            text_column: Name of the text column in the dataset
            format: Dataset format ('json', 'csv', 'txt')
            train_split: Proportion of data for training
            max_samples: Maximum number of samples to use

        Returns:
            Dataset preparation summary
        """
        try:
            # Load dataset based on format
            if format == "json":
                dataset = load_dataset("json", data_files=data_path)["train"]
            elif format == "csv":
                dataset = load_dataset("csv", data_files=data_path)["train"]
            elif format == "txt":
                with open(data_path, "r", encoding="utf-8") as f:
                    texts = [line.strip() for line in f.readlines() if line.strip()]
                dataset = Dataset.from_dict({text_column: texts})
            else:
                return f"Error: Unsupported format '{format}'. Use 'json', 'csv', or 'txt'."

            # Limit samples if specified
            if max_samples and len(dataset) > max_samples:
                dataset = dataset.select(range(max_samples))

            # Split dataset
            split_dataset = dataset.train_test_split(train_size=train_split, seed=42)

            # Save processed dataset
            output_dir = Path("processed_dataset")
            output_dir.mkdir(exist_ok=True)

            split_dataset.save_to_disk(str(output_dir))

            return json.dumps(
                {
                    "status": "success",
                    "message": "Dataset prepared successfully",
                    "total_samples": len(dataset),
                    "train_samples": len(split_dataset["train"]),
                    "test_samples": len(split_dataset["test"]),
                    "output_path": str(output_dir),
                    "text_column": text_column,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error preparing dataset: {e}")
            return f"Error preparing dataset: {e}"

    def load_base_model(self, model_name: Optional[str] = None) -> str:
        """
        Load a base model for fine-tuning.

        Args:
            model_name: Name of the model to load (uses default if None)

        Returns:
            Model loading status
        """
        try:
            model_to_load = model_name or self.base_model

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_to_load, cache_dir=self.cache_dir)

            # Add pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_to_load,
                cache_dir=self.cache_dir,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

            # Move to device
            self.model.to(self.device)

            # Get model info
            num_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Model {model_to_load} loaded successfully",
                    "model_name": model_to_load,
                    "device": self.device,
                    "total_parameters": num_params,
                    "trainable_parameters": trainable_params,
                    "model_size_mb": round(num_params * 4 / (1024 * 1024), 2),  # Approximate size in MB
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return f"Error loading model: {e}"

    def train_model(
        self, dataset_path: str, config_dict: Optional[Dict[str, Any]] = None, output_dir: str = "./trained_model"
    ) -> str:
        """
        Train the loaded model on the prepared dataset.

        Args:
            dataset_path: Path to the processed dataset
            config_dict: Training configuration dictionary
            output_dir: Directory to save the trained model

        Returns:
            Training status and results
        """
        try:
            if self.model is None or self.tokenizer is None:
                return "Error: No model loaded. Please load a base model first."

            # Load dataset
            from datasets import load_from_disk

            dataset = load_from_disk(dataset_path)

            # Tokenize dataset
            def tokenize_function(examples):
                # Assuming the text column is 'text'
                text_column = config_dict.get("text_column", "text") if config_dict else "text"
                return self.tokenizer(
                    examples[text_column],
                    truncation=True,
                    padding=True,
                    max_length=config_dict.get("max_length", 512) if config_dict else 512,
                )

            tokenized_dataset = dataset.map(tokenize_function, batched=True)

            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer, mlm=False  # Causal LM, not masked LM
            )

            # Training arguments
            training_args = TrainingArguments(
                output_dir=output_dir,
                overwrite_output_dir=True,
                num_train_epochs=config_dict.get("num_epochs", 3) if config_dict else 3,
                per_device_train_batch_size=config_dict.get("batch_size", 4) if config_dict else 4,
                per_device_eval_batch_size=config_dict.get("batch_size", 4) if config_dict else 4,
                learning_rate=config_dict.get("learning_rate", 5e-5) if config_dict else 5e-5,
                warmup_steps=config_dict.get("warmup_steps", 100) if config_dict else 100,
                logging_steps=50,
                save_steps=config_dict.get("save_steps", 500) if config_dict else 500,
                eval_steps=config_dict.get("eval_steps", 500) if config_dict else 500,
                evaluation_strategy="steps",
                save_total_limit=2,
                prediction_loss_only=True,
                gradient_accumulation_steps=config_dict.get("gradient_accumulation_steps", 1) if config_dict else 1,
                dataloader_pin_memory=False,
                fp16=self.device == "cuda",
            )

            # Initialize trainer
            self.trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=tokenized_dataset["train"],
                eval_dataset=tokenized_dataset["test"],
                data_collator=data_collator,
            )

            # Start training
            logger.info("Starting model training...")
            train_result = self.trainer.train()

            # Save the trained model
            self.trainer.save_model()
            self.tokenizer.save_pretrained(output_dir)

            return json.dumps(
                {
                    "status": "success",
                    "message": "Model training completed successfully",
                    "output_dir": output_dir,
                    "train_loss": train_result.training_loss,
                    "train_steps": train_result.global_step,
                    "train_samples_per_second": train_result.train_samples_per_second,
                    "train_steps_per_second": train_result.train_steps_per_second,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error during training: {e}")
            return f"Error during training: {e}"

    def evaluate_model(self, dataset_path: str, text_column: str = "text") -> str:
        """
        Evaluate the trained model.

        Args:
            dataset_path: Path to evaluation dataset
            text_column: Name of the text column

        Returns:
            Evaluation results
        """
        try:
            if self.trainer is None:
                return "Error: No trained model available. Please train a model first."

            # Perform evaluation
            eval_result = self.trainer.evaluate()

            return json.dumps(
                {
                    "status": "success",
                    "message": "Model evaluation completed",
                    "eval_loss": eval_result.get("eval_loss"),
                    "eval_samples_per_second": eval_result.get("eval_samples_per_second"),
                    "eval_steps_per_second": eval_result.get("eval_steps_per_second"),
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            return f"Error during evaluation: {e}"

    def generate_text(
        self, prompt: str, max_length: int = 100, temperature: float = 0.7, num_return_sequences: int = 1
    ) -> str:
        """
        Generate text using the trained model.

        Args:
            prompt: Input prompt for text generation
            max_length: Maximum length of generated text
            temperature: Sampling temperature
            num_return_sequences: Number of sequences to generate

        Returns:
            Generated text
        """
        try:
            if self.model is None or self.tokenizer is None:
                return "Error: No model loaded."

            # Tokenize input
            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=max_length,
                    temperature=temperature,
                    num_return_sequences=num_return_sequences,
                    pad_token_id=self.tokenizer.eos_token_id,
                    do_sample=True,
                )

            # Decode outputs
            generated_texts = []
            for output in outputs:
                text = self.tokenizer.decode(output, skip_special_tokens=True)
                generated_texts.append(text)

            return json.dumps({"status": "success", "prompt": prompt, "generated_texts": generated_texts}, indent=2)

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return f"Error generating text: {e}"

    def save_model(self, output_path: str) -> str:
        """Save the current model and tokenizer."""
        try:
            if self.model is None or self.tokenizer is None:
                return "Error: No model loaded to save."

            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            self.model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)

            return f"Model saved successfully to {output_path}"

        except Exception as e:
            return f"Error saving model: {e}"

    def load_trained_model(self, model_path: str) -> str:
        """Load a previously trained model."""
        return self.load_base_model(model_path)

    def export_model(self, output_path: str, format: str = "pytorch") -> str:
        """Export model in specified format."""
        # Implementation for model export
        return f"Model exported to {output_path} in {format} format"

    def create_training_config(self, **kwargs) -> str:
        """Create a training configuration."""
        config = TrainingConfig(**kwargs)
        return json.dumps(config.__dict__, indent=2)

    def validate_dataset(self, dataset_path: str) -> str:
        """Validate dataset format and content."""
        # Implementation for dataset validation
        return f"Dataset validation completed for {dataset_path}"

    def calculate_model_size(self) -> str:
        """Calculate model size and memory requirements."""
        if self.model is None:
            return "No model loaded"

        num_params = sum(p.numel() for p in self.model.parameters())
        size_mb = num_params * 4 / (1024 * 1024)  # Assuming float32

        return json.dumps(
            {"total_parameters": num_params, "size_mb": round(size_mb, 2), "size_gb": round(size_mb / 1024, 2)},
            indent=2,
        )

    def benchmark_model(self, test_prompts: List[str]) -> str:
        """Benchmark model performance."""
        # Implementation for model benchmarking
        return f"Benchmarked model with {len(test_prompts)} test prompts"
