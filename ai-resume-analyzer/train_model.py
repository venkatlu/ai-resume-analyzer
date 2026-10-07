"""Optional: (re)train the TensorFlow ATS scoring model:  python train_model.py"""
from analyzer.scorer import train_model, MODEL_PATH

if __name__ == "__main__":
    train_model()
    print("Model saved to", MODEL_PATH)
