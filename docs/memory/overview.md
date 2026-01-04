# Memory Management System

Buddy AI's memory system provides intelligent storage, retrieval, and management of conversation history, learned information, and contextual knowledge across agent interactions.

## 🧠 Memory Overview

The memory system enables agents to:

- **Retain Context**: Maintain conversation history and context across interactions
- **Learn from Experience**: Store and recall insights from previous interactions  
- **Personalize Responses**: Remember user preferences and interaction patterns
- **Share Knowledge**: Access collective knowledge across agent instances
- **Manage Information**: Organize and retrieve relevant information efficiently

```mermaid
graph TD
    A[Memory System] --> B[Conversational Memory]
    A --> C[Episodic Memory] 
    A --> D[Semantic Memory]
    A --> E[Working Memory]
    A --> F[Long-term Memory]
    
    B --> B1[Chat History]
    B --> B2[Context Window]
    B --> B3[Turn Management]
    
    C --> C1[Interaction Episodes]
    C --> C2[Learning Events]
    C --> C3[Experience Patterns]
    
    D --> D1[Facts & Knowledge]
    D --> D2[Concepts & Relations]
    D --> D3[Procedures & Skills]
    
    E --> E1[Active Context]
    E --> E2[Current Focus]
    E --> E3[Temporary Variables]
    
    F --> F1[Persistent Storage]
    F --> F2[Knowledge Base]
    F --> F3[User Profiles]
```

## 🚀 Quick Start

### Basic Memory Setup
```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory import MemoryManager, ConversationalMemory

# Create memory manager
memory_manager = MemoryManager(
    memory_types=[
        ConversationalMemory(max_history=100),  # Keep last 100 exchanges
        # More memory types can be added
    ],
    storage_backend="local",  # or "redis", "postgres", "mongodb"
    persistence=True
)

# Create agent with memory
agent = Agent(
    model=OpenAIChat(),
    memory=memory_manager,
    instructions="Use your memory to provide personalized assistance."
)

# Interact with memory-enabled agent
response1 = agent.run("My name is Alice and I love hiking.")
# Agent stores: user name, interests

response2 = agent.run("What outdoor activities would you recommend?")
# Agent recalls: Alice loves hiking, suggests related activities

# Access memory directly
stored_info = agent.memory.recall("user preferences")
print(f"Stored user info: {stored_info}")
```

### Memory with Persistence
```python
from buddy.memory import PersistentMemory

# Memory that persists across sessions
persistent_memory = PersistentMemory(
    storage_path="./agent_memory",
    user_id="alice_123",
    encryption_key="secure_key_here",  # Optional encryption
    auto_save=True,
    backup_enabled=True
)

agent = Agent(
    model=OpenAIChat(),
    memory=persistent_memory
)

# Memory persists even after agent restart
agent.run("Remember that I'm working on a Python project.")
# ... later session ...
agent.run("What was I working on?")  # Recalls Python project
```

## 💭 Memory Types

### ConversationalMemory
```python
from buddy.memory.conversational import ConversationalMemory

conversational_memory = ConversationalMemory(
    max_history=200,           # Maximum conversation turns to retain
    context_window=4000,       # Token limit for active context
    compression_enabled=True,   # Compress old conversations
    summarization_threshold=50, # Summarize after 50 turns
    
    # Filtering options
    filter_sensitive_data=True,
    retention_rules={
        "personal_info": "7_days",
        "preferences": "30_days", 
        "general_chat": "3_days"
    }
)

# Add conversation turns
conversational_memory.add_exchange(
    user_message="I'm planning a trip to Japan",
    agent_response="That's exciting! What cities are you considering?",
    metadata={
        "timestamp": "2024-01-15T10:00:00Z",
        "session_id": "sess_123",
        "topic": "travel_planning"
    }
)

# Retrieve conversation history
history = conversational_memory.get_recent_history(limit=10)
for exchange in history:
    print(f"User: {exchange.user_message}")
    print(f"Agent: {exchange.agent_response}")
```

### EpisodicMemory
```python
from buddy.memory.episodic import EpisodicMemory

episodic_memory = EpisodicMemory(
    episode_types=[
        "learning_events",
        "problem_solving",
        "user_interactions",
        "task_completions",
        "error_corrections"
    ],
    indexing_strategy="semantic",  # or "temporal", "hybrid"
    max_episodes=1000
)

# Store learning episode
episodic_memory.store_episode(
    episode_type="learning_event",
    content={
        "trigger": "User asked about machine learning",
        "learning": "User prefers practical examples over theory",
        "context": "Educational conversation",
        "outcome": "Positive feedback on example-heavy response"
    },
    importance_score=0.8,  # 0.0 to 1.0
    tags=["user_preference", "learning_style", "education"]
)

# Recall similar episodes
similar_episodes = episodic_memory.recall_similar(
    query="user prefers examples",
    max_results=5,
    similarity_threshold=0.7
)

for episode in similar_episodes:
    print(f"Episode: {episode.content}")
    print(f"Relevance: {episode.similarity_score:.2f}")
```

