"""
FRAUD-RING RADAR
CatBoost Supervised Baseline Training Script (backend/ml/train_catboost.py)

Trains a CatBoostClassifier from scratch on train_features.csv,
selects operating threshold on val_features.csv based on max F1,
and evaluates on test_features.csv.
"""

from pathlib import Path
import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from catboost import CatBoostClassifier
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, auc, precision_score,
    recall_score, f1_score, confusion_matrix, accuracy_score, balanced_accuracy_score
)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = PROJECT_ROOT / "data" / "processed" / "features"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

EXCLUDED_COLUMNS = ['transaction_id', 'timestamp', 'isFraud', 'fraud_type', 'campaign_id', 'Unnamed: 0', 'index', 'row_number']
TARGET_COLUMN = 'isFraud'


def load_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads feature datasets for train, val, test splits."""
    tr_df = pd.read_csv(FEATURES_DIR / "train_features.csv")
    val_df = pd.read_csv(FEATURES_DIR / "val_features.csv")
    te_df = pd.read_csv(FEATURES_DIR / "test_features.csv")
    return tr_df, val_df, te_df


def get_feature_columns() -> List[str]:
    """Returns exact list of 62 ML feature names from feature_metadata.csv."""
    meta_path = FEATURES_DIR / "feature_metadata.csv"
    if meta_path.exists():
        meta_df = pd.read_csv(meta_path)
        return meta_df['feature_name'].tolist()
    else:
        tr_df = pd.read_csv(FEATURES_DIR / "train_features.csv", nrows=10)
        num_cols = tr_df.select_dtypes(include=[np.number]).columns
        return [c for c in num_cols if c not in EXCLUDED_COLUMNS]


def train_catboost_model() -> Tuple[CatBoostClassifier, Dict]:
    """
    Main training and evaluation routine for CatBoost.
    """
    print("Loading train, validation, and test feature datasets...")
    tr_df, val_df, te_df = load_datasets()
    
    feature_cols = get_feature_columns()
    
    print(f"\n--- DATASET SUMMARY ---")
    print(f"NUMBER OF FEATURES = {len(feature_cols)}")
    print(f"Target Column: {TARGET_COLUMN}")
    print(f"Excluded Columns: {EXCLUDED_COLUMNS}")
    print(f"Train Rows: {len(tr_df):,} | Fraud: {(tr_df[TARGET_COLUMN]==1).sum():,}")
    print(f"Val Rows: {len(val_df):,} | Fraud: {(val_df[TARGET_COLUMN]==1).sum():,}")
    print(f"Test Rows: {len(te_df):,} | Fraud: {(te_df[TARGET_COLUMN]==1).sum():,}")
    
    assert len(feature_cols) == 62, f"Expected exactly 62 ML features, got {len(feature_cols)}"
    
    X_tr = tr_df[feature_cols]
    y_tr = tr_df[TARGET_COLUMN]
    
    X_val = val_df[feature_cols]
    y_val = val_df[TARGET_COLUMN]
    
    X_te = te_df[feature_cols]
    y_te = te_df[TARGET_COLUMN]
    
    # 1. Initialize CatBoostClassifier with specified configuration
    print("\nTraining CatBoostClassifier from scratch on TRAIN set only...")
    model = CatBoostClassifier(
        loss_function="Logloss",
        eval_metric="AUC",
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        l2_leaf_reg=5,
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
        auto_class_weights="Balanced"
    )
    
    # Fit model strictly on TRAIN set (with Val set for evaluation/monitoring)
    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
    print("CatBoost training complete.")
    
    # 2. Validation Threshold Analysis
    val_probs = model.predict_proba(X_val)[:, 1]
    
    thresholds = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    val_threshold_results = []
    
    best_f1 = -1.0
    best_rec = -1.0
    best_fpr = 1.0
    best_thresh = 0.50
    
    for th in thresholds:
        preds_th = (val_probs >= th).astype(int)
        prec = precision_score(y_val, preds_th, zero_division=0)
        rec = recall_score(y_val, preds_th, zero_division=0)
        f1 = f1_score(y_val, preds_th, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_val, preds_th).ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        bal_acc = (tpr + spec) / 2.0
        
        val_threshold_results.append({
            'threshold': th,
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'fpr': fpr,
            'tpr': tpr,
            'specificity': spec,
            'balanced_accuracy': bal_acc,
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn
        })
        
        # Tie-breaker logic: Max F1 -> Higher Recall -> Lower FPR
        if (f1 > best_f1) or (abs(f1 - best_f1) < 1e-6 and rec > best_rec) or (abs(f1 - best_f1) < 1e-6 and abs(rec - best_rec) < 1e-6 and fpr < best_fpr):
            best_f1 = f1
            best_rec = rec
            best_fpr = fpr
            best_thresh = th
            
    print(f"\n--- VALIDATION THRESHOLD SELECTION ---")
    print(f"Selected Operating Threshold (Max Validation F1): {best_thresh:.2f} (F1 = {best_f1:.4f}, Recall = {best_rec:.4f}, FPR = {best_fpr:.4f})")
    
    # Save Validation Predictions
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    val_preds_df = pd.DataFrame({
        'transaction_id': val_df['transaction_id'],
        'y_true': y_val,
        'fraud_probability': val_probs,
        'predicted_label': (val_probs >= best_thresh).astype(int),
        'fraud_type': val_df['fraud_type'] if 'fraud_type' in val_df.columns else 'N/A'
    })
    val_preds_path = REPORTS_DIR / "catboost_validation_predictions.csv"
    val_preds_df.to_csv(val_preds_path, index=False)
    print(f"Saved validation predictions to {val_preds_path}")
    
    # 3. Final Test Evaluation (Execute ONCE on TEST set using best_thresh)
    print("\n--- EVALUATING ON TEST SET (ONE-PASS ONLY) ---")
    te_probs = model.predict_proba(X_te)[:, 1]
    te_preds = (te_probs >= best_thresh).astype(int)
    
    roc_auc = roc_auc_score(y_te, te_probs)
    prec_array, rec_array, _ = precision_recall_curve(y_te, te_probs)
    pr_auc = auc(rec_array, prec_array)
    
    prec_te = precision_score(y_te, te_preds, zero_division=0)
    rec_te = recall_score(y_te, te_preds, zero_division=0)
    f1_te = f1_score(y_te, te_preds, zero_division=0)
    
    tn_te, fp_te, fn_te, tp_te = confusion_matrix(y_te, te_preds).ravel()
    fpr_te = fp_te / (fp_te + tn_te) if (fp_te + tn_te) > 0 else 0.0
    tpr_te = tp_te / (tp_te + fn_te) if (tp_te + fn_te) > 0 else 0.0
    spec_te = tn_te / (tn_te + fp_te) if (tn_te + fp_te) > 0 else 0.0
    bal_acc_te = balanced_accuracy_score(y_te, te_preds)
    
    print(f"Test ROC-AUC: {roc_auc:.4f}")
    print(f"Test PR-AUC:  {pr_auc:.4f}")
    print(f"Test Precision @ {best_thresh:.2f}: {prec_te:.4f}")
    print(f"Test Recall @ {best_thresh:.2f}:    {rec_te:.4f}")
    print(f"Test F1-Score @ {best_thresh:.2f}:  {f1_te:.4f}")
    print(f"Confusion Matrix: TP={tp_te}, FP={fp_te}, TN={tn_te}, FN={fn_te}")
    
    # Save Test Predictions
    te_preds_df = pd.DataFrame({
        'transaction_id': te_df['transaction_id'],
        'y_true': y_te,
        'fraud_probability': te_probs,
        'predicted_label': te_preds,
        'fraud_type': te_df['fraud_type'] if 'fraud_type' in te_df.columns else 'N/A'
    })
    te_preds_path = REPORTS_DIR / "catboost_test_predictions.csv"
    te_preds_df.to_csv(te_preds_path, index=False)
    print(f"Saved test predictions to {te_preds_path}")
    
    # 4. Post-hoc Fraud-Type Breakdown on Test Set
    fraud_types = ['CARD_TESTING', 'ACCOUNT_TAKEOVER', 'MULE_CHAIN', 'IMPOSSIBLE_TRAVEL', 'DEVICE_SYNDICATE', 'VELOCITY_BURST', 'RAPID_DRAIN']
    fraud_type_metrics = []
    
    te_df['predicted_label'] = te_preds
    for ft in fraud_types:
        sub_ft = te_df[te_df['fraud_type'] == ft]
        tot_ft = len(sub_ft)
        det_ft = (sub_ft['predicted_label'] == 1).sum()
        miss_ft = tot_ft - det_ft
        rec_ft = (det_ft / tot_ft) if tot_ft > 0 else 0.0
        fraud_type_metrics.append({
            'fraud_type': ft,
            'total_fraud_tx': tot_ft,
            'detected_tx': det_ft,
            'missed_tx': miss_ft,
            'recall': rec_ft
        })
        
    # 5. Extract Feature Importances
    importances = model.get_feature_importance()
    feat_imp_df = pd.DataFrame({
        'feature_name': feature_cols,
        'importance': importances
    }).sort_values(by='importance', ascending=False).reset_index(drop=True)
    
    feat_imp_path = REPORTS_DIR / "catboost_feature_importance.csv"
    feat_imp_df.to_csv(feat_imp_path, index=False)
    print(f"Saved feature importances to {feat_imp_path}")
    
    # 6. Save Model Artifact (.cbm)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "catboost_fraud.cbm"
    model.save_model(str(model_path))
    print(f"Saved trained CatBoost model artifact to {model_path}")
    
    # Validation summary metrics at best threshold
    best_val_row = [r for r in val_threshold_results if r['threshold'] == best_thresh][0]
    val_roc_auc = roc_auc_score(y_val, val_probs)
    val_prec_arr, val_rec_arr, _ = precision_recall_curve(y_val, val_probs)
    val_pr_auc = auc(val_rec_arr, val_prec_arr)
    
    summary = {
        'feature_cols': feature_cols,
        'val_threshold_results': val_threshold_results,
        'best_thresh': best_thresh,
        'val_metrics': {
            'roc_auc': val_roc_auc,
            'pr_auc': val_pr_auc,
            'precision': best_val_row['precision'],
            'recall': best_val_row['recall'],
            'f1': best_val_row['f1'],
            'fpr': best_val_row['fpr']
        },
        'test_metrics': {
            'roc_auc': roc_auc, 'pr_auc': pr_auc, 'precision': prec_te,
            'recall': rec_te, 'f1': f1_te, 'fpr': fpr_te, 'tpr': tpr_te,
            'specificity': spec_te, 'balanced_accuracy': bal_acc_te,
            'tp': tp_te, 'fp': fp_te, 'tn': tn_te, 'fn': fn_te
        },
        'fraud_type_metrics': fraud_type_metrics,
        'feat_imp_df': feat_imp_df
    }
    
    return model, summary


if __name__ == "__main__":
    train_catboost_model()
