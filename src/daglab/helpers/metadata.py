"""Metadata attachment system for Dagster integration."""

import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import requests
from urllib.parse import urljoin

from daglab.runtime.logging import setup_logger

logger = setup_logger(__name__)


class MetadataAttacher:
    """Attach metadata to Dagster assets and jobs."""
    
    def __init__(
        self,
        dagster_url: str,
        auth_token: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize metadata attacher.
        
        Args:
            dagster_url: Dagster instance URL
            auth_token: Optional authentication token
            timeout: Request timeout in seconds
        """
        self.dagster_url = dagster_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
        }
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
    
    def attach_export_metadata(
        self,
        asset_key: str,
        export_url: str,
        format: str,
        metadata: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Attach export metadata to a Dagster asset.
        
        Args:
            asset_key: Asset key in Dagster
            export_url: URL of exported file
            format: Export format
            metadata: Additional metadata
            run_id: Optional run ID for run-time attachment
            
        Returns:
            Response from Dagster or None if failed
        """
        # Build metadata payload
        export_metadata = {
            "export_url": export_url,
            "format": format,
            "exported_at": datetime.now().isoformat(),
        }
        
        if metadata:
            export_metadata.update(metadata)
        
        # Try GraphQL mutation first
        result = self._attach_via_graphql(asset_key, export_metadata, run_id)
        
        # Fallback to REST API if GraphQL fails
        if not result:
            result = self._attach_via_rest(asset_key, export_metadata, run_id)
        
        return result
    
    def _attach_via_graphql(
        self,
        asset_key: str,
        metadata: Dict[str, Any],
        run_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Attach metadata using GraphQL API."""
        graphql_url = urljoin(self.dagster_url, "/graphql")
        
        # Build GraphQL mutation
        if run_id:
            # Attach to specific run
            mutation = """
            mutation AttachRunMetadata($runId: String!, $metadata: JSON!) {
                attachRunMetadata(runId: $runId, metadata: $metadata) {
                    success
                    run {
                        runId
                        tags
                    }
                }
            }
            """
            variables = {
                "runId": run_id,
                "metadata": metadata,
            }
        else:
            # Attach to asset
            mutation = """
            mutation AttachAssetMetadata($assetKey: String!, $metadata: JSON!) {
                attachAssetMetadata(assetKey: $assetKey, metadata: $metadata) {
                    success
                    asset {
                        key
                        metadata
                    }
                }
            }
            """
            variables = {
                "assetKey": asset_key,
                "metadata": metadata,
            }
        
        payload = {
            "query": mutation,
            "variables": variables,
        }
        
        try:
            response = requests.post(
                graphql_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    return None
                return result.get("data")
            else:
                logger.error(
                    f"GraphQL request failed with status {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            logger.error(f"GraphQL request failed: {e}")
            return None
    
    def _attach_via_rest(
        self,
        asset_key: str,
        metadata: Dict[str, Any],
        run_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Attach metadata using REST API (fallback)."""
        if run_id:
            # Attach to run
            url = urljoin(
                self.dagster_url,
                f"/api/runs/{run_id}/metadata"
            )
        else:
            # Attach to asset
            url = urljoin(
                self.dagster_url,
                f"/api/assets/{asset_key}/metadata"
            )
        
        try:
            response = requests.post(
                url,
                json=metadata,
                headers=self.headers,
                timeout=self.timeout,
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(
                    f"REST request failed with status {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            logger.error(f"REST request failed: {e}")
            return None
    
    def generate_notebook_metadata(
        self,
        notebook_path: Path,
        export_path: Path,
        format: str,
        preview_image: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for notebook export.
        
        Args:
            notebook_path: Original notebook path
            export_path: Exported file path
            format: Export format
            preview_image: Optional preview image path
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "notebook": {
                "path": str(notebook_path),
                "name": notebook_path.name,
                "size": notebook_path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    notebook_path.stat().st_mtime
                ).isoformat(),
            },
            "export": {
                "path": str(export_path),
                "format": format,
                "size": export_path.stat().st_size if export_path.exists() else 0,
                "timestamp": datetime.now().isoformat(),
            },
        }
        
        # Add preview image if provided
        if preview_image and preview_image.exists():
            with open(preview_image, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
                metadata["preview"] = {
                    "image": f"data:image/png;base64,{image_data}",
                    "type": "png",
                }
        
        # Extract additional metadata from notebook
        try:
            content = notebook_path.read_text()
            
            # Count cells (marimo uses specific markers)
            cell_count = content.count("@app.cell")
            metadata["notebook"]["cells"] = cell_count
            
            # Extract imports
            imports = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("import ") or line.startswith("from "):
                    imports.append(line)
            metadata["notebook"]["imports"] = imports[:10]  # First 10 imports
            
        except Exception as e:
            logger.warning(f"Failed to extract notebook metadata: {e}")
        
        return metadata
    
    def create_asset_version(
        self,
        asset_key: str,
        version: str,
        metadata: Dict[str, Any],
        parent_version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new version of an asset with metadata.
        
        Args:
            asset_key: Asset key in Dagster
            version: Version identifier
            metadata: Version metadata
            parent_version: Optional parent version
            
        Returns:
            Response from Dagster
        """
        mutation = """
        mutation CreateAssetVersion(
            $assetKey: String!,
            $version: String!,
            $metadata: JSON!,
            $parentVersion: String
        ) {
            createAssetVersion(
                assetKey: $assetKey,
                version: $version,
                metadata: $metadata,
                parentVersion: $parentVersion
            ) {
                success
                version {
                    id
                    version
                    createdAt
                }
            }
        }
        """
        
        variables = {
            "assetKey": asset_key,
            "version": version,
            "metadata": metadata,
            "parentVersion": parent_version,
        }
        
        payload = {
            "query": mutation,
            "variables": variables,
        }
        
        graphql_url = urljoin(self.dagster_url, "/graphql")
        
        try:
            response = requests.post(
                graphql_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    return None
                return result.get("data")
            else:
                logger.error(
                    f"Version creation failed with status {response.status_code}"
                )
                return None
                
        except Exception as e:
            logger.error(f"Version creation failed: {e}")
            return None
    
    def track_export_lineage(
        self,
        asset_key: str,
        export_info: Dict[str, Any],
        upstream_assets: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Track lineage for exported assets.
        
        Args:
            asset_key: Asset key in Dagster
            export_info: Export information
            upstream_assets: List of upstream asset keys
            
        Returns:
            Response from Dagster
        """
        lineage_data = {
            "asset_key": asset_key,
            "operation": "export",
            "timestamp": datetime.now().isoformat(),
            "export_info": export_info,
        }
        
        if upstream_assets:
            lineage_data["upstream_assets"] = upstream_assets
        
        mutation = """
        mutation TrackAssetLineage($lineageData: JSON!) {
            trackAssetLineage(lineageData: $lineageData) {
                success
                lineage {
                    id
                    createdAt
                }
            }
        }
        """
        
        variables = {
            "lineageData": lineage_data,
        }
        
        payload = {
            "query": mutation,
            "variables": variables,
        }
        
        graphql_url = urljoin(self.dagster_url, "/graphql")
        
        try:
            response = requests.post(
                graphql_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("data")
            else:
                logger.warning(
                    f"Lineage tracking failed with status {response.status_code}"
                )
                return None
                
        except Exception as e:
            logger.warning(f"Lineage tracking failed: {e}")
            return None
    
    def bulk_attach_metadata(
        self,
        metadata_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Attach metadata in bulk for multiple assets.
        
        Args:
            metadata_entries: List of metadata entries, each with asset_key and metadata
            
        Returns:
            Summary of results
        """
        results = {
            "success": [],
            "failed": [],
            "total": len(metadata_entries),
        }
        
        for entry in metadata_entries:
            asset_key = entry.get("asset_key")
            metadata = entry.get("metadata", {})
            
            if not asset_key:
                results["failed"].append({
                    "error": "Missing asset_key",
                    "entry": entry,
                })
                continue
            
            result = self._attach_via_graphql(asset_key, metadata)
            
            if result:
                results["success"].append({
                    "asset_key": asset_key,
                    "result": result,
                })
            else:
                results["failed"].append({
                    "asset_key": asset_key,
                    "error": "Attachment failed",
                })
        
        results["success_rate"] = len(results["success"]) / results["total"]
        
        return results