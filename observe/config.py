"""
Configuration system for Dhruva Observability Plugin

Handles environment variables, defaults, and plugin configuration.
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PluginConfig:
    """Configuration for Dhruva Observability Plugin."""
    
    # Core settings
    enabled: bool = False
    debug: bool = False
    
    # Endpoint settings
    metrics_path: str = "/enterprise/metrics"
    health_path: str = "/enterprise/health"
    
    # Monitoring settings
    collect_system_metrics: bool = True
    collect_gpu_metrics: bool = True
    collect_db_metrics: bool = True
    
    # SLA settings
    availability_target: float = 100.0
    response_time_target: float = 1.0
    throughput_target: float = 20.0
    
    # Advanced settings
    max_completed_requests: int = 1000
    metrics_update_interval: int = 10
    system_metrics_interval: int = 5
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        # Override with environment variables if set
        if os.getenv("OBSERVE_UTIL_ENABLED") is not None:
            self.enabled = os.getenv("OBSERVE_UTIL_ENABLED", "false").lower() == "true"
        if os.getenv("OBSERVE_UTIL_DEBUG") is not None:
            self.debug = os.getenv("OBSERVE_UTIL_DEBUG", "false").lower() == "true"
        
        self.metrics_path = os.getenv("OBSERVE_UTIL_METRICS_PATH", self.metrics_path)
        self.health_path = os.getenv("OBSERVE_UTIL_HEALTH_PATH", self.health_path)
        
        self.collect_system_metrics = os.getenv("OBSERVE_UTIL_COLLECT_SYSTEM_METRICS", "true").lower() == "true"                                                                                                
        self.collect_gpu_metrics = os.getenv("OBSERVE_UTIL_COLLECT_GPU_METRICS", "true").lower() == "true"                                                                                                      
        self.collect_db_metrics = os.getenv("OBSERVE_UTIL_COLLECT_DB_METRICS", "true").lower() == "true"                                                                                                        
        
        # SLA targets
        self.availability_target = float(os.getenv("OBSERVE_UTIL_AVAILABILITY_TARGET", self.availability_target))                                                                                               
        self.response_time_target = float(os.getenv("OBSERVE_UTIL_RESPONSE_TIME_TARGET", self.response_time_target))                                                                                            
        self.throughput_target = float(os.getenv("OBSERVE_UTIL_THROUGHPUT_TARGET", self.throughput_target))                                                                                                     
        
        # Advanced settings
        self.max_completed_requests = int(os.getenv("OBSERVE_UTIL_MAX_COMPLETED_REQUESTS", self.max_completed_requests))                                                                                        
        self.metrics_update_interval = int(os.getenv("OBSERVE_UTIL_METRICS_UPDATE_INTERVAL", self.metrics_update_interval))                                                                                     
        self.system_metrics_interval = int(os.getenv("OBSERVE_UTIL_SYSTEM_METRICS_INTERVAL", self.system_metrics_interval))                                                                                     
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enabled": self.enabled,
            "debug": self.debug,
            "metrics_path": self.metrics_path,
            "health_path": self.health_path,
            "collect_system_metrics": self.collect_system_metrics,
            "collect_gpu_metrics": self.collect_gpu_metrics,
            "collect_db_metrics": self.collect_db_metrics,
            "availability_target": self.availability_target,
            "response_time_target": self.response_time_target,
            "throughput_target": self.throughput_target,
            "max_completed_requests": self.max_completed_requests,
            "metrics_update_interval": self.metrics_update_interval,
            "system_metrics_interval": self.system_metrics_interval,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PluginConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> "PluginConfig":
        """Create configuration from environment variables."""
        return cls()


# Global configuration instance
config = PluginConfig.from_env()
