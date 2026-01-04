"""
Local Trained Model Integration for Buddy

Integrates locally trained models with the Buddy agent system.
Allows using custom trained models as the LLM backend for agents.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Iterator, AsyncIterator
import json

from buddy.models.base import Model
from buddy.models.message import Message
from buddy.models.response import ModelResponse
from buddy.train.model_manager import ModelManager
from buddy.utils.log import logger


@dataclass
class BuddyTrainedModel(Model):
    """
    Integration class for using locally trained models with Buddy agents.
    
    This allows you to use models trained with `buddy train` as the LLM backend
    for your Buddy AI agents.
    """
    
    id: str = "buddy-trained-model"
    name: str = "Buddy Trained Model"
    provider: str = "BuddyTrain"
    
    # Model path
    model_path: str = "./trained_models/my-model"
    
    # Generation parameters
    max_length: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 50
    repetition_penalty: Optional[float] = 1.1
    do_sample: Optional[bool] = True
    
    # Model manager
    model_manager: Optional[ModelManager] = None
    
    def __post_init__(self):
        """Initialize the model manager and load the model."""
        super().__post_init__()
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize and load the trained model."""
        try:
            self.model_manager = ModelManager()
            
            # Check if model path exists
            if not Path(self.model_path).exists():
                logger.error(f"Model path does not exist: {self.model_path}")
                return
            
            # Load the model
            result = self.model_manager.load_model(self.model_path)
            result_data = json.loads(result)
            
            if result_data['status'] != 'success':
                logger.error(f"Failed to load model: {result_data['message']}")
                return
            
            logger.info(f"Successfully loaded trained model from: {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error initializing trained model: {e}")
    
    def invoke(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> ModelResponse:
        """
        Send a completion request to the locally trained model.
        
        Args:
            messages: List of conversation messages
            response_format: Response format (not supported for local models)
            tools: Tools available to the model (not supported for local models)
            tool_choice: Tool choice strategy (not supported for local models)
            
        Returns:
            ModelResponse with the generated text
        """
        if not self.model_manager or not self.model_manager.model:
            raise RuntimeError(f"Model not loaded from path: {self.model_path}")
        
        # Convert messages to a single prompt
        prompt = self._format_messages_to_prompt(messages)
        
        # Generate response
        try:
            result = self.model_manager.generate_text(
                prompt=prompt,
                max_length=self.max_length or 200,
                temperature=self.temperature or 0.7,
                top_p=self.top_p or 0.9,
                top_k=self.top_k or 50,
                repetition_penalty=self.repetition_penalty or 1.1,
                do_sample=self.do_sample if self.do_sample is not None else True,
                num_return_sequences=1
            )
            
            # Return the raw result for parse_provider_response to handle
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")
    
    async def ainvoke(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> ModelResponse:
        """
        Async version of invoke (runs synchronously for local models).
        """
        return self.invoke(messages, response_format, tools, tool_choice)
    
    def invoke_stream(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Iterator[ModelResponse]:
        """
        Stream completion (not supported for local models, returns single response).
        """
        response = self.invoke(messages, response_format, tools, tool_choice)
        yield response
    
    async def ainvoke_stream(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> AsyncIterator[ModelResponse]:
        """
        Async streaming version (not supported for local models, yields single response).
        """
        response = await self.ainvoke(messages, response_format, tools, tool_choice)
        yield response
    
    def parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        """
        Parse the raw response from the local model into a ModelResponse.
        
        Args:
            response: Raw response from the local model (JSON string)
            
        Returns:
            ModelResponse: Parsed response data
        """
        if isinstance(response, str):
            try:
                result_data = json.loads(response)
            except json.JSONDecodeError:
                # If it's not JSON, treat as plain text
                result_data = {"status": "success", "generated_texts": [response]}
        else:
            result_data = response
        
        if result_data.get('status') != 'success':
            raise RuntimeError(f"Model generation failed: {result_data.get('message', 'Unknown error')}")
        
        generated_text = result_data.get('generated_texts', [''])[0]
        
        return ModelResponse(
            content=generated_text.strip(),
            role="assistant"
        )
    
    def parse_provider_response_delta(self, response: Any) -> ModelResponse:
        """
        Parse streaming response delta (local models don't stream, so same as parse_provider_response).
        
        Args:
            response: Raw response chunk from the local model
            
        Returns:
            ModelResponse: Parsed response delta
        """
        return self.parse_provider_response(response)
    
    def _format_messages_to_prompt(self, messages: List[Message]) -> str:
        """
        Convert a list of messages to a single prompt string.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        for message in messages:
            role = message.role
            content = message.content
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Join with newlines and add a prompt for the assistant to respond
        prompt = "\n".join(prompt_parts)
        if prompt and not prompt.endswith("Assistant:"):
            prompt += "\nAssistant:"
            
        return prompt


# Convenience function to create a trained model instance
def create_trained_model(
    model_path: str,
    model_name: str = "My Trained Model",
    **generation_params
) -> BuddyTrainedModel:
    """
    Create a BuddyTrainedModel instance from a trained model path.
    
    Args:
        model_path: Path to the trained model directory
        model_name: Display name for the model
        **generation_params: Additional generation parameters
        
    Returns:
        BuddyTrainedModel instance
    """
    return BuddyTrainedModel(
        name=model_name,
        model_path=model_path,
        **generation_params
    )


# Integration with buddy agents
def use_trained_model_with_agent(agent, model_path: str, **generation_params):
    """
    Configure a Buddy agent to use a locally trained model.
    
    Args:
        agent: Buddy agent instance
        model_path: Path to the trained model
        **generation_params: Generation parameters
    """
    trained_model = create_trained_model(model_path, **generation_params)
    agent.model = trained_model
    return agent


# Example usage
"""
# Create an agent with a trained model
from buddy import Agent
from buddy.train.integration import create_trained_model, use_trained_model_with_agent

# Method 1: Create model and assign to agent
trained_model = create_trained_model(
    model_path="./trained_models/my-model",
    temperature=0.8,
    max_length=300
)

agent = Agent(
    name="My Custom Agent",
    model=trained_model,
    instructions="You are a helpful assistant trained on my custom data."
)

# Method 2: Use helper function
agent = Agent(name="My Agent")
use_trained_model_with_agent(
    agent, 
    model_path="./trained_models/my-model",
    temperature=0.7
)

# Use the agent
response = agent.run("Hello, how can you help me?")
print(response.content)
"""