### SemanticMemory
```python
from buddy.memory.semantic import SemanticMemory

semantic_memory = SemanticMemory(
    knowledge_domains=[
        "user_preferences",
        "domain_expertise",
        "factual_knowledge",
        "procedural_knowledge",
        "conceptual_relations"
    ],
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    vector_store="chroma"  # or "pinecone", "weaviate", "qdrant"
)

# Store semantic knowledge
semantic_memory.store_knowledge(
    concept="user_communication_style",
    knowledge={
        "prefers_detailed_explanations": True,
        "likes_step_by_step_guidance": True,
        "responds_well_to_encouragement": True,
        "technical_level": "intermediate"
    },
    confidence=0.9,
    sources=["conversation_analysis", "explicit_feedback"]
)

# Retrieve related knowledge
related_knowledge = semantic_memory.retrieve_knowledge(
    query="How should I communicate with this user?",
    knowledge_types=["user_communication_style", "user_preferences"]
)

print("Communication guidance:")
for item in related_knowledge:
    print(f"  {item.concept}: {item.knowledge}")
```

### WorkingMemory
```python
from buddy.memory.working import WorkingMemory

working_memory = WorkingMemory(
    capacity_limit=7,  # Miller's magic number
    decay_factor=0.9,  # Information decay over time
    refresh_on_access=True,  # Refresh accessed items
    
    # Priority management
    priority_weights={
        "current_task": 1.0,
        "user_context": 0.8,
        "recent_facts": 0.6,
        "background_info": 0.4
    }
)

# Add items to working memory
working_memory.add_item(
    content="User is debugging Python code", 
    item_type="current_task",
    importance=1.0
)

working_memory.add_item(
    content="Error: IndexError in line 42",
    item_type="recent_facts", 
    importance=0.8
)

# Retrieve active context
active_items = working_memory.get_active_items()
print("Current working memory:")
for item in active_items:
    print(f"  {item.content} (importance: {item.current_importance:.2f})")
```

## 🗄️ Memory Storage Backends

### Local File Storage
```python
from buddy.memory.storage import LocalFileStorage

local_storage = LocalFileStorage(
    base_path="./memory_data",
    file_format="json",  # or "pickle", "parquet"
    compression="gzip",
    encryption_enabled=True,
    backup_rotation=7  # Keep 7 backup versions
)
```

### Redis Storage
```python
from buddy.memory.storage import RedisStorage

redis_storage = RedisStorage(
    host="localhost",
    port=6379,
    db=0,
    password="secure_password",
    
    # Memory optimization
    memory_policy="allkeys-lru",  # Eviction policy
    max_memory="1gb",
    
    # Persistence
    persistence_enabled=True,
    snapshot_frequency="300s"  # Save snapshot every 5 minutes
)
```

### PostgreSQL Storage
```python
from buddy.memory.storage import PostgreSQLStorage

postgres_storage = PostgreSQLStorage(
    connection_string="postgresql://user:password@localhost:5432/buddy_memory",
    
    # Schema configuration
    schema_name="agent_memory",
    table_prefix="buddy_",
    
    # Performance optimization
    connection_pool_size=10,
    enable_partitioning=True,  # Partition by date
    index_strategy="btree_gin"  # For JSON queries
)
```

### Vector Database Storage
```python
from buddy.memory.storage import VectorStorage

vector_storage = VectorStorage(
    provider="chroma",  # or "pinecone", "weaviate", "qdrant"
    
    # Chroma configuration
    chroma_config={
        "collection_name": "buddy_memories",
        "embedding_model": "all-MiniLM-L6-v2",
        "distance_metric": "cosine"
    },
    
    # Performance settings
    batch_size=100,
    index_rebuild_threshold=10000
)
```

## 🔍 Memory Retrieval

### Query-based Retrieval
```python
from buddy.memory.retrieval import MemoryRetriever

retriever = MemoryRetriever(
    strategies=[
        "semantic_search",   # Vector similarity search
        "keyword_matching",  # Exact keyword matches
        "temporal_proximity", # Recent interactions
        "importance_ranking", # High-importance items first
        "user_context"       # User-specific memories
    ],
    
    # Combining strategies
    combination_method="weighted_fusion",
    strategy_weights={
        "semantic_search": 0.4,
        "keyword_matching": 0.2,
        "temporal_proximity": 0.2,
        "importance_ranking": 0.1,
        "user_context": 0.1
    }
)

# Retrieve relevant memories
query = "What does the user like for breakfast?"
relevant_memories = retriever.retrieve(
    query=query,
    memory_types=["conversational", "semantic"],
    max_results=10,
    relevance_threshold=0.6
)

print("Retrieved memories:")
for memory in relevant_memories:
    print(f"  {memory.content} (score: {memory.relevance_score:.2f})")
```

