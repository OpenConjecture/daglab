"""Pydantic models for GraphQL responses and Dagster entities."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class RunStatus(str, Enum):
    """Dagster run status enumeration."""
    NOT_STARTED = "NOT_STARTED"
    STARTING = "STARTING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELING = "CANCELING"
    CANCELED = "CANCELED"


class EventType(str, Enum):
    """Dagster event types."""
    STEP_START = "STEP_START"
    STEP_SUCCESS = "STEP_SUCCESS"
    STEP_FAILURE = "STEP_FAILURE"
    STEP_SKIPPED = "STEP_SKIPPED"
    ASSET_MATERIALIZATION = "ASSET_MATERIALIZATION"
    ASSET_OBSERVATION = "ASSET_OBSERVATION"
    ASSET_CHECK = "ASSET_CHECK"
    PIPELINE_START = "PIPELINE_START"
    PIPELINE_SUCCESS = "PIPELINE_SUCCESS"
    PIPELINE_FAILURE = "PIPELINE_FAILURE"
    ENGINE_EVENT = "ENGINE_EVENT"
    HOOK_COMPLETED = "HOOK_COMPLETED"
    HOOK_ERRORED = "HOOK_ERRORED"
    HOOK_SKIPPED = "HOOK_SKIPPED"


class AssetKey(BaseModel):
    """Asset key representation."""
    path: List[str]
    
    @property
    def to_string(self) -> str:
        """Convert asset key to string representation."""
        return ".".join(self.path)
    
    @classmethod
    def from_string(cls, key_string: str) -> "AssetKey":
        """Create asset key from string."""
        return cls(path=key_string.split("."))


class Tag(BaseModel):
    """Key-value tag."""
    key: str
    value: str


class GraphQLError(BaseModel):
    """GraphQL error representation."""
    message: str
    path: Optional[List[Union[str, int]]] = None
    extensions: Optional[Dict[str, Any]] = None
    locations: Optional[List[Dict[str, int]]] = None


class GraphQLResponse(BaseModel):
    """GraphQL response wrapper."""
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[GraphQLError]] = None
    extensions: Optional[Dict[str, Any]] = None
    
    @property
    def has_errors(self) -> bool:
        """Check if response has errors."""
        return bool(self.errors)
    
    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return not self.has_errors and self.data is not None


class LocationInfo(BaseModel):
    """Repository location information."""
    id: str
    name: str


class RepositoryInfo(BaseModel):
    """Repository information."""
    id: str
    name: str
    location: LocationInfo
    pipelines: Optional[List["JobInfo"]] = None
    assets: Optional[List["AssetInfo"]] = None


class ModeInfo(BaseModel):
    """Pipeline/job mode information."""
    name: str
    description: Optional[str] = None


class SolidDefinition(BaseModel):
    """Solid/op definition information."""
    name: str
    description: Optional[str] = None


class TypeInfo(BaseModel):
    """Type information for inputs/outputs."""
    displayName: str


class InputDefinition(BaseModel):
    """Input definition information."""
    name: str
    type: TypeInfo


class OutputDefinition(BaseModel):
    """Output definition information."""
    name: str
    type: TypeInfo


class SolidInfo(BaseModel):
    """Solid/op information."""
    name: str
    definition: SolidDefinition
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)


class SolidHandle(BaseModel):
    """Solid handle information."""
    handleID: str
    solid: SolidInfo


class JobInfo(BaseModel):
    """Job/pipeline information."""
    id: str
    name: str
    description: Optional[str] = None
    modes: List[ModeInfo] = Field(default_factory=list)
    tags: List[Tag] = Field(default_factory=list)
    solidHandles: Optional[List[SolidHandle]] = None


class AssetDependency(BaseModel):
    """Asset dependency information."""
    asset: Dict[str, Any]
    
    @property
    def asset_key(self) -> AssetKey:
        """Get asset key from dependency."""
        return AssetKey(path=self.asset["assetKey"]["path"])


class AssetInfo(BaseModel):
    """Asset information."""
    id: str
    assetKey: AssetKey
    description: Optional[str] = None
    opNames: List[str] = Field(default_factory=list)
    dependencies: List[AssetDependency] = Field(default_factory=list)
    
    @property
    def key(self) -> str:
        """Get asset key as string."""
        return self.assetKey.to_string


class MetadataEntry(BaseModel):
    """Base metadata entry."""
    label: str
    description: Optional[str] = None


class TextMetadataEntry(MetadataEntry):
    """Text metadata entry."""
    text: str


class FloatMetadataEntry(MetadataEntry):
    """Float metadata entry."""
    floatValue: float


class IntMetadataEntry(MetadataEntry):
    """Integer metadata entry."""
    intValue: int


class JsonMetadataEntry(MetadataEntry):
    """JSON metadata entry."""
    jsonString: str


class AssetMaterialization(BaseModel):
    """Asset materialization event."""
    timestamp: str
    runId: str
    partition: Optional[str] = None
    metadataEntries: List[Union[
        TextMetadataEntry,
        FloatMetadataEntry,
        IntMetadataEntry,
        JsonMetadataEntry,
        MetadataEntry
    ]] = Field(default_factory=list)


class RunStats(BaseModel):
    """Run statistics."""
    startTime: Optional[float] = None
    endTime: Optional[float] = None
    stepsFailed: int = 0
    stepsSucceeded: int = 0
    materializations: int = 0
    expectations: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate run duration in seconds."""
        if self.startTime and self.endTime:
            return self.endTime - self.startTime
        return None


