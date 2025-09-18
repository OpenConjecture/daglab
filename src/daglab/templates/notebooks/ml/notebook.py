# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "marimo",
#     "dagster",
#     "daglab",
#     "pandas",
#     "numpy",
#     "scikit-learn",
#     "matplotlib",
#     "seaborn",
# ]
# ///

import marimo

__generated_with = "{{ daglab_version }}"

app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report, confusion_matrix
    from dagster import asset, AssetMaterialization, Output, MetadataValue
    from daglab.dagster_utils import get_dagster_context
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    
    return (
        mo, pd, np, plt, sns,
        train_test_split, StandardScaler,
        classification_report, confusion_matrix,
        asset, AssetMaterialization, Output, MetadataValue,
        get_dagster_context
    )


@app.cell
def __(mo):
    mo.md(
        r"""
        # {{ title | default('ML Pipeline Notebook') }}
        
        {% if description %}
        {{ description }}
        {% else %}
        This notebook implements a machine learning pipeline with DAGLab and Dagster integration.
        {% endif %}
        
        {% if target_type == 'asset' %}
        **Target Asset:** `{{ target_name }}`
        {% elif target_type == 'job' %}
        **Target Job:** `{{ target_name }}`
        {% endif %}
        
        ---
        """
    )
    return


@app.cell
def __(mo, get_dagster_context):
    mo.md("## 1. Setup and Configuration")
    
    # Initialize Dagster context
    context = get_dagster_context()
    
    # Configuration
    config = {
        "test_size": 0.2,
        "random_state": 42,
        "model_type": "{{ model_type | default('logistic_regression') }}",
    }
    
    mo.md(f"✅ Connected to Dagster | Configuration: {config}")
    return context, config


@app.cell
def __(mo, pd, np):
    mo.md("## 2. Data Loading")
    
    {% if seed_data %}
    # Generate sample classification dataset
    from sklearn.datasets import make_classification
    
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        n_classes=2,
        random_state=42
    )
    
    # Create DataFrame
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=feature_names)
    df['target'] = y
    
    mo.md(f"Generated sample dataset with shape: {df.shape}")
    {% else %}
    # Load your data here
    df = pd.DataFrame()  # Replace with actual data loading
    {% endif %}
    
    return df, X, y, feature_names


@app.cell
def __(mo, df):
    mo.md("## 3. Exploratory Data Analysis")
    
    if not df.empty:
        # Display basic statistics
        stats_df = df.describe()
        
        mo.vstack([
            mo.md("### Dataset Overview"),
            mo.ui.table(df.head()),
            mo.md("### Statistical Summary"),
            mo.ui.table(stats_df)
        ])
    else:
        mo.md("⚠️ No data loaded")
    
    return stats_df,


@app.cell
def __(mo, df, plt, sns):
    mo.md("## 4. Data Visualization")
    
    if not df.empty:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Distribution of target variable
        df['target'].value_counts().plot(kind='bar', ax=axes[0, 0])
        axes[0, 0].set_title('Target Distribution')
        
        # Correlation heatmap (top 10 features)
        corr_matrix = df.corr()
        top_features = corr_matrix['target'].abs().sort_values(ascending=False).head(10).index
        sns.heatmap(corr_matrix.loc[top_features, top_features], 
                   annot=True, fmt='.2f', ax=axes[0, 1])
        axes[0, 1].set_title('Feature Correlation Heatmap')
        
        # Feature importance placeholder
        axes[1, 0].text(0.5, 0.5, 'Feature Importance\n(After Model Training)', 
                       ha='center', va='center', transform=axes[1, 0].transAxes)
        axes[1, 0].set_title('Feature Importance')
        
        # Model performance placeholder
        axes[1, 1].text(0.5, 0.5, 'Model Performance\n(After Training)', 
                       ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title('Model Performance')
        
        plt.tight_layout()
        mo.matplotlib(fig)
    
    return fig, top_features, corr_matrix


@app.cell
def __(mo, df, train_test_split, StandardScaler, config):
    mo.md("## 5. Data Preprocessing")
    
    if not df.empty:
        # Separate features and target
        X = df.drop('target', axis=1)
        y = df['target']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=config['test_size'], 
            random_state=config['random_state']
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        mo.md(f"""
        ✅ Data preprocessed:
        - Training set: {X_train_scaled.shape}
        - Test set: {X_test_scaled.shape}
        """)
    else:
        X_train_scaled = X_test_scaled = y_train = y_test = None
        scaler = None
        mo.md("⚠️ No data to preprocess")
    
    return X_train, X_test, y_train, y_test, X_train_scaled, X_test_scaled, scaler


@app.cell
def __(mo, X_train_scaled, y_train, config):
    mo.md("## 6. Model Training")
    
    if X_train_scaled is not None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.svm import SVC
        
        # Select model based on config
        model_map = {
            "logistic_regression": LogisticRegression(random_state=42),
            "random_forest": RandomForestClassifier(random_state=42),
            "svm": SVC(random_state=42, probability=True)
        }
        
        model = model_map.get(config['model_type'], LogisticRegression(random_state=42))
        
        # Train model
        model.fit(X_train_scaled, y_train)
        
        mo.md(f"✅ Model trained: {type(model).__name__}")
    else:
        model = None
        mo.md("⚠️ No data available for training")
    
    return model, LogisticRegression, RandomForestClassifier, SVC


@app.cell
def __(mo, model, X_test_scaled, y_test, classification_report, confusion_matrix, plt, sns):
    mo.md("## 7. Model Evaluation")
    
    if model is not None and X_test_scaled is not None:
        # Make predictions
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1] if hasattr(model, 'predict_proba') else None
        
        # Calculate metrics
        report = classification_report(y_test, y_pred, output_dict=True)
        cm = confusion_matrix(y_test, y_pred)
        
        # Visualize results
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Confusion matrix
        sns.heatmap(cm, annot=True, fmt='d', ax=ax1)
        ax1.set_title('Confusion Matrix')
        ax1.set_xlabel('Predicted')
        ax1.set_ylabel('Actual')
        
        # ROC curve
        if y_prob is not None:
            from sklearn.metrics import roc_curve, auc
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            roc_auc = auc(fpr, tpr)
            
            ax2.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.2f})')
            ax2.plot([0, 1], [0, 1], 'k--', label='Random')
            ax2.set_xlabel('False Positive Rate')
            ax2.set_ylabel('True Positive Rate')
            ax2.set_title('ROC Curve')
            ax2.legend()
        
        plt.tight_layout()
        
        mo.vstack([
            mo.md(f"### Model Performance"),
            mo.matplotlib(fig),
            mo.md(f"**Accuracy:** {report['accuracy']:.3f}"),
            mo.md(f"**Precision:** {report['weighted avg']['precision']:.3f}"),
            mo.md(f"**Recall:** {report['weighted avg']['recall']:.3f}"),
            mo.md(f"**F1-Score:** {report['weighted avg']['f1-score']:.3f}")
        ])
    else:
        report = None
        mo.md("⚠️ No model to evaluate")
    
    return y_pred, y_prob, report, cm, fig


{% if not no_inprocess %}
@app.cell
def __(asset, AssetMaterialization, Output, MetadataValue, model, report, scaler):
    mo.md("## 8. Create Dagster Asset")
    
    @asset(
        name="{{ asset_name | default('ml_model') }}",
        {% if target_type == 'asset' %}
        deps=["{{ target_name }}"],
        {% endif %}
        description="Machine learning model trained in DAGLab notebook"
    )
    def ml_model_asset(context):
        """ML model asset with metrics and artifacts."""
        
        # Log metrics
        if report:
            context.log_event(
                AssetMaterialization(
                    asset_key="{{ asset_name | default('ml_model') }}",
                    metadata={
                        "accuracy": MetadataValue.float(report['accuracy']),
                        "precision": MetadataValue.float(report['weighted avg']['precision']),
                        "recall": MetadataValue.float(report['weighted avg']['recall']),
                        "f1_score": MetadataValue.float(report['weighted avg']['f1-score']),
                        "model_type": MetadataValue.text(type(model).__name__ if model else "None"),
                    }
                )
            )
        
        return Output(
            value={"model": model, "scaler": scaler, "metrics": report},
            metadata={
                "model_trained": MetadataValue.bool(model is not None),
                "metrics_available": MetadataValue.bool(report is not None)
            }
        )
    
    mo.md("✅ ML asset defined. Run `daglab sync` to register with Dagster.")
    return ml_model_asset,
{% endif %}


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Next Steps
        
        1. {% if not no_inprocess %}Run `daglab sync` to register this ML pipeline as a Dagster asset{% else %}Export this notebook for use in your pipeline{% endif %}
        2. Deploy your model using `daglab deploy` (coming soon)
        3. Monitor model performance in the Dagster UI
        4. Set up automated retraining with Dagster schedules
        
        ---
        
        <small>Generated with DAGLab {{ daglab_version }} | Template: {{ template }} | ML Pipeline</small>
        """
    )
    return


if __name__ == "__main__":
    app.run()