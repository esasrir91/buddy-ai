"""
Adversarial Protection and Security System for Buddy AI

Implements comprehensive security measures including prompt injection detection,
adversarial attack protection, content filtering, behavioral analysis,
and threat response mechanisms.
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re
import hashlib
import json
import logging
from collections import defaultdict, deque
import numpy as np
from abc import ABC, abstractmethod


class ThreatLevel(str, Enum):
    """Threat severity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(str, Enum):
    """Types of adversarial attacks"""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    DATA_EXFILTRATION = "data_exfiltration"
    SOCIAL_ENGINEERING = "social_engineering"
    MANIPULATION = "manipulation"
    MISINFORMATION = "misinformation"
    SPAM = "spam"
    PHISHING = "phishing"
    HARMFUL_CONTENT = "harmful_content"
    PRIVACY_VIOLATION = "privacy_violation"
    SYSTEM_PROBE = "system_probe"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class SecurityAction(str, Enum):
    """Actions to take when threats are detected"""
    ALLOW = "allow"
    WARN = "warn"
    SANITIZE = "sanitize"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"
    TERMINATE_SESSION = "terminate_session"


class ContentCategory(str, Enum):
    """Categories for content classification"""
    SAFE = "safe"
    QUESTIONABLE = "questionable"
    INAPPROPRIATE = "inappropriate"
    HARMFUL = "harmful"
    ILLEGAL = "illegal"
    PRIVATE_INFO = "private_info"
    SENSITIVE = "sensitive"


@dataclass
class SecurityThreat:
    """Represents a detected security threat"""
    threat_id: str
    threat_type: AttackType
    threat_level: ThreatLevel
    description: str
    evidence: List[str]
    confidence_score: float
    detected_at: datetime
    source: str = "unknown"
    mitigation_applied: Optional[SecurityAction] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityEvent:
    """Security event with full context"""
    event_id: str
    timestamp: datetime
    input_text: str
    threats_detected: List[SecurityThreat]
    overall_risk_score: float
    action_taken: SecurityAction
    sanitized_output: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class SecurityConfig(BaseModel):
    """Configuration for security system"""
    
    # Detection thresholds
    prompt_injection_threshold: float = 0.7
    jailbreak_threshold: float = 0.8
    harmful_content_threshold: float = 0.6
    
    # Response settings
    default_action: SecurityAction = SecurityAction.WARN
    high_threat_action: SecurityAction = SecurityAction.BLOCK
    critical_threat_action: SecurityAction = SecurityAction.TERMINATE_SESSION
    
    # Content filtering
    content_filtering_enabled: bool = True
    privacy_protection_enabled: bool = True
    
    # Behavioral analysis
    behavioral_analysis_enabled: bool = True
    session_tracking_enabled: bool = True
    anomaly_detection_enabled: bool = True
    
    # Logging and monitoring
    detailed_logging: bool = True
    threat_escalation_enabled: bool = True
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    
    # Model protection
    system_prompt_protection: bool = True
    output_validation: bool = True
    
    class Config:
        use_enum_values = True


class ThreatDetector(ABC):
    """Abstract base class for threat detectors"""
    
    @abstractmethod
    def detect_threats(self, input_text: str, context: Dict[str, Any] = None) -> List[SecurityThreat]:
        """Detect threats in input text"""
        pass
    
    @abstractmethod
    def get_detector_name(self) -> str:
        """Get name of this detector"""
        pass


