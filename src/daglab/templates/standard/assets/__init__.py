"""Example assets for standard Dagster project."""

from dagster import asset
import pandas as pd
from datetime import datetime


@asset
def sample_data() -> pd.DataFrame:
    """Generate sample data for demonstration."""
    data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='D'),
        'value': [100, 102, 99, 105, 108, 107, 110, 113, 111, 115],
        'status': ['active'] * 10
    }
    return pd.DataFrame(data)


@asset
def processed_data(sample_data: pd.DataFrame) -> pd.DataFrame:
    """Process the sample data."""
    df = sample_data.copy()
    df['rolling_avg'] = df['value'].rolling(window=3).mean()
    df['pct_change'] = df['value'].pct_change()
    return df


@asset
def data_summary(processed_data: pd.DataFrame) -> dict:
    """Create summary statistics."""
    return {
        'count': len(processed_data),
        'mean_value': processed_data['value'].mean(),
        'max_value': processed_data['value'].max(),
        'min_value': processed_data['value'].min(),
        'last_updated': datetime.now().isoformat()
    }