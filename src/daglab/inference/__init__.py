"""Inference and ML model integration."""

from typing import Any, Dict, List, Optional, Protocol
import numpy as np


class Model(Protocol):
    """Protocol for ML models."""
    
    def predict(self, inputs: Any) -> Any:
        """Make predictions."""
        ...
    
    def load(self, path: str) -> None:
        """Load model from disk."""
        ...
    
    def save(self, path: str) -> None:
        """Save model to disk."""
        ...


class InferenceEngine:
    """Engine for running model inference."""
    
    def __init__(self):
        self._models: Dict[str, Model] = {}
        self._preprocessors: Dict[str, Any] = {}
        self._postprocessors: Dict[str, Any] = {}
    
    def register_model(self, name: str, model: Model) -> None:
        """Register a model for inference."""
        self._models[name] = model
    
    def register_preprocessor(self, name: str, preprocessor: Any) -> None:
        """Register a preprocessor."""
        self._preprocessors[name] = preprocessor
    
    def register_postprocessor(self, name: str, postprocessor: Any) -> None:
        """Register a postprocessor."""
        self._postprocessors[name] = postprocessor
    
    async def predict(self, model_name: str, inputs: Any, 
                     preprocess: bool = True, 
                     postprocess: bool = True) -> Any:
        """Run inference with a registered model."""
        if model_name not in self._models:
            raise ValueError(f"Model {model_name} not registered")
        
        model = self._models[model_name]
        
        # Preprocess if requested
        if preprocess and model_name in self._preprocessors:
            inputs = self._preprocessors[model_name](inputs)
        
        # Run inference
        predictions = model.predict(inputs)
        
        # Postprocess if requested
        if postprocess and model_name in self._postprocessors:
            predictions = self._postprocessors[model_name](predictions)
        
        return predictions


class ModelRegistry:
    """Registry for ML models."""
    
    def __init__(self):
        self._models: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, version: str, 
                 model_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a model version."""
        if name not in self._models:
            self._models[name] = {}
        
        self._models[name][version] = {
            "path": model_path,
            "metadata": metadata or {},
            "registered_at": np.datetime64('now')
        }
    
    def get_latest(self, name: str) -> Optional[Dict[str, Any]]:
        """Get latest model version."""
        if name not in self._models:
            return None
        
        versions = self._models[name]
        if not versions:
            return None
        
        # Get latest version
        latest_version = sorted(versions.keys())[-1]
        return versions[latest_version]
    
    def list_models(self) -> List[str]:
        """List all registered models."""
        return list(self._models.keys())
    
    def list_versions(self, name: str) -> List[str]:
        """List all versions of a model."""
        if name not in self._models:
            return []
        return list(self._models[name].keys())


__all__ = [
    "Model",
    "InferenceEngine",
    "ModelRegistry",
]