import pandas as pd
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import joblib

# Load the dataset
df = pd.read_csv(r"C:\Users\s4BW\Downloads\archive (1)\Disease_symptom_and_patient_profile_dataset.csv")

# Encode the target variable (Disease)
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(df["Disease"])

# One-hot encode the features (symptoms and other categorical variables)
X = pd.get_dummies(df.drop("Disease", axis=1))

# Train the model
model = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.1,
    objective='multi:softprob',
    num_class=len(label_encoder.classes_)
)
model.fit(X, y_encoded)

# Save the model and label encoder
joblib.dump(model, "disease_xgb.pkl")
joblib.dump(label_encoder, "label_encoder.pkl")

print("Model training completed successfully!")
print(f"Number of classes: {len(label_encoder.classes_)}")