"""
Model Manager for Buddy Train

Handles loading, running inference, and managing trained models.
Provides a unified interface for working with local trained models.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, GenerationConfig, pipeline

    transformers_available = True
except ImportError:
    transformers_available = False

from buddy.utils.log import logger


class ModelManager:
    """
    Manages trained models for inference and deployment.

    Features:
    - Load and manage multiple models
    - Text generation with various parameters
    - Model information and statistics
    - Memory management and optimization
    - Batch inference support
    """

    def __init__(self, device: str = "auto", cache_dir: Optional[str] = None):
        if not transformers_available:
            raise ImportError(
                "Model management dependencies not available. " "Run 'buddy train install-deps' to install them."
            )

        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = cache_dir or "./model_cache"

        # Current loaded model
        self.model = None
        self.tokenizer = None
        self.config = None
        self.model_path = None
        self.model_info = {}

        logger.info(f"ModelManager initialized with device: {self.device}")

    def load_model(self, model_path: str) -> str:
        """
        Load a trained model from the specified path.

        Args:
            model_path: Path to the trained model directory

        Returns:
            Status message as JSON string
        """
        try:
            model_path_obj = Path(model_path)

            if not model_path_obj.exists():
                return json.dumps({"status": "error", "message": f"Model path does not exist: {model_path}"})

            # Check if it's a valid model directory
            if not (model_path_obj / "config.json").exists():
                return json.dumps(
                    {"status": "error", "message": f"Invalid model directory: {model_path} (missing config.json)"}
                )

            logger.info(f"Loading model from: {model_path}")

            # Clear previous model
            self.unload_model()

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True, local_files_only=True)

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                local_files_only=True,
            )

            # Move to device
            self.model.to(self.device)

            # Load config
            self.config = AutoConfig.from_pretrained(model_path, local_files_only=True)

            # Store model info
            self.model_path = str(model_path_obj)
            self.model_info = self._extract_model_info(model_path_obj)

            # Get model statistics
            num_params = sum(p.numel() for p in self.model.parameters())
            model_size_mb = self._get_model_size_mb(model_path_obj)

            result = {
                "status": "success",
                "message": f"Model loaded successfully from {model_path}",
                "model_path": self.model_path,
                "model_type": self.config.model_type if self.config else "unknown",
                "total_parameters": num_params,
                "model_size_mb": model_size_mb,
                "device": self.device,
                "model_info": self.model_info,
            }

            logger.info(f"Model loaded successfully: {num_params:,} parameters, {model_size_mb:.1f} MB")

            return json.dumps(result, indent=2)

        except Exception as e:
            error_msg = f"Error loading model: {e}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    def generate_text(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 0.7,
        num_return_sequences: int = 1,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        do_sample: bool = True,
        pad_token_id: Optional[int] = None,
        eos_token_id: Optional[int] = None,
    ) -> str:
        """
        Generate text using the loaded model.

        Args:
            prompt: Input prompt for text generation
            max_length: Maximum length of generated text
            temperature: Sampling temperature (higher = more random)
            num_return_sequences: Number of sequences to generate
            top_p: Nucleus sampling probability
            top_k: Top-k sampling parameter
            repetition_penalty: Penalty for repetition
            do_sample: Whether to use sampling or greedy decoding
            pad_token_id: Padding token ID
            eos_token_id: End-of-sequence token ID

        Returns:
            Generated text as JSON string
        """
        try:
            if self.model is None or self.tokenizer is None:
                return json.dumps({"status": "error", "message": "No model loaded. Please load a model first."})

            logger.debug(f"Generating text for prompt: {prompt[:50]}...")

            # Tokenize input
            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

            # Set default token IDs if not provided
            if pad_token_id is None:
                pad_token_id = self.tokenizer.eos_token_id
            if eos_token_id is None:
                eos_token_id = self.tokenizer.eos_token_id

            # Generate text
            start_time = datetime.now()

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=len(inputs[0]) + max_length,
                    temperature=temperature,
                    num_return_sequences=num_return_sequences,
                    top_p=top_p,
                    top_k=top_k,
                    repetition_penalty=repetition_penalty,
                    do_sample=do_sample,
                    pad_token_id=pad_token_id,
                    eos_token_id=eos_token_id,
                    early_stopping=True,
                )

            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            # Decode outputs
            generated_texts = []
            for output in outputs:
                # Remove the input tokens from the output
                generated_tokens = output[len(inputs[0]) :]
                text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
                generated_texts.append(text.strip())

            result = {
                "status": "success",
                "prompt": prompt,
                "generated_texts": generated_texts,
                "generation_time": generation_time,
                "parameters": {
                    "max_length": max_length,
                    "temperature": temperature,
                    "num_return_sequences": num_return_sequences,
                    "top_p": top_p,
                    "top_k": top_k,
                    "repetition_penalty": repetition_penalty,
                    "do_sample": do_sample,
                },
            }

            logger.debug(f"Text generation completed in {generation_time:.2f}s")

            return json.dumps(result, indent=2)

        except Exception as e:
            error_msg = f"Error generating text: {e}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    def generate_batch(self, prompts: List[str], max_length: int = 100, **kwargs) -> str:
        """
        Generate text for multiple prompts in batch.

        Args:
            prompts: List of input prompts
            max_length: Maximum length per generation
            **kwargs: Additional generation parameters

        Returns:
            Batch generation results as JSON string
        """
        try:
            if self.model is None or self.tokenizer is None:
                return json.dumps({"status": "error", "message": "No model loaded. Please load a model first."})

            logger.info(f"Generating text for {len(prompts)} prompts...")

            results = []
            total_time = 0

            for i, prompt in enumerate(prompts):
                logger.debug(f"Processing prompt {i+1}/{len(prompts)}")

                result_json = self.generate_text(prompt, max_length, **kwargs)
                result = json.loads(result_json)

                if result["status"] == "success":
                    total_time += result["generation_time"]

                results.append(result)

            batch_result = {
                "status": "success",
                "total_prompts": len(prompts),
                "successful_generations": sum(1 for r in results if r["status"] == "success"),
                "total_time": total_time,
                "avg_time_per_prompt": total_time / len(prompts),
                "results": results,
            }

            return json.dumps(batch_result, indent=2)

        except Exception as e:
            error_msg = f"Error in batch generation: {e}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    def get_model_info(self) -> str:
        """
        Get information about the currently loaded model.

        Returns:
            Model information as JSON string
        """
        if self.model is None:
            return json.dumps({"status": "error", "message": "No model loaded"})

        num_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

        info = {
            "status": "success",
            "model_path": self.model_path,
            "model_type": self.config.model_type if self.config else "unknown",
            "total_parameters": num_params,
            "trainable_parameters": trainable_params,
            "model_size_mb": self._get_model_size_mb(Path(self.model_path)) if self.model_path else 0,
            "device": self.device,
            "vocab_size": self.tokenizer.vocab_size if self.tokenizer else 0,
            "max_position_embeddings": getattr(self.config, "max_position_embeddings", "unknown"),
            "model_info": self.model_info,
        }

        return json.dumps(info, indent=2)

    def unload_model(self):
        """Unload the current model and free memory."""
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        if self.config is not None:
            del self.config
            self.config = None

        self.model_path = None
        self.model_info = {}

        # Clear GPU cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Model unloaded and memory cleared")

    def _extract_model_info(self, model_path: Path) -> Dict[str, Any]:
        """Extract model information from training files."""
        info = {}

        # Try to load training info
        training_info_path = model_path / "training_info.json"
        if training_info_path.exists():
            try:
                with open(training_info_path, "r") as f:
                    info.update(json.load(f))
            except:
                pass

        # Try to load training report
        training_report_path = model_path / "training_report.json"
        if training_report_path.exists():
            try:
                with open(training_report_path, "r") as f:
                    report = json.load(f)
                    info["training_report"] = {
                        "final_loss": report.get("final_loss"),
                        "training_duration": report.get("training_duration_formatted"),
                        "training_samples": report.get("training_samples"),
                        "base_model": report.get("base_model"),
                    }
            except:
                pass

        return info

    def _get_model_size_mb(self, model_path: Path) -> float:
        """Calculate model size in MB."""
        try:
            total_size = 0
            for file_path in model_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)
        except:
            return 0.0

    def save_generation_config(self, output_path: str, **generation_params) -> str:
        """
        Save generation configuration for future use.

        Args:
            output_path: Path to save the configuration
            **generation_params: Generation parameters to save

        Returns:
            Status message
        """
        try:
            config = {
                "model_path": self.model_path,
                "generation_params": generation_params,
                "created_at": datetime.now().isoformat(),
                "device": self.device,
            }

            with open(output_path, "w") as f:
                json.dump(config, f, indent=2)

            return f"Generation config saved to: {output_path}"

        except Exception as e:
            return f"Error saving config: {e}"

    def load_generation_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load generation configuration from file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def benchmark_model(self, test_prompts: List[str] = None) -> str:
        """
        Benchmark the loaded model's performance.

        Args:
            test_prompts: List of test prompts, uses defaults if None

        Returns:
            Benchmark results as JSON string
        """
        if test_prompts is None:
            test_prompts = [
                "Hello, how are you?",
                "What is artificial intelligence?",
                "Tell me a short story.",
                "Explain machine learning.",
                "How does a computer work?",
            ]

        try:
            if self.model is None:
                return json.dumps({"status": "error", "message": "No model loaded"})

            logger.info(f"Benchmarking model with {len(test_prompts)} prompts...")

            results = []
            total_time = 0
            total_tokens = 0

            for prompt in test_prompts:
                start_time = datetime.now()

                result_json = self.generate_text(prompt, max_length=50, temperature=0.7, num_return_sequences=1)
                result = json.loads(result_json)

                end_time = datetime.now()
                generation_time = (end_time - start_time).total_seconds()

                if result["status"] == "success":
                    generated_text = result["generated_texts"][0]
                    tokens = len(self.tokenizer.encode(generated_text))

                    results.append(
                        {
                            "prompt": prompt,
                            "generated_text": generated_text,
                            "generation_time": generation_time,
                            "tokens_generated": tokens,
                            "tokens_per_second": tokens / generation_time if generation_time > 0 else 0,
                        }
                    )

                    total_time += generation_time
                    total_tokens += tokens

            avg_time = total_time / len(results) if results else 0
            avg_tokens_per_second = total_tokens / total_time if total_time > 0 else 0

            benchmark = {
                "status": "success",
                "model_path": self.model_path,
                "total_prompts": len(test_prompts),
                "successful_generations": len(results),
                "total_time": total_time,
                "total_tokens_generated": total_tokens,
                "avg_time_per_prompt": avg_time,
                "avg_tokens_per_second": avg_tokens_per_second,
                "results": results,
            }

            return json.dumps(benchmark, indent=2)

        except Exception as e:
            error_msg = f"Error benchmarking model: {e}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})