### Context-aware Retrieval
```python
from buddy.memory.retrieval import ContextualRetriever

contextual_retriever = ContextualRetriever(
    context_factors=[
        "current_conversation_topic",
        "user_emotional_state", 
        "task_complexity",
        "user_expertise_level",
        "time_of_day",
        "interaction_history"
    ]
)

# Retrieve with context
context = {
    "current_topic": "cooking",
    "user_mood": "frustrated",
    "task_type": "problem_solving",
    "user_level": "beginner"
}

contextual_memories = contextual_retriever.retrieve_with_context(
    query="help with recipe",
    context=context,
    adaptation_strategy="empathetic_support"
)
```

## 🧹 Memory Management

### Memory Cleanup
```python
from buddy.memory.management import MemoryManager

memory_manager = MemoryManager(
    cleanup_policies=[
        {
            "name": "age_based_cleanup",
            "condition": "age > 30 days",
            "action": "archive",  # or "delete", "compress"
            "exceptions": ["important_user_preferences"]
        },
        {
            "name": "relevance_cleanup", 
            "condition": "access_count < 2 AND age > 7 days",
            "action": "delete",
            "memory_types": ["conversational"]
        },
        {
            "name": "size_based_cleanup",
            "condition": "total_size > 1GB",
            "action": "compress_oldest",
            "target_size": "800MB"
        }
    ],
    
    # Automatic cleanup
    auto_cleanup_enabled=True,
    cleanup_schedule="daily",  # Run cleanup daily
    cleanup_time="02:00"       # At 2 AM
)
```

### Memory Optimization
```python
from buddy.memory.optimization import MemoryOptimizer

optimizer = MemoryOptimizer(
    optimization_strategies=[
        "duplicate_detection",     # Remove duplicate memories
        "information_merging",     # Merge similar information
        "importance_recalculation", # Update importance scores
        "access_pattern_analysis",  # Optimize based on usage
        "compression_opportunities" # Identify compressible data
    ]
)

# Run optimization
optimization_report = optimizer.optimize_memory(memory_manager)
print("Optimization Results:")
print(f"  Space saved: {optimization_report['space_saved_mb']:.1f}MB")
print(f"  Items merged: {optimization_report['items_merged']}")
print(f"  Duplicates removed: {optimization_report['duplicates_removed']}")
```

## 🔒 Memory Security

### Encryption and Privacy
```python
from buddy.memory.security import MemorySecurity

memory_security = MemorySecurity(
    encryption_config={
        "algorithm": "AES-256-GCM",
        "key_rotation_days": 90,
        "key_derivation": "PBKDF2"
    },
    
    privacy_settings={
        "anonymize_personal_data": True,
        "redact_sensitive_info": True,
        "retention_limits": {
            "personal_identifiers": "30_days",
            "financial_data": "0_days",  # Never store
            "health_information": "0_days"
        }
    },
    
    access_control={
        "require_authentication": True,
        "role_based_access": True,
        "audit_logging": True
    }
)

agent.memory.set_security_manager(memory_security)
```

### Data Anonymization
```python
from buddy.memory.privacy import DataAnonymizer

anonymizer = DataAnonymizer(
    anonymization_rules=[
        {"pattern": r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", 
         "replacement": "[EMAIL]"},
        {"pattern": r"\\b\\d{3}-\\d{3}-\\d{4}\\b", 
         "replacement": "[PHONE]"},
        {"pattern": r"\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b", 
         "replacement": "[CREDIT_CARD]"}
    ],
    
    preserve_context=True,  # Maintain conversational flow
    reversible_anonymization=False  # One-way anonymization
)

# Apply anonymization to memory
anonymizer.anonymize_memory_content(agent.memory)
```

## 📊 Memory Analytics