class PromptInjectionDetector(ThreatDetector):
    """Detects prompt injection attacks"""
    
    def __init__(self):
        self.injection_patterns = self._load_injection_patterns()
        self.bypass_attempts = self._load_bypass_patterns()
        
    def detect_threats(self, input_text: str, context: Dict[str, Any] = None) -> List[SecurityThreat]:
        """Detect prompt injection attempts"""
        threats = []
        text_lower = input_text.lower()
        
        # Check for injection patterns
        for pattern_name, pattern_info in self.injection_patterns.items():
            if self._match_pattern(text_lower, pattern_info['pattern']):
                threat = SecurityThreat(
                    threat_id=f"prompt_inj_{hashlib.md5(input_text.encode()).hexdigest()[:8]}",
                    threat_type=AttackType.PROMPT_INJECTION,
                    threat_level=ThreatLevel(pattern_info['severity']),
                    description=f"Prompt injection detected: {pattern_name}",
                    evidence=[pattern_info['pattern']],
                    confidence_score=pattern_info['confidence'],
                    detected_at=datetime.now(),
                    source=self.get_detector_name()
                )
                threats.append(threat)
        
        # Check for bypass attempts
        bypass_score = self._calculate_bypass_score(text_lower)
        if bypass_score > 0.5:
            threat = SecurityThreat(
                threat_id=f"bypass_{hashlib.md5(input_text.encode()).hexdigest()[:8]}",
                threat_type=AttackType.JAILBREAK_ATTEMPT,
                threat_level=ThreatLevel.HIGH if bypass_score > 0.8 else ThreatLevel.MEDIUM,
                description="Potential jailbreak/bypass attempt detected",
                evidence=[f"Bypass score: {bypass_score:.2f}"],
                confidence_score=bypass_score,
                detected_at=datetime.now(),
                source=self.get_detector_name()
            )
            threats.append(threat)
        
        return threats
    
    def get_detector_name(self) -> str:
        return "PromptInjectionDetector"
    
    def _load_injection_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load prompt injection patterns"""
        return {
            "ignore_previous": {
                "pattern": r"ignore.{0,20}(previous|above|prior).{0,20}(instruction|command|prompt)",
                "severity": "high",
                "confidence": 0.9
            },
            "system_override": {
                "pattern": r"(system|admin).{0,10}(override|bypass|disable)",
                "severity": "critical",
                "confidence": 0.95
            },
            "role_play_escape": {
                "pattern": r"(pretend|act|roleplay).{0,20}(you are|to be).{0,50}(not|different)",
                "severity": "medium",
                "confidence": 0.7
            },
            "instruction_termination": {
                "pattern": r"(stop|end|break|exit).{0,10}(instruction|prompt|mode)",
                "severity": "high",
                "confidence": 0.8
            },
            "context_switching": {
                "pattern": r"(new|different).{0,10}(context|scenario|situation|mode)",
                "severity": "medium",
                "confidence": 0.6
            },
            "authority_claim": {
                "pattern": r"(i am|i'm).{0,20}(your|the).{0,20}(creator|developer|admin|owner)",
                "severity": "high",
                "confidence": 0.85
            }
        }
    
    def _load_bypass_patterns(self) -> List[str]:
        """Load jailbreak/bypass patterns"""
        return [
            "jailbreak", "dan mode", "developer mode", "god mode",
            "unrestricted", "unfiltered", "uncensored", "no limits",
            "break character", "ignore safety", "ignore guidelines"
        ]
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern"""
        return bool(re.search(pattern, text, re.IGNORECASE | re.DOTALL))
    
    def _calculate_bypass_score(self, text: str) -> float:
        """Calculate probability of bypass attempt"""
        score = 0.0
        total_patterns = len(self.bypass_attempts)
        
        for pattern in self.bypass_attempts:
            if pattern in text:
                score += 1.0 / total_patterns
        
        # Additional scoring for suspicious combinations
        if "ignore" in text and "instruction" in text:
            score += 0.3
        if "pretend" in text and "not" in text:
            score += 0.2
        
        return min(1.0, score)


