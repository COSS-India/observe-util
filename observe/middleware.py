"""
Middleware for Dhruva Observability Plugin

Handles request tracking, service detection, and metrics collection.
"""
import time
import jwt
import json
import base64
import io
import wave
import hashlib
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .config import PluginConfig
from .metrics import MetricsCollector


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking requests and collecting metrics."""
    
    def __init__(self, app, metrics_collector: Optional[MetricsCollector] = None, 
                 config: Optional[PluginConfig] = None):
        """Initialize middleware."""
        super().__init__(app)
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.config = config or PluginConfig()
    
    async def dispatch(self, request: Request, call_next):
        """Process request through middleware."""
        if not self.config.enabled:
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract metadata from request
        path = request.url.path
        method = request.method
        headers = request.headers
        
        # Extract organization and app (including from JWT token)
        organization, app = self._extract_customer_app(request)
        
        # Detect service type
        service_type = self._detect_service_type(path)
        
        # Extract real character count for TTS, translation, and ASR requests
        # IMPORTANT: We need to read and restore the body to avoid consuming the stream
        tts_characters = 0
        translation_characters = 0
        asr_audio_length = 0
        if method == "POST" and service_type in ["tts", "translation", "asr"]:
            body_bytes = await request.body()
            # Restore the body for downstream handlers
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
            
            # Extract metrics from the body
            if service_type == "tts":
                tts_characters = self._extract_tts_characters_from_body(body_bytes)
            elif service_type == "translation":
                translation_characters = self._extract_translation_characters_from_body(body_bytes)
            elif service_type == "asr":
                asr_audio_length = self._extract_asr_audio_length_from_body(body_bytes)
        
        # Debug logging
        if self.config.debug:
            print(f"🔍 Request: {method} {path} -> Service: {service_type}, Organization: {organization}, App: {app}")
            if tts_characters > 0:
                print(f"📝 TTS Characters detected: {tts_characters}")
            if translation_characters > 0:
                print(f"📝 Translation Characters detected: {translation_characters}")
            if asr_audio_length > 0:
                print(f"🎵 ASR Audio length detected: {asr_audio_length:.2f} seconds")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Track request
        try:
            self.metrics_collector.track_request(
                organization=organization,
                app=app,
                method=method,
                endpoint=path,
                status_code=response.status_code,
                duration=duration,
                service_type=service_type
            )
            
            # Track additional metrics based on service type
            self._track_additional_metrics(organization, app, service_type, path, duration, tts_characters, translation_characters, asr_audio_length)
            
        except Exception as e:
            # Don't let metrics collection break the request
            if self.config.debug:
                print(f"⚠️ Metrics collection failed: {e}")

        return response
    
    def _decode_jwt_token(self, authorization_header: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token from authorization header."""
        try:
            # Extract token from "Bearer <token>" format
            if not authorization_header.startswith("Bearer "):
                return None
            
            token = authorization_header[7:]  # Remove "Bearer " prefix
            
            # Decode without verification to get claims (for customer name extraction)
            # In production, you might want to verify the token with proper secret
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            
            return decoded_token
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ JWT decoding failed: {e}")
            return None
    
    @staticmethod
    def _get_organization_from_api_key(api_key: str) -> str:
        """Map API key to organization name using consistent hashing."""
        # Organization names
        organizations = ["irctc", "kisanmitra", "bashadaan", "beml"]
        
        # Use hash of API key to consistently map to same organization
        hash_value = int(hashlib.md5(api_key.encode()).hexdigest(), 16)
        org_index = hash_value % len(organizations)
        
        return organizations[org_index]
    
    def _extract_customer_from_token(self, request: Request) -> Optional[str]:
        """Extract customer name from JWT token in authorization header."""
        auth_header = request.headers.get("authorization", "")
        
        if auth_header:
            decoded_token = self._decode_jwt_token(auth_header)
            if decoded_token:
                # Extract customer name from 'name' field in token
                customer_name = decoded_token.get("name")
                if customer_name:
                    if self.config.debug:
                        print(f"🔑 Extracted customer from JWT: {customer_name}")
                    return customer_name
                
                # Fallback: try to extract from 'sub' field if 'name' is not available
                sub = decoded_token.get("sub")
                if sub:
                    if self.config.debug:
                        print(f"🔑 Using 'sub' field as customer: {sub}")
                    return sub
        
        return None
    
    def _extract_customer_app(self, request: Request) -> tuple:
        """Extract organization and app from request headers and JWT token."""
        # First try to get customer from JWT token
        organization = self._extract_customer_from_token(request)
        
        # If not found in token, fallback to header
        if organization is None:
            organization = request.headers.get("X-Customer-ID")
        
        # Extract organization from API key
        auth_header = request.headers.get("authorization", "")
        
        if auth_header and organization is None:
            # Extract the API key (remove "Bearer " prefix if present)
            api_key = auth_header
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            
            # Map API key to organization (overrides any previous value)
            organization = self._get_organization_from_api_key(api_key)
            
            if self.config.debug:
                print(f"🏢 Mapped API key to organization: {organization}")
        
        # If still no organization, use "unknown"
        if organization is None:
            organization = "unknown"
            if self.config.debug:
                print(f"⚠️ No organization found, using: {organization}")
        
        # Get app from header or use "unknown"
        app = request.headers.get("X-App-ID")
        if app is None:
            app = "unknown"
            
        return organization, app
    
    def _detect_service_type(self, path: str) -> str:
        """Detect service type from URL path."""
        path_lower = path.lower()
        
        # Check for specific service patterns
        if any(pattern in path_lower for pattern in ["/translation", "/nmt", "/translate"]):
            return "translation"
        elif any(pattern in path_lower for pattern in ["/asr", "/transcribe", "/speech"]):
            return "asr"
        elif any(pattern in path_lower for pattern in ["/tts", "/synthesize", "/speak"]):
            return "tts"
        elif any(pattern in path_lower for pattern in ["/ner", "/entity", "/entities"]):
            return "ner"
        elif any(pattern in path_lower for pattern in ["/transliteration", "/xlit", "/transliterate"]):
            return "transliteration"
        elif any(pattern in path_lower for pattern in ["/llm", "/generate", "/chat", "/completion"]):
            return "llm"
        elif any(pattern in path_lower for pattern in ["/enterprise", "/health", "/metrics", "/config"]):
            return "enterprise"
        elif any(pattern in path_lower for pattern in ["/docs", "/openapi", "/redoc"]):
            return "documentation"
        else:
            return "unknown"
    
    def _track_additional_metrics(self, organization: str, app: str, service_type: str, path: str, duration: float, tts_characters: int = 0, translation_characters: int = 0, asr_audio_length: float = 0):
        """Track additional metrics based on service type."""
        try:
            # Track component latency
            self.metrics_collector.track_component_latency(
                organization=organization,
                app=app,
                component=service_type,
                duration=duration
            )
            
            # Track data processing based on service type
            if service_type == "llm":
                # Mock LLM token processing
                tokens = self._estimate_llm_tokens(path)
                self.metrics_collector.track_llm_tokens(
                    organization=organization,
                    app=app,
                    model="gpt-3.5-turbo",  # Mock model
                    tokens=tokens
                )
            elif service_type == "tts":
                # Track real TTS character count
                if tts_characters > 0:
                    self.metrics_collector.track_tts_characters(
                        organization=organization,
                        app=app,
                        language="en",  # Default language
                        characters=tts_characters
                    )
                    if self.config.debug:
                        print(f"📊 Tracked real TTS characters: {tts_characters}")
            elif service_type == "translation":
                # Track real translation character count
                if translation_characters > 0:
                    self.metrics_collector.track_nmt_characters(
                        organization=organization,
                        app=app,
                        source_lang="en",  # Default source language
                        target_lang="hi",  # Default target language
                        characters=translation_characters
                    )
                    if self.config.debug:
                        print(f"📊 Tracked real translation characters: {translation_characters}")
            elif service_type == "asr":
                # Track real ASR audio length
                if asr_audio_length > 0:
                    self.metrics_collector.track_asr_audio_length(
                        organization=organization,
                        app=app,
                        language="en",  # Default language
                        audio_seconds=asr_audio_length
                    )
                    if self.config.debug:
                        print(f"📊 Tracked real ASR audio length: {asr_audio_length:.2f} seconds")
            
            # Update SLA compliance (mock calculation)
            compliance = self._calculate_sla_compliance(service_type, duration)
            self.metrics_collector.update_sla_compliance(
                organization=organization,
                app=app,
                sla_type=f"{service_type}_availability",
                compliance_percent=compliance
            )
            
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ Additional metrics tracking failed: {e}")
    
    def _estimate_llm_tokens(self, path: str) -> int:
        """Estimate LLM tokens based on path."""
        # Mock estimation - in real implementation, this would analyze request content
        return 100  # Mock value
    
    
    
    def _extract_tts_characters_from_body(self, body_bytes: bytes) -> int:
        """Extract real character count from TTS request body."""
        try:
            if not body_bytes:
                return 0
            
            # Parse JSON request
            request_data = json.loads(body_bytes.decode('utf-8'))
            
            # Extract character count from TTS input
            total_characters = 0
            if 'input' in request_data:
                for input_item in request_data['input']:
                    if 'source' in input_item:
                        total_characters += len(input_item['source'])
            
            return total_characters
            
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ Failed to extract TTS characters: {e}")
            return 0
    
    def _extract_translation_characters_from_body(self, body_bytes: bytes) -> int:
        """Extract real character count from translation request body."""
        try:
            if not body_bytes:
                return 0
            
            # Parse JSON request
            request_data = json.loads(body_bytes.decode('utf-8'))
            
            # Extract character count from translation input
            total_characters = 0
            if 'input' in request_data:
                for input_item in request_data['input']:
                    if 'source' in input_item:
                        total_characters += len(input_item['source'])
            
            return total_characters
            
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ Failed to extract translation characters: {e}")
            return 0
    
    def _extract_asr_audio_length_from_body(self, body_bytes: bytes) -> float:
        """Extract real audio length in seconds from ASR request body."""
        try:
            if not body_bytes:
                return 0.0
            
            # Parse JSON request
            request_data = json.loads(body_bytes.decode('utf-8'))
            
            # Extract audio length from ASR input
            total_audio_length = 0.0
            audio_items_found = 0
            
            # Check for standard ASR format: {"audio": [...], "config": {...}}
            if 'audio' in request_data:
                for audio_item in request_data['audio']:
                    if 'audioContent' in audio_item:
                        # Decode base64 audio and calculate length
                        audio_length = self._calculate_audio_length_from_base64(audio_item['audioContent'])
                        total_audio_length += audio_length
                        audio_items_found += 1
                        if self.config.debug:
                            print(f"🎵 ASR audio item {audio_items_found}: {audio_length:.2f} seconds")
            # Also check for pipeline format: {"inputData": {"audio": [...]}, ...}
            elif 'inputData' in request_data and 'audio' in request_data['inputData']:
                for audio_item in request_data['inputData']['audio']:
                    if 'audioContent' in audio_item:
                        # Decode base64 audio and calculate length
                        audio_length = self._calculate_audio_length_from_base64(audio_item['audioContent'])
                        total_audio_length += audio_length
                        audio_items_found += 1
                        if self.config.debug:
                            print(f"🎵 ASR audio item {audio_items_found}: {audio_length:.2f} seconds")
            else:
                if self.config.debug:
                    print(f"⚠️ ASR request structure not recognized. Keys: {list(request_data.keys())}")
            
            return total_audio_length
            
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ Failed to extract ASR audio length: {e}")
            return 0.0
    
    def _calculate_audio_length_from_base64(self, base64_audio: str) -> float:
        """Calculate audio length in seconds from base64 encoded audio."""
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(base64_audio)
            
            # Create a BytesIO object to read the audio data
            audio_buffer = io.BytesIO(audio_data)
            
            # Try to read as WAV file
            with wave.open(audio_buffer, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                if self.config.debug:
                    print(f"✅ Calculated WAV audio length: {duration:.2f} seconds ({frames} frames @ {sample_rate} Hz)")
                return duration
                
        except Exception as e:
            if self.config.debug:
                print(f"⚠️ Failed to parse as WAV file: {e}, trying fallback estimation")
            # Fallback: estimate based on data size (rough approximation)
            try:
                audio_data = base64.b64decode(base64_audio)
                # Rough estimate: 16-bit audio at 16kHz = 32KB per second
                estimated_duration = len(audio_data) / 32000
                if self.config.debug:
                    print(f"📊 Estimated audio length: {estimated_duration:.2f} seconds (based on {len(audio_data)} bytes)")
                return estimated_duration
            except Exception as fallback_error:
                if self.config.debug:
                    print(f"❌ Fallback estimation also failed: {fallback_error}")
                return 0.0
    
    def _calculate_sla_compliance(self, service_type: str, duration: float) -> float:
        """Calculate SLA compliance based on service type and duration."""
        # Mock SLA compliance calculation
        if service_type == "llm":
            return 99.5 if duration < 2.0 else 95.0
        elif service_type == "tts":
            return 99.8 if duration < 1.0 else 97.0
        elif service_type == "translation":
            return 99.9 if duration < 0.5 else 98.0
        else:
            return 99.0