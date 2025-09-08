"""Configuration module placeholder for daglab.

This is a temporary placeholder that provides default settings
for the runtime modules. The full configuration system will be
implemented as part of the configuration management phase.
"""

import os
from pathlib import Path


class Settings:
    """Default settings for daglab runtime."""
    
    def __init__(self):
        # Logging settings
        self.log_level = os.environ.get('DAGLAB_LOG_LEVEL', 'INFO')
        self.log_format = os.environ.get('DAGLAB_LOG_FORMAT', 'json')
        self.log_to_file = os.environ.get('DAGLAB_LOG_TO_FILE', 'true').lower() == 'true'
        self.log_dir = os.environ.get('DAGLAB_LOG_DIR', './logs')
        self.log_max_bytes = int(os.environ.get('DAGLAB_LOG_MAX_BYTES', '10485760'))  # 10MB
        self.log_backup_count = int(os.environ.get('DAGLAB_LOG_BACKUP_COUNT', '5'))
        
        # Telemetry settings
        self.telemetry_enabled = os.environ.get('DAGLAB_TELEMETRY_ENABLED', 'true').lower() == 'true'
        self.telemetry_level = os.environ.get('DAGLAB_TELEMETRY_LEVEL', 'standard')
        
        # Data directory
        self.data_dir = os.environ.get('DAGLAB_DATA_DIR', './data')


# Global settings instance
settings = Settings()