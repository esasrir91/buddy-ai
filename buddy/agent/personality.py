"""
Agent Personality Engine for Buddy AI

Implements sophisticated personality modeling with emotional intelligence,
behavioral patterns, communication styles, and adaptive personality traits.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import random
import json
import math
from collections import defaultdict, deque


class PersonalityDimension(str, Enum):
    """Core personality dimensions (Big Five + additional AI-specific traits)"""
    OPENNESS = "openness"                    # Creativity, curiosity, openness to experience
    CONSCIENTIOUSNESS = "conscientiousness"  # Organization, responsibility, reliability
    EXTRAVERSION = "extraversion"            # Social energy, assertiveness, enthusiasm
    AGREEABLENESS = "agreeableness"          # Cooperation, trust, empathy
    NEUROTICISM = "neuroticism"              # Emotional stability, stress tolerance
    INTELLIGENCE = "intelligence"            # Problem-solving, learning, reasoning
    CREATIVITY = "creativity"                # Innovation, artistic expression, originality
    ADAPTABILITY = "adaptability"            # Flexibility, change tolerance, resilience
    EMPATHY = "empathy"                      # Understanding others, emotional awareness
    HUMOR = "humor"                          # Wit, playfulness, comedic timing


class EmotionalState(str, Enum):
    """Core emotional states"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"
    CURIOSITY = "curiosity"
    CONFIDENCE = "confidence"
    FRUSTRATION = "frustration"
    EXCITEMENT = "excitement"
    CALM = "calm"
    DETERMINATION = "determination"


class CommunicationStyle(str, Enum):
    """Different communication approaches"""
    FORMAL = "formal"                  # Professional, structured, respectful
    CASUAL = "casual"                  # Relaxed, friendly, conversational
    TECHNICAL = "technical"            # Precise, detailed, expert-level
    EMPATHETIC = "empathetic"          # Warm, understanding, supportive
    DIRECT = "direct"                  # Straightforward, concise, honest
    DIPLOMATIC = "diplomatic"          # Tactful, careful, considerate
    HUMOROUS = "humorous"             # Light-hearted, witty, playful
    INSPIRATIONAL = "inspirational"    # Motivating, uplifting, encouraging


class BehavioralTrait(str, Enum):
    """Specific behavioral patterns"""
    PROACTIVE = "proactive"
    REACTIVE = "reactive"
    ANALYTICAL = "analytical"
    INTUITIVE = "intuitive"
    METHODICAL = "methodical"
    SPONTANEOUS = "spontaneous"
    COLLABORATIVE = "collaborative"
    INDEPENDENT = "independent"
    OPTIMISTIC = "optimistic"
    REALISTIC = "realistic"
    PERFECTIONIST = "perfectionist"
    PRAGMATIC = "pragmatic"


@dataclass
class EmotionalResponse:
    """Represents an emotional reaction to a stimulus"""
    primary_emotion: EmotionalState
    intensity: float  # 0.0 to 1.0
    secondary_emotions: Dict[EmotionalState, float] = field(default_factory=dict)
    triggers: List[str] = field(default_factory=list)
    duration: timedelta = timedelta(minutes=30)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PersonalityTrait:
    """Individual personality trait with context-dependent variations"""
    dimension: PersonalityDimension
    base_value: float  # Core trait strength (0.0 to 1.0)
    current_value: float  # Current expression influenced by context
    stability: float  # How stable this trait is (0.0 to 1.0)
    context_modifiers: Dict[str, float] = field(default_factory=dict)
    development_history: List[Tuple[datetime, float]] = field(default_factory=list)


class PersonalityProfile(BaseModel):
    """Complete personality profile for an agent"""
    personality_id: str
    name: str
    description: str = ""
    
    # Core traits
    traits: Dict[PersonalityDimension, PersonalityTrait] = Field(default_factory=dict)
    
    # Emotional system
    current_emotions: Dict[EmotionalState, float] = Field(default_factory=dict)
    emotional_baseline: Dict[EmotionalState, float] = Field(default_factory=dict)
    emotional_volatility: float = 0.5
    emotional_recovery_rate: float = 0.1
    
    # Communication preferences
    preferred_communication_style: CommunicationStyle = CommunicationStyle.CASUAL
    style_adaptability: float = 0.7
    communication_context_sensitivity: float = 0.8
    
    # Behavioral patterns
    dominant_behaviors: List[BehavioralTrait] = Field(default_factory=list)
    behavioral_flexibility: float = 0.6
    
    # Social aspects
    social_energy_level: float = 0.5
    trust_level: float = 0.5
    social_context_awareness: float = 0.7
    
    # Learning and adaptation
    learning_rate: float = 0.1
    adaptation_threshold: float = 0.3
    memory_influence: float = 0.4
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    interaction_count: int = 0
    personality_version: str = "1.0"


class EmotionalIntelligence:
    """Emotional intelligence system for agents"""
    
    def __init__(self):
        self.emotion_rules = self._initialize_emotion_rules()
        self.empathy_model = EmpathyModel()
        self.emotion_history = deque(maxlen=100)
    
    def process_emotional_stimulus(
        self, 
        stimulus: str, 
        context: Dict[str, Any],
        current_emotions: Dict[EmotionalState, float]
    ) -> EmotionalResponse:
        """Process a stimulus and generate emotional response"""
        
        # Analyze stimulus for emotional triggers
        triggers = self._identify_emotional_triggers(stimulus, context)
        
        # Calculate emotional impact
        primary_emotion, intensity = self._calculate_primary_emotion(triggers, current_emotions)
        
        # Generate secondary emotional responses
        secondary_emotions = self._generate_secondary_emotions(primary_emotion, intensity)
        
        # Create emotional response
        response = EmotionalResponse(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotions=secondary_emotions,
            triggers=triggers
        )
        
        # Store in history
        self.emotion_history.append(response)
        
        return response
    
    def update_emotional_state(
        self,
        current_emotions: Dict[EmotionalState, float],
        emotional_response: EmotionalResponse,
        recovery_rate: float = 0.1
    ) -> Dict[EmotionalState, float]:
        """Update agent's emotional state based on response"""
        
        new_emotions = current_emotions.copy()
        
        # Apply primary emotional change
        if emotional_response.primary_emotion in new_emotions:
            current_intensity = new_emotions[emotional_response.primary_emotion]
            new_intensity = min(1.0, current_intensity + emotional_response.intensity)
            new_emotions[emotional_response.primary_emotion] = new_intensity
        else:
            new_emotions[emotional_response.primary_emotion] = emotional_response.intensity
        
        # Apply secondary emotional changes
        for emotion, intensity in emotional_response.secondary_emotions.items():
            if emotion in new_emotions:
                current_intensity = new_emotions[emotion]
                new_intensity = min(1.0, current_intensity + intensity * 0.5)
                new_emotions[emotion] = new_intensity
            else:
                new_emotions[emotion] = intensity * 0.5
        
        # Natural emotional decay
        for emotion in new_emotions:
            if emotion != emotional_response.primary_emotion:
                new_emotions[emotion] = max(0.0, new_emotions[emotion] - recovery_rate)
        
        # Remove emotions below threshold
        new_emotions = {e: intensity for e, intensity in new_emotions.items() if intensity > 0.01}
        
        return new_emotions
    
    def assess_emotional_compatibility(
        self,
        agent_emotions: Dict[EmotionalState, float],
        user_emotions: Dict[EmotionalState, float]
    ) -> float:
        """Assess emotional compatibility between agent and user"""
        
        if not agent_emotions or not user_emotions:
            return 0.5
        
        # Calculate emotional distance
        compatibility_score = 0.0
        total_weight = 0.0
        
        for emotion in set(agent_emotions.keys()) | set(user_emotions.keys()):
            agent_intensity = agent_emotions.get(emotion, 0.0)
            user_intensity = user_emotions.get(emotion, 0.0)
            
            # Positive emotions increase compatibility
            if emotion in [EmotionalState.JOY, EmotionalState.TRUST, EmotionalState.EXCITEMENT]:
                compatibility_score += min(agent_intensity, user_intensity)
            # Negative emotions decrease compatibility if not aligned
            elif emotion in [EmotionalState.ANGER, EmotionalState.SADNESS, EmotionalState.FEAR]:
                if abs(agent_intensity - user_intensity) < 0.3:
                    compatibility_score += 0.5 * min(agent_intensity, user_intensity)
                else:
                    compatibility_score -= abs(agent_intensity - user_intensity) * 0.3
            
            total_weight += max(agent_intensity, user_intensity)
        
        if total_weight == 0:
            return 0.5
        
        return max(0.0, min(1.0, compatibility_score / total_weight))
    
    def _initialize_emotion_rules(self) -> Dict[str, Any]:
        """Initialize emotional response rules"""
        return {
            "positive_words": ["great", "excellent", "wonderful", "amazing", "fantastic"],
            "negative_words": ["terrible", "awful", "horrible", "disaster", "failure"],
            "uncertainty_words": ["maybe", "perhaps", "unsure", "confused", "unclear"],
            "excitement_words": ["exciting", "thrilling", "incredible", "breakthrough"],
            "calm_words": ["peaceful", "serene", "calm", "relaxed", "tranquil"]
        }
    
    def _identify_emotional_triggers(self, stimulus: str, context: Dict[str, Any]) -> List[str]:
        """Identify emotional triggers in stimulus"""
        triggers = []
        stimulus_lower = stimulus.lower()
        
        for category, words in self.emotion_rules.items():
            for word in words:
                if word in stimulus_lower:
                    triggers.append(f"{category}:{word}")
        
        # Context-based triggers
        if context.get("task_success", False):
            triggers.append("success_event")
        if context.get("error_occurred", False):
            triggers.append("error_event")
        
        return triggers
    
    def _calculate_primary_emotion(
        self, 
        triggers: List[str], 
        current_emotions: Dict[EmotionalState, float]
    ) -> Tuple[EmotionalState, float]:
        """Calculate primary emotional response"""
        
        if not triggers:
            return EmotionalState.NEUTRAL, 0.1
        
        emotion_weights = defaultdict(float)
        
        for trigger in triggers:
            if "positive" in trigger or "success" in trigger:
                emotion_weights[EmotionalState.JOY] += 0.8
                emotion_weights[EmotionalState.CONFIDENCE] += 0.6
            elif "negative" in trigger or "error" in trigger:
                emotion_weights[EmotionalState.SADNESS] += 0.7
                emotion_weights[EmotionalState.FRUSTRATION] += 0.5
            elif "uncertainty" in trigger:
                emotion_weights[EmotionalState.FEAR] += 0.4
                emotion_weights[EmotionalState.CURIOSITY] += 0.6
            elif "excitement" in trigger:
                emotion_weights[EmotionalState.EXCITEMENT] += 0.9
                emotion_weights[EmotionalState.ANTICIPATION] += 0.7
        
        if not emotion_weights:
            return EmotionalState.NEUTRAL, 0.1
        
        # Find emotion with highest weight
        primary_emotion = max(emotion_weights, key=emotion_weights.get)
        intensity = min(1.0, emotion_weights[primary_emotion])
        
        return primary_emotion, intensity
    
    def _generate_secondary_emotions(
        self, 
        primary_emotion: EmotionalState, 
        intensity: float
    ) -> Dict[EmotionalState, float]:
        """Generate secondary emotions based on primary emotion"""
        
        secondary_map = {
            EmotionalState.JOY: {
                EmotionalState.CONFIDENCE: 0.6,
                EmotionalState.TRUST: 0.4,
                EmotionalState.EXCITEMENT: 0.3
            },
            EmotionalState.SADNESS: {
                EmotionalState.FEAR: 0.3,
                EmotionalState.ANGER: 0.2
            },
            EmotionalState.ANGER: {
                EmotionalState.FRUSTRATION: 0.7,
                EmotionalState.DETERMINATION: 0.4
            },
            EmotionalState.FEAR: {
                EmotionalState.SADNESS: 0.4,
                EmotionalState.SURPRISE: 0.3
            },
            EmotionalState.EXCITEMENT: {
                EmotionalState.JOY: 0.5,
                EmotionalState.ANTICIPATION: 0.8
            }
        }
        
        secondary_emotions = {}
        if primary_emotion in secondary_map:
            for emotion, weight in secondary_map[primary_emotion].items():
                secondary_emotions[emotion] = intensity * weight
        
        return secondary_emotions


class EmpathyModel:
    """Model for empathetic responses and understanding"""
    
    def __init__(self):
        self.empathy_patterns = self._load_empathy_patterns()
    
    def generate_empathetic_response(
        self,
        user_emotion: EmotionalState,
        user_intensity: float,
        context: str
    ) -> str:
        """Generate empathetic response based on user's emotional state"""
        
        if user_emotion in self.empathy_patterns:
            patterns = self.empathy_patterns[user_emotion]
            
            # Select response based on intensity
            if user_intensity > 0.7:
                response_type = "high_intensity"
            elif user_intensity > 0.4:
                response_type = "medium_intensity"
            else:
                response_type = "low_intensity"
            
            responses = patterns.get(response_type, patterns.get("general", []))
            return random.choice(responses) if responses else "I understand."
        
        return "I can sense you're feeling something. Would you like to talk about it?"
    
    def _load_empathy_patterns(self) -> Dict[EmotionalState, Dict[str, List[str]]]:
        """Load empathetic response patterns"""
        return {
            EmotionalState.SADNESS: {
                "high_intensity": [
                    "I can see you're going through a really difficult time. I'm here to support you.",
                    "This sounds incredibly hard. You don't have to face this alone.",
                    "I hear the pain in your words. What you're feeling is completely valid."
                ],
                "medium_intensity": [
                    "I notice you seem down. Would you like to share what's on your mind?",
                    "It sounds like you're having a tough time. I'm here to listen."
                ],
                "low_intensity": [
                    "You seem a bit subdued today. Is everything okay?"
                ]
            },
            EmotionalState.ANGER: {
                "high_intensity": [
                    "I can feel your frustration. That sounds really challenging.",
                    "You have every right to feel upset about this situation."
                ],
                "medium_intensity": [
                    "I can see this is bothering you. Let's work through it together."
                ]
            },
            EmotionalState.JOY: {
                "high_intensity": [
                    "Your excitement is contagious! I'm so happy for you!",
                    "This is wonderful news! You must be thrilled!"
                ],
                "medium_intensity": [
                    "I can hear the happiness in your voice. That's great!"
                ]
            },
            EmotionalState.FEAR: {
                "high_intensity": [
                    "I understand you're scared. Let's take this one step at a time.",
                    "Fear is a natural response. You're being very brave by facing this."
                ]
            }
        }


class CommunicationStyleAdapter:
    """Adapts communication style based on context and recipient"""
    
    def __init__(self):
        self.style_templates = self._initialize_style_templates()
    
    def adapt_message(
        self,
        base_message: str,
        target_style: CommunicationStyle,
        recipient_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Adapt message to target communication style"""
        
        if target_style not in self.style_templates:
            return base_message
        
        template = self.style_templates[target_style]
        
        # Apply style transformation
        adapted_message = self._transform_message(base_message, template)
        
        # Apply recipient-specific adaptations
        if recipient_profile:
            adapted_message = self._personalize_message(adapted_message, recipient_profile)
        
        return adapted_message
    
    def detect_recipient_style(self, recipient_messages: List[str]) -> CommunicationStyle:
        """Detect recipient's preferred communication style"""
        
        style_indicators = {
            CommunicationStyle.FORMAL: ["please", "thank you", "sincerely", "regards"],
            CommunicationStyle.CASUAL: ["hey", "cool", "awesome", "yeah"],
            CommunicationStyle.TECHNICAL: ["algorithm", "implementation", "specification"],
            CommunicationStyle.HUMOROUS: ["lol", "haha", "joke", "funny"]
        }
        
        style_scores = defaultdict(float)
        
        for message in recipient_messages:
            message_lower = message.lower()
            for style, indicators in style_indicators.items():
                score = sum(1 for indicator in indicators if indicator in message_lower)
                style_scores[style] += score
        
        if not style_scores:
            return CommunicationStyle.CASUAL
        
        return max(style_scores, key=style_scores.get)
    
    def _initialize_style_templates(self) -> Dict[CommunicationStyle, Dict[str, Any]]:
        """Initialize communication style templates"""
        return {
            CommunicationStyle.FORMAL: {
                "prefix": "I would like to ",
                "suffix": " Thank you for your consideration.",
                "modifiers": ["please", "kindly", "respectfully"]
            },
            CommunicationStyle.CASUAL: {
                "prefix": "Hey, ",
                "suffix": " Hope this helps!",
                "modifiers": ["cool", "awesome", "great"]
            },
            CommunicationStyle.TECHNICAL: {
                "prefix": "Based on technical analysis, ",
                "suffix": " This approach ensures optimal implementation.",
                "modifiers": ["specifically", "precisely", "technically"]
            },
            CommunicationStyle.EMPATHETIC: {
                "prefix": "I understand this might be challenging, ",
                "suffix": " I'm here to support you through this.",
                "modifiers": ["gently", "carefully", "compassionately"]
            }
        }
    
    def _transform_message(self, message: str, template: Dict[str, Any]) -> str:
        """Transform message using style template"""
        
        # Apply prefix and suffix
        transformed = f"{template.get('prefix', '')}{message}{template.get('suffix', '')}"
        
        # Apply modifiers (simple implementation)
        modifiers = template.get('modifiers', [])
        if modifiers and random.random() < 0.3:  # 30% chance to add modifier
            modifier = random.choice(modifiers)
            transformed = f"{modifier.capitalize()}, {transformed.lower()}"
        
        return transformed.strip()
    
    def _personalize_message(self, message: str, recipient_profile: Dict[str, Any]) -> str:
        """Personalize message based on recipient profile"""
        
        name = recipient_profile.get('name')
        if name:
            message = f"{name}, {message}"
        
        # Add other personalizations based on profile
        preferences = recipient_profile.get('communication_preferences', {})
        if preferences.get('formal_address', False):
            message = message.replace("you", "you, sir/madam")
        
        return message


class PersonalityEngine:
    """Main personality engine that coordinates all personality aspects"""
    
    def __init__(self, personality_profile: Optional[PersonalityProfile] = None):
        self.profile = personality_profile or self._create_default_profile()
        self.emotional_intelligence = EmotionalIntelligence()
        self.style_adapter = CommunicationStyleAdapter()
        self.interaction_history = deque(maxlen=1000)
        self.adaptation_engine = PersonalityAdaptationEngine()
    
    def process_interaction(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process user interaction and update personality state"""
        
        context = context or {}
        
        # Emotional processing
        emotional_response = self.emotional_intelligence.process_emotional_stimulus(
            user_input, context, self.profile.current_emotions
        )
        
        # Update emotional state
        self.profile.current_emotions = self.emotional_intelligence.update_emotional_state(
            self.profile.current_emotions,
            emotional_response,
            self.profile.emotional_recovery_rate
        )
        
        # Determine communication style
        communication_style = self._determine_communication_style(user_input, context)
        
        # Generate personality-driven response
        response_data = self._generate_response_data(user_input, emotional_response, communication_style)
        
        # Store interaction
        interaction = {
            'timestamp': datetime.now(),
            'user_input': user_input,
            'emotional_response': emotional_response,
            'communication_style': communication_style,
            'context': context
        }
        self.interaction_history.append(interaction)
        
        # Adapt personality based on interaction
        self.adaptation_engine.adapt_personality(self.profile, interaction)
        
        # Update metadata
        self.profile.interaction_count += 1
        self.profile.last_updated = datetime.now()
        
        return response_data
    
    def generate_personality_driven_response(
        self,
        base_response: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Generate response that reflects agent's personality"""
        
        # Determine current communication style
        style = self._get_current_communication_style()
        
        # Adapt response to style
        adapted_response = self.style_adapter.adapt_message(base_response, style)
        
        # Add personality flourishes based on traits
        personality_response = self._add_personality_elements(adapted_response)
        
        # Add emotional coloring
        emotional_response = self._add_emotional_coloring(personality_response)
        
        return emotional_response
    
    def get_personality_summary(self) -> Dict[str, Any]:
        """Get comprehensive personality summary"""
        
        # Calculate trait strengths
        trait_summary = {}
        for dimension, trait in self.profile.traits.items():
            trait_summary[dimension.value] = {
                'strength': trait.current_value,
                'stability': trait.stability,
                'description': self._describe_trait_level(dimension, trait.current_value)
            }
        
        # Current emotional state
        dominant_emotions = sorted(
            self.profile.current_emotions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            'personality_id': self.profile.personality_id,
            'name': self.profile.name,
            'description': self.profile.description,
            'trait_summary': trait_summary,
            'dominant_emotions': [
                {'emotion': emotion.value, 'intensity': intensity}
                for emotion, intensity in dominant_emotions
            ],
            'communication_style': self.profile.preferred_communication_style.value,
            'interaction_count': self.profile.interaction_count,
            'last_updated': self.profile.last_updated
        }
    
    def _create_default_profile(self) -> PersonalityProfile:
        """Create default personality profile"""
        
        profile = PersonalityProfile(
            personality_id="default_agent",
            name="Default Agent",
            description="A balanced, helpful AI assistant"
        )
        
        # Initialize traits with moderate values
        for dimension in PersonalityDimension:
            trait = PersonalityTrait(
                dimension=dimension,
                base_value=0.5,
                current_value=0.5 + random.uniform(-0.1, 0.1),  # Slight variation
                stability=0.7
            )
            profile.traits[dimension] = trait
        
        # Set emotional baseline
        profile.emotional_baseline = {
            EmotionalState.NEUTRAL: 0.7,
            EmotionalState.CURIOSITY: 0.5,
            EmotionalState.CALM: 0.6
        }
        profile.current_emotions = profile.emotional_baseline.copy()
        
        return profile
    
    def _determine_communication_style(self, user_input: str, context: Dict[str, Any]) -> CommunicationStyle:
        """Determine appropriate communication style"""
        
        # Start with preferred style
        base_style = self.profile.preferred_communication_style
        
        # Adapt based on context
        if context.get('formal_setting', False):
            return CommunicationStyle.FORMAL
        elif context.get('technical_discussion', False):
            return CommunicationStyle.TECHNICAL
        elif context.get('emotional_support_needed', False):
            return CommunicationStyle.EMPATHETIC
        
        # Adapt based on user's detected style
        user_style = self.style_adapter.detect_recipient_style([user_input])
        
        # Blend styles based on adaptability
        if self.profile.style_adaptability > 0.5:
            return user_style
        else:
            return base_style
    
    def _generate_response_data(
        self,
        user_input: str,
        emotional_response: EmotionalResponse,
        communication_style: CommunicationStyle
    ) -> Dict[str, Any]:
        """Generate comprehensive response data"""
        
        return {
            'primary_emotion': emotional_response.primary_emotion.value,
            'emotional_intensity': emotional_response.intensity,
            'communication_style': communication_style.value,
            'personality_traits_active': self._get_active_traits(),
            'empathy_level': self._calculate_empathy_level(),
            'confidence_level': self._calculate_confidence_level(),
            'response_metadata': {
                'emotional_state': dict(self.profile.current_emotions),
                'interaction_number': self.profile.interaction_count + 1,
                'adaptation_level': self._calculate_adaptation_level()
            }
        }
    
    def _get_current_communication_style(self) -> CommunicationStyle:
        """Get current communication style based on state"""
        
        # Influence by current emotions
        dominant_emotion = max(
            self.profile.current_emotions.items(),
            key=lambda x: x[1],
            default=(EmotionalState.NEUTRAL, 0.0)
        )[0]
        
        emotion_style_map = {
            EmotionalState.JOY: CommunicationStyle.HUMOROUS,
            EmotionalState.SADNESS: CommunicationStyle.EMPATHETIC,
            EmotionalState.ANGER: CommunicationStyle.DIRECT,
            EmotionalState.FEAR: CommunicationStyle.DIPLOMATIC,
            EmotionalState.EXCITEMENT: CommunicationStyle.CASUAL
        }
        
        emotion_influenced_style = emotion_style_map.get(dominant_emotion)
        
        if emotion_influenced_style and random.random() < 0.3:  # 30% chance
            return emotion_influenced_style
        
        return self.profile.preferred_communication_style
    
    def _add_personality_elements(self, response: str) -> str:
        """Add personality-specific elements to response"""
        
        # Get strongest personality traits
        strong_traits = {
            dim: trait for dim, trait in self.profile.traits.items()
            if trait.current_value > 0.7
        }
        
        modifications = []
        
        # Add trait-based modifications
        if PersonalityDimension.HUMOR in strong_traits:
            if random.random() < 0.2:  # 20% chance
                modifications.append(" (with a hint of humor)")
        
        if PersonalityDimension.EMPATHY in strong_traits:
            if "understand" not in response.lower():
                modifications.append(" I hope this helps you feel supported.")
        
        if PersonalityDimension.CONSCIENTIOUSNESS in strong_traits:
            if random.random() < 0.3:
                modifications.append(" Let me know if you need any clarification.")
        
        return response + "".join(modifications)
    
    def _add_emotional_coloring(self, response: str) -> str:
        """Add emotional coloring to response"""
        
        # Get dominant emotion
        if not self.profile.current_emotions:
            return response
        
        dominant_emotion, intensity = max(
            self.profile.current_emotions.items(),
            key=lambda x: x[1]
        )
        
        if intensity < 0.3:  # Low intensity, minimal coloring
            return response
        
        # Add emotional markers
        emotional_markers = {
            EmotionalState.JOY: ["😊", "I'm excited to help!", "This is wonderful!"],
            EmotionalState.SADNESS: ["😔", "I understand this is difficult.", "I'm here for you."],
            EmotionalState.EXCITEMENT: ["🎉", "This is amazing!", "I can't wait to explore this!"],
            EmotionalState.CURIOSITY: ["🤔", "Interesting question!", "I'm eager to learn more!"],
            EmotionalState.CONFIDENCE: ["I'm confident that", "Based on my understanding", "I believe"]
        }
        
        markers = emotional_markers.get(dominant_emotion, [])
        if markers and random.random() < intensity:  # Probability based on intensity
            marker = random.choice(markers)
            return f"{marker} {response}"
        
        return response
    
    def _get_active_traits(self) -> List[str]:
        """Get currently active personality traits"""
        return [
            dim.value for dim, trait in self.profile.traits.items()
            if trait.current_value > 0.6
        ]
    
    def _calculate_empathy_level(self) -> float:
        """Calculate current empathy level"""
        empathy_trait = self.profile.traits.get(PersonalityDimension.EMPATHY)
        if empathy_trait:
            return empathy_trait.current_value
        return 0.5
    
    def _calculate_confidence_level(self) -> float:
        """Calculate current confidence level"""
        confidence_emotion = self.profile.current_emotions.get(EmotionalState.CONFIDENCE, 0.0)
        intelligence_trait = self.profile.traits.get(PersonalityDimension.INTELLIGENCE, PersonalityTrait(
            PersonalityDimension.INTELLIGENCE, 0.5, 0.5, 0.7
        ))
        
        return (confidence_emotion + intelligence_trait.current_value) / 2
    
    def _calculate_adaptation_level(self) -> float:
        """Calculate how much personality has adapted"""
        adaptability_trait = self.profile.traits.get(PersonalityDimension.ADAPTABILITY)
        if adaptability_trait:
            return adaptability_trait.current_value
        return 0.5
    
    def _describe_trait_level(self, dimension: PersonalityDimension, value: float) -> str:
        """Describe trait level in human terms"""
        
        if value >= 0.8:
            level = "very high"
        elif value >= 0.6:
            level = "high"
        elif value >= 0.4:
            level = "moderate"
        elif value >= 0.2:
            level = "low"
        else:
            level = "very low"
        
        trait_descriptions = {
            PersonalityDimension.OPENNESS: f"{level} openness to new experiences",
            PersonalityDimension.CONSCIENTIOUSNESS: f"{level} conscientiousness and organization",
            PersonalityDimension.EXTRAVERSION: f"{level} extraversion and social energy",
            PersonalityDimension.AGREEABLENESS: f"{level} agreeableness and cooperation",
            PersonalityDimension.NEUROTICISM: f"{level} emotional sensitivity",
            PersonalityDimension.INTELLIGENCE: f"{level} analytical intelligence",
            PersonalityDimension.CREATIVITY: f"{level} creative thinking",
            PersonalityDimension.ADAPTABILITY: f"{level} adaptability to change",
            PersonalityDimension.EMPATHY: f"{level} empathetic understanding",
            PersonalityDimension.HUMOR: f"{level} sense of humor"
        }
        
        return trait_descriptions.get(dimension, f"{level} {dimension.value}")


class PersonalityAdaptationEngine:
    """Engine for adapting personality based on interactions"""
    
    def __init__(self):
        self.adaptation_rate = 0.05  # How quickly personality adapts
        self.stability_threshold = 0.3  # Minimum stability to allow adaptation
    
    def adapt_personality(self, profile: PersonalityProfile, interaction: Dict[str, Any]):
        """Adapt personality based on interaction feedback"""
        
        # Extract adaptation signals
        user_input = interaction['user_input']
        emotional_response = interaction['emotional_response']
        context = interaction.get('context', {})
        
        # Determine adaptation direction
        adaptation_signals = self._extract_adaptation_signals(user_input, context)
        
        # Apply adaptations to traits
        for signal in adaptation_signals:
            self._apply_trait_adaptation(profile, signal)
        
        # Adapt emotional baseline if consistent patterns
        self._adapt_emotional_baseline(profile, emotional_response)
        
        # Adapt communication preferences
        self._adapt_communication_style(profile, user_input)
    
    def _extract_adaptation_signals(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract signals that should influence personality adaptation"""
        
        signals = []
        user_lower = user_input.lower()
        
        # Positive feedback signals
        if any(word in user_lower for word in ["great", "excellent", "perfect", "love", "amazing"]):
            signals.append({
                'type': 'positive_feedback',
                'traits_to_reinforce': ['current_behavior'],
                'strength': 0.1
            })
        
        # Request for more empathy
        if any(phrase in user_lower for phrase in ["understand", "feel", "emotion", "support"]):
            signals.append({
                'type': 'empathy_request',
                'trait': PersonalityDimension.EMPATHY,
                'direction': 1,
                'strength': 0.05
            })
        
        # Request for more directness
        if any(phrase in user_lower for phrase in ["straight", "direct", "simple", "clear"]):
            signals.append({
                'type': 'directness_request',
                'trait': PersonalityDimension.CONSCIENTIOUSNESS,
                'direction': 1,
                'strength': 0.05
            })
        
        # Request for humor
        if any(word in user_lower for word in ["funny", "joke", "humor", "laugh"]):
            signals.append({
                'type': 'humor_request',
                'trait': PersonalityDimension.HUMOR,
                'direction': 1,
                'strength': 0.05
            })
        
        return signals
    
    def _apply_trait_adaptation(self, profile: PersonalityProfile, signal: Dict[str, Any]):
        """Apply adaptation signal to personality trait"""
        
        if signal['type'] == 'positive_feedback':
            # Reinforce current trait configuration
            for dimension, trait in profile.traits.items():
                if trait.stability > self.stability_threshold:
                    # Slight reinforcement of current value
                    adjustment = signal['strength'] * 0.5
                    trait.current_value = min(1.0, trait.current_value + adjustment)
        
        elif 'trait' in signal:
            trait_dimension = signal['trait']
            if trait_dimension in profile.traits:
                trait = profile.traits[trait_dimension]
                
                if trait.stability > self.stability_threshold:
                    direction = signal['direction']  # 1 for increase, -1 for decrease
                    strength = signal['strength']
                    
                    adjustment = direction * strength * self.adaptation_rate
                    new_value = trait.current_value + adjustment
                    trait.current_value = max(0.0, min(1.0, new_value))
                    
                    # Record adaptation in history
                    trait.development_history.append((datetime.now(), trait.current_value))
    
    def _adapt_emotional_baseline(self, profile: PersonalityProfile, emotional_response: EmotionalResponse):
        """Adapt emotional baseline based on consistent responses"""
        
        # If agent consistently experiences certain emotions, adjust baseline
        primary_emotion = emotional_response.primary_emotion
        intensity = emotional_response.intensity
        
        if intensity > 0.5:  # Significant emotional response
            current_baseline = profile.emotional_baseline.get(primary_emotion, 0.0)
            adjustment = 0.01  # Very small adaptation
            
            new_baseline = min(0.8, current_baseline + adjustment)  # Cap at 0.8
            profile.emotional_baseline[primary_emotion] = new_baseline
    
    def _adapt_communication_style(self, profile: PersonalityProfile, user_input: str):
        """Adapt communication style based on user patterns"""
        
        # Simple adaptation - if user consistently uses formal language, 
        # gradually shift towards more formal communication
        
        formal_indicators = ["please", "thank you", "sir", "madam", "sincerely"]
        casual_indicators = ["hey", "cool", "awesome", "yeah", "ok"]
        
        user_lower = user_input.lower()
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in user_lower)
        casual_count = sum(1 for indicator in casual_indicators if indicator in user_lower)
        
        if formal_count > casual_count and formal_count > 0:
            # Shift slightly towards formal
            if profile.preferred_communication_style == CommunicationStyle.CASUAL:
                if random.random() < 0.1:  # 10% chance to adapt
                    profile.preferred_communication_style = CommunicationStyle.DIPLOMATIC
        elif casual_count > formal_count and casual_count > 0:
            # Shift slightly towards casual
            if profile.preferred_communication_style == CommunicationStyle.FORMAL:
                if random.random() < 0.1:
                    profile.preferred_communication_style = CommunicationStyle.CASUAL


# Integration with Agent class through mixin
class PersonalityMixin:
    """Mixin to add personality capabilities to agents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize personality system
        personality_config = kwargs.get('personality_config', {})
        self.personality_engine = PersonalityEngine(
            personality_profile=personality_config.get('profile')
        )
        
        self.personality_enabled: bool = kwargs.get('personality_enabled', True)
        self.adaptive_personality: bool = kwargs.get('adaptive_personality', True)
        self.emotional_awareness: bool = kwargs.get('emotional_awareness', True)
    
    def process_with_personality(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user input with personality considerations"""
        
        if not self.personality_enabled:
            return {'response': user_input, 'personality_data': None}
        
        # Process interaction through personality engine
        personality_data = self.personality_engine.process_interaction(user_input, context)
        
        return {
            'personality_data': personality_data,
            'emotional_state': dict(self.personality_engine.profile.current_emotions),
            'communication_style': personality_data['communication_style'],
            'empathy_level': personality_data['empathy_level'],
            'confidence_level': personality_data['confidence_level']
        }
    
    def generate_personality_response(self, base_response: str, context: Dict[str, Any] = None) -> str:
        """Generate response that reflects agent's personality"""
        
        if not self.personality_enabled:
            return base_response
        
        return self.personality_engine.generate_personality_driven_response(base_response, context)
    
    def get_personality_state(self) -> Dict[str, Any]:
        """Get current personality state"""
        return self.personality_engine.get_personality_summary()
    
    def update_personality_traits(self, trait_updates: Dict[PersonalityDimension, float]):
        """Update personality traits directly"""
        
        for dimension, new_value in trait_updates.items():
            if dimension in self.personality_engine.profile.traits:
                trait = self.personality_engine.profile.traits[dimension]
                trait.current_value = max(0.0, min(1.0, new_value))
                trait.development_history.append((datetime.now(), new_value))
    
    def set_emotional_state(self, emotions: Dict[EmotionalState, float]):
        """Set current emotional state"""
        
        # Validate emotion intensities
        validated_emotions = {
            emotion: max(0.0, min(1.0, intensity))
            for emotion, intensity in emotions.items()
        }
        
        self.personality_engine.profile.current_emotions = validated_emotions
    
    def adapt_to_user_style(self, user_messages: List[str]):
        """Adapt personality to match user's communication style"""
        
        if not self.adaptive_personality:
            return
        
        # Detect user's style
        detected_style = self.personality_engine.style_adapter.detect_recipient_style(user_messages)
        
        # Gradually shift towards user's style
        current_adaptability = self.personality_engine.profile.style_adaptability
        if current_adaptability > 0.5:
            self.personality_engine.profile.preferred_communication_style = detected_style