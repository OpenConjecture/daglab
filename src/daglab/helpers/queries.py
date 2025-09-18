"""GraphQL query library for Dagster operations."""
from typing import Dict, List, Optional, Any
from enum import Enum


class DagsterVersion(Enum):
    """Dagster version compatibility."""
    V1_0 = "1.0"
    V1_5 = "1.5"
    V1_6 = "1.6"
    V1_7 = "1.7"
    LATEST = "latest"


class QueryFragments:
    """Reusable GraphQL query fragments."""
    
    REPOSITORY_INFO = """
    fragment RepositoryInfo on Repository {
        id
        name
        location {
            id
            name
        }
    }
    """
    
    JOB_INFO = """
    fragment JobInfo on Pipeline {
        id
        name
        description
        modes {
            name
            description
        }
        tags {
            key
            value
        }
    }
    """
    
    ASSET_INFO = """
    fragment AssetInfo on AssetNode {
        id
        assetKey {
            path
        }
        description
        opNames
        dependencies {
            asset {
                assetKey {
                    path
                }
            }
        }
    }
    """
    
    RUN_INFO = """
    fragment RunInfo on PipelineRun {
        runId
        pipelineName
        mode
        status
        startTime
        endTime
        tags {
            key
            value
        }
        stats {
            ... on RunStatsSnapshot {
                startTime
                endTime
                stepsFailed
                stepsSucceeded
                materializations
                expectations
            }
        }
    }
    """
    
    RUN_EVENT_INFO = """
    fragment RunEventInfo on PipelineRunEvent {
        timestamp
        level
        eventType
        message
        stepKey
    }
    """


class Queries:
    """GraphQL queries for Dagster operations."""
    
    # Repository queries
    GET_REPOSITORIES = """
    query GetRepositories {
        repositoriesOrError {
            __typename
            ... on RepositoryConnection {
                nodes {
                    ...RepositoryInfo
                }
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.REPOSITORY_INFO
    
    GET_REPOSITORY = """
    query GetRepository($repositorySelector: RepositorySelector!) {
        repositoryOrError(repositorySelector: $repositorySelector) {
            __typename
            ... on Repository {
                ...RepositoryInfo
                pipelines {
                    ...JobInfo
                }
                assets {
                    nodes {
                        ...AssetInfo
                    }
                }
            }
            ... on RepositoryNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.REPOSITORY_INFO + QueryFragments.JOB_INFO + QueryFragments.ASSET_INFO
    
    # Job/Pipeline queries
    GET_JOBS = """
    query GetJobs($repositorySelector: RepositorySelector!) {
        repositoryOrError(repositorySelector: $repositorySelector) {
            __typename
            ... on Repository {
                pipelines {
                    ...JobInfo
                }
            }
            ... on RepositoryNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.JOB_INFO
    
    GET_JOB = """
    query GetJob($pipelineSelector: PipelineSelector!) {
        pipelineOrError(params: $pipelineSelector) {
            __typename
            ... on Pipeline {
                ...JobInfo
                solidHandles {
                    handleID
                    solid {
                        name
                        definition {
                            name
                            description
                        }
                        inputs {
                            definition {
                                name
                                type {
                                    displayName
                                }
                            }
                        }
                        outputs {
                            definition {
                                name
                                type {
                                    displayName
                                }
                            }
                        }
                    }
                }
            }
            ... on PipelineNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.JOB_INFO
    
    # Asset queries
    GET_ASSETS = """
    query GetAssets($repositorySelector: RepositorySelector!) {
        repositoryOrError(repositorySelector: $repositorySelector) {
            __typename
            ... on Repository {
                assets {
                    nodes {
                        ...AssetInfo
                    }
                }
            }
            ... on RepositoryNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.ASSET_INFO
    
    GET_ASSET = """
    query GetAsset($assetKey: AssetKeyInput!) {
        assetOrError(assetKey: $assetKey) {
            __typename
            ... on Asset {
                key {
                    path
                }
                assetMaterializations {
                    timestamp
                    runId
                    partition
                    metadataEntries {
                        label
                        description
                        ... on TextMetadataEntry {
                            text
                        }
                        ... on FloatMetadataEntry {
                            floatValue
                        }
                        ... on IntMetadataEntry {
                            intValue
                        }
                        ... on JsonMetadataEntry {
                            jsonString
                        }
                    }
                }
            }
            ... on AssetNotFoundError {
                message
            }
        }
    }
    """
    
    # Run queries
    GET_RUNS = """
    query GetRuns($filter: RunsFilter, $limit: Int) {
        pipelineRunsOrError(filter: $filter, limit: $limit) {
            __typename
            ... on PipelineRuns {
                results {
                    ...RunInfo
                }
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.RUN_INFO
    
    GET_RUN = """
    query GetRun($runId: ID!) {
        pipelineRunOrError(runId: $runId) {
            __typename
            ... on PipelineRun {
                ...RunInfo
                executionPlan {
                    steps {
                        key
                        kind
                        inputs {
                            dependsOn {
                                key
                                outputs {
                                    name
                                    type {
                                        displayName
                                    }
                                }
                            }
                        }
                    }
                }
            }
            ... on RunNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.RUN_INFO
    
    GET_RUN_EVENTS = """
    query GetRunEvents($runId: ID!, $cursor: String, $limit: Int) {
        pipelineRunOrError(runId: $runId) {
            __typename
            ... on PipelineRun {
                events(cursor: $cursor, limit: $limit) {
                    ...RunEventInfo
                }
            }
            ... on RunNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """ + QueryFragments.RUN_EVENT_INFO
    
    # Health check
    HEALTH_CHECK = """
    query HealthCheck {
        version
        repositoriesOrError {
            __typename
        }
    }
    """


class Mutations:
    """GraphQL mutations for Dagster operations."""
    
    LAUNCH_RUN = """
    mutation LaunchRun($executionParams: ExecutionParams!) {
        launchRun(executionParams: $executionParams) {
            __typename
            ... on LaunchRunSuccess {
                run {
                    runId
                    pipelineName
                    status
                }
            }
            ... on PipelineNotFoundError {
                message
            }
            ... on RunConfigValidationInvalid {
                errors {
                    message
                    fieldName
                    fieldPath
                    reason
                }
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """
    
    TERMINATE_RUN = """
    mutation TerminateRun($runId: String!) {
        terminateRun(runId: $runId) {
            __typename
            ... on TerminateRunSuccess {
                run {
                    runId
                    status
                }
            }
            ... on RunNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """
    
    RELOAD_REPOSITORY_LOCATION = """
    mutation ReloadRepositoryLocation($repositoryLocationName: String!) {
        reloadRepositoryLocation(repositoryLocationName: $repositoryLocationName) {
            __typename
            ... on WorkspaceLocationEntry {
                locationOrLoadError {
                    __typename
                    ... on RepositoryLocation {
                        name
                        repositories {
                            name
                        }
                    }
                    ... on PythonError {
                        message
                        stack
                    }
                }
            }
            ... on UnauthorizedError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """
    
    MATERIALIZE_ASSET = """
    mutation MaterializeAsset($assetKey: AssetKeyInput!) {
        assetMaterialize(assetKey: $assetKey) {
            __typename
            ... on LaunchRunSuccess {
                run {
                    runId
                    status
                }
            }
            ... on AssetNotFoundError {
                message
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """
    
    # For older Dagster versions
    LAUNCH_PIPELINE_EXECUTION = """
    mutation LaunchPipelineExecution($executionParams: ExecutionParams!) {
        launchPipelineExecution(executionParams: $executionParams) {
            __typename
            ... on LaunchRunSuccess {
                run {
                    runId
                    pipelineName
                    status
                }
            }
            ... on PipelineNotFoundError {
                message
            }
            ... on RunConfigValidationInvalid {
                errors {
                    message
                    fieldName
                    fieldPath
                    reason
                }
            }
            ... on PythonError {
                message
                stack
            }
        }
    }
    """


class Subscriptions:
    """GraphQL subscriptions for real-time updates."""
    
    PIPELINE_RUN_LOGS = """
    subscription PipelineRunLogs($runId: ID!, $after: Cursor) {
        pipelineRunLogs(runId: $runId, after: $after) {
            __typename
            ... on PipelineRunLogsSubscriptionSuccess {
                messages {
                    ... on MessageEvent {
                        timestamp
                        level
                        message
                        eventType
                        stepKey
                    }
                }
                cursor
            }
            ... on PipelineRunLogsSubscriptionFailure {
                message
            }
        }
    }
    """
    
    COMPUTE_LOGS = """
    subscription ComputeLogs($runId: ID!, $stepKey: String!, $ioType: ComputeIOType!, $cursor: String) {
        computeLogs(runId: $runId, stepKey: $stepKey, ioType: $ioType, cursor: $cursor) {
            data
            cursor
        }
    }
    """


def get_query(
    query_name: str,
    version: DagsterVersion = DagsterVersion.LATEST
) -> str:
    """Get query for specific Dagster version.
    
    Args:
        query_name: Name of the query
        version: Dagster version
        
    Returns:
        GraphQL query string
    """
    # Version-specific query mapping
    version_queries = {
        DagsterVersion.V1_0: {
            "LAUNCH_RUN": Mutations.LAUNCH_PIPELINE_EXECUTION,
        }
    }
    
    # Check for version-specific query
    if version in version_queries and query_name in version_queries[version]:
        return version_queries[version][query_name]
    
    # Return default query
    if hasattr(Queries, query_name):
        return getattr(Queries, query_name)
    elif hasattr(Mutations, query_name):
        return getattr(Mutations, query_name)
    elif hasattr(Subscriptions, query_name):
        return getattr(Subscriptions, query_name)
    else:
        raise ValueError(f"Unknown query: {query_name}")


def build_repository_selector(
    repository_name: str,
    repository_location_name: str
) -> Dict[str, Any]:
    """Build repository selector for queries."""
    return {
        "repositoryName": repository_name,
        "repositoryLocationName": repository_location_name
    }


def build_pipeline_selector(
    pipeline_name: str,
    repository_name: str,
    repository_location_name: str,
    solid_selection: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Build pipeline selector for queries."""
    selector = {
        "pipelineName": pipeline_name,
        "repositoryName": repository_name,
        "repositoryLocationName": repository_location_name
    }
    
    if solid_selection:
        selector["solidSelection"] = solid_selection
    
    return selector


def build_execution_params(
    selector: Dict[str, Any],
    run_config: Optional[Dict[str, Any]] = None,
    mode: str = "default",
    tags: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Build execution parameters for run launch."""
    params = {
        "selector": selector,
        "mode": mode
    }
    
    if run_config:
        params["runConfigData"] = run_config
    
    if tags:
        params["executionMetadata"] = {
            "tags": [{"key": k, "value": v} for k, v in tags.items()]
        }
    
    return params