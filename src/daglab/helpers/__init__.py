"""GraphQL client and helpers for Dagster integration."""
from .auth import (
    AuthConfig,
    AuthType,
    AuthProvider,
    BearerAuthProvider,
    BasicAuthProvider,
    CustomAuthProvider,
    TokenManager,
    TokenProvider,
)
from .graphql import (
    DagsterClient,
    DagsterClientSync,
    DagsterClientError,
    GraphQLQueryError,
)
from .models import (
    # Core models
    GraphQLResponse,
    GraphQLError,
    RepositoryInfo,
    JobInfo,
    AssetInfo,
    RunInfo,
    RunEvent,
    AssetMaterialization,
    # Enums
    RunStatus,
    EventType,
    # Helper models
    AssetKey,
    Tag,
    LocationInfo,
    ModeInfo,
    RunStats,
    # Error models
    PythonError,
    RepositoryNotFoundError,
    PipelineNotFoundError,
    RunNotFoundError,
    AssetNotFoundError,
    UnauthorizedError,
    RunConfigValidationInvalid,
    ValidationError,
    # Response models
    LaunchRunSuccess,
    # Utilities
    parse_graphql_response,
)
from .queries import (
    Queries,
    Mutations,
    Subscriptions,
    QueryFragments,
    DagsterVersion,
    get_query,
    build_repository_selector,
    build_pipeline_selector,
    build_execution_params,
)

__all__ = [
    # Client
    "DagsterClient",
    "DagsterClientSync",
    "DagsterClientError",
    "GraphQLQueryError",
    # Auth
    "AuthConfig",
    "AuthType",
    "AuthProvider",
    "BearerAuthProvider",
    "BasicAuthProvider",
    "CustomAuthProvider",
    "TokenManager",
    "TokenProvider",
    # Models
    "GraphQLResponse",
    "GraphQLError",
    "RepositoryInfo",
    "JobInfo",
    "AssetInfo",
    "RunInfo",
    "RunEvent",
    "AssetMaterialization",
    "RunStatus",
    "EventType",
    "AssetKey",
    "Tag",
    "LocationInfo",
    "ModeInfo",
    "RunStats",
    "PythonError",
    "RepositoryNotFoundError",
    "PipelineNotFoundError",
    "RunNotFoundError",
    "AssetNotFoundError",
    "UnauthorizedError",
    "RunConfigValidationInvalid",
    "ValidationError",
    "LaunchRunSuccess",
    "parse_graphql_response",
    # Queries
    "Queries",
    "Mutations",
    "Subscriptions",
    "QueryFragments",
    "DagsterVersion",
    "get_query",
    "build_repository_selector",
    "build_pipeline_selector",
    "build_execution_params",
]