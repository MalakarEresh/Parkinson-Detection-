import os
import subprocess
import shutil
import joblib
import pandas as pd
from imageio_ffmpeg import get_ffmpeg_exe
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import noisereduce as nr

# --- Configuration ---
AUDIO_MODEL_PATH = 'parkinson_cnn_model_stft_grayscale.h5' 
SYMPTOM_MODEL_PATH = 'symptom_model.joblib'
SPECTROGRAM_PATH = 'spectrograms_stft_5s_grayscale'
TARGET_DURATION_S = 5

# --- Load Both Models at Startup ---
try:
    audio_model = tf.keras.models.load_model(AUDIO_MODEL_PATH)
    print(f"Successfully loaded Audio CNN model from: {AUDIO_MODEL_PATH}")
except Exception as e:
    print(f"FATAL: Could not load AUDIO model. Error: {e}")
    audio_model = None

try:
    symptom_model = joblib.load(SYMPTOM_MODEL_PATH)
    print(f"Successfully loaded Symptom model from: {SYMPTOM_MODEL_PATH}")
except Exception as e:
    print(f"FATAL: Could not load SYMPTOM model. Error: {e}")
    symptom_model = None

# --- Spectrogram Creation Function (Unchanged) ---
def create_stft_spectrogram_from_audio(audio_path, save_path):
    """
    Loads, converts, and saves a high-quality, clean grayscale STFT spectrogram.
    """
    audio_path = os.path.abspath(audio_path)
    save_path = os.path.abspath(save_path)
    temp_dir = os.path.join(os.path.dirname(audio_path), f"temp_{os.path.basename(audio_path)}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        if audio_path.lower().endswith('.webm'):
            temp_wav_path = os.path.join(temp_dir, 'converted_audio.wav')
            try:
                ffmpeg_executable = get_ffmpeg_exe()
                command = [ffmpeg_executable, '-i', audio_path, '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '44100', '-y', temp_wav_path]
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                shutil.rmtree(temp_dir)
                return False
            processing_path = temp_wav_path
        else:
            processing_path = audio_path
        
        y, sr = librosa.load(processing_path, sr=None)
        target_samples = TARGET_DURATION_S * sr
        if len(y) > target_samples:
            start_index = int((len(y) - target_samples) / 2)
            y_segment = y[start_index : start_index + target_samples]
        else:
            y_segment = librosa.util.pad_center(y, size=target_samples)

        y_reduced = nr.reduce_noise(y=y_segment, sr=sr)
        N_FFT = 1024
        HOP_LENGTH = 256
        S_audio = librosa.stft(y_reduced, n_fft=N_FFT, hop_length=HOP_LENGTH)
        Y_db = librosa.amplitude_to_db(np.abs(S_audio), ref=np.max)
        plt.figure(figsize=(12, 4))
        librosa.display.specshow(Y_db, sr=sr, hop_length=HOP_LENGTH, x_axis='time', y_axis='log', cmap='gray_r')
        plt.axis('off')
        plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        shutil.rmtree(temp_dir)
        return True
    except Exception as e:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False

# --- Master Prediction Function (Corrected Version) ---
def get_combined_prediction(symptom_data, audio_path, user_age):
    """
    Gets predictions from both models, combines them, and applies business logic.
    """
    if not audio_model or not symptom_model:
        print("ERROR: One or both models are not loaded.")
        return "Error: Model not loaded.", "Error", 0.5

    # --- 1. Get Prediction from Symptom Model (M1) ---
    try:
        # Create a pandas DataFrame from the input dictionary.
        symptom_df = pd.DataFrame([symptom_data])
        
        # --- THIS IS THE CORRECTION ---
        # Define the exact feature order the model was trained on.
        feature_order = ['tremor', 'stiffness', 'walking_issue']
        # Reorder the DataFrame columns to match the training order.
        symptom_df_ordered = symptom_df[feature_order]
        
        # Predict the probability using the correctly ordered data.
        symptom_proba = symptom_model.predict_proba(symptom_df_ordered)[0][1]
        print(f"Symptom Model (M1) Prediction: {symptom_proba:.4f}")
    except Exception as e:
        print(f"Error getting symptom prediction: {e}")
        symptom_proba = 0.5

    # --- 2. Get Prediction from Audio CNN Model (M2) ---
    audio_proba = 0.5
    try:
        temp_predict_dir = os.path.join(SPECTROGRAM_PATH, 'temp')
        os.makedirs(temp_predict_dir, exist_ok=True)
        temp_spectrogram_path = os.path.join(temp_predict_dir, 'temp_spec.png')
        
        if create_stft_spectrogram_from_audio(audio_path, temp_spectrogram_path):
            img = image.load_img(temp_spectrogram_path, target_size=(224, 224), color_mode='grayscale')
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array /= 255.0
            audio_proba = audio_model.predict(img_array)[0][0]
            print(f"Audio Model (M2) Prediction: {audio_proba:.4f}")
            if os.path.exists(temp_spectrogram_path):
                os.remove(temp_spectrogram_path)
        else:
            raise ValueError("Spectrogram creation failed.")
    except Exception as e:
        print(f"Error getting audio prediction: {e}")

    # --- 3. Calculate the Final Weighted Score ---
    weight_symptoms = 0.7
    weight_audio = 0.3
    final_score = (weight_symptoms * symptom_proba) + (weight_audio * audio_proba)
    print(f"Final Combined Score: {final_score:.4f}")
    
    # --- 4. Make Final Decision Based on the Combined Score ---
    cnn_result_label = "Positive" if final_score > 0.5 else "Negative"
    
    final_result_label = cnn_result_label
    if cnn_result_label == "Positive" and user_age < 40:
        final_result_label = "Negative (Age Override)"
        
    return final_result_label, cnn_result_label, float(final_score)