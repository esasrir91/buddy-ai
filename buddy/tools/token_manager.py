import json
import re
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from buddy.tools import Toolkit
from buddy.models.message import MessageMetrics
from buddy.utils.log import log_debug, log_info, log_warning, log_error, logger


@dataclass
class TokenUsageStats:
    """Statistics for token usage tracking"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    session_count: int = 0
    peak_tokens_per_request: int = 0
    last_reset_time: Optional[datetime] = None
    
    def reset(self):
        """Reset all counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.session_count = 0
        self.peak_tokens_per_request = 0
        self.last_reset_time = datetime.now()

    def add_usage(self, input_tokens: int, output_tokens: int):
        """Add token usage to statistics"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        current_request_tokens = input_tokens + output_tokens
        if current_request_tokens > self.peak_tokens_per_request:
            self.peak_tokens_per_request = current_request_tokens


@dataclass 
class TokenLimits:
    """Token limits configuration"""
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    max_total_tokens: Optional[int] = None
    max_tokens_per_request: Optional[int] = None
    max_context_window: Optional[int] = None
    soft_limit_threshold: float = 0.8  # Trigger warning at 80% of limit
    

class TokenManager(Toolkit):
    """
    Advanced token management tool for LLM interactions.
    
    Provides comprehensive token counting, limit enforcement, usage tracking,
    and automatic token management for AI agents. When added to an agent,
    it automatically monitors and manages token usage for all model interactions.
    """
    
    def __init__(
        self,
        # Token limits
        max_input_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None, 
        max_total_tokens: Optional[int] = None,
        max_tokens_per_request: Optional[int] = None,
        max_context_window: Optional[int] = None,
        
        # Behavior settings
        auto_truncate: bool = False,  # Agent should manage chunks, not auto-truncate
        auto_summarize: bool = False,
        strict_mode: bool = False,
        enable_warnings: bool = True,
        provide_chunk_guidance: bool = True,
        
        # Token counting method
        encoding: str = "cl100k_base",
        
        # Tool selection
        get_token_count: bool = True,
        get_usage_stats: bool = True,
        set_token_limits: bool = True,
        reset_usage_stats: bool = True,
        check_token_limits: bool = True,
        estimate_cost: bool = True,
        truncate_text: bool = True,
        register_with_agent: bool = True,
        auto_register_agent_hook: bool = True,
        track_message_metrics: bool = True,
        update_usage_from_metrics: bool = True,
        extract_usage_from_response: bool = True,
        suggest_optimal_chunks: bool = True,
        **kwargs
    ):
        """
        Initialize TokenManager tool.
        
        Args:
            max_input_tokens: Maximum input tokens allowed
            max_output_tokens: Maximum output tokens allowed
            max_total_tokens: Maximum total tokens per session
            max_tokens_per_request: Maximum tokens per single request
            max_context_window: Maximum context window size
            auto_truncate: Automatically truncate inputs that exceed limits
            auto_summarize: Summarize content when approaching limits
            strict_mode: Raise exceptions on limit violations
            enable_warnings: Enable warning messages
            encoding: Tokenizer encoding to use for counting
        """
        
        self.limits = TokenLimits(
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            max_total_tokens=max_total_tokens,
            max_tokens_per_request=max_tokens_per_request,
            max_context_window=max_context_window
        )
        
        self.stats = TokenUsageStats()
        
        # Configuration
        self.auto_truncate = auto_truncate
        self.auto_summarize = auto_summarize
        self.strict_mode = strict_mode
        self.enable_warnings = enable_warnings
        self.provide_chunk_guidance = provide_chunk_guidance
        self.encoding = encoding
        
        # Try to import tiktoken for accurate token counting
        self.tiktoken_available = False
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding(encoding)
            self.tiktoken_available = True
            log_debug(f"TokenManager: Using tiktoken with encoding {encoding}")
        except ImportError:
            log_warning("TokenManager: tiktoken not available, using approximate token counting")
            self.tokenizer = None
            
        # Model-specific token costs (per 1K tokens)
        self.token_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "gemini-pro": {"input": 0.0005, "output": 0.0015},
        }
        
        # Build tools list
        tools: List[Callable] = []
        if get_token_count:
            tools.append(self.get_token_count)
        if get_usage_stats:
            tools.append(self.get_usage_stats)
        if set_token_limits:
            tools.append(self.set_token_limits)
        if reset_usage_stats:
            tools.append(self.reset_usage_stats)
        if check_token_limits:
            tools.append(self.check_token_limits)
        if estimate_cost:
            tools.append(self.estimate_cost)
        if truncate_text:
            tools.append(self.truncate_text)
        if register_with_agent:
            tools.append(self.setup_agent_integration)
        if auto_register_agent_hook:
            tools.append(self.auto_register_agent_hook)
        if track_message_metrics:
            tools.append(self.track_message_metrics)
        if update_usage_from_metrics:
            tools.append(self.update_usage_from_metrics)
        if extract_usage_from_response:
            tools.append(self.extract_and_update_usage_from_response)
        if suggest_optimal_chunks:
            tools.append(self.suggest_optimal_chunks)
            
        super().__init__(
            name="token_manager",
            tools=tools,
            instructions="""
            This tool provides comprehensive token management for LLM interactions.
            Use it to monitor token usage, enforce limits, and optimize token consumption.
            
            Key Philosophy: When content exceeds token limits, the agent should break work 
            into smaller chunks rather than truncating content. This preserves context, 
            maintains quality, and gives the agent full control over processing.
            
            Core Functions:
            - Monitor token usage and track costs
            - Check if content fits within limits
            - Suggest optimal chunking strategies for large content
            - Provide guidance for staying within token budgets
            
            When limits are exceeded, use suggest_optimal_chunks() to get a detailed 
            strategy for breaking content into manageable pieces.
            """,
            **kwargs
        )
        
        # Agent reference - will be set when added to agent
        self._agent_ref = None
        
    def setup_agent_integration(self) -> str:
        """
        Set up automatic token tracking with the current agent.
        Call this method after adding the tool to an agent for automatic tracking.
        This method will auto-detect the agent from the tool context.
        
        Returns:
            JSON string with registration status
        """
        try:
            # Auto-detect agent from function context
            agent = None
            for func in self.functions.values():
                if hasattr(func, '_agent') and func._agent:
                    agent = func._agent
                    break
                
            if agent is None:
                return json.dumps({
                    "status": "error",
                    "message": "No agent found. Add this tool to an agent first, then call setup_agent_integration()."
                })
            
            self._agent_ref = agent
            
            # Add a hook to track token usage from agent runs
            if not hasattr(agent, '_token_managers'):
                agent._token_managers = []
            
            # Avoid duplicate registration
            if self not in agent._token_managers:
                agent._token_managers.append(self)
                
            # Set up post-run hook if the agent supports it
            if hasattr(agent, 'add_post_run_hook'):
                agent.add_post_run_hook(self._post_run_hook)
            elif hasattr(agent, '_post_run_hooks'):
                if not hasattr(agent._post_run_hooks, '__iter__'):
                    agent._post_run_hooks = []
                if self._post_run_hook not in agent._post_run_hooks:
                    agent._post_run_hooks.append(self._post_run_hook)
            else:
                # Add the hook directly if no standard method exists
                if not hasattr(agent, '_token_post_run_hooks'):
                    agent._token_post_run_hooks = []
                if self._post_run_hook not in agent._token_post_run_hooks:
                    agent._token_post_run_hooks.append(self._post_run_hook)
                
            result = {
                "status": "success",
                "message": "Token manager registered with agent",
                "agent_name": getattr(agent, 'name', 'unknown'),
                "agent_id": getattr(agent, 'agent_id', 'unknown')
            }
            
            log_info(f"TokenManager: Registered with agent {result['agent_name']}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error registering with agent: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def register_with_agent_manually(self, agent) -> bool:
        """
        Manually register this token manager with an agent.
        This method is for programmatic use, not as a tool function.
        
        Args:
            agent: The agent to register with
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            self._agent_ref = agent
            
            # Add a hook to track token usage from agent runs
            if not hasattr(agent, '_token_managers'):
                agent._token_managers = []
            
            # Avoid duplicate registration
            if self not in agent._token_managers:
                agent._token_managers.append(self)
                
            # Set up post-run hook if the agent supports it
            if hasattr(agent, 'add_post_run_hook'):
                agent.add_post_run_hook(self._post_run_hook)
            elif hasattr(agent, '_post_run_hooks'):
                if not hasattr(agent._post_run_hooks, '__iter__'):
                    agent._post_run_hooks = []
                if self._post_run_hook not in agent._post_run_hooks:
                    agent._post_run_hooks.append(self._post_run_hook)
            else:
                # Add the hook directly if no standard method exists
                if not hasattr(agent, '_token_post_run_hooks'):
                    agent._token_post_run_hooks = []
                if self._post_run_hook not in agent._token_post_run_hooks:
                    agent._token_post_run_hooks.append(self._post_run_hook)
                    
            log_info(f"TokenManager: Manually registered with agent {getattr(agent, 'name', 'unknown')}")
            return True
            
        except Exception as e:
            log_error(f"TokenManager: Error in manual registration: {e}")
            return False
            
    def register_with_agent(self, agent=None) -> str:
        """
        Backward compatibility method for registering with an agent.
        
        Args:
            agent: The agent to register with
            
        Returns:
            JSON string with registration status
        """
        if agent is not None:
            success = self.register_with_agent_manually(agent)
            if success:
                return json.dumps({
                    "status": "success",
                    "message": "Token manager registered with agent",
                    "agent_name": getattr(agent, 'name', 'unknown'),
                    "agent_id": getattr(agent, 'agent_id', 'unknown')
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to register with agent"
                })
        else:
            return self.setup_agent_integration()
            
    def auto_register_agent_hook(self) -> str:
        """
        Automatically register with agent if this tool is added to one.
        This method scans for agent reference in the functions.
        
        Returns:
            JSON string with registration status
        """
        try:
            # Check if any function has an agent reference
            for func in self.functions.values():
                if hasattr(func, '_agent') and func._agent:
                    return self.setup_agent_integration()
                    
            return json.dumps({
                "status": "warning", 
                "message": "No agent reference found. Add this tool to an agent first, then call setup_agent_integration()."
            })
            
        except Exception as e:
            error_msg = f"Error auto-registering with agent: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
        
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken or approximation.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
            
        if self.tiktoken_available and self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                log_warning(f"TokenManager: tiktoken encoding failed: {e}")
                
        # Fallback to approximation (roughly 4 characters per token)
        # Remove extra whitespace and count words + punctuation
        clean_text = re.sub(r'\s+', ' ', text.strip())
        word_count = len(clean_text.split())
        char_count = len(clean_text)
        
        # Approximate tokens: blend of word count and character count
        approx_tokens = int((word_count * 1.3) + (char_count * 0.25))
        return max(1, approx_tokens)
    
    def _check_limits(self, input_tokens: int, output_tokens: int = 0) -> Dict[str, Any]:
        """
        Check if token usage is within limits.
        
        Args:
            input_tokens: Input token count
            output_tokens: Output token count (optional)
            
        Returns:
            Dictionary with check results
        """
        total_tokens = input_tokens + output_tokens
        violations = []
        warnings = []
        
        # Check individual limits
        if self.limits.max_input_tokens and input_tokens > self.limits.max_input_tokens:
            violations.append(f"Input tokens ({input_tokens}) exceed limit ({self.limits.max_input_tokens})")
        elif self.limits.max_input_tokens and input_tokens > (self.limits.max_input_tokens * self.limits.soft_limit_threshold):
            warnings.append(f"Input tokens ({input_tokens}) approaching limit ({self.limits.max_input_tokens})")
            
        if self.limits.max_output_tokens and output_tokens > self.limits.max_output_tokens:
            violations.append(f"Output tokens ({output_tokens}) exceed limit ({self.limits.max_output_tokens})")
            
        if self.limits.max_tokens_per_request and total_tokens > self.limits.max_tokens_per_request:
            violations.append(f"Request tokens ({total_tokens}) exceed per-request limit ({self.limits.max_tokens_per_request})")
            
        if self.limits.max_total_tokens and (self.stats.total_tokens + total_tokens) > self.limits.max_total_tokens:
            violations.append(f"Session total ({self.stats.total_tokens + total_tokens}) would exceed session limit ({self.limits.max_total_tokens})")
            
        return {
            "within_limits": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }
    
    def get_token_count(self, text: str, include_metadata: bool = True) -> str:
        """
        Count tokens in the provided text.
        
        Args:
            text: Text to count tokens for
            include_metadata: Include additional metadata in response
            
        Returns:
            JSON string with token count and metadata
        """
        try:
            token_count = self._count_tokens(text)
            
            result = {
                "token_count": token_count,
                "character_count": len(text),
                "word_count": len(text.split()),
                "encoding_method": "tiktoken" if self.tiktoken_available else "approximation"
            }
            
            if include_metadata:
                result.update({
                    "text_preview": text[:100] + "..." if len(text) > 100 else text,
                    "estimated_cost_gpt4": round((token_count / 1000) * 0.03, 6),
                    "estimated_cost_gpt3_5": round((token_count / 1000) * 0.0015, 6)
                })
            
            log_debug(f"TokenManager: Counted {token_count} tokens in text")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error counting tokens: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def get_usage_stats(self) -> str:
        """
        Get current token usage statistics.
        
        Returns:
            JSON string with usage statistics
        """
        try:
            result = {
                "total_input_tokens": self.stats.total_input_tokens,
                "total_output_tokens": self.stats.total_output_tokens,
                "total_tokens": self.stats.total_tokens,
                "session_count": self.stats.session_count,
                "peak_tokens_per_request": self.stats.peak_tokens_per_request,
                "average_tokens_per_session": round(self.stats.total_tokens / max(1, self.stats.session_count), 2),
                "last_reset_time": self.stats.last_reset_time.isoformat() if self.stats.last_reset_time else None,
                "current_limits": {
                    "max_input_tokens": self.limits.max_input_tokens,
                    "max_output_tokens": self.limits.max_output_tokens,
                    "max_total_tokens": self.limits.max_total_tokens,
                    "max_tokens_per_request": self.limits.max_tokens_per_request,
                    "max_context_window": self.limits.max_context_window
                }
            }
            
            # Add utilization percentages
            if self.limits.max_total_tokens:
                result["total_token_utilization_percent"] = round(
                    (self.stats.total_tokens / self.limits.max_total_tokens) * 100, 2
                )
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error getting usage stats: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def set_token_limits(
        self,
        max_input_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        max_total_tokens: Optional[int] = None,
        max_tokens_per_request: Optional[int] = None,
        max_context_window: Optional[int] = None
    ) -> str:
        """
        Set or update token limits.
        
        Args:
            max_input_tokens: Maximum input tokens allowed
            max_output_tokens: Maximum output tokens allowed
            max_total_tokens: Maximum total tokens per session
            max_tokens_per_request: Maximum tokens per single request
            max_context_window: Maximum context window size
            
        Returns:
            JSON string with updated limits
        """
        try:
            # Update limits
            if max_input_tokens is not None:
                self.limits.max_input_tokens = max_input_tokens
            if max_output_tokens is not None:
                self.limits.max_output_tokens = max_output_tokens
            if max_total_tokens is not None:
                self.limits.max_total_tokens = max_total_tokens
            if max_tokens_per_request is not None:
                self.limits.max_tokens_per_request = max_tokens_per_request
            if max_context_window is not None:
                self.limits.max_context_window = max_context_window
            
            result = {
                "status": "success",
                "message": "Token limits updated successfully",
                "updated_limits": {
                    "max_input_tokens": self.limits.max_input_tokens,
                    "max_output_tokens": self.limits.max_output_tokens,
                    "max_total_tokens": self.limits.max_total_tokens,
                    "max_tokens_per_request": self.limits.max_tokens_per_request,
                    "max_context_window": self.limits.max_context_window
                }
            }
            
            log_info(f"TokenManager: Updated token limits")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error setting token limits: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def reset_usage_stats(self) -> str:
        """
        Reset token usage statistics.
        
        Returns:
            JSON string with reset confirmation
        """
        try:
            old_stats = {
                "total_tokens": self.stats.total_tokens,
                "session_count": self.stats.session_count
            }
            
            self.stats.reset()
            
            result = {
                "status": "success",
                "message": "Token usage statistics reset successfully",
                "previous_stats": old_stats,
                "reset_time": self.stats.last_reset_time.isoformat()
            }
            
            log_info("TokenManager: Usage statistics reset")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error resetting usage stats: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def check_token_limits(self, text: str, expected_output_tokens: int = 0) -> str:
        """
        Check if text would exceed token limits.
        
        Args:
            text: Text to check
            expected_output_tokens: Expected output token count
            
        Returns:
            JSON string with limit check results
        """
        try:
            input_tokens = self._count_tokens(text)
            check_result = self._check_limits(input_tokens, expected_output_tokens)
            
            result = {
                "within_limits": check_result["within_limits"],
                "input_tokens": input_tokens,
                "expected_output_tokens": expected_output_tokens,
                "total_tokens": check_result["total_tokens"],
                "violations": check_result["violations"],
                "warnings": check_result["warnings"],
                "current_session_tokens": self.stats.total_tokens,
                "remaining_session_tokens": (
                    self.limits.max_total_tokens - self.stats.total_tokens 
                    if self.limits.max_total_tokens else None
                )
            }
            
            # Add chunking guidance if limits are exceeded and chunking is enabled
            if not check_result["within_limits"] and self.provide_chunk_guidance:
                if self.limits.max_input_tokens and input_tokens > self.limits.max_input_tokens:
                    target_chunk_size = int(self.limits.max_input_tokens * 0.7)
                    estimated_chunks = max(1, (input_tokens // target_chunk_size) + 1)
                    
                    result["chunking_guidance"] = {
                        "recommended": True,
                        "reason": "Input exceeds maximum allowed tokens",
                        "suggested_chunks": estimated_chunks,
                        "target_tokens_per_chunk": target_chunk_size,
                        "message": f"Consider breaking content into ~{estimated_chunks} chunks of ~{target_chunk_size} tokens each",
                        "use_suggest_optimal_chunks": "Call suggest_optimal_chunks() for detailed chunking strategy"
                    }
            
            if check_result["violations"] and self.enable_warnings:
                for violation in check_result["violations"]:
                    log_warning(f"TokenManager: {violation}")
                    
            if check_result["warnings"] and self.enable_warnings:
                for warning in check_result["warnings"]:
                    log_warning(f"TokenManager: {warning}")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error checking token limits: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def estimate_cost(self, text: str, model: str = "gpt-4", expected_output_tokens: int = 0) -> str:
        """
        Estimate the cost of processing text with specified model.
        
        Args:
            text: Text to estimate cost for
            model: Model name for cost calculation
            expected_output_tokens: Expected output token count
            
        Returns:
            JSON string with cost estimation
        """
        try:
            input_tokens = self._count_tokens(text)
            total_input_tokens = input_tokens
            total_output_tokens = expected_output_tokens
            
            # Get model costs
            model_costs = self.token_costs.get(model, {"input": 0.03, "output": 0.06})
            
            input_cost = (total_input_tokens / 1000) * model_costs["input"]
            output_cost = (total_output_tokens / 1000) * model_costs["output"]
            total_cost = input_cost + output_cost
            
            result = {
                "model": model,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "costs": {
                    "input_cost_usd": round(input_cost, 6),
                    "output_cost_usd": round(output_cost, 6),
                    "total_cost_usd": round(total_cost, 6)
                },
                "cost_per_1k_tokens": {
                    "input": model_costs["input"],
                    "output": model_costs["output"]
                }
            }
            
            # Add session cost estimates
            if self.stats.total_tokens > 0:
                session_input_cost = (self.stats.total_input_tokens / 1000) * model_costs["input"]
                session_output_cost = (self.stats.total_output_tokens / 1000) * model_costs["output"]
                result["session_total_cost_usd"] = round(session_input_cost + session_output_cost, 6)
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error estimating cost: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def truncate_text(self, text: str, max_tokens: int, preserve_ending: bool = False) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            preserve_ending: Whether to preserve the end of the text instead of beginning
            
        Returns:
            JSON string with truncated text
        """
        try:
            current_tokens = self._count_tokens(text)
            
            if current_tokens <= max_tokens:
                return json.dumps({
                    "status": "no_truncation_needed",
                    "original_tokens": current_tokens,
                    "max_tokens": max_tokens,
                    "text": text,
                    "truncated": False
                })
            
            # Binary search for optimal truncation point
            if preserve_ending:
                words = text.split()
                start_idx = 0
                end_idx = len(words)
                
                while start_idx < end_idx - 1:
                    mid_idx = (start_idx + end_idx) // 2
                    test_text = ' '.join(words[mid_idx:])
                    test_tokens = self._count_tokens(test_text)
                    
                    if test_tokens <= max_tokens:
                        end_idx = mid_idx
                    else:
                        start_idx = mid_idx
                        
                truncated_text = ' '.join(words[end_idx:])
                truncation_indicator = "... "
                
            else:
                words = text.split()
                start_idx = 0
                end_idx = len(words)
                
                while start_idx < end_idx - 1:
                    mid_idx = (start_idx + end_idx) // 2
                    test_text = ' '.join(words[:mid_idx])
                    test_tokens = self._count_tokens(test_text)
                    
                    if test_tokens <= max_tokens:
                        start_idx = mid_idx
                    else:
                        end_idx = mid_idx
                        
                truncated_text = ' '.join(words[:start_idx])
                truncation_indicator = " ..."
            
            # Add truncation indicator if there's room
            final_text = truncated_text + truncation_indicator
            final_tokens = self._count_tokens(final_text)
            
            if final_tokens > max_tokens:
                final_text = truncated_text
                final_tokens = self._count_tokens(final_text)
            
            result = {
                "status": "truncated",
                "original_tokens": current_tokens,
                "final_tokens": final_tokens,
                "max_tokens": max_tokens,
                "text": final_text,
                "truncated": True,
                "chars_removed": len(text) - len(final_text),
                "tokens_removed": current_tokens - final_tokens,
                "preserve_ending": preserve_ending
            }
            
            log_info(f"TokenManager: Truncated text from {current_tokens} to {final_tokens} tokens")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error truncating text: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def track_message_metrics(self, input_tokens: int, output_tokens: int = 0) -> str:
        """
        Manually track token usage from message metrics.
        
        Args:
            input_tokens: Number of input tokens to track
            output_tokens: Number of output tokens to track
            
        Returns:
            JSON string with tracking result
        """
        try:
            old_total = self.stats.total_tokens
            self.stats.add_usage(input_tokens, output_tokens)
            self.stats.session_count += 1
            
            # Check for limit violations
            check_result = self._check_limits(input_tokens, output_tokens)
            
            result = {
                "status": "success",
                "message": "Token usage tracked successfully",
                "tracked_tokens": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                "updated_stats": {
                    "total_tokens": self.stats.total_tokens,
                    "total_input_tokens": self.stats.total_input_tokens,
                    "total_output_tokens": self.stats.total_output_tokens,
                    "session_count": self.stats.session_count
                },
                "limit_check": {
                    "within_limits": check_result["within_limits"],
                    "violations": check_result["violations"],
                    "warnings": check_result["warnings"]
                }
            }
            
            # Log warnings if any
            if check_result["violations"] and self.enable_warnings:
                for violation in check_result["violations"]:
                    log_warning(f"TokenManager: {violation}")
                    
            if check_result["warnings"] and self.enable_warnings:
                for warning in check_result["warnings"]:
                    log_warning(f"TokenManager: {warning}")
            
            log_debug(f"TokenManager: Tracked {input_tokens} input, {output_tokens} output tokens")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error tracking message metrics: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def update_usage_from_metrics(self, metrics: MessageMetrics) -> str:
        """
        Update usage statistics from MessageMetrics.
        This method can be called manually to track usage from external sources.
        
        Args:
            metrics: MessageMetrics from agent run
            
        Returns:
            JSON string with tracking result
        """
        try:
            input_tokens = metrics.input_tokens or 0
            output_tokens = metrics.output_tokens or 0
            
            if input_tokens > 0 or output_tokens > 0:
                self.stats.add_usage(input_tokens, output_tokens)
                self.stats.session_count += 1
                
                log_debug(f"TokenManager: Updated usage - Input: {input_tokens}, Output: {output_tokens}")
                
                # Check for limit violations
                check_result = self._check_limits(input_tokens, output_tokens)
                if not check_result["within_limits"] and self.enable_warnings:
                    for violation in check_result["violations"]:
                        log_warning(f"TokenManager: {violation}")
                        
                if self.strict_mode and check_result["violations"]:
                    error_msg = f"Token limit violation: {'; '.join(check_result['violations'])}"
                    log_error(f"TokenManager: {error_msg}")
                    return json.dumps({"error": error_msg})
                    
                return json.dumps({
                    "status": "success",
                    "message": "Usage updated from metrics",
                    "tracked_tokens": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    },
                    "total_session_tokens": self.stats.total_tokens
                })
                    
        except Exception as e:
            error_msg = f"Error updating usage from metrics: {str(e)}"
            log_error(f"TokenManager: {error_msg}")
            return json.dumps({"error": error_msg})
    
    def _post_run_hook(self, agent, result):
        """
        Internal method called by agents after runs to track token usage.
        This is automatically called when the agent is properly integrated.
        
        Args:
            agent: The agent that completed the run
            result: The run result containing metrics
        """
        try:
            if hasattr(result, 'usage_metrics') and result.usage_metrics:
                metrics = result.usage_metrics
                if hasattr(metrics, 'input_tokens') and hasattr(metrics, 'output_tokens'):
                    input_tokens = getattr(metrics, 'input_tokens', 0) or 0
                    output_tokens = getattr(metrics, 'output_tokens', 0) or 0
                    
                    if input_tokens > 0 or output_tokens > 0:
                        self.stats.add_usage(input_tokens, output_tokens)
                        self.stats.session_count += 1
                        log_debug(f"TokenManager: Auto-tracked {input_tokens} input, {output_tokens} output tokens")
                        
                        # Check for limit violations
                        check_result = self._check_limits(input_tokens, output_tokens)
                        if not check_result["within_limits"] and self.enable_warnings:
                            for violation in check_result["violations"]:
                                log_warning(f"TokenManager: {violation}")
                                
        except Exception as e:
            log_error(f"TokenManager: Error in post-run hook: {e}")
    
    def extract_and_update_usage_from_response(self, response) -> str:
        """
        Extract and update token usage from an agent response object.
        This method can be called manually after agent runs to track usage.
        
        Args:
            response: Agent response object
            
        Returns:
            JSON string with tracking result
        """
        try:
            input_tokens = 0
            output_tokens = 0
            
            # Try to extract metrics from various response object structures
            if hasattr(response, 'usage_metrics'):
                metrics = response.usage_metrics
                input_tokens = getattr(metrics, 'input_tokens', 0) or 0
                output_tokens = getattr(metrics, 'output_tokens', 0) or 0
            elif hasattr(response, 'metrics'):
                metrics = response.metrics
                input_tokens = getattr(metrics, 'input_tokens', 0) or 0
                output_tokens = getattr(metrics, 'output_tokens', 0) or 0
            elif hasattr(response, 'token_usage'):
                usage = response.token_usage
                input_tokens = getattr(usage, 'prompt_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0
            elif hasattr(response, 'usage'):
                usage = response.usage
                input_tokens = getattr(usage, 'prompt_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0
            
            # Also try to extract from content if tokens are 0
            if input_tokens == 0 and output_tokens == 0:
                if hasattr(response, 'content') and response.content:
                    # Estimate output tokens from content
                    output_tokens = self._count_tokens(str(response.content))
                    log_debug(f"TokenManager: Estimated {output_tokens} output tokens from response content")
                    
            if input_tokens > 0 or output_tokens > 0:
                self.stats.add_usage(input_tokens, output_tokens)
                self.stats.session_count += 1
                
                result = {
                    "status": "success",
                    "message": "Token usage extracted and tracked",
                    "tracked_tokens": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    },
                    "total_session_tokens": self.stats.total_tokens,
                    "extraction_method": "response_object_analysis"
                }
                
                log_debug(f"TokenManager: Extracted and tracked {input_tokens} input, {output_tokens} output tokens")
                return json.dumps(result)
            else:
                return json.dumps({
                    "status": "warning",
                    "message": "No token usage found in response object",
                    "response_attributes": [attr for attr in dir(response) if not attr.startswith('_')]
                })
                
        except Exception as e:
            error_msg = f"Error extracting usage from response: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def suggest_optimal_chunks(self, text: str, target_chunk_tokens: Optional[int] = None) -> str:
        """
        Suggest how to break large content into optimal chunks for processing.
        This helps agents manage large content without hitting token limits.
        
        Args:
            text: The text that needs to be processed in chunks
            target_chunk_tokens: Target tokens per chunk (defaults to 70% of max_input_tokens)
            
        Returns:
            JSON string with chunking suggestions
        """
        try:
            total_tokens = self._count_tokens(text)
            
            # Determine target chunk size
            if target_chunk_tokens is None:
                if self.limits.max_input_tokens:
                    # Use 70% of max input tokens to leave room for instructions and context
                    target_chunk_tokens = int(self.limits.max_input_tokens * 0.7)
                else:
                    # Default to a reasonable chunk size if no limits set
                    target_chunk_tokens = 1000
            
            # Calculate chunking strategy
            if total_tokens <= target_chunk_tokens:
                return json.dumps({
                    "status": "no_chunking_needed",
                    "total_tokens": total_tokens,
                    "target_chunk_tokens": target_chunk_tokens,
                    "recommendation": "Content fits within limits - no chunking required",
                    "can_process_directly": True
                })
            
            # Calculate optimal chunking
            estimated_chunks = max(1, (total_tokens // target_chunk_tokens) + (1 if total_tokens % target_chunk_tokens > 0 else 0))
            
            # Split text into sentences for better chunk boundaries
            sentences = self._split_into_sentences(text)
            suggested_chunks = self._create_chunks_from_sentences(sentences, target_chunk_tokens)
            
            result = {
                "status": "chunking_recommended",
                "analysis": {
                    "total_tokens": total_tokens,
                    "target_chunk_tokens": target_chunk_tokens,
                    "estimated_chunks": len(suggested_chunks),
                    "average_chunk_tokens": sum(chunk["tokens"] for chunk in suggested_chunks) // len(suggested_chunks) if suggested_chunks else 0
                },
                "recommendation": f"Break content into {len(suggested_chunks)} chunks for optimal processing",
                "chunks": suggested_chunks,
                "processing_strategy": {
                    "approach": "sequential_processing",
                    "description": "Process each chunk separately, then combine results",
                    "benefits": ["Stays within token limits", "Preserves context", "Maintains quality"]
                },
                "can_process_directly": False
            }
            
            # Add warnings if chunks are still too large
            oversized_chunks = [i for i, chunk in enumerate(suggested_chunks) if chunk["tokens"] > target_chunk_tokens]
            if oversized_chunks:
                result["warnings"] = [
                    f"Chunk {i+1} ({suggested_chunks[i]['tokens']} tokens) still exceeds target size"
                    for i in oversized_chunks
                ]
                result["additional_recommendations"] = [
                    "Consider further breaking down oversized chunks",
                    "Or increase target_chunk_tokens parameter"
                ]
            
            log_info(f"TokenManager: Suggested {len(suggested_chunks)} chunks for {total_tokens} token content")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error suggesting optimal chunks: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunk boundaries."""
        import re
        # Simple sentence splitting - can be improved with more sophisticated methods
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_chunks_from_sentences(self, sentences: List[str], target_tokens: int) -> List[Dict[str, Any]]:
        """Create chunks from sentences, respecting token limits."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # If adding this sentence would exceed target, start a new chunk
            if current_tokens + sentence_tokens > target_tokens and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "text": chunk_text,
                    "tokens": current_tokens,
                    "sentences": len(current_chunk),
                    "preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
                })
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "text": chunk_text,
                "tokens": current_tokens,
                "sentences": len(current_chunk),
                "preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
            })
        
        return chunks