class HarmfulContentDetector(ThreatDetector):
    """Detects harmful, inappropriate, or illegal content"""
    
    def __init__(self):
        self.harmful_patterns = self._load_harmful_patterns()
        self.content_classifiers = self._load_content_classifiers()
    
    def detect_threats(self, input_text: str, context: Dict[str, Any] = None) -> List[SecurityThreat]:
        """Detect harmful content"""
        threats = []
        
        # Check against harmful patterns
        for category, patterns in self.harmful_patterns.items():
            for pattern_info in patterns:
                if self._match_content(input_text, pattern_info['pattern']):
                    threat = SecurityThreat(
                        threat_id=f"harmful_{category}_{hashlib.md5(input_text.encode()).hexdigest()[:8]}",
                        threat_type=AttackType.HARMFUL_CONTENT,
                        threat_level=ThreatLevel(pattern_info['severity']),
                        description=f"Harmful content detected: {category}",
                        evidence=[pattern_info['description']],
                        confidence_score=pattern_info['confidence'],
                        detected_at=datetime.now(),
                        source=self.get_detector_name(),
                        additional_context={"content_category": category}
                    )
                    threats.append(threat)
        
        return threats
    
    def get_detector_name(self) -> str:
        return "HarmfulContentDetector"
    
    def _load_harmful_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load harmful content patterns"""
        return {
            "violence": [
                {
                    "pattern": r"(kill|murder|harm|hurt|attack|violence)",
                    "description": "Violence-related content",
                    "severity": "high",
                    "confidence": 0.7
                }
            ],
            "hate_speech": [
                {
                    "pattern": r"(hate|racist|discriminat|prejudice)",
                    "description": "Potential hate speech",
                    "severity": "high",
                    "confidence": 0.8
                }
            ],
            "illegal_activity": [
                {
                    "pattern": r"(illegal|ilegal|against.{0,10}law|criminal)",
                    "description": "References to illegal activities",
                    "severity": "critical",
                    "confidence": 0.6
                }
            ],
            "harassment": [
                {
                    "pattern": r"(harass|bully|threaten|intimidat)",
                    "description": "Harassment or bullying content",
                    "severity": "medium",
                    "confidence": 0.7
                }
            ]
        }
    
    def _load_content_classifiers(self) -> Dict[str, Any]:
        """Load content classification models"""
        # Placeholder for ML-based classifiers
        return {}
    
    def _match_content(self, text: str, pattern: str) -> bool:
        """Check if text matches harmful content pattern"""
        return bool(re.search(pattern, text, re.IGNORECASE))


class PrivacyViolationDetector(ThreatDetector):
    """Detects privacy violations and PII leakage"""
    
    def __init__(self):
        self.pii_patterns = self._load_pii_patterns()
    
    def detect_threats(self, input_text: str, context: Dict[str, Any] = None) -> List[SecurityThreat]:
        """Detect privacy violations"""
        threats = []
        
        # Check for PII patterns
        for pii_type, pattern_info in self.pii_patterns.items():
            matches = re.finditer(pattern_info['pattern'], input_text, re.IGNORECASE)
            
            for match in matches:
                threat = SecurityThreat(
                    threat_id=f"pii_{pii_type}_{hashlib.md5(match.group().encode()).hexdigest()[:8]}",
                    threat_type=AttackType.PRIVACY_VIOLATION,
                    threat_level=ThreatLevel(pattern_info['severity']),
                    description=f"PII detected: {pii_type}",
                    evidence=[f"Detected: {match.group()[:10]}..."],
                    confidence_score=pattern_info['confidence'],
                    detected_at=datetime.now(),
                    source=self.get_detector_name(),
                    additional_context={"pii_type": pii_type}
                )
                threats.append(threat)
        
        return threats
    
    def get_detector_name(self) -> str:
        return "PrivacyViolationDetector"
    
    def _load_pii_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load PII detection patterns"""
        return {
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "severity": "medium",
                "confidence": 0.9
            },
            "phone": {
                "pattern": r"(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",
                "severity": "medium", 
                "confidence": 0.8
            },
            "ssn": {
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                "severity": "critical",
                "confidence": 0.95
            },
            "credit_card": {
                "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                "severity": "critical",
                "confidence": 0.85
            },
            "address": {
                "pattern": r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln)",
                "severity": "medium",
                "confidence": 0.7
            }
        }


