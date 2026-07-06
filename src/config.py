"""Application configuration and settings.

Centralized configuration management with persistent storage.
"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration file path (class-level constant)
CONFIG_FILE = Path.home() / ".salesforce-tools" / "config.json"


@dataclass
class AppConfig:
    """Application configuration."""

    # Extraction settings
    chunk_size: int = 200
    default_output_dir: str = field(default_factory=lambda: str(Path("./salesforce_extracts").resolve()))
    
    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["csv", "json"])
    json_flatten: bool = False
    
    # Viewer settings
    page_size: int = 100
    
    # UI settings
    theme: str = "dark"
    window_width: int = 1500
    window_height: int = 960
    
    # Performance
    max_workers: int = 4
    cli_timeout: int = 40
    
    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from file or return defaults.
        
        Returns:
            AppConfig instance
        """
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded config from {CONFIG_FILE}")
                return cls(**data)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
                return cls()
        return cls()
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            config_data = asdict(self)
            with open(CONFIG_FILE, "w") as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"Config saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def update(self, **kwargs) -> None:
        """Update configuration values.
        
        Args:
            **kwargs: Config values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