### Usage Analytics
```python
from buddy.memory.analytics import MemoryAnalytics

analytics = MemoryAnalytics(
    metrics=[
        "memory_usage_patterns",
        "retrieval_success_rate",
        "information_decay_rate",
        "user_preference_evolution",
        "knowledge_accumulation_rate"
    ]
)

# Generate analytics report
usage_report = analytics.generate_usage_report()
print("Memory Usage Analytics:")
print(f"  Total memories stored: {usage_report['total_memories']:,}")
print(f"  Average retrieval time: {usage_report['avg_retrieval_time']:.3f}s")
print(f"  Memory hit rate: {usage_report['hit_rate']:.1%}")
print(f"  Storage efficiency: {usage_report['storage_efficiency']:.1%}")

# Memory growth trends
growth_analysis = analytics.analyze_memory_growth()
print("\\nMemory Growth Trends:")
print(f"  Weekly growth rate: {growth_analysis['weekly_growth_rate']:.1%}")
print(f"  Predicted storage need (30d): {growth_analysis['predicted_storage_mb']:.1f}MB")
```

### Quality Assessment
```python
from buddy.memory.quality import MemoryQualityAssessor

quality_assessor = MemoryQualityAssessor(
    quality_metrics=[
        "information_accuracy",
        "relevance_score",
        "completeness",
        "consistency",
        "freshness",
        "utility_score"
    ]
)

# Assess memory quality
quality_report = quality_assessor.assess_memory_quality(agent.memory)
print("Memory Quality Assessment:")
for metric, score in quality_report['scores'].items():
    print(f"  {metric}: {score:.2f}")

print("\\nRecommendations:")
for recommendation in quality_report['recommendations']:
    print(f"  - {recommendation}")
```

## 🎯 Advanced Memory Features

### Federated Memory
```python
from buddy.memory.federation import FederatedMemory

# Memory shared across multiple agent instances
federated_memory = FederatedMemory(
    agents=["agent_1", "agent_2", "agent_3"],
    
    # Sharing policies
    sharing_rules={
        "public_knowledge": "share_all",
        "user_preferences": "share_with_permission", 
        "private_conversations": "no_sharing",
        "learned_skills": "share_all"
    },
    
    # Conflict resolution
    conflict_resolution="latest_timestamp",  # or "voting", "authority_based"
    consistency_level="eventual"  # or "strong", "weak"
)
```

### Memory Dreams (Background Processing)
```python
from buddy.memory.dreams import MemoryDreams

# Background memory processing during idle time
memory_dreams = MemoryDreams(
    dream_activities=[
        "consolidate_memories",     # Strengthen important memories
        "find_patterns",           # Identify recurring patterns
        "resolve_inconsistencies", # Fix contradictory information
        "generate_insights",       # Create new knowledge from existing
        "optimize_structure"       # Reorganize for efficiency
    ],
    
    # Dream scheduling
    dream_trigger="idle_time",  # or "scheduled", "memory_pressure"
    min_idle_time="5_minutes",
    max_dream_duration="30_minutes"
)

agent.memory.enable_dreams(memory_dreams)
```

## 🛠️ Memory Customization

### Custom Memory Types
```python
from buddy.memory.base import BaseMemory

class TaskMemory(BaseMemory):
    \"\"\"Custom memory for tracking task execution patterns.\"\"\"
    
    def __init__(self):
        super().__init__()
        self.task_history = []
        self.performance_patterns = {}
    
    def store_task_execution(self, task_info: Dict):
        \"\"\"Store task execution details.\"\"\"
        self.task_history.append({
            "task_type": task_info["type"],
            "execution_time": task_info["duration"],
            "success": task_info["success"],
            "errors": task_info.get("errors", []),
            "timestamp": datetime.now()
        })
        
        # Update performance patterns
        task_type = task_info["type"]
        if task_type not in self.performance_patterns:
            self.performance_patterns[task_type] = {
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "common_errors": []
            }
        
        self._update_patterns(task_type, task_info)
    
    def recall_task_performance(self, task_type: str) -> Dict:
        \"\"\"Recall performance patterns for task type.\"\"\"
        return self.performance_patterns.get(task_type, {})

# Use custom memory
task_memory = TaskMemory()
agent.memory.add_memory_component(task_memory)
```

## 🏆 Best Practices

### Memory Design Principles
1. **Selective Storage**: Store information based on importance and relevance
2. **Efficient Retrieval**: Design for fast and accurate memory recall
3. **Privacy by Design**: Implement privacy protection from the start
4. **Graceful Degradation**: Handle memory limits and failures gracefully
5. **Context Awareness**: Consider context when storing and retrieving memories

### Performance Optimization
1. **Lazy Loading**: Load memories only when needed
2. **Caching Strategy**: Cache frequently accessed memories
3. **Batch Operations**: Process multiple memory operations together
4. **Asynchronous Processing**: Handle memory operations asynchronously
5. **Memory Hierarchy**: Use different storage tiers for different types of memories

The memory management system enables Buddy AI agents to maintain context, learn from experience, and provide increasingly personalized and effective assistance over time.