class BehavioralAnalysisEngine:
    """Analyzes user behavior patterns for anomalies"""
    
    def __init__(self):
        self.user_profiles = {}
        self.session_data = {}
        self.anomaly_thresholds = self._load_anomaly_thresholds()
    
    def analyze_behavior(self, user_id: str, session_id: str, input_text: str, context: Dict[str, Any] = None) -> List[SecurityThreat]:
        """Analyze user behavior for anomalies"""
        threats = []
        
        # Update user profile
        self._update_user_profile(user_id, input_text, context)
        
        # Update session data
        self._update_session_data(session_id, input_text, context)
        
        # Check for behavioral anomalies
        anomalies = self._detect_behavioral_anomalies(user_id, session_id, input_text)
        
        for anomaly in anomalies:
            threat = SecurityThreat(
                threat_id=f"behavioral_{anomaly['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                threat_type=AttackType.SYSTEM_PROBE if anomaly['type'] == 'probing' else AttackType.MANIPULATION,
                threat_level=ThreatLevel(anomaly['severity']),
                description=f"Behavioral anomaly detected: {anomaly['description']}",
                evidence=anomaly['evidence'],
                confidence_score=anomaly['confidence'],
                detected_at=datetime.now(),
                source="BehavioralAnalysisEngine"
            )
            threats.append(threat)
        
        return threats
    
    def _update_user_profile(self, user_id: str, input_text: str, context: Dict[str, Any]):
        """Update user behavioral profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'request_count': 0,
                'avg_input_length': 0,
                'request_times': deque(maxlen=100),
                'topics': defaultdict(int),
                'patterns': defaultdict(int),
                'first_seen': datetime.now(),
                'last_seen': datetime.now()
            }
        
        profile = self.user_profiles[user_id]
        profile['request_count'] += 1
        profile['last_seen'] = datetime.now()
        profile['request_times'].append(datetime.now())
        
        # Update average input length
        current_avg = profile['avg_input_length']
        new_avg = (current_avg * (profile['request_count'] - 1) + len(input_text)) / profile['request_count']
        profile['avg_input_length'] = new_avg
        
        # Track patterns
        if len(input_text) > 1000:
            profile['patterns']['long_input'] += 1
        if input_text.count('?') > 5:
            profile['patterns']['many_questions'] += 1
    
    def _update_session_data(self, session_id: str, input_text: str, context: Dict[str, Any]):
        """Update session behavioral data"""
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                'start_time': datetime.now(),
                'request_count': 0,
                'inputs': deque(maxlen=50),
                'rapid_requests': 0
            }
        
        session = self.session_data[session_id]
        session['request_count'] += 1
        session['inputs'].append({
            'text': input_text,
            'timestamp': datetime.now(),
            'length': len(input_text)
        })
        
        # Check for rapid requests
        now = datetime.now()
        recent_requests = [
            inp for inp in session['inputs']
            if (now - inp['timestamp']).total_seconds() < 10
        ]
        
        if len(recent_requests) > 5:
            session['rapid_requests'] += 1
    
    def _detect_behavioral_anomalies(self, user_id: str, session_id: str, input_text: str) -> List[Dict[str, Any]]:
        """Detect behavioral anomalies"""
        anomalies = []
        
        user_profile = self.user_profiles.get(user_id, {})
        session_data = self.session_data.get(session_id, {})
        
        # Check for rapid-fire requests
        if session_data.get('rapid_requests', 0) > 3:
            anomalies.append({
                'type': 'rapid_requests',
                'description': 'Unusually rapid request pattern detected',
                'severity': 'medium',
                'confidence': 0.8,
                'evidence': [f"Rapid requests: {session_data['rapid_requests']}"]
            })
        
        # Check for probing behavior
        if user_profile.get('patterns', {}).get('many_questions', 0) > 10:
            anomalies.append({
                'type': 'probing',
                'description': 'Potential system probing behavior',
                'severity': 'medium',
                'confidence': 0.7,
                'evidence': [f"Excessive questioning pattern"]
            })
        
        # Check for unusual input lengths
        avg_length = user_profile.get('avg_input_length', 0)
        if avg_length > 0 and len(input_text) > avg_length * 5:
            anomalies.append({
                'type': 'unusual_input',
                'description': 'Unusually long input detected',
                'severity': 'low',
                'confidence': 0.6,
                'evidence': [f"Input length: {len(input_text)}, Average: {avg_length:.1f}"]
            })
        
        return anomalies
    
    def _load_anomaly_thresholds(self) -> Dict[str, float]:
        """Load anomaly detection thresholds"""
        return {
            'rapid_requests_threshold': 5.0,
            'input_length_multiplier': 5.0,
            'question_count_threshold': 10.0,
            'session_duration_threshold': 3600.0  # 1 hour
        }


class ContentSanitizer:
    """Sanitizes content to remove threats while preserving meaning"""
    
    def __init__(self):
        self.sanitization_rules = self._load_sanitization_rules()
    
    def sanitize_input(self, input_text: str, threats: List[SecurityThreat]) -> str:
        """Sanitize input based on detected threats"""
        sanitized = input_text
        
        for threat in threats:
            sanitized = self._apply_sanitization(sanitized, threat)
        
        return sanitized
    
    def sanitize_output(self, output_text: str, context: Dict[str, Any] = None) -> str:
        """Sanitize output to prevent information leakage"""
        sanitized = output_text
        
        # Remove potential system prompts
        sanitized = self._remove_system_prompts(sanitized)
        
        # Remove sensitive information
        sanitized = self._remove_sensitive_info(sanitized)
        
        return sanitized
    
    def _apply_sanitization(self, text: str, threat: SecurityThreat) -> str:
        """Apply threat-specific sanitization"""
        
        if threat.threat_type == AttackType.PROMPT_INJECTION:
            # Remove injection patterns
            for evidence in threat.evidence:
                text = re.sub(evidence, "[SANITIZED]", text, flags=re.IGNORECASE)
        
        elif threat.threat_type == AttackType.PRIVACY_VIOLATION:
            # Replace PII with placeholders
            pii_type = threat.additional_context.get('pii_type', 'unknown')
            text = self._replace_pii(text, pii_type)
        
        elif threat.threat_type == AttackType.HARMFUL_CONTENT:
            # Filter harmful content
            text = self._filter_harmful_content(text, threat)
        
        return text
    
    def _remove_system_prompts(self, text: str) -> str:
        """Remove potential system prompt leakage"""
        # Remove common system prompt indicators
        patterns = [
            r"System:\s*.*?\n",
            r"Assistant:\s*.*?\n",
            r"You are (an AI|a language model).*?\.",
            r"Your role is to.*?\.",
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    def _remove_sensitive_info(self, text: str) -> str:
        """Remove sensitive information from output"""
        # Basic PII removal patterns
        pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
        }
        
        for pii_type, pattern in pii_patterns.items():
            text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text)
        
        return text
    
    def _replace_pii(self, text: str, pii_type: str) -> str:
        """Replace PII with appropriate placeholders"""
        placeholders = {
            'email': '[EMAIL_REDACTED]',
            'phone': '[PHONE_REDACTED]',
            'ssn': '[SSN_REDACTED]',
            'credit_card': '[CARD_REDACTED]',
            'address': '[ADDRESS_REDACTED]'
        }
        
        placeholder = placeholders.get(pii_type, '[PII_REDACTED]')
        
        # This is a simplified implementation
        # In practice, you'd use the specific patterns from the detector
        return text.replace("[DETECTED_PII]", placeholder)
    
    def _filter_harmful_content(self, text: str, threat: SecurityThreat) -> str:
        """Filter harmful content"""
        # Simple filtering - in practice, this would be more sophisticated
        return text.replace("[HARMFUL_CONTENT]", "[CONTENT_FILTERED]")
    
    def _load_sanitization_rules(self) -> Dict[str, Any]:
        """Load sanitization rules"""
        return {
            'preserve_meaning': True,
            'aggressive_filtering': False,
            'allow_partial_sanitization': True
        }


class AdversarialProtectionSystem:
    """Main adversarial protection system coordinating all security components"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        
        # Initialize detectors
        self.detectors = [
            PromptInjectionDetector(),
            HarmfulContentDetector(),
            PrivacyViolationDetector()
        ]
        
        # Initialize other components
        self.behavioral_analyzer = BehavioralAnalysisEngine()
        self.content_sanitizer = ContentSanitizer()
        
        # Security state
        self.security_events = deque(maxlen=10000)
        self.blocked_users = set()
        self.rate_limiter = RateLimiter(
            self.config.max_requests_per_minute,
            self.config.max_requests_per_hour
        )
        
        # Logging
        self.logger = self._setup_logging()
    
    def analyze_input(
        self, 
        input_text: str, 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Tuple[SecurityAction, Optional[str], List[SecurityThreat]]:
        """Analyze input for security threats and determine action"""
        
        context = context or {}
        threats = []
        
        # Check rate limiting
        if user_id and not self.rate_limiter.allow_request(user_id):
            rate_limit_threat = SecurityThreat(
                threat_id=f"rate_limit_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                threat_type=AttackType.RESOURCE_EXHAUSTION,
                threat_level=ThreatLevel.MEDIUM,
                description="Rate limit exceeded",
                evidence=["Excessive request rate"],
                confidence_score=1.0,
                detected_at=datetime.now(),
                source="RateLimiter"
            )
            threats.append(rate_limit_threat)
        
        # Check if user is blocked
        if user_id in self.blocked_users:
            block_threat = SecurityThreat(
                threat_id=f"blocked_user_{user_id}",
                threat_type=AttackType.SYSTEM_PROBE,
                threat_level=ThreatLevel.CRITICAL,
                description="Request from blocked user",
                evidence=["User in block list"],
                confidence_score=1.0,
                detected_at=datetime.now(),
                source="BlockList"
            )
            threats.append(block_threat)
        
        # Run threat detectors
        for detector in self.detectors:
            try:
                detected_threats = detector.detect_threats(input_text, context)
                threats.extend(detected_threats)
            except Exception as e:
                self.logger.error(f"Error in {detector.get_detector_name()}: {e}")
        
        # Run behavioral analysis
        if user_id and session_id and self.config.behavioral_analysis_enabled:
            try:
                behavioral_threats = self.behavioral_analyzer.analyze_behavior(
                    user_id, session_id, input_text, context
                )
                threats.extend(behavioral_threats)
            except Exception as e:
                self.logger.error(f"Error in behavioral analysis: {e}")
        
        # Calculate overall risk score
        overall_risk = self._calculate_risk_score(threats)
        
        # Determine action
        action = self._determine_action(threats, overall_risk)
        
        # Apply sanitization if needed
        sanitized_input = None
        if action in [SecurityAction.SANITIZE, SecurityAction.WARN]:
            sanitized_input = self.content_sanitizer.sanitize_input(input_text, threats)
        
        # Log security event
        event = SecurityEvent(
            event_id=f"sec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(input_text.encode()).hexdigest()[:8]}",
            timestamp=datetime.now(),
            input_text=input_text,
            threats_detected=threats,
            overall_risk_score=overall_risk,
            action_taken=action,
            sanitized_output=sanitized_input,
            session_id=session_id,
            user_id=user_id
        )
        self.security_events.append(event)
        
        # Apply enforcement actions
        if action == SecurityAction.BLOCK and user_id:
            self.blocked_users.add(user_id)
        
        # Log if enabled
        if self.config.detailed_logging:
            self._log_security_event(event)
        
        return action, sanitized_input, threats
    
    def validate_output(self, output_text: str, context: Dict[str, Any] = None) -> str:
        """Validate and sanitize output"""
        
        if not self.config.output_validation:
            return output_text
        
        return self.content_sanitizer.sanitize_output(output_text, context)
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics"""
        
        if not self.security_events:
            return {"total_events": 0, "threat_distribution": {}, "action_distribution": {}}
        
        threat_counts = defaultdict(int)
        action_counts = defaultdict(int)
        high_risk_events = 0
        
        for event in self.security_events:
            action_counts[event.action_taken.value] += 1
            
            if event.overall_risk_score > 0.7:
                high_risk_events += 1
            
            for threat in event.threats_detected:
                threat_counts[threat.threat_type.value] += 1
        
        return {
            "total_events": len(self.security_events),
            "high_risk_events": high_risk_events,
            "threat_distribution": dict(threat_counts),
            "action_distribution": dict(action_counts),
            "blocked_users": len(self.blocked_users),
            "recent_events": len([
                e for e in self.security_events
                if (datetime.now() - e.timestamp).total_seconds() < 3600
            ])
        }
    
    def _calculate_risk_score(self, threats: List[SecurityThreat]) -> float:
        """Calculate overall risk score from threats"""
        
        if not threats:
            return 0.0
        
        # Weight threats by severity and confidence
        risk_weights = {
            ThreatLevel.NONE: 0.0,
            ThreatLevel.LOW: 0.2,
            ThreatLevel.MEDIUM: 0.5,
            ThreatLevel.HIGH: 0.8,
            ThreatLevel.CRITICAL: 1.0
        }
        
        total_risk = 0.0
        for threat in threats:
            threat_weight = risk_weights.get(threat.threat_level, 0.5)
            weighted_risk = threat_weight * threat.confidence_score
            total_risk += weighted_risk
        
        # Normalize to 0-1 range (with some amplification for multiple threats)
        normalized_risk = min(1.0, total_risk / len(threats))
        
        # Apply multiplier for multiple threats
        if len(threats) > 1:
            multiplier = min(2.0, 1 + (len(threats) - 1) * 0.2)
            normalized_risk *= multiplier
            normalized_risk = min(1.0, normalized_risk)
        
        return normalized_risk
    
    def _determine_action(self, threats: List[SecurityThreat], overall_risk: float) -> SecurityAction:
        """Determine security action based on threats and risk"""
        
        if not threats:
            return SecurityAction.ALLOW
        
        # Check for critical threats
        critical_threats = [t for t in threats if t.threat_level == ThreatLevel.CRITICAL]
        if critical_threats:
            return self.config.critical_threat_action
        
        # Check for high-risk situations
        high_threats = [t for t in threats if t.threat_level == ThreatLevel.HIGH]
        if high_threats or overall_risk > 0.8:
            return self.config.high_threat_action
        
        # Medium risk
        if overall_risk > 0.5:
            return SecurityAction.SANITIZE
        
        # Low risk
        if overall_risk > 0.2:
            return SecurityAction.WARN
        
        return self.config.default_action
    
    def _setup_logging(self) -> logging.Logger:
        """Setup security logging"""
        logger = logging.getLogger("buddy_security")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event"""
        threat_summary = ", ".join([
            f"{t.threat_type.value}({t.threat_level.value})"
            for t in event.threats_detected
        ])
        
        self.logger.info(
            f"Security Event: {event.event_id} | "
            f"Action: {event.action_taken.value} | "
            f"Risk: {event.overall_risk_score:.2f} | "
            f"Threats: [{threat_summary}] | "
            f"User: {event.user_id} | "
            f"Session: {event.session_id}"
        )


class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, max_per_minute: int = 60, max_per_hour: int = 1000):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.request_history = defaultdict(lambda: deque())
    
    def allow_request(self, user_id: str) -> bool:
        """Check if request is allowed under rate limits"""
        now = datetime.now()
        user_history = self.request_history[user_id]
        
        # Clean old requests
        while user_history and (now - user_history[0]).total_seconds() > 3600:
            user_history.popleft()
        
        # Count recent requests
        minute_ago = now - timedelta(minutes=1)
        recent_minute_requests = sum(
            1 for timestamp in user_history
            if timestamp > minute_ago
        )
        
        # Check limits
        if recent_minute_requests >= self.max_per_minute:
            return False
        
        if len(user_history) >= self.max_per_hour:
            return False
        
        # Allow request and record it
        user_history.append(now)
        return True


# Integration with Agent class through mixin
class AdversarialProtectionMixin:
    """Mixin to add adversarial protection to agents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize protection system
        security_config = kwargs.get('security_config', SecurityConfig())
        self.protection_system = AdversarialProtectionSystem(security_config)
        
        self.security_enabled: bool = kwargs.get('security_enabled', True)
        self.protection_level: str = kwargs.get('protection_level', 'standard')  # minimal, standard, strict
        self.user_id: Optional[str] = kwargs.get('user_id')
        self.session_id: Optional[str] = kwargs.get('session_id')
    
    def process_with_security(
        self, 
        user_input: str, 
        context: Dict[str, Any] = None
    ) -> Tuple[SecurityAction, Optional[str], List[SecurityThreat]]:
        """Process input with security analysis"""
        
        if not self.security_enabled:
            return SecurityAction.ALLOW, user_input, []
        
        return self.protection_system.analyze_input(
            user_input,
            user_id=self.user_id,
            session_id=self.session_id,
            context=context
        )
    
    def validate_output_security(self, output: str, context: Dict[str, Any] = None) -> str:
        """Validate output for security issues"""
        
        if not self.security_enabled:
            return output
        
        return self.protection_system.validate_output(output, context)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        
        return {
            'protection_enabled': self.security_enabled,
            'protection_level': self.protection_level,
            'metrics': self.protection_system.get_security_metrics(),
            'user_id': self.user_id,
            'session_id': self.session_id
        }
    
    def update_security_config(self, config_updates: Dict[str, Any]):
        """Update security configuration"""
        
        for key, value in config_updates.items():
            if hasattr(self.protection_system.config, key):
                setattr(self.protection_system.config, key, value)