class ExecutionStep(BaseModel):
    """Execution plan step."""
    key: str
    kind: str
    inputs: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    """Execution plan information."""
    steps: List[ExecutionStep] = Field(default_factory=list)


class RunInfo(BaseModel):
    """Run information."""
    runId: str
    pipelineName: str
    mode: str = "default"
    status: RunStatus
    startTime: Optional[float] = None
    endTime: Optional[float] = None
    tags: List[Tag] = Field(default_factory=list)
    stats: Optional[RunStats] = None
    executionPlan: Optional[ExecutionPlan] = None
    
    @property
    def is_finished(self) -> bool:
        """Check if run is finished."""
        return self.status in [
            RunStatus.SUCCESS,
            RunStatus.FAILURE,
            RunStatus.CANCELED
        ]
    
    @property
    def is_running(self) -> bool:
        """Check if run is currently running."""
        return self.status in [
            RunStatus.STARTING,
            RunStatus.STARTED
        ]
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate run duration in seconds."""
        if self.startTime and self.endTime:
            return self.endTime - self.startTime
        return None


class RunEvent(BaseModel):
    """Run event information."""
    timestamp: str
    level: Optional[str] = None
    eventType: Optional[EventType] = None
    message: str
    stepKey: Optional[str] = None


class ValidationError(BaseModel):
    """Validation error information."""
    message: str
    fieldName: Optional[str] = None
    fieldPath: Optional[List[str]] = None
    reason: Optional[str] = None


class LaunchRunSuccess(BaseModel):
    """Successful run launch response."""
    run: RunInfo


class PythonError(BaseModel):
    """Python error response."""
    message: str
    stack: Optional[List[str]] = None
    
    @property
    def full_message(self) -> str:
        """Get full error message with stack trace."""
        if self.stack:
            return f"{self.message}\n\nStack trace:\n" + "\n".join(self.stack)
        return self.message


class RepositoryNotFoundError(BaseModel):
    """Repository not found error."""
    message: str


class PipelineNotFoundError(BaseModel):
    """Pipeline not found error."""
    message: str


class RunNotFoundError(BaseModel):
    """Run not found error."""
    message: str


class AssetNotFoundError(BaseModel):
    """Asset not found error."""
    message: str


class UnauthorizedError(BaseModel):
    """Unauthorized error."""
    message: str


class RunConfigValidationInvalid(BaseModel):
    """Run config validation error."""
    errors: List[ValidationError]


# Model registry for easy type lookup
MODEL_REGISTRY = {
    "RepositoryInfo": RepositoryInfo,
    "JobInfo": JobInfo,
    "AssetInfo": AssetInfo,
    "RunInfo": RunInfo,
    "RunEvent": RunEvent,
    "AssetMaterialization": AssetMaterialization,
    "LaunchRunSuccess": LaunchRunSuccess,
    "PythonError": PythonError,
    "RepositoryNotFoundError": RepositoryNotFoundError,
    "PipelineNotFoundError": PipelineNotFoundError,
    "RunNotFoundError": RunNotFoundError,
    "AssetNotFoundError": AssetNotFoundError,
    "UnauthorizedError": UnauthorizedError,
    "RunConfigValidationInvalid": RunConfigValidationInvalid,
}


def parse_graphql_response(
    response: GraphQLResponse,
    expected_type: Optional[str] = None
) -> Any:
    """Parse GraphQL response into appropriate model.
    
    Args:
        response: GraphQL response
        expected_type: Expected model type name
        
    Returns:
        Parsed model instance
        
    Raises:
        ValueError: If parsing fails
    """
    if response.has_errors:
        raise ValueError(f"GraphQL errors: {response.errors}")
    
    if not response.data:
        raise ValueError("No data in response")
    
    if expected_type and expected_type in MODEL_REGISTRY:
        model_class = MODEL_REGISTRY[expected_type]
        return model_class(**response.data)
    
    return response.data