"""
Model Trainer for Buddy Train

Handles the complete training pipeline from processed data to trained model.
Supports various model architectures and training configurations.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import torch
    from datasets import Dataset
    from transformers import (
        AutoConfig,
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        EarlyStoppingCallback,
        Trainer,
        TrainerCallback,
        TrainingArguments,
    )

    transformers_available = True
except ImportError:
    transformers_available = False

from buddy.train.data_processor import DataProcessor, ProcessedData
from buddy.train.model_manager import ModelManager
from buddy.utils.log import logger


if transformers_available:

    class ProgressReportingCallback(TrainerCallback):
        """Reports training progress to an optional callback (used by the Fire UI)."""

        def __init__(self, callback):
            self.callback = callback

        def on_log(self, args, state, control, logs=None, **kwargs):
            if not self.callback or not logs:
                return
            max_steps = max(getattr(state, "max_steps", 0) or 1, 1)
            progress = 0.25 + (state.global_step / max_steps) * 0.65
            self.callback(
                {
                    "step": f"step {state.global_step}/{max_steps}",
                    "progress": progress,
                    "logs": logs,
                    "epoch": getattr(state, "epoch", None),
                }
            )

        def on_epoch_end(self, args, state, control, **kwargs):
            if not self.callback:
                return
            total_epochs = args.num_train_epochs
            epoch = int(state.epoch) if state.epoch else 0
            progress = 0.25 + (epoch / max(total_epochs, 1)) * 0.65
            self.callback({"step": f"epoch {epoch}/{int(total_epochs)}", "progress": progress})


class ModelTrainer:
    """
    Complete training pipeline for local language models.

    Features:
    - Supports multiple model architectures
    - Automatic hyperparameter optimization
    - Memory-efficient training
    - Progress tracking and logging
    - Model validation and testing
    """

    def __init__(
        self,
        base_model: str = "microsoft/DialoGPT-small",
        output_dir: Path = Path("./trained_model"),
        device: str = "auto",
        cache_dir: Optional[str] = None,
    ):
        if not transformers_available:
            raise ImportError("Training dependencies not available. Run 'buddy train install-deps' to install them.")

        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = cache_dir or "./model_cache"

        # Training state
        self.tokenizer = None
        self.model = None
        self.trainer = None
        self.training_args = None

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ModelTrainer initialized with device: {self.device}")

    def train_from_processed_data(
        self, processed_data_path: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Train a model from processed data file.

        Args:
            processed_data_path: Path to processed data JSON file
            config: Training configuration dictionary

        Returns:
            Training results and metrics
        """
        # Load processed data
        processor = DataProcessor()
        processed_data = processor.load_processed_data(processed_data_path)

        logger.info(f"Loaded {len(processed_data.texts)} training examples")

        return self.train_from_data(processed_data, config)

    def train_from_data(self, processed_data: ProcessedData, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Train a model from ProcessedData object.

        Args:
            processed_data: ProcessedData object containing texts and metadata
            config: Training configuration dictionary

        Returns:
            Training results and metrics
        """
        if not processed_data.texts:
            raise ValueError("No training data provided")

        # Set default config
        default_config = {
            "num_epochs": 3,
            "batch_size": 4,
            "learning_rate": 5e-5,
            "max_length": 512,
            "save_steps": 500,
            "eval_steps": 500,
            "warmup_steps": 100,
            "gradient_accumulation_steps": 1,
            "weight_decay": 0.01,
            "logging_steps": 50,
            "save_total_limit": 2,
            "evaluation_strategy": "steps",
            "load_best_model_at_end": True,
            "metric_for_best_model": "eval_loss",
            "greater_is_better": False,
        }

        if config:
            default_config.update(config)

        config = default_config
        self._progress_callback = config.pop("progress_callback", None)

        try:
            # Step 1: Load base model and tokenizer
            logger.info(f"Loading base model: {self.base_model}")
            self._load_base_model()

            # Step 2: Prepare dataset
            logger.info("Preparing training dataset...")
            train_dataset, eval_dataset = self._prepare_dataset(processed_data, config)

            # Step 3: Setup training arguments
            logger.info("Setting up training configuration...")
            self._setup_training_args(config)

            # Step 4: Initialize trainer
            logger.info("Initializing trainer...")
            self._initialize_trainer(train_dataset, eval_dataset)

            # Step 5: Start training
            logger.info("Starting training...")
            training_start_time = datetime.now()

            train_result = self.trainer.train()

            training_end_time = datetime.now()
            training_duration = training_end_time - training_start_time

            # Step 6: Save the model
            logger.info("Saving trained model...")
            self._save_model()

            # Step 7: Generate training report
            results = self._generate_training_report(train_result, training_duration, processed_data, config)

            logger.info("Training completed successfully!")
            return results

        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise e

    def _load_base_model(self):
        """Load the base model and tokenizer."""
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model, cache_dir=self.cache_dir, use_fast=True)

            # Add special tokens if needed
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                cache_dir=self.cache_dir,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
            )

            # Move to device
            self.model.to(self.device)

            # Log model info
            num_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            logger.info(f"Model loaded: {self.base_model}")
            logger.info(f"Total parameters: {num_params:,}")
            logger.info(f"Trainable parameters: {trainable_params:,}")
            logger.info(f"Model size: ~{num_params * 4 / (1024**3):.2f} GB")

        except Exception as e:
            logger.error(f"Failed to load base model: {e}")
            raise e

    def _prepare_dataset(self, processed_data: ProcessedData, config: Dict[str, Any]) -> tuple:
        """Prepare training and evaluation datasets."""
        texts = processed_data.texts
        max_length = config["max_length"]

        # Create dataset
        dataset_dict = {"text": texts}
        dataset = Dataset.from_dict(dataset_dict)

        # Tokenize the dataset
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"], truncation=True, padding=True, max_length=max_length, return_tensors="pt"
            )

        logger.info("Tokenizing dataset...")
        tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"], desc="Tokenizing")

        # Split into train/eval (90/10 split) - handle small datasets
        if len(tokenized_dataset) < 2:
            # For very small datasets, use the same data for both train and eval
            train_dataset = tokenized_dataset
            eval_dataset = tokenized_dataset
            logger.warning(f"Dataset too small ({len(tokenized_dataset)} samples), using same data for train/eval")
        else:
            train_size = max(1, int(0.9 * len(tokenized_dataset)))
            eval_size = len(tokenized_dataset) - train_size

            # Ensure we have at least 1 sample for evaluation
            if eval_size == 0:
                eval_size = 1
                train_size = len(tokenized_dataset) - 1

            split_dataset = tokenized_dataset.train_test_split(train_size=train_size, test_size=eval_size, seed=42)

            train_dataset = split_dataset["train"]
            eval_dataset = split_dataset["test"]

        logger.info(f"Training samples: {len(train_dataset)}")
        logger.info(f"Evaluation samples: {len(eval_dataset)}")

        return train_dataset, eval_dataset

    def _setup_training_args(self, config: Dict[str, Any]):
        """Setup training arguments."""
        self.training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            overwrite_output_dir=True,
            num_train_epochs=config["num_epochs"],
            per_device_train_batch_size=config["batch_size"],
            per_device_eval_batch_size=config["batch_size"],
            learning_rate=config["learning_rate"],
            warmup_steps=config["warmup_steps"],
            weight_decay=config["weight_decay"],
            logging_steps=config["logging_steps"],
            save_steps=config["save_steps"],
            eval_steps=config["eval_steps"],
            evaluation_strategy=config["evaluation_strategy"],
            save_total_limit=config["save_total_limit"],
            prediction_loss_only=True,
            gradient_accumulation_steps=config["gradient_accumulation_steps"],
            dataloader_pin_memory=False,
            fp16=self.device == "cuda",
            load_best_model_at_end=config["load_best_model_at_end"],
            metric_for_best_model=config["metric_for_best_model"],
            greater_is_better=config["greater_is_better"],
            report_to=None,  # Disable wandb/tensorboard
            logging_dir=str(self.output_dir / "logs"),
        )

    def _initialize_trainer(self, train_dataset, eval_dataset):
        """Initialize the Trainer."""
        # Data collator for language modeling
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal language modeling
            pad_to_multiple_of=8 if self.device == "cuda" else None,
        )

        # Callbacks
        callbacks = []
        if eval_dataset:
            callbacks.append(EarlyStoppingCallback(early_stopping_patience=3))

        progress_callback = getattr(self, "_progress_callback", None)
        if progress_callback and transformers_available:
            callbacks.append(ProgressReportingCallback(progress_callback))

        # Initialize trainer
        self.trainer = Trainer(
            model=self.model,
            args=self.training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            callbacks=callbacks,
        )

    def _save_model(self):
        """Save the trained model and tokenizer."""
        try:
            # Save model and tokenizer
            self.trainer.save_model()
            self.tokenizer.save_pretrained(self.output_dir)

            # Save training info
            training_info = {
                "base_model": self.base_model,
                "training_time": datetime.now().isoformat(),
                "device": self.device,
                "model_type": "causal_lm",
                "framework": "transformers",
                "buddy_version": "26.1",
            }

            with open(self.output_dir / "training_info.json", "w") as f:
                json.dump(training_info, f, indent=2)

            logger.info(f"Model saved to: {self.output_dir}")

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise e

    def _generate_training_report(
        self, train_result, training_duration, processed_data: ProcessedData, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a comprehensive training report."""

        results = {
            "status": "success",
            "base_model": self.base_model,
            "output_dir": str(self.output_dir),
            "training_duration_seconds": training_duration.total_seconds(),
            "training_duration_formatted": str(training_duration),
            "device": self.device,
            # Training metrics
            "final_loss": getattr(train_result, "training_loss", None),
            "global_step": getattr(train_result, "global_step", None),
            "epoch": getattr(train_result, "epoch", None),
            # Data info
            "training_samples": len(processed_data.texts),
            "total_characters": processed_data.stats.get("total_characters", 0),
            "avg_text_length": processed_data.stats.get("avg_text_length", 0),
            # Configuration
            "config": config,
            # Model info
            "model_size_mb": self._get_model_size_mb(),
        }

        # Add performance metrics if available
        if hasattr(train_result, "metrics"):
            results.update(train_result.metrics)

        # Save report
        report_path = self.output_dir / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Training report saved to: {report_path}")

        return results

    def _get_model_size_mb(self) -> float:
        """Calculate model size in MB."""
        try:
            total_size = 0
            for file_path in self.output_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)
        except:
            return 0.0

    def validate_model(self, test_prompts: List[str] = None) -> Dict[str, Any]:
        """
        Validate the trained model with test prompts.

        Args:
            test_prompts: List of test prompts, uses defaults if None

        Returns:
            Validation results
        """
        if test_prompts is None:
            test_prompts = [
                "Hello, how are you?",
                "What is the weather like?",
                "Tell me about artificial intelligence.",
                "How do I learn programming?",
                "What is the meaning of life?",
            ]

        if not self.model or not self.tokenizer:
            # Try to load the model from output directory
            manager = ModelManager()
            load_result = manager.load_model(str(self.output_dir))
            if "error" in load_result.lower():
                return {"error": f"Could not load model for validation: {load_result}"}

            self.model = manager.model
            self.tokenizer = manager.tokenizer

        validation_results = {
            "test_prompts": [],
            "avg_generation_time": 0,
            "total_tests": len(test_prompts),
            "successful_generations": 0,
        }

        total_time = 0

        for prompt in test_prompts:
            try:
                start_time = datetime.now()

                # Generate response
                inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs,
                        max_length=100,
                        temperature=0.7,
                        num_return_sequences=1,
                        pad_token_id=self.tokenizer.eos_token_id,
                        do_sample=True,
                    )

                generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

                end_time = datetime.now()
                generation_time = (end_time - start_time).total_seconds()
                total_time += generation_time

                validation_results["test_prompts"].append(
                    {
                        "prompt": prompt,
                        "generated_text": generated_text,
                        "generation_time": generation_time,
                        "success": True,
                    }
                )

                validation_results["successful_generations"] += 1

            except Exception as e:
                validation_results["test_prompts"].append({"prompt": prompt, "error": str(e), "success": False})

        validation_results["avg_generation_time"] = total_time / len(test_prompts)
        validation_results["success_rate"] = validation_results["successful_generations"] / len(test_prompts)

        return validation_results

    def cleanup(self):
        """Clean up resources."""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if self.trainer:
            del self.trainer

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Training resources cleaned up")
