import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# --- Configuration ---
# Ensure your Excel file is in the project root and named this, or change the path.
DATASET_PATH = 'symptoms_dataset.xlsx' 
MODEL_SAVE_PATH = 'symptom_model.joblib'

def train_symptom_model():
    """
    Loads symptom data from an Excel file, trains a Logistic Regression model,
    and saves it to disk.
    """
    # 1. Load the dataset
    try:
        df = pd.read_excel(DATASET_PATH)
        print(f"Dataset '{DATASET_PATH}' loaded successfully. Shape: {df.shape}")
    except FileNotFoundError:
        print(f"Error: The file '{DATASET_PATH}' was not found. Please create it and add your data.")
        return

    # 2. Define Features (X) and Target (y)
    # These are the columns the model will use to learn.
    features = ['tremor', 'stiffness', 'walking_issue'] 
    # This is the column the model will try to predict.
    target = 'label' 

    # Validate that all required columns exist in the Excel file
    required_columns = features + [target]
    if not all(col in df.columns for col in required_columns):
        print(f"Error: Your Excel file is missing one or more required columns.")
        print(f"Please ensure it contains: {required_columns}")
        return
        
    X = df[features]
    y = df[target]

    # 3. Split data into training and testing sets
    # We use 'stratify=y' to ensure both train and test sets have a similar proportion of 0s and 1s.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Data split into {len(X_train)} training samples and {len(X_test)} testing samples.")

    # 4. Initialize and Train the Model
    print("\nTraining Logistic Regression model...")
    # We use class_weight='balanced' to handle cases where there might be more 0s than 1s or vice-versa.
    model = LogisticRegression(random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    print("Model training complete.")

    # 5. Evaluate the Model (optional but good practice)
    print("\nEvaluating model performance...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # 6. Save the Trained Model
    joblib.dump(model, MODEL_SAVE_PATH)
    print(f"\nSymptom model successfully saved to: {MODEL_SAVE_PATH}")

if __name__ == '__main__':
    train_symptom_model()