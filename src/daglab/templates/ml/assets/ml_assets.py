"""Machine learning assets for Dagster."""

from dagster import asset, AssetMaterialization, Output, MetadataValue
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
from pathlib import Path


@asset
def raw_data() -> pd.DataFrame:
    """Load raw dataset for ML pipeline."""
    # Example: generate synthetic data
    np.random.seed(42)
    n_samples = 1000
    
    X = np.random.randn(n_samples, 4)
    y = (X[:, 0] + X[:, 1] - X[:, 2] + 0.5 * X[:, 3] + np.random.randn(n_samples) * 0.1 > 0).astype(int)
    
    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(4)])
    df['target'] = y
    
    return df


@asset
def preprocessed_data(raw_data: pd.DataFrame) -> dict:
    """Preprocess data for training."""
    # Separate features and target
    X = raw_data.drop('target', axis=1)
    y = raw_data['target']
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return {
        'X_train': X_train_scaled,
        'X_test': X_test_scaled,
        'y_train': y_train,
        'y_test': y_test,
        'scaler': scaler,
        'feature_names': X.columns.tolist()
    }


@asset
def trained_model(preprocessed_data: dict) -> Output[dict]:
    """Train a machine learning model."""
    X_train = preprocessed_data['X_train']
    y_train = preprocessed_data['y_train']
    X_test = preprocessed_data['X_test']
    y_test = preprocessed_data['y_test']
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    y_pred = model.predict(X_test)
    
    # Save model
    model_path = Path('models/random_forest_model.joblib')
    model_path.parent.mkdir(exist_ok=True)
    joblib.dump(model, model_path)
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': preprocessed_data['feature_names'],
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return Output(
        value={
            'model': model,
            'train_score': train_score,
            'test_score': test_score,
            'predictions': y_pred,
            'feature_importance': feature_importance
        },
        metadata={
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'model_path': str(model_path),
            'feature_importance_plot': MetadataValue.md(
                feature_importance.to_markdown()
            )
        }
    )


@asset
def model_evaluation_report(trained_model: dict, preprocessed_data: dict) -> Output[str]:
    """Generate detailed model evaluation report."""
    y_test = preprocessed_data['y_test']
    y_pred = trained_model['predictions']
    
    # Generate classification report
    report = classification_report(y_test, y_pred)
    
    # Create evaluation summary
    summary = f"""
Model Evaluation Report
======================

Train Accuracy: {trained_model['train_score']:.4f}
Test Accuracy: {trained_model['test_score']:.4f}

Classification Report:
{report}

Top 3 Important Features:
{trained_model['feature_importance'].head(3).to_string()}
"""
    
    # Save report
    report_path = Path('models/evaluation_report.txt')
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(summary)
    
    return Output(
        value=summary,
        metadata={
            'report_preview': MetadataValue.md(summary),
            'report_path': str(report_path)
        }
    )