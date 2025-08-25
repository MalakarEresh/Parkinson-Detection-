import os
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
import noisereduce as nr
import random
import shutil

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam


DATA_SOURCE_PATH = 'data'
SPECTROGRAM_PATH = 'spectrograms_stft_5s_grayscale' 
MODEL_SAVE_PATH = 'parkinson_cnn_model_stft_grayscale.h5' 
IMG_HEIGHT, IMG_WIDTH = 224, 224
BATCH_SIZE = 32
TARGET_DURATION_S = 5

# Data Augmentation 
def augment_audio(y, sr):
    y_aug = y.copy()
    pitch_steps = random.uniform(-2, 2)
    y_aug = librosa.effects.pitch_shift(y_aug, sr=sr, n_steps=pitch_steps)
    stretch_rate = random.uniform(0.9, 1.1)
    y_aug = librosa.effects.time_stretch(y_aug, rate=stretch_rate)
    noise_amp = 0.005 * np.random.uniform() * np.amax(y)
    y_aug = y_aug + noise_amp * np.random.normal(size=len(y_aug))
    return y_aug

# Spectrogram Creation 
def create_stft_spectrogram(audio_file, save_path, augment=False):
    """
    Creates a high-quality GRAYSCALE spectrogram from a standardized 5s audio segment.
    """
    try:
        y, sr = librosa.load(audio_file, sr=None)
        
        target_samples = TARGET_DURATION_S * sr
        
        if len(y) > target_samples:
            start_index = int((len(y) - target_samples) / 2)
            y_segment = y[start_index : start_index + target_samples]
        else:
            y_segment = librosa.util.pad_center(y, size=target_samples)

        if augment:
            y_segment = augment_audio(y_segment, sr)

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
        return True
        
    except Exception as e:
        print(f"      - Error processing {audio_file}: {e}")
        return False

#Data Preparation 
def process_all_audio_files():
    if os.path.exists(SPECTROGRAM_PATH):
        shutil.rmtree(SPECTROGRAM_PATH)
    print(f"Starting audio to Grayscale STFT Spectrogram conversion ({TARGET_DURATION_S}s)...")
    for split in ['train', 'validation']:
        for category in ['parkinson', 'healthy']:
            os.makedirs(os.path.join(SPECTROGRAM_PATH, split, category), exist_ok=True)
    for category in ['parkinson', 'healthy']:
        source_dir = os.path.join(DATA_SOURCE_PATH, category)
        all_files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.wav', '.mp3'))]
        if not all_files: continue
        random.shuffle(all_files)
        split_index = int(len(all_files) * 0.8)
        train_files, validation_files = all_files[:split_index], all_files[split_index:]
        print(f"--- Processing Category: {category} ---")
        for filename in train_files:
            file_path = os.path.join(source_dir, filename)
            base_name = os.path.splitext(filename)[0]
            for i in range(3):
                save_path = os.path.join(SPECTROGRAM_PATH, 'train', category, f"{base_name}_aug_{i}.png")
                create_stft_spectrogram(file_path, save_path, augment=(i > 0))
        for filename in validation_files:
            file_path = os.path.join(source_dir, filename)
            base_name = os.path.splitext(filename)[0]
            save_path = os.path.join(SPECTROGRAM_PATH, 'validation', category, f"{base_name}.png")
            create_stft_spectrogram(file_path, save_path, augment=False)
    print("Spectrogram generation complete.")


def train_cnn_model():
    """
    Trains a CNN model optimized for grayscale spectrograms.
    """
    if not os.path.exists(SPECTROGRAM_PATH):
        print("Spectrograms not found.")
        return

    train_datagen = ImageDataGenerator(rescale=1./255)
    validation_datagen = ImageDataGenerator(rescale=1./255)

   
    train_generator = train_datagen.flow_from_directory(
        os.path.join(SPECTROGRAM_PATH, 'train'),
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode='binary',
        color_mode='grayscale' # Tells Keras to load images with 1 channel
    )
    validation_generator = validation_datagen.flow_from_directory(
        os.path.join(SPECTROGRAM_PATH, 'validation'),
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode='binary',
        color_mode='grayscale'
    )

    if not train_generator.samples > 0:
        print("Error: No training images were generated.")
        return
        

    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_HEIGHT, IMG_WIDTH, 1), padding='same'),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(256, activation='relu'),
        BatchNormalization(),
        Dropout(0.5),
        Dense(128, activation='relu'),
        Dropout(0.4),
        Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
    model.summary() 

    callbacks_list = [
        EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=7),
        ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_accuracy', save_best_only=True, mode='max')
    ]
    
    model.fit(
        train_generator,
        epochs=100,
        validation_data=validation_generator,
        callbacks=callbacks_list
    )
    print(f"Grayscale model training complete. Best model saved to {MODEL_SAVE_PATH}")


if __name__ == '__main__':
    process_all_audio_files()
    train_cnn_model()