"""Storage backends for data and artifacts."""

from typing import Any, Dict, List, Optional, Union, Protocol
from pathlib import Path
import json
import pickle
import fsspec
from abc import ABC, abstractmethod
import pandas as pd
import pyarrow.parquet as pq


class StorageBackend(Protocol):
    """Protocol for storage backends."""
    
    async def read(self, path: str) -> bytes:
        """Read data from storage."""
        ...
    
    async def write(self, path: str, data: bytes) -> None:
        """Write data to storage."""
        ...
    
    async def delete(self, path: str) -> None:
        """Delete data from storage."""
        ...
    
    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        ...
    
    async def list(self, prefix: str) -> List[str]:
        """List objects with given prefix."""
        ...


class LocalStorage:
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def read(self, path: str) -> bytes:
        """Read file from local storage."""
        full_path = self.base_path / path
        with open(full_path, 'rb') as f:
            return f.read()
    
    async def write(self, path: str, data: bytes) -> None:
        """Write file to local storage."""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(data)
    
    async def delete(self, path: str) -> None:
        """Delete file from local storage."""
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()
    
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        return (self.base_path / path).exists()
    
    async def list(self, prefix: str) -> List[str]:
        """List files with given prefix."""
        results = []
        search_path = self.base_path / prefix
        
        if search_path.is_dir():
            for item in search_path.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(self.base_path)
                    results.append(str(relative_path))
        
        return results


class S3Storage:
    """S3-compatible storage backend."""
    
    def __init__(self, bucket: str, **kwargs):
        self.bucket = bucket
        self.fs = fsspec.filesystem('s3', **kwargs)
    
    def _get_path(self, path: str) -> str:
        """Get full S3 path."""
        return f"{self.bucket}/{path}"
    
    async def read(self, path: str) -> bytes:
        """Read from S3."""
        with self.fs.open(self._get_path(path), 'rb') as f:
            return f.read()
    
    async def write(self, path: str, data: bytes) -> None:
        """Write to S3."""
        with self.fs.open(self._get_path(path), 'wb') as f:
            f.write(data)
    
    async def delete(self, path: str) -> None:
        """Delete from S3."""
        self.fs.rm(self._get_path(path))
    
    async def exists(self, path: str) -> bool:
        """Check if exists in S3."""
        return self.fs.exists(self._get_path(path))
    
    async def list(self, prefix: str) -> List[str]:
        """List objects in S3."""
        full_prefix = self._get_path(prefix)
        files = self.fs.ls(full_prefix, detail=False)
        # Remove bucket prefix
        return [f.replace(f"{self.bucket}/", "") for f in files]


class ArtifactStore:
    """Store for DAG artifacts and results."""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
    
    async def save_json(self, path: str, data: Any) -> None:
        """Save data as JSON."""
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        await self.backend.write(path, json_bytes)
    
    async def load_json(self, path: str) -> Any:
        """Load JSON data."""
        data = await self.backend.read(path)
        return json.loads(data.decode('utf-8'))
    
    async def save_pickle(self, path: str, obj: Any) -> None:
        """Save object as pickle."""
        pickle_bytes = pickle.dumps(obj)
        await self.backend.write(path, pickle_bytes)
    
    async def load_pickle(self, path: str) -> Any:
        """Load pickled object."""
        data = await self.backend.read(path)
        return pickle.loads(data)
    
    async def save_dataframe(self, path: str, df: pd.DataFrame, 
                            format: str = "parquet") -> None:
        """Save pandas DataFrame."""
        if format == "parquet":
            buffer = df.to_parquet()
            await self.backend.write(f"{path}.parquet", buffer)
        elif format == "csv":
            csv_data = df.to_csv(index=False).encode('utf-8')
            await self.backend.write(f"{path}.csv", csv_data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def load_dataframe(self, path: str) -> pd.DataFrame:
        """Load pandas DataFrame."""
        if path.endswith('.parquet'):
            data = await self.backend.read(path)
            return pd.read_parquet(data)
        elif path.endswith('.csv'):
            data = await self.backend.read(path)
            return pd.read_csv(data.decode('utf-8'))
        else:
            raise ValueError("Unsupported file format")
    
    async def save_model(self, path: str, model: Any, 
                        serializer: str = "pickle") -> None:
        """Save ML model."""
        if serializer == "pickle":
            await self.save_pickle(f"{path}.pkl", model)
        else:
            raise ValueError(f"Unsupported serializer: {serializer}")
    
    async def load_model(self, path: str) -> Any:
        """Load ML model."""
        if path.endswith('.pkl'):
            return await self.load_pickle(path)
        else:
            raise ValueError("Unsupported model format")


__all__ = [
    "StorageBackend",
    "LocalStorage",
    "S3Storage",
    "ArtifactStore",
]