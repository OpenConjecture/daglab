"""Cloud storage integration for notebook exports."""

import os
import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO
from datetime import timedelta, datetime
import hashlib
import json

# Cloud provider imports
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_AWS = True
except ImportError:
    HAS_AWS = False

try:
    from google.cloud import storage as gcs
    from google.api_core import exceptions as gcs_exceptions
    HAS_GCS = True
except ImportError:
    HAS_GCS = False

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings, BlobSasPermissions, generate_blob_sas
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

from daglab.runtime.logging import setup_logger

logger = setup_logger(__name__)


class CloudStorageProvider(ABC):
    """Abstract base class for cloud storage providers."""
    
    def __init__(self, bucket: str, **kwargs):
        """Initialize cloud storage provider.
        
        Args:
            bucket: Bucket/container name
            **kwargs: Provider-specific configuration
        """
        self.bucket = bucket
        self.config = kwargs
    
    @abstractmethod
    def upload(
        self,
        file_path: Path,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        retention_days: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to cloud storage.
        
        Args:
            file_path: Local file to upload
            key: Object key/path in cloud storage
            metadata: Optional metadata to attach
            retention_days: Optional retention policy in days
            content_type: Optional MIME type
            
        Returns:
            Upload result with URL and metadata
        """
        pass
    
    @abstractmethod
    def download(self, key: str, output_path: Path) -> Path:
        """Download file from cloud storage.
        
        Args:
            key: Object key/path in cloud storage
            output_path: Local path to save file
            
        Returns:
            Path to downloaded file
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete file from cloud storage.
        
        Args:
            key: Object key/path to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in bucket.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object keys
        """
        pass
    
    @abstractmethod
    def generate_signed_url(
        self,
        key: str,
        expiration_hours: int = 24,
        method: str = "GET",
    ) -> str:
        """Generate signed URL for temporary access.
        
        Args:
            key: Object key/path
            expiration_hours: URL validity in hours
            method: HTTP method (GET/PUT)
            
        Returns:
            Signed URL
        """
        pass
    
    def _guess_content_type(self, file_path: Path) -> str:
        """Guess MIME type from file extension."""
        content_type, _ = mimetypes.guess_type(str(file_path))
        return content_type or "application/octet-stream"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file."""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()


class S3Storage(CloudStorageProvider):
    """AWS S3 storage provider."""
    
    def __init__(self, bucket: str, **kwargs):
        """Initialize S3 storage.
        
        Args:
            bucket: S3 bucket name
            **kwargs: AWS configuration (region, access_key_id, secret_access_key)
        """
        if not HAS_AWS:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        
        super().__init__(bucket, **kwargs)
        
        # Create S3 client
        session_kwargs = {}
        if "region" in kwargs:
            session_kwargs["region_name"] = kwargs["region"]
        if "access_key_id" in kwargs and "secret_access_key" in kwargs:
            session_kwargs["aws_access_key_id"] = kwargs["access_key_id"]
            session_kwargs["aws_secret_access_key"] = kwargs["secret_access_key"]
        
        self.s3 = boto3.client("s3", **session_kwargs)
    
    def upload(
        self,
        file_path: Path,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        retention_days: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to S3."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Prepare upload parameters
        upload_args = {
            "Filename": str(file_path),
            "Bucket": self.bucket,
            "Key": key,
        }
        
        # Set content type
        if content_type is None:
            content_type = self._guess_content_type(file_path)
        upload_args["ExtraArgs"] = {"ContentType": content_type}
        
        # Add metadata
        if metadata:
            upload_args["ExtraArgs"]["Metadata"] = metadata
        
        # Add retention policy
        if retention_days:
            expiration_date = datetime.now() + timedelta(days=retention_days)
            upload_args["ExtraArgs"]["Expires"] = expiration_date
        
        # Handle large files with multipart upload
        file_size = file_path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # 100MB
            return self._multipart_upload(file_path, key, upload_args["ExtraArgs"])
        
        # Standard upload
        try:
            self.s3.upload_file(**upload_args)
            
            # Get object URL
            url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            
            return {
                "url": url,
                "key": key,
                "bucket": self.bucket,
                "size": file_size,
                "checksum": self._calculate_checksum(file_path),
                "content_type": content_type,
            }
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def _multipart_upload(
        self,
        file_path: Path,
        key: str,
        extra_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle multipart upload for large files."""
        # Create multipart upload
        response = self.s3.create_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            **extra_args,
        )
        upload_id = response["UploadId"]
        
        parts = []
        part_number = 1
        chunk_size = 50 * 1024 * 1024  # 50MB chunks
        
        try:
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    response = self.s3.upload_part(
                        Bucket=self.bucket,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=data,
                    )
                    
                    parts.append({
                        "PartNumber": part_number,
                        "ETag": response["ETag"],
                    })
                    part_number += 1
            
            # Complete multipart upload
            self.s3.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            
            url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            
            return {
                "url": url,
                "key": key,
                "bucket": self.bucket,
                "size": file_path.stat().st_size,
                "checksum": self._calculate_checksum(file_path),
                "multipart": True,
                "parts": len(parts),
            }
            
        except Exception as e:
            # Abort multipart upload on error
            self.s3.abort_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
            )
            raise
    
    def download(self, key: str, output_path: Path) -> Path:
        """Download file from S3."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.s3.download_file(self.bucket, key, str(output_path))
            return output_path
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise
    
    def delete(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False
    
    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in S3 bucket."""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix or "",
            )
            
            objects = []
            for page in pages:
                if "Contents" in page:
                    objects.extend([obj["Key"] for obj in page["Contents"]])
            
            return objects
        except ClientError as e:
            logger.error(f"S3 list failed: {e}")
            return []
    
    def generate_signed_url(
        self,
        key: str,
        expiration_hours: int = 24,
        method: str = "GET",
    ) -> str:
        """Generate presigned URL for S3 object."""
        try:
            client_method = "get_object" if method == "GET" else "put_object"
            
            url = self.s3.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration_hours * 3600,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


class GCSStorage(CloudStorageProvider):
    """Google Cloud Storage provider."""
    
    def __init__(self, bucket: str, **kwargs):
        """Initialize GCS storage.
        
        Args:
            bucket: GCS bucket name
            **kwargs: GCP configuration (project_id, credentials_path)
        """
        if not HAS_GCS:
            raise ImportError(
                "google-cloud-storage is required for GCS. "
                "Install with: pip install google-cloud-storage"
            )
        
        super().__init__(bucket, **kwargs)
        
        # Set credentials if provided
        if "credentials_path" in kwargs:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = kwargs["credentials_path"]
        
        # Create GCS client
        self.client = gcs.Client(project=kwargs.get("project_id"))
        self.bucket_obj = self.client.bucket(bucket)
    
    def upload(
        self,
        file_path: Path,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        retention_days: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to GCS."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        blob = self.bucket_obj.blob(key)
        
        # Set content type
        if content_type is None:
            content_type = self._guess_content_type(file_path)
        blob.content_type = content_type
        
        # Set metadata
        if metadata:
            blob.metadata = metadata
        
        # Upload file
        file_size = file_path.stat().st_size
        
        # Use resumable upload for large files
        if file_size > 100 * 1024 * 1024:  # 100MB
            blob.chunk_size = 50 * 1024 * 1024  # 50MB chunks
        
        try:
            blob.upload_from_filename(str(file_path))
            
            # Set retention policy
            if retention_days:
                from datetime import datetime, timedelta
                expiration = datetime.now() + timedelta(days=retention_days)
                blob.retention_expiration_time = expiration
                blob.update()
            
            return {
                "url": blob.public_url,
                "key": key,
                "bucket": self.bucket,
                "size": file_size,
                "checksum": blob.md5_hash,
                "content_type": content_type,
            }
            
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise
    
    def download(self, key: str, output_path: Path) -> Path:
        """Download file from GCS."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        blob = self.bucket_obj.blob(key)
        
        try:
            blob.download_to_filename(str(output_path))
            return output_path
        except gcs_exceptions.NotFound:
            raise FileNotFoundError(f"Object not found: {key}")
    
    def delete(self, key: str) -> bool:
        """Delete file from GCS."""
        blob = self.bucket_obj.blob(key)
        
        try:
            blob.delete()
            return True
        except gcs_exceptions.NotFound:
            logger.warning(f"Object not found for deletion: {key}")
            return False
    
    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in GCS bucket."""
        blobs = self.bucket_obj.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    
    def generate_signed_url(
        self,
        key: str,
        expiration_hours: int = 24,
        method: str = "GET",
    ) -> str:
        """Generate signed URL for GCS object."""
        blob = self.bucket_obj.blob(key)
        
        expiration = datetime.now() + timedelta(hours=expiration_hours)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method=method,
        )
        return url


class AzureStorage(CloudStorageProvider):
    """Azure Blob Storage provider."""
    
    def __init__(self, bucket: str, **kwargs):
        """Initialize Azure storage.
        
        Args:
            bucket: Container name
            **kwargs: Azure configuration (account_name, account_key, connection_string)
        """
        if not HAS_AZURE:
            raise ImportError(
                "azure-storage-blob is required for Azure Storage. "
                "Install with: pip install azure-storage-blob"
            )
        
        super().__init__(bucket, **kwargs)
        
        # Create Azure client
        if "connection_string" in kwargs:
            self.client = BlobServiceClient.from_connection_string(
                kwargs["connection_string"]
            )
        elif "account_name" in kwargs and "account_key" in kwargs:
            self.client = BlobServiceClient(
                account_url=f"https://{kwargs['account_name']}.blob.core.windows.net",
                credential=kwargs["account_key"],
            )
        else:
            raise ValueError(
                "Azure Storage requires either connection_string or "
                "account_name + account_key"
            )
        
        self.container_client = self.client.get_container_client(bucket)
    
    def upload(
        self,
        file_path: Path,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        retention_days: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Azure Blob Storage."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        blob_client = self.container_client.get_blob_client(key)
        
        # Set content settings
        if content_type is None:
            content_type = self._guess_content_type(file_path)
        content_settings = ContentSettings(content_type=content_type)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata["uploaded_at"] = datetime.now().isoformat()
        
        file_size = file_path.stat().st_size
        
        try:
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=content_settings,
                    metadata=metadata,
                )
            
            return {
                "url": blob_client.url,
                "key": key,
                "bucket": self.bucket,
                "size": file_size,
                "checksum": self._calculate_checksum(file_path),
                "content_type": content_type,
            }
            
        except Exception as e:
            logger.error(f"Azure upload failed: {e}")
            raise
    
    def download(self, key: str, output_path: Path) -> Path:
        """Download file from Azure Blob Storage."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        blob_client = self.container_client.get_blob_client(key)
        
        try:
            with open(output_path, "wb") as data:
                data.write(blob_client.download_blob().readall())
            return output_path
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {key}")
    
    def delete(self, key: str) -> bool:
        """Delete file from Azure Blob Storage."""
        blob_client = self.container_client.get_blob_client(key)
        
        try:
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {key}")
            return False
    
    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in Azure container."""
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
    
    def generate_signed_url(
        self,
        key: str,
        expiration_hours: int = 24,
        method: str = "GET",
    ) -> str:
        """Generate SAS URL for Azure blob."""
        blob_client = self.container_client.get_blob_client(key)
        
        # Set permissions based on method
        if method == "GET":
            permission = BlobSasPermissions(read=True)
        else:
            permission = BlobSasPermissions(write=True)
        
        expiry = datetime.utcnow() + timedelta(hours=expiration_hours)
        
        sas_token = generate_blob_sas(
            account_name=self.client.account_name,
            container_name=self.bucket,
            blob_name=key,
            account_key=self.config.get("account_key"),
            permission=permission,
            expiry=expiry,
        )
        
        return f"{blob_client.url}?{sas_token}"


def create_storage_provider(
    provider: str,
    bucket: str,
    **kwargs,
) -> CloudStorageProvider:
    """Factory function to create storage provider.
    
    Args:
        provider: Provider name (s3, gcs, azure)
        bucket: Bucket/container name
        **kwargs: Provider-specific configuration
        
    Returns:
        CloudStorageProvider instance
    """
    providers = {
        "s3": S3Storage,
        "gcs": GCSStorage,
        "azure": AzureStorage,
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Choose from: {list(providers.keys())}")
    
    return providers[provider](bucket, **kwargs)