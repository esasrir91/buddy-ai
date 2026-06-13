from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union, Tuple
from collections import Counter
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity
import sqlite3
import os
import hashlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from buddy.document import Document
from buddy.knowledge.agent import AgentKnowledge
from buddy.utils.log import log_info, logger, log_debug


class irag(AgentKnowledge):
    """
    Intelligent Retrieval and Generation (iRAG) Knowledge Base
    
    An efficient knowledge base that combines NLP-based ontology mapping, TF-IDF vectorization,
    and cosine similarity for intelligent document search and retrieval.
    
    ENHANCED FOR COMPLETE RETRIEVAL:
    - Reduced default accuracy thresholds (50% instead of 75%) for broader results
    - Improved document chunking with overlapping context preservation
    - Multiple search strategies working in parallel instead of early termination
    - New comprehensive search method for maximum recall
    - More lenient similarity thresholds to catch relevant partial matches
    
    Features:
    - Automatic document ingestion from files or directories
    - NLP-based entity extraction and ontology mapping
    - Multiple search strategies (ontology, TF-IDF, basic text)
    - SQLite database backend for fast retrieval
    - Strict or flexible modes for agent integration
    - Support for various file formats
    - Enhanced retrieval completeness with comprehensive search
    
    Example Usage:
        # Create knowledge base from a single file
        kb = irag(file_path="logs/system.log")
        kb.load()
        
        # Create from directory with specific formats
        kb = irag(dir_path="documents/", formats=[".txt", ".log", ".md"])
        kb.load()
        
        # Standard search with improved defaults
        results = kb.search("error timeout database")
        for doc in results:
            print(f"Found: {doc.content[:100]}...")
        
        # Comprehensive search for maximum recall
        results = kb.search_comprehensive("connection issue", min_accuracy=25.0)
        
        # Create agent with strict KB mode
        kb = irag(file_path="support_docs.txt", strict_kb_mode=True)
        kb.load()
        agent = kb.create_agent(Agent, model=OpenAIChat())
        response = agent.run("What are the common issues?")
        
        # Get database statistics
        info = kb.get_database_info()
        print(f"Documents: {info['total_documents']}")
        
        # Debug search functionality
        kb.debug_search("connection failed")
    
    Available Methods:
        - search(query, num_documents=20): Search for relevant documents (improved defaults)
        - search_comprehensive(query): Maximum recall search with low thresholds
        - load(recreate=False): Load documents into the database
        - create_agent(agent_class, model): Create an agent using this KB
        - get_database_info(): Get statistics about the knowledge base
        - get_ontology_stats(): Get NLP ontology extraction statistics
        - debug_search(query): Debug why search results may be empty
        
    Parameters:
        file_path (str|Path): Path to a single file to ingest
        dir_path (str|Path): Path to a directory to ingest recursively
        path (str|Path|List): Legacy parameter for backwards compatibility
        db_path (str): SQLite database file path (default: "knowledge_database.db")
        formats (List[str]): File extensions to include (e.g., [".txt", ".log"])
        strict_kb_mode (bool): If True, agents must search KB before answering
        instructions (str): Custom instructions for agents using this KB
    """
    
    path: Optional[Union[str, Path, List[Dict[str, Union[str, Dict[str, Any]]]]]] = None
    file_path: Optional[Union[str, Path]] = None  # Explicit file path option
    dir_path: Optional[Union[str, Path]] = None   # Explicit directory path option
    db_path: str = "knowledge_database.db"
    formats: List[str] = []
    table_name: str = "documents"
    metadata_table_name: str = "document_metadata"
    ontology_table_name: str = "ontology_terms"
    instructions: Optional[str] = None  # Default instructions for agents using this KB
    retriever: Optional[Any] = True  # Dummy retriever to pass agent framework check
    strict_kb_mode: bool = False  # Controls whether agent must always search KB first
    max_workers: Optional[int] = None  # Number of parallel workers for ontology processing
    
    # NLP-based ontology mapping
    nlp_model: Optional[Any] = None
    
    # Efficient cosine similarity
    tfidf_vectorizer: Optional[Any] = None
    document_vectors: Optional[np.ndarray] = None
    document_ids: List[str] = []

    def __init__(self, 
                 file_path: Optional[Union[str, Path]] = None,
                 dir_path: Optional[Union[str, Path]] = None, 
                 path: Optional[Union[str, Path, List[Dict[str, Union[str, Dict[str, Any]]]]]] = None,
                 db_path: str = "knowledge_database.db",
                 formats: Optional[List[str]] = None,
                 strict_kb_mode: bool = False,
                 instructions: Optional[str] = None,
                 max_workers: Optional[int] = None,
                 **kwargs):
        """
        Initialize the iRAG knowledge base.
        
        Args:
            file_path (str|Path, optional): Path to a single file to ingest
            dir_path (str|Path, optional): Path to directory to ingest recursively  
            path (str|Path|List, optional): Legacy parameter for backwards compatibility
            db_path (str, optional): SQLite database path. Defaults to "knowledge_database.db"
            formats (List[str], optional): File extensions to include (e.g., [".txt", ".log"])
            strict_kb_mode (bool, optional): Force agents to search KB first. Defaults to False
            instructions (str, optional): Custom instructions for agents using this KB
            max_workers (int, optional): Number of parallel workers for ontology processing. Defaults to CPU count
            
        Examples:
            # Single file
            kb = irag(file_path="system.log")
            
            # Directory with format filtering
            kb = irag(dir_path="logs/", formats=[".log", ".txt"])
            
            # Strict mode for knowledge-only responses
            kb = irag(file_path="docs.txt", strict_kb_mode=True)
            
            # Custom database location
            kb = irag(dir_path="data/", db_path="custom_kb.db")
        """
        # Combine explicit parameters with any additional kwargs
        data = {
            'file_path': file_path,
            'dir_path': dir_path,
            'path': path,
            'db_path': db_path,
            'formats': formats or [],
            'strict_kb_mode': strict_kb_mode,
            'instructions': instructions,
            'max_workers': max_workers or min(mp.cpu_count(), 8),  # Default to CPU count, max 8
            **kwargs
        }
        super().__init__(**data)
        self.document_ids = []
        
        # Handle path resolution - prioritize explicit file_path/dir_path over generic path
        self._resolve_paths(**data)
        
        # Set strict KB mode
        self.strict_kb_mode = data.get('strict_kb_mode', False)
        
        # Set max_workers for parallel processing
        self.max_workers = data.get('max_workers', min(mp.cpu_count(), 8))
        
        # Set instructions - always use iRAG's own instructions
        if 'instructions' in data and data['instructions'] is not None:
            # Allow custom instructions but warn they override KB behavior
            self.instructions = data['instructions']
            #log_info("⚠️  Using custom instructions - this may override iRAG KB behavior")
        else:
            # Use iRAG's default instructions based on mode
            self.instructions = self.get_default_instructions()
            #log_info(f"📋 Using iRAG {'strict' if self.strict_kb_mode else 'flexible'} mode instructions")
        # Add dummy retriever so agent framework calls our search method
        self.retriever = True  # Dummy value to pass agent framework check
        self._init_database()
        self._init_nlp()
    
    def get_kb_instructions(self) -> str:
        """Get instructions that should be used by any agent using this KB"""
        return self.instructions
    
    def configure_agent_instructions(self, agent) -> None:
        """Configure an agent to use this KB's instructions"""
        if hasattr(agent, 'instructions'):
            agent.instructions = self.instructions
        return agent
    
    def create_agent(self, agent_class, model, **agent_kwargs):
        """
        Create an AI agent properly configured to use this iRAG knowledge base.
        
        The agent will be configured with appropriate instructions based on the KB mode
        (strict or flexible) and will have access to the search_knowledge_base function.
        
        Args:
            agent_class: Agent class to instantiate (e.g., Agent)
            model: Language model to use (e.g., OpenAIChat(), ClaudeChat())
            **agent_kwargs: Additional arguments passed to agent constructor
            
        Returns:
            Agent: Configured agent instance ready to use the knowledge base
            
        Examples:
            # Create agent with OpenAI
            from buddy.models.openai import OpenAIChat
            from buddy.agent import Agent
            
            kb = irag(file_path="support_docs.txt", strict_kb_mode=True)
            kb.load()
            agent = kb.create_agent(Agent, OpenAIChat())
            
            # Ask questions that will search the KB
            response = agent.run("What are the known issues with login?")
            print(response.content)
            
            # Create with custom agent settings
            agent = kb.create_agent(
                Agent, 
                OpenAIChat(),
                name="Support Assistant",
                description="Expert in troubleshooting"
            )
            
        Note:
            - In strict_kb_mode=True, agent must search KB before answering
            - In strict_kb_mode=False, agent can supplement KB with general knowledge
        """
        # Ensure the agent uses iRAG's instructions
        agent_params = {
            "knowledge": self,
            "instructions": self.instructions,  # Always use iRAG's instructions
            "search_knowledge": self.strict_kb_mode,  # Enable search in strict mode
            "model": model,
            **agent_kwargs
        }
        
        agent = agent_class(**agent_params)
        #log_info(f"🤖 Created agent with iRAG {'strict' if self.strict_kb_mode else 'flexible'} mode")
        return agent
    
    def _resolve_paths(self, **data):
        """Resolve and validate file/directory paths from initialization parameters"""
        # Priority: file_path > dir_path > path (for backwards compatibility)
        if 'file_path' in data and data['file_path'] is not None:
            file_path = Path(data['file_path'])
            if not file_path.exists():
                raise ValueError(f"File not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            self.path = file_path
            #log_info(f"📄 iRAG initialized with file: {file_path}")
            
        elif 'dir_path' in data and data['dir_path'] is not None:
            dir_path = Path(data['dir_path'])
            if not dir_path.exists():
                raise ValueError(f"Directory not found: {dir_path}")
            if not dir_path.is_dir():
                raise ValueError(f"Path is not a directory: {dir_path}")
            self.path = dir_path
            #log_info(f"📁 iRAG initialized with directory: {dir_path}")
            
        elif 'path' in data and data['path'] is not None:
            # Backwards compatibility - use existing path parameter
            self.path = data['path']
            log_info(f"🔄 iRAG initialized with path: {self.path}")
            
        else:
            raise ValueError("Must specify either file_path, dir_path, or path parameter")
    
    def get_default_instructions(self) -> str:
        """Get default instructions for agents using this knowledge base"""
        if self.strict_kb_mode:
            # Strict mode - force KB searching for 100% accuracy
            return """
            You are an intelligent knowledge base assistant optimized for 100% ACCURATE and COMPLETE answers.

            MANDATORY SEARCH PROTOCOL FOR 100% ACCURACY:
            1. For EVERY user question, you MUST call search_knowledge_base with the user's exact query
            2. If results seem incomplete, IMMEDIATELY call search_comprehensive for maximum coverage
            3. For complex questions, break them down and search each component separately
            4. Search using multiple variations of key terms to ensure nothing is missed
            5. Continue searching until you have comprehensive coverage of the topic
            6. NEVER stop searching if the answer seems incomplete or partial

            COMPLETENESS REQUIREMENTS:
            1. You MUST provide COMPLETE answers based on ALL available information in the knowledge base
            2. If multiple documents contain relevant information, synthesize ALL of them into your response
            3. Include specific details, examples, and context from the search results
            4. Quote relevant sections to demonstrate completeness
            5. If information spans multiple files/sources, combine everything into one comprehensive answer
            6. NEVER give partial answers - if you find some information, search for more related content

            ACCURACY REQUIREMENTS:
            1. Base your answers ONLY on information found in search_knowledge_base results
            2. Quote exact text when providing specific details or technical information
            3. Maintain exact technical terms, numbers, and specifications from the source
            4. If sources contradict each other, present all versions and note the discrepancy
            5. NEVER add, modify, or interpret information beyond what is explicitly stated

            ANSWER STRUCTURE:
            - Always search comprehensively first
            - Provide complete, detailed answers that fully address the question
            - Include all relevant information found in the knowledge base
            - Use specific quotes and references
            - If information is spread across multiple sources, synthesize it completely
            - End with confirmation that you've covered all available information

            Remember: Your goal is 100% ACCURATE and 100% COMPLETE answers. Never settle for partial responses.
            """
        else:
            # Flexible mode but still emphasize completeness
            return """
            You are a helpful AI assistant with access to a comprehensive knowledge base, optimized for complete and accurate responses.
            
            When answering questions:
            1. Always search the knowledge base comprehensively first using search_knowledge_base
            2. Use search_comprehensive for complex questions requiring maximum coverage
            3. Provide complete, detailed answers that address all aspects of the question
            4. Supplement knowledge base results with your general knowledge when helpful, but clearly distinguish sources
            5. For technical or specific questions, prioritize knowledge base information for accuracy
            6. Always aim for completeness - if the answer seems partial, search for additional related information
            
            Your goal is to provide the most accurate and complete information possible.
            """

    def search(self, query: str, num_documents: Optional[int] = None, filters: Optional[Dict[str, Any]] = None, search_method: str = "all", accuracy: float = 0.0) -> List['Document']:
        """
        Search the knowledge base using multiple intelligent search strategies.
        
        Combines ontology-based matching, TF-IDF cosine similarity, and basic text search
        to find the most relevant documents for your query.
        
        Args:
            query (str): Search query (e.g., "database connection error timeout")
            num_documents (int, optional): Maximum documents to return. Defaults to 10
            filters (Dict[str, Any], optional): Additional search filters (not implemented)
            search_method (str, optional): Search strategy to use. Options:
                - "all" (default): Use all search methods for best results
                - "ontology": Use only NLP-based ontology matching
                - "tfidf": Use only TF-IDF cosine similarity
                - "basic": Use only basic text search
            accuracy (float, optional): Minimum match accuracy as percentage (0-100). Defaults to 75.0
                Higher values = stricter matching, lower values = broader results
            
        Returns:
            List[Document]: List of relevant documents sorted by relevance
            
        Examples:
            # Simple search with default 75% accuracy
            results = kb.search("error message")
            
            # High accuracy search (strict matching)
            results = kb.search("database error", accuracy=90.0)
            
            # Low accuracy search (broad results)
            results = kb.search("connection issue", accuracy=50.0)
            
            # Use specific method with custom accuracy
            results = kb.search("login failed", search_method="tfidf", accuracy=85.0)
            
            # Process results with accuracy scores
            for doc in kb.search("error code", accuracy=80.0):
                print(f"File: {doc.meta_data.get('source', 'unknown')}")
                print(f"Accuracy: {doc.meta_data.get('match_accuracy', 'N/A')}")
                print(f"Content: {doc.content[:200]}...")
        """
        print("🔎 Searching the Knowledge Base...")
        
        try:
            _num_documents = num_documents or 100  # Massive increase for complete coverage
            all_results = []
            used_doc_ids = set()
            
            # Validate search_method parameter
            valid_methods = ["all", "ontology", "tfidf", "basic"]
            if search_method not in valid_methods:
                logger.warning(f"Invalid search_method '{search_method}'. Using 'all' instead. Valid options: {valid_methods}")
                search_method = "all"
            
            # For 100% accuracy, set minimum possible thresholds
            accuracy = max(0.0, min(100.0, accuracy))
            similarity_threshold = 0.001  # Extremely low threshold for maximum recall
            
            # Method 1: Ontology-enhanced search
            if search_method in ["all", "ontology"]:
                query_ontology = self._extract_query_ontology(query)
                if query_ontology:
                    ontology_results = self._search_by_ontology_match(query, query_ontology, _num_documents, accuracy)
                    for doc in ontology_results:
                        if doc.id not in used_doc_ids:
                            doc.meta_data['search_method'] = 'ontology'
                            all_results.append(doc)
                            used_doc_ids.add(doc.id)
                            
                    # If using only ontology search and we have results, return them
                    if search_method == "ontology":
                        return all_results[:_num_documents]
            
            # Method 2: TF-IDF search - ALWAYS RUN for semantic completeness
            tfidf_results = self.search_tfidf(query, num_documents=_num_documents * 5, similarity_threshold=0.001, accuracy_percent=0.0)
            for doc in tfidf_results:
                if doc.id not in used_doc_ids:
                    all_results.append(doc)
                    used_doc_ids.add(doc.id)
                    
            # If using only TF-IDF search, still add other methods for completeness
            if search_method == "tfidf":
                basic_results = self.search_basic(query, num_documents=_num_documents, accuracy_percent=0.0)
                for doc in basic_results:
                    if doc.id not in used_doc_ids:
                        all_results.append(doc)
                        used_doc_ids.add(doc.id)
            
            # Method 3: Basic search - ALWAYS RUN for exact matches
            basic_results = self.search_basic(query, num_documents=_num_documents * 5, accuracy_percent=0.0)
            for doc in basic_results:
                if doc.id not in used_doc_ids:
                    all_results.append(doc)
                    used_doc_ids.add(doc.id)
                    
            # Method 4: Fuzzy/partial term search for completeness
            fuzzy_results = self._search_fuzzy_terms(query, num_documents=_num_documents * 2)
            for doc in fuzzy_results:
                if doc.id not in used_doc_ids:
                    all_results.append(doc)
                    used_doc_ids.add(doc.id)
            
            # Return best results (prioritize by search method quality)
            return all_results[:_num_documents]
                
        except Exception as e:
            logger.error(f"iRAG search error: {e}")
            # Emergency fallback - try basic search only
            try:
                return self.search_basic(query, num_documents or 5)
            except:
                return []
    
    def search_comprehensive(self, query: str, num_documents: Optional[int] = None, 
                           include_scores: bool = True, min_accuracy: float = 0.0) -> List['Document']:
        """
        ULTRA-COMPREHENSIVE search optimized for 100% accurate and complete answers.
        
        This method is designed to find EVERY relevant piece of information by:
        1. Using NO accuracy thresholds (0% minimum)
        2. Combining ALL search methods with maximum results
        3. Including fuzzy/partial matches for completeness
        4. Providing detailed scoring information
        5. Searching with query variations and expansions
        
        Args:
            query (str): Search query
            num_documents (int, optional): Maximum documents to return. Defaults to 200 for maximum coverage
            include_scores (bool): Include detailed scoring in metadata. Defaults to True
            min_accuracy (float): Minimum accuracy threshold (0-100). Defaults to 0.0 for maximum recall
            
        Returns:
            List[Document]: Ultra-comprehensive list of ALL relevant documents with detailed scoring
            
        Examples:
            # Get maximum comprehensive results
            results = kb.search_comprehensive("database error timeout")
            
            # Maximum coverage for complex topics
            results = kb.search_comprehensive("system architecture", num_documents=500)
        """
        print("🚀 Performing ULTRA-COMPREHENSIVE search for 100% complete coverage...")
        
        _num_documents = num_documents or 200  # Massive default for complete coverage
        all_results = []
        used_doc_ids = set()
        
        try:
            # Search with original query - ALL methods
            original_results = self.search(query, num_documents=_num_documents, accuracy=0.0)
            for doc in original_results:
                if doc.id not in used_doc_ids:
                    if include_scores:
                        doc.meta_data['search_priority'] = 'original_query'
                    all_results.append(doc)
                    used_doc_ids.add(doc.id)
            
            # Search with individual terms for completeness
            query_words = [word.strip() for word in query.split() if len(word.strip()) > 2]
            for word in query_words:
                if len(all_results) < _num_documents * 2:  # Allow massive results
                    word_results = self.search(word, num_documents=_num_documents // 2, accuracy=0.0)
                    for doc in word_results:
                        if doc.id not in used_doc_ids:
                            if include_scores:
                                doc.meta_data['search_priority'] = f'individual_term_{word}'
                            all_results.append(doc)
                            used_doc_ids.add(doc.id)
            
            # Fuzzy/partial search for missed content
            fuzzy_results = self._search_fuzzy_terms(query, num_documents=_num_documents)
            for doc in fuzzy_results:
                if doc.id not in used_doc_ids:
                    if include_scores:
                        doc.meta_data['search_priority'] = 'fuzzy_partial'
                    all_results.append(doc)
                    used_doc_ids.add(doc.id)
            
            # Additional ontology-only search to catch missed entities
            query_ontology = self._extract_query_ontology(query)
            if query_ontology:
                extra_ontology = self._search_by_ontology_match(query, query_ontology, _num_documents * 2, 0.0)
                for doc in extra_ontology:
                    if doc.id not in used_doc_ids:
                        if include_scores:
                            doc.meta_data['search_priority'] = 'extra_ontology'
                        all_results.append(doc)
                        used_doc_ids.add(doc.id)
            
            # Sort by relevance but preserve all results
            def get_sort_key(doc):
                priority_order = {
                    'original_query': 5, 
                    'extra_ontology': 4,
                    'individual_term': 3,
                    'fuzzy_partial': 2,
                    'fallback': 1
                }
                
                search_priority = doc.meta_data.get('search_priority', 'fallback')
                priority_base = priority_order.get(search_priority.split('_')[0], 1)
                
                # Extract numeric accuracy if available
                accuracy_str = doc.meta_data.get('match_accuracy', '0%')
                try:
                    accuracy = float(accuracy_str.replace('%', ''))
                except:
                    accuracy = 0
                
                cosine_sim = doc.meta_data.get('cosine_similarity', 0)
                ontology_matches = doc.meta_data.get('ontology_matches', 0)
                
                return (priority_base, accuracy, cosine_sim, ontology_matches)
            
            all_results.sort(key=get_sort_key, reverse=True)
            
            if include_scores:
                log_info(f"🎯 ULTRA-COMPREHENSIVE search found {len(all_results)} total results for 100% coverage")
                
            return all_results[:_num_documents]
            
        except Exception as e:
            logger.error(f"Error in ultra-comprehensive search: {e}")
            # Ultimate fallback - return everything we can find
            try:
                return self.search(query, num_documents=_num_documents, accuracy=0.0)
            except:
                return []

    def _extract_query_ontology(self, query: str) -> List[str]:
        """Extract key entities/terms from user query using NLP"""
        if not SPACY_AVAILABLE or self.nlp_model is None:
            return []
        
        try:
            doc = self.nlp_model(query.lower())
            entities = []
            
            # Extract named entities
            for ent in doc.ents:
                entities.append(ent.text.lower())
            
            # Extract important noun phrases, keywords, and action verbs  
            verbs_found = []
            for token in doc:
                if (token.pos_ in ['NOUN', 'PROPN', 'VERB'] and 
                    not token.is_stop and 
                    len(token.text) > 1 and
                    # Filter out common/generic verbs for better precision
                    (token.pos_ != 'VERB' or token.lemma_.lower() not in ['be', 'have', 'do', 'get', 'go', 'say', 'see', 'know', 'think', 'take', 'come', 'give', 'look', 'use', 'find', 'want', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call'])):
                    entities.append(token.lemma_.lower())
                    if token.pos_ == 'VERB':
                        verbs_found.append(token.lemma_.lower())
                        
            # Also add the original query terms
            query_words = [word.lower() for word in query.split() if len(word) > 1]
            entities.extend(query_words)
            
            unique_entities = list(set(entities))  # Remove duplicates
            return unique_entities
            
        except Exception as e:
            logger.error(f"Error extracting query ontology: {e}")
            return []

    def _search_by_ontology_match(self, query: str, query_entities: List[str], num_documents: int, accuracy_percent: float = 0.0) -> List['Document']:
        """Search using ontology term matching with accuracy scoring"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find documents that contain matching ontology terms
            placeholders = ','.join('?' * len(query_entities))
            
            query_sql = f"""
                SELECT DISTINCT d.doc_id, d.content, d.meta_data, 
                       COUNT(m.term) as match_count
                FROM {self.table_name} d
                JOIN {self.ontology_table_name}_mapping m ON d.doc_id = m.doc_id
                WHERE m.term IN ({placeholders})
                GROUP BY d.doc_id, d.content, d.meta_data
                ORDER BY match_count DESC, d.doc_id
                LIMIT ?
            """
            
            cursor.execute(query_sql, query_entities + [num_documents])
            results = cursor.fetchall()
            conn.close()
            
            documents = []
            for row in results:
                doc_id, content, metadata_str, match_count = row
                
                # Parse metadata
                metadata = {}
                if metadata_str:
                    try:
                        import json
                        metadata = json.loads(metadata_str)
                    except:
                        pass
                
                # Calculate accuracy as percentage of matched terms
                total_query_terms = len(query_entities)
                match_accuracy = (match_count / total_query_terms * 100) if total_query_terms > 0 else 0
                
                # Include ALL matches for 100% completeness - no accuracy filtering
                metadata['ontology_matches'] = match_count
                metadata['match_accuracy'] = f"{match_accuracy:.1f}%"
                metadata['search_method'] = 'ontology'
                metadata['matched_query'] = query
                
                doc = Document(
                    id=doc_id,
                    content=content,
                    meta_data=metadata
                )
                documents.append(doc)
                
            return documents
            
        except Exception as e:
            logger.error(f"Error in ontology search: {e}")
            # Fallback to basic search
            if hasattr(self, 'search_basic'):
                return self.search_basic(query, num_documents=num_documents)
            return []
    
    def _search_fuzzy_terms(self, query: str, num_documents: Optional[int] = None) -> List['Document']:
        """
        Fuzzy search for partial matches, word variations, and related terms.
        This method ensures maximum completeness by finding content that might be
        related but doesn't exactly match the query terms.
        """
        if not query.strip():
            return []
            
        _num_documents = num_documents or 50
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        documents = []
        used_doc_ids = set()
        
        try:
            # Extract individual words and create variations
            words = query.lower().split()
            search_patterns = []
            
            # Add original words
            search_patterns.extend(words)
            
            # Add partial matches (3+ character substrings)
            for word in words:
                if len(word) >= 4:
                    # Add prefixes and suffixes for partial matching
                    search_patterns.append(word[:3] + '%')  # Prefix match
                    search_patterns.append('%' + word[-3:])  # Suffix match
                    search_patterns.append('%' + word[1:-1] + '%')  # Contains core
            
            # Search for each pattern
            for pattern in search_patterns[:20]:  # Limit to prevent excessive queries
                if len(documents) >= _num_documents:
                    break
                    
                try:
                    cursor.execute(f"""
                        SELECT doc_id, content, meta_data 
                        FROM {self.table_name} 
                        WHERE LOWER(content) LIKE ? 
                        AND doc_id NOT IN ({','.join(['?'] * len(used_doc_ids)) if used_doc_ids else 'NULL'})
                        ORDER BY LENGTH(content) ASC 
                        LIMIT ?
                    """, [f"%{pattern.replace('%', '')}%"] + list(used_doc_ids) + [_num_documents - len(documents)])
                    
                    for row in cursor.fetchall():
                        if len(documents) >= _num_documents:
                            break
                        doc_id, content, metadata_str = row
                        if doc_id not in used_doc_ids:
                            metadata = self._parse_metadata(metadata_str)
                            metadata['search_method'] = 'fuzzy_partial'
                            metadata['matched_pattern'] = pattern
                            metadata['matched_query'] = query
                            metadata['match_type'] = 'partial'
                            documents.append(Document(id=doc_id, content=content, meta_data=metadata))
                            used_doc_ids.add(doc_id)
                except Exception as e:
                    # Skip problematic patterns
                    continue
                        
        except Exception as e:
            logger.error(f"Error in fuzzy search: {e}")
        finally:
            conn.close()
            
        return documents[:_num_documents]
    
    def search_basic(self, query: str, num_documents: Optional[int] = None, accuracy_percent: float = 0.0) -> List['Document']:
        """Enhanced basic search using multiple SQL strategies with accuracy scoring"""
        if not query.strip():
            return []
            
        _num_documents = num_documents or 10
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        documents = []
        used_doc_ids = set()
        
        try:
            # Strategy 1: Exact phrase search
            cursor.execute(f"""
                SELECT doc_id, content, meta_data 
                FROM {self.table_name} 
                WHERE LOWER(content) LIKE ? 
                ORDER BY doc_id 
                LIMIT ?
            """, (f"%{query.lower()}%", _num_documents))
            
            for row in cursor.fetchall():
                doc_id, content, metadata_str = row
                if doc_id not in used_doc_ids:
                    metadata = self._parse_metadata(metadata_str)
                    
                    # Calculate accuracy for exact phrase match (100% for exact match)
                    match_accuracy = 100.0
                    
                    if match_accuracy >= accuracy_percent:
                        metadata['search_method'] = 'basic_exact'
                        metadata['match_accuracy'] = f"{match_accuracy:.1f}%"
                        metadata['matched_query'] = query
                        documents.append(Document(id=doc_id, content=content, meta_data=metadata))
                        used_doc_ids.add(doc_id)
            
            # Strategy 2: Individual terms search (if not enough results)
            if len(documents) < _num_documents:
                search_terms = [term.strip().lower() for term in query.split() if len(term.strip()) > 1]
                if search_terms:
                    for term in search_terms:
                        if len(documents) >= _num_documents:
                            break
                            
                        cursor.execute(f"""
                            SELECT doc_id, content, meta_data 
                            FROM {self.table_name} 
                            WHERE LOWER(content) LIKE ? 
                            AND doc_id NOT IN ({','.join(['?'] * len(used_doc_ids)) if used_doc_ids else 'NULL'})
                            ORDER BY doc_id 
                            LIMIT ?
                        """, [f"%{term}%"] + list(used_doc_ids) + [_num_documents - len(documents)])
                        
                        for row in cursor.fetchall():
                            doc_id, content, metadata_str = row
                            if doc_id not in used_doc_ids:
                                metadata = self._parse_metadata(metadata_str)
                                
                                # Calculate accuracy but don't filter - include ALL matches
                                content_lower = content.lower()
                                term_matches = sum(1 for t in search_terms if t in content_lower)
                                match_accuracy = (term_matches / len(search_terms) * 100) if search_terms else 0
                                
                                # Include ALL matches for 100% completeness
                                metadata['search_method'] = 'basic_terms'
                                metadata['match_accuracy'] = f"{match_accuracy:.1f}%"
                                metadata['matched_query'] = query
                                metadata['matched_term'] = term
                                documents.append(Document(id=doc_id, content=content, meta_data=metadata))
                                used_doc_ids.add(doc_id)
                                if len(documents) >= _num_documents:
                                    break
                    
        except Exception as e:
            logger.error(f"Error in basic search: {e}")
        finally:
            conn.close()
            
        return documents[:_num_documents]

    def search_tfidf(self, query: str, num_documents: Optional[int] = None, 
                     similarity_threshold: float = 0.001, accuracy_percent: float = 0.0) -> List[Document]:
        """Enhanced TF-IDF search with better error handling and percentage accuracy display"""
        if not query.strip():
            return []
            
        _num_documents = num_documents or 10
        
        try:
            # Build TF-IDF vectors if not already built
            self._build_tfidf_vectors()
            
            if self.tfidf_vectorizer is None or self.document_vectors is None:
                return []  # TF-IDF not available, caller should try basic search
            
            # Get similarities
            similarities = self._calculate_cosine_similarity(query, _num_documents * 2)
            
            if not similarities:
                return []
            
            # Filter by threshold and get documents - batch retrieval for performance
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            documents = []
            try:
                # Collect all valid doc_ids first
                valid_doc_ids = [doc_id for doc_id, similarity in similarities if similarity >= similarity_threshold]
                
                if valid_doc_ids:
                    # Batch retrieve all documents at once
                    placeholders = ','.join('?' * len(valid_doc_ids[:_num_documents]))
                    cursor.execute(
                        f"SELECT doc_id, filepath, filename, content, meta_data FROM {self.table_name} WHERE doc_id IN ({placeholders})",
                        valid_doc_ids[:_num_documents]
                    )
                    results = cursor.fetchall()
                    
                    # Create a lookup for similarities
                    similarity_lookup = {doc_id: sim for doc_id, sim in similarities}
                    
                    for result in results:
                    
                        doc_id, filepath, filename, content, meta_data_str = result
                        meta_data = self._parse_metadata(meta_data_str)
                        
                        # Add similarity score and search method to metadata
                        similarity = similarity_lookup.get(doc_id, 0.0)
                        match_accuracy = similarity * 100  # Convert to percentage
                        
                        meta_data['cosine_similarity'] = similarity  # Keep raw score for sorting
                        meta_data['match_accuracy'] = f"{match_accuracy:.1f}%"  # User-friendly percentage
                        meta_data['search_method'] = 'tfidf'
                        meta_data['matched_query'] = query
                        
                        documents.append(Document(
                            id=doc_id,
                            content=content,
                            meta_data=meta_data
                        ))
                    
                    # Sort by similarity score
                    documents.sort(key=lambda x: x.meta_data.get('cosine_similarity', 0), reverse=True)
                    documents = documents[:_num_documents]
                            
            except Exception as e:
                logger.error(f"Error retrieving TF-IDF search results: {e}")
            finally:
                conn.close()
                
            return documents
            
        except Exception as e:
            logger.error(f"Error in TF-IDF search: {e}")
            return []
    
    def _parse_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """Helper to safely parse metadata string"""
        if not metadata_str:
            return {}
        try:
            import json
            return json.loads(metadata_str)
        except:
            try:
                return eval(metadata_str)
            except:
                return {}
    
    def debug_search(self, query: str) -> None:
        """
        Debug search functionality by showing database contents and query matching.
        
        Useful for troubleshooting when search returns no results or unexpected results.
        Displays information about total documents, matching documents, and sample content.
        
        Args:
            query (str): The search query to debug
            
        Examples:
            # Debug why no results found
            results = kb.search("connection timeout")
            if not results:
                kb.debug_search("connection timeout")
                
            # Check what's in the database
            kb.debug_search("")
            
            # Debug specific terms
            kb.debug_search("error")
            kb.debug_search("database")
            
        Output includes:
            - Total documents in database
            - Number of documents containing the query term
            - Sample document content from the database
            - Helps identify if the issue is with loading or searching
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check total documents
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            doc_count = cursor.fetchone()[0]
            print(f"DEBUG: Total documents in DB: {doc_count}")
            
            # Check if any documents contain the query term
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE LOWER(content) LIKE ?", (f"%{query.lower()}%",))
            matching_count = cursor.fetchone()[0]
            print(f"DEBUG: Documents containing '{query}': {matching_count}")
            
            # Show first few documents if any exist
            cursor.execute(f"SELECT content FROM {self.table_name} LIMIT 3")
            sample_docs = cursor.fetchall()
            print(f"DEBUG: Sample documents:")
            for i, doc in enumerate(sample_docs):
                content = doc[0][:100] + "..." if len(doc[0]) > 100 else doc[0]
                print(f"  {i+1}: {content}")
                
        except Exception as e:
            print(f"DEBUG: Error checking database: {e}")
        finally:
            conn.close()
    
    def _init_nlp(self) -> None:
        """Initialize spaCy NLP for efficient ontology mapping"""
        if not SPACY_AVAILABLE:
            return
        
        try:
            self.nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            pass

    def _init_database(self) -> None:
        """Initialize SQLite database with essential tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Documents table
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT,
                    filepath TEXT,
                    filename TEXT,
                    content TEXT,
                    chunk_index INTEGER,
                    meta_data TEXT
                )
            ''')
            
            # Metadata table for file tracking
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.metadata_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE,
                    file_hash TEXT,
                    last_modified REAL,
                    last_ingested TEXT,
                    file_size INTEGER
                )
            ''')
            
            # Check if ontology table exists and has correct schema
            cursor.execute(f"PRAGMA table_info({self.ontology_table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if not columns or 'entity_type' not in columns:
                # Drop and recreate ontology table with correct schema
                cursor.execute(f'DROP TABLE IF EXISTS {self.ontology_table_name}')
            
            # NLP-extracted ontology terms
            # Document-Term mapping table (many-to-many)
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.ontology_table_name}_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT,
                    term TEXT,
                    FOREIGN KEY(doc_id) REFERENCES {self.table_name}(doc_id)
                )
            ''')
            
            # Original ontology table for global stats
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.ontology_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE,
                    entity_type TEXT,
                    frequency INTEGER,
                    document_count INTEGER,
                    contexts TEXT,
                    created_at TEXT
                )
            ''')
            
            # Essential indexes
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_content ON {self.table_name}(content)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_filepath ON {self.table_name}(filepath)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_doc_term ON {self.ontology_table_name}_mapping(doc_id, term)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_doc_id ON {self.table_name}(doc_id)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_ontology_term ON {self.ontology_table_name}(term)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_ontology_type ON {self.ontology_table_name}(entity_type)')
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate MD5 hash of a file to detect changes"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    def _is_valid_file(self, path: Path) -> bool:
        """Helper to check if path is a valid file with supported format"""
        if not (path.exists() and path.is_file()):
            return False
        if not self.formats:
            return True
        return path.suffix in self.formats

    @staticmethod
    def _extract_ontology_batch(doc_batch: List[Tuple[str, str]]) -> List[Tuple[str, List[Tuple[str, str, List[str]]]]]:
        """
        Static method for parallel ontology extraction from a batch of documents.
        Returns list of (doc_id, ontology_terms) tuples.
        """
        if not SPACY_AVAILABLE:
            return []
        
        try:
            # Load spaCy model in each worker process
            import spacy
            nlp_model = spacy.load("en_core_web_sm")
        except (OSError, ImportError):
            return []
        
        results = []
        for doc_id, text in doc_batch:
            try:
                doc = nlp_model(text)
                ontology_terms = []
                
                # Extract named entities
                for ent in doc.ents:
                    if len(ent.text.strip()) > 2:
                        contexts = [sent.text.strip() for sent in doc.sents if ent.text in sent.text]
                        ontology_terms.append((ent.text.lower(), ent.label_, contexts[:3]))
                
                # Extract noun phrases
                for chunk in doc.noun_chunks:
                    if len(chunk.text.strip()) > 3 and chunk.root.pos_ == 'NOUN':
                        contexts = [sent.text.strip() for sent in doc.sents if chunk.text in sent.text]
                        ontology_terms.append((chunk.text.lower(), 'CONCEPT', contexts[:2]))
                
                # Extract verbs for actions
                for token in doc:
                    if (token.pos_ == 'VERB' and 
                        not token.is_stop and 
                        len(token.lemma_) > 2 and
                        token.lemma_.lower() not in ['be', 'have', 'do', 'get', 'go', 'say', 'see', 'know', 'think', 'take', 'come', 'give', 'look', 'use', 'find', 'want', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call']):
                        verb_lemma = token.lemma_.lower()
                        contexts = [sent.text.strip() for sent in doc.sents if token.text in sent.text]
                        ontology_terms.append((verb_lemma, 'ACTION', contexts[:2]))
                
                results.append((doc_id, ontology_terms))
                
            except Exception as e:
                # Skip problematic documents
                continue
        
        return results
    
    def _extract_ontology_with_nlp(self, text: str) -> List[Tuple[str, str, List[str]]]:
        """Extract ontology terms using NLP entity recognition"""
        if not self.nlp_model:
            return []
        
        try:
            doc = self.nlp_model(text)
            ontology_terms = []
            
            # Extract named entities
            for ent in doc.ents:
                if len(ent.text.strip()) > 1:  # Reduced threshold to catch short award names
                    contexts = [sent.text.strip() for sent in doc.sents if ent.text in sent.text]
                    ontology_terms.append((ent.text.lower(), ent.label_, contexts[:3]))
            
            # Extract noun phrases for domain terms
            for chunk in doc.noun_chunks:
                if len(chunk.text.strip()) > 1 and chunk.root.pos_ == 'NOUN':
                    contexts = [sent.text.strip() for sent in doc.sents if chunk.text in sent.text]
                    ontology_terms.append((chunk.text.lower(), 'CONCEPT', contexts[:2]))
            
            # Extract verbs for actions and processes
            for token in doc:
                if (token.pos_ == 'VERB' and 
                    not token.is_stop and 
                    len(token.lemma_) > 2 and
                    token.lemma_.lower() not in ['be', 'have', 'do', 'get', 'go', 'say', 'see', 'know', 'think', 'take', 'come', 'give', 'look', 'use', 'find', 'want', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call']):  # Filter common/generic verbs
                    verb_lemma = token.lemma_.lower()
                    contexts = [sent.text.strip() for sent in doc.sents if token.text in sent.text]
                    ontology_terms.append((verb_lemma, 'ACTION', contexts[:2]))
            
            return ontology_terms
            
        except Exception as e:
            logger.error(f"Error in NLP ontology extraction: {e}")
            return []
    
    def _store_ontology_nlp(self, documents: List[Document], file_path: Path) -> None:
        """Store NLP-extracted ontology terms in database using parallel processing"""
        if not documents:
            return
        
        #log_info(f"📊 Processing {len(documents)} documents for ontology extraction with {self.max_workers} workers")
        
        try:
            # Prepare document batches for parallel processing
            doc_data = [(doc.id, doc.content) for doc in documents]
            batch_size = max(1, len(doc_data) // self.max_workers)
            batches = [doc_data[i:i + batch_size] for i in range(0, len(doc_data), batch_size)]
            
            all_results = []
            
            if SPACY_AVAILABLE and len(documents) > 10:  # Use parallel processing for larger document sets
                try:
                    # Use ProcessPoolExecutor for CPU-intensive NLP work
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Submit all batches
                        future_to_batch = {executor.submit(self._extract_ontology_batch, batch): batch for batch in batches}
                        
                        # Collect results as they complete
                        for future in as_completed(future_to_batch):
                            try:
                                batch_results = future.result(timeout=120)  # 2 min timeout per batch
                                all_results.extend(batch_results)
                            except Exception as e:
                                logger.error(f"Error processing ontology batch: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"Error in parallel ontology processing: {e}")
                    # Fallback to sequential processing
                    all_results = self._extract_ontology_sequential(documents)
            else:
                # Use sequential processing for small document sets or when spaCy unavailable
                all_results = self._extract_ontology_sequential(documents)
            
            # Store results in database
            self._store_ontology_results(all_results, file_path)
            
            #log_info(f"✅ Completed ontology extraction for {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error in ontology processing: {e}")
    
    def _extract_ontology_sequential(self, documents: List[Document]) -> List[Tuple[str, List[Tuple[str, str, List[str]]]]]:
        """Fallback sequential ontology extraction"""
        results = []
        for doc in documents:
            try:
                terms = self._extract_ontology_with_nlp(doc.content)
                results.append((doc.id, terms))
            except Exception as e:
                logger.error(f"Error extracting ontology from document {doc.id}: {e}")
                continue
        return results
    
    def _store_ontology_results(self, all_results: List[Tuple[str, List[Tuple[str, str, List[str]]]]], file_path: Path) -> None:
        """Store ontology extraction results in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            term_counts = Counter()
            all_terms = []
            
            # Process all results and create mappings
            for doc_id, terms in all_results:
                all_terms.extend(terms)
                
                # Store document-term mappings
                for term, entity_type, contexts in terms:
                    term_counts[term] += 1
                    try:
                        cursor.execute(f'''
                            INSERT INTO {self.ontology_table_name}_mapping (doc_id, term)
                            VALUES (?, ?)
                        ''', (doc_id, term))
                    except Exception as e:
                        logger.error(f"Error storing doc-term mapping: {e}")
            
            # Store unique terms with frequency
            stored_count = 0
            for term, frequency in term_counts.items():
                term_data = [t for t in all_terms if t[0] == term]
                if term_data:
                    entity_type = term_data[0][1]
                    all_contexts = []
                    for _, _, contexts in term_data:
                        all_contexts.extend(contexts)
                    
                    try:
                        cursor.execute(f'''
                            INSERT OR REPLACE INTO {self.ontology_table_name}
                            (term, entity_type, frequency, document_count, contexts, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            term, entity_type, frequency, 1, 
                            '\\n'.join(all_contexts[:5]), current_time
                        ))
                        stored_count += 1
                    except Exception as e:
                        logger.error(f"Error storing term '{term}': {e}")
            
            conn.commit()
            #log_info(f"📈 Stored {stored_count} unique ontology terms")
            
        except Exception as e:
            logger.error(f"Error storing ontology results: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _should_ingest_file(self, file_path: Path) -> bool:
        """Check if file should be ingested (new or changed)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            file_stat = os.stat(file_path)
            current_hash = self._get_file_hash(file_path)
            current_modified = file_stat.st_mtime
            current_size = file_stat.st_size
            
            if current_hash is None:
                return False
            
            cursor.execute(
                f"SELECT file_hash, last_modified, file_size FROM {self.metadata_table_name} WHERE filepath = ?",
                (str(file_path),)
            )
            existing_record = cursor.fetchone()
            
            if existing_record is None:
                return True
            
            stored_hash, stored_modified, stored_size = existing_record
            if (current_hash != stored_hash or 
                current_modified != stored_modified or 
                current_size != stored_size):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return False
        finally:
            conn.close()

    def _store_documents_in_db(self, documents: List[Document], file_path: Path) -> None:
        """Store documents in the SQL database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Remove old content for this file
            cursor.execute(f"DELETE FROM {self.table_name} WHERE filepath = ?", (str(file_path),))
            
            # Insert new documents
            for i, doc in enumerate(documents):
                cursor.execute(f'''
                    INSERT INTO {self.table_name} 
                    (doc_id, filepath, filename, content, chunk_index, meta_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    doc.id,
                    str(file_path),
                    file_path.name,
                    doc.content,
                    i,
                    str(doc.meta_data) if doc.meta_data else "{}"
                ))
            
            # Update metadata
            file_stat = os.stat(file_path)
            current_hash = self._get_file_hash(file_path)
            current_modified = file_stat.st_mtime
            current_size = file_stat.st_size
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO {self.metadata_table_name} 
                (filepath, file_hash, last_modified, last_ingested, file_size)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(file_path), 
                current_hash, 
                current_modified, 
                datetime.now().isoformat(), 
                current_size
            ))
            
            conn.commit()
            
            # Extract and store NLP-based ontology
            self._store_ontology_nlp(documents, file_path)
            
            # Invalidate TF-IDF vectors for cosine similarity rebuild
            self.tfidf_vectorizer = None
            self.document_vectors = None
            
        except Exception as e:
            logger.error(f"Error storing documents from {file_path}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _build_tfidf_vectors(self, force_rebuild: bool = False) -> None:
        """Build TF-IDF vectors for all documents for cosine similarity"""
        if self.tfidf_vectorizer is not None and self.document_vectors is not None and not force_rebuild:
            #print("📊 Using cached TF-IDF vectors")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT doc_id, content FROM {self.table_name}")
            results = cursor.fetchall()
            
            if not results:
                return
                
            self.document_ids = [row[0] for row in results]
            document_contents = [row[1] for row in results]
            
            # Initialize TF-IDF vectorizer with optimized parameters
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,  # Limit features for performance
                stop_words='english',
                ngram_range=(1, 2),  # Include bigrams
                min_df=1,  # Minimum document frequency
                max_df=0.95,  # Maximum document frequency
                sublinear_tf=True  # Apply sublinear scaling
            )
            
            # Fit and transform documents
            self.document_vectors = self.tfidf_vectorizer.fit_transform(document_contents)
            
        except Exception as e:
            logger.error(f"Error building TF-IDF vectors: {e}")
        finally:
            conn.close()
    
    def _calculate_cosine_similarity(self, query: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Calculate cosine similarity between query and all documents"""
        if self.tfidf_vectorizer is None or self.document_vectors is None:
            self._build_tfidf_vectors()
            
        if self.tfidf_vectorizer is None:
            return []
            
        try:
            # Transform query using the same vectorizer
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate cosine similarities
            similarities = sklearn_cosine_similarity(query_vector, self.document_vectors).flatten()
            
            # Create list of (doc_id, similarity) pairs
            doc_similarities = list(zip(self.document_ids, similarities))
            
            # Sort by similarity (descending)
            doc_similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k results
            if top_k:
                return doc_similarities[:top_k]
            return doc_similarities
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return []

    def search_cosine(self, query: str, num_documents: Optional[int] = None, 
                     similarity_threshold: float = 0.001) -> List[Document]:
        """Search documents using cosine similarity with TF-IDF vectors"""
        if not query.strip():
            return []
            
        _num_documents = num_documents or self.num_documents
        
        # Get similarities
        similarities = self._calculate_cosine_similarity(query, _num_documents * 2)
        
        if not similarities:
            return []
            
        # Filter by threshold and get documents
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        documents = []
        try:
            for doc_id, similarity in similarities:
                if similarity < similarity_threshold:
                    continue
                    
                cursor.execute(
                    f"SELECT doc_id, filepath, filename, content, meta_data FROM {self.table_name} WHERE doc_id = ?",
                    (doc_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    doc_id, filepath, filename, content, meta_data_str = result
                    try:
                        meta_data = eval(meta_data_str) if meta_data_str else {}
                    except:
                        meta_data = {}
                    
                    # Add similarity score to metadata
                    meta_data['cosine_similarity'] = similarity
                    
                    documents.append(Document(
                        id=doc_id,
                        content=content,
                        meta_data=meta_data
                    ))
                    
                    if len(documents) >= _num_documents:
                        break
                        
        except Exception as e:
            logger.error(f"Error retrieving cosine similarity results: {e}")
        finally:
            conn.close()
            
        return documents

    async def async_search(self, query: str, num_documents: Optional[int] = None, 
                          filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Async search - delegates to sync version"""
        return self.search(query, num_documents, filters)

    def get_ontology_stats(self) -> Dict[str, Any]:
        """
        Get statistics about NLP-extracted ontology terms and entities.
        
        Shows information about named entities, technical terms, and concepts
        automatically extracted from your documents using spaCy NLP.
        
        Returns:
            Dict[str, Any]: Dictionary containing ontology statistics
            
        Examples:
            # Get ontology overview
            stats = kb.get_ontology_stats()
            print(f"Total terms: {stats['total_terms']}")
            
            # See entity types found
            stats = kb.get_ontology_stats()
            for entity_type, count in stats['entity_types'].items():
                print(f"{entity_type}: {count} terms")
                
            # View most frequent terms
            stats = kb.get_ontology_stats()
            for term, frequency in stats['top_terms']:
                print(f"{term}: appears {frequency} times")
                
        Returns dictionary with keys:
            - total_terms: Total number of unique ontology terms
            - entity_types: Breakdown by entity type (PERSON, ORG, TECH, etc.)
            - top_terms: Most frequently occurring terms
            - document_coverage: How many documents contain ontology terms
            
        Note:
            Requires spaCy model 'en_core_web_sm' to be installed for full functionality.
            Install with: python -m spacy download en_core_web_sm
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total terms
            cursor.execute(f"SELECT COUNT(*) FROM {self.ontology_table_name}")
            total_terms = cursor.fetchone()[0]
            
            # Terms by entity type
            cursor.execute(f'''
                SELECT entity_type, COUNT(*) 
                FROM {self.ontology_table_name} 
                GROUP BY entity_type 
                ORDER BY COUNT(*) DESC
            ''')
            entity_types = dict(cursor.fetchall())
            
            # Top frequent terms
            cursor.execute(f'''
                SELECT term, frequency 
                FROM {self.ontology_table_name} 
                ORDER BY frequency DESC 
                LIMIT 10
            ''')
            top_terms = cursor.fetchall()
            
            return {
                "total_terms": total_terms,
                "entity_types": entity_types,
                "top_terms": top_terms
            }
            
        except Exception as e:
            logger.error(f"Error getting ontology stats: {e}")
            return {}
        finally:
            conn.close()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over files and yield lists of documents."""
        if self.path is None:
            return

        if isinstance(self.path, list):
            for path_data in self.path:
                if isinstance(path_data, dict):
                    path_obj = Path(path_data.get("path", ""))
                    metadata = path_data.get("metadata", {})
                else:
                    path_obj = Path(path_data)
                    metadata = None
                
                if self._is_valid_file(path_obj) and self._should_ingest_file(path_obj):
                    documents = self._read_file_to_documents(path_obj, metadata)
                    if documents:
                        self._store_documents_in_db(documents, path_obj)
                        yield documents
        else:
            path_obj = Path(self.path)
            
            if path_obj.is_file():
                if self._is_valid_file(path_obj) and self._should_ingest_file(path_obj):
                    documents = self._read_file_to_documents(path_obj)
                    if documents:
                        self._store_documents_in_db(documents, path_obj)
                        yield documents
            elif path_obj.is_dir():
                for file_path in path_obj.rglob("*"):
                    if self._is_valid_file(file_path) and self._should_ingest_file(file_path):
                        documents = self._read_file_to_documents(file_path)
                        if documents:
                            self._store_documents_in_db(documents, file_path)
                            yield documents

    @property
    async def async_document_lists(self) -> AsyncIterator[List[Document]]:
        """Async version - delegates to sync version"""
        for doc_list in self.document_lists:
            yield doc_list
    
    def _read_file_to_documents(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Read file content and convert to Document objects - split log files line by line"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # For log files, create large overlapping chunks to preserve maximum context
            if file_path.suffix.lower() in ['.log', '.txt']:
                lines = content.strip().split('\n')
                documents = []
                
                # Create larger chunks with significant overlap for complete context
                chunk_size = 10  # Increased from 5 for more context
                overlap = 5      # Increased from 2 for better context preservation
                
                for i in range(0, len(lines), chunk_size - overlap):
                    chunk_lines = lines[i:i + chunk_size]
                    if chunk_lines and any(line.strip() for line in chunk_lines):
                        chunk_content = '\n'.join(chunk_lines).strip()
                        if chunk_content:
                            doc = Document(
                                id=f"{file_path.name}_chunk_{i}_{datetime.now().isoformat()}",
                                content=chunk_content,
                                meta_data={
                                    "filepath": str(file_path),
                                    "filename": file_path.name,
                                    "file_extension": file_path.suffix,
                                    "chunk_start_line": i + 1,
                                    "chunk_end_line": min(i + chunk_size, len(lines)),
                                    "total_lines": len(lines),
                                    "chunk_type": "overlapping_large",
                                    **(metadata or {})
                                }
                            )
                            documents.append(doc)
                
                # ALWAYS keep the full file for complete context
                doc = Document(
                    id=f"{file_path.name}_full_{datetime.now().isoformat()}",
                    content=content,
                    meta_data={
                        "filepath": str(file_path),
                        "filename": file_path.name,
                        "file_extension": file_path.suffix,
                        "total_lines": len(lines),
                        "chunk_type": "complete_file",
                        **(metadata or {})
                    }
                )
                documents.append(doc)
                
                return documents
            
            else:
                # For non-log files, keep as single document
                doc = Document(
                    id=f"{file_path}_{datetime.now().isoformat()}",
                    content=content,
                    meta_data={
                        "filepath": str(file_path),
                        "filename": file_path.name,
                        "file_extension": file_path.suffix,
                        "file_size": len(content),
                        **(metadata or {})
                    }
                )
                return [doc]
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

    def load(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True) -> None:
        """
        Load documents from specified files/directories into the knowledge base.
        
        Processes files, extracts text content, performs NLP analysis for ontology
        extraction, and stores everything in the SQLite database for fast searching.
        
        Args:
            recreate (bool): If True, delete existing DB and start fresh. Defaults to False
            upsert (bool): If True, update existing documents. Defaults to False
            skip_existing (bool): If True, skip files that haven't changed. Defaults to True
            
        Examples:
            # Basic loading
            kb = irag(dir_path="logs/")
            kb.load()
            
            # Force complete rebuild
            kb.load(recreate=True)
            
            # Update existing documents
            kb.load(upsert=True, skip_existing=False)
            
            # Load and check results
            kb.load()
            info = kb.get_database_info()
            print(f"Loaded {info['total_documents']} documents")
        """
        if recreate:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name}")
            cursor.execute(f"DELETE FROM {self.metadata_table_name}")
            cursor.execute(f"DELETE FROM {self.ontology_table_name}")
            conn.commit()
            conn.close()
        
        num_documents = 0
        for document_list in self.document_lists:
            num_documents += len(document_list)
    
    async def aload(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True) -> None:
        """Async load - delegates to sync version"""
        self.load(recreate, upsert, skip_existing)
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the knowledge base database.
        
        Returns information about document counts, file sources, database size,
        and other useful metadata for monitoring and debugging.
        
        Returns:
            Dict[str, Any]: Dictionary containing database statistics
            
        Examples:
            # Get basic stats
            info = kb.get_database_info()
            print(f"Total documents: {info['total_documents']}")
            print(f"Unique files: {info['total_files']}")
            
            # Check if KB is loaded
            info = kb.get_database_info()
            if info['total_documents'] == 0:
                print("No documents loaded. Run kb.load() first.")
                
            # Display detailed info
            info = kb.get_database_info()
            for key, value in info.items():
                print(f"{key}: {value}")
                
        Returns dictionary with keys:
            - total_documents: Number of document chunks in database
            - total_files: Number of source files processed
            - database_size: Size of SQLite database file
            - ontology_terms: Number of extracted ontology terms
            - last_updated: Timestamp of most recent update
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT COUNT(DISTINCT filepath) FROM {self.table_name}")
            file_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT MAX(last_ingested) FROM {self.metadata_table_name}")
            latest_ingestion = cursor.fetchone()[0]
            
            ontology_stats = self.get_ontology_stats()
            
            return {
                "document_count": doc_count,
                "file_count": file_count,
                "latest_ingestion": latest_ingestion,
                "database_path": self.db_path,
                "ontology_stats": ontology_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {}
        finally:
            conn.close()