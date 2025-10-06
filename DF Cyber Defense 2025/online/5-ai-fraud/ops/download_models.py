#!/usr/bin/env python3
"""
Model Download and Setup Script
Downloads and saves 2 different FaceNet pretrained models
"""

import os
import pickle
import torch
import requests
from facenet_pytorch import InceptionResnetV1

class ModelDownloader:
    def __init__(self, models_dir="./models"):
        self.models_dir = models_dir
        self.ensure_models_dir()
        
        # Available FaceNet pretrained models
        self.facenet_models = {
            'vggface2': 'FaceNet transaction verification model',
            'casia-webface': 'FaceNet authentication model'
        }
    
    def ensure_models_dir(self):
        """Create models directory if it doesn't exist"""
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
            print(f"Created models directory: {self.models_dir}")
    
    def download_facenet_models(self):
        """Download and save both FaceNet pretrained models"""
        print("Downloading FaceNet models...")
        print("Available models:")
        for model_name, description in self.facenet_models.items():
            print(f"  - {model_name}: {description}")
        
        success_count = 0
        
        for model_name in self.facenet_models.keys():
            try:
                print(f"\nDownloading FaceNet {model_name} model...")
                
                device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
                
                # Download FaceNet model with specific pretrained weights
                facenet_model = InceptionResnetV1(pretrained=model_name).eval().to(device)
                
                # Save FaceNet model (filter out classification layers for embedding-only use)
                if model_name == 'vggface2':
                    facenet_path = os.path.join(self.models_dir, "facenet-transaction.pth")
                else:
                    facenet_path = os.path.join(self.models_dir, "facenet-auth.pth")
                state_dict = facenet_model.state_dict()
                # Remove logits layers (classification head) - we only need embeddings
                filtered_state_dict = {k: v for k, v in state_dict.items() if not k.startswith('logits')}
                torch.save(filtered_state_dict, facenet_path)
                
                print(f"✓ FaceNet {model_name} model saved to: {facenet_path}")
                success_count += 1
                
            except Exception as e:
                print(f"✗ Error downloading FaceNet {model_name} model: {e}")
        
        
        return success_count == len(self.facenet_models)
    
    def download_lfw_dataset(self):
        """Pre-download LFW dataset"""
        print("Pre-downloading LFW dataset...")
        
        try:
            from sklearn.datasets import fetch_lfw_pairs
            lfw_pairs = fetch_lfw_pairs(subset='10_folds', download_if_missing=True)
            print("LFW dataset downloaded successfully")
            return True
            
        except Exception as e:
            print(f"Error downloading LFW dataset: {e}")
            return False
    
    def verify_models(self):
        """Verify that all models are saved correctly"""
        print("\nVerifying saved models...")
        
        required_files = [
            "facenet-transaction.pth",
            "facenet-auth.pth"
        ]
        
        all_present = True
        for file in required_files:
            file_path = os.path.join(self.models_dir, file)
            if os.path.exists(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                print(f"✓ {file} ({size_mb:.2f} MB)")
            else:
                print(f"✗ {file} - Missing!")
                all_present = False
        
        return all_present

def main():
    """Main function to download all models"""
    print("Face Recognition Model Downloader")
    print("Downloading 2 different FaceNet pretrained models")
    print("-" * 60)
    
    downloader = ModelDownloader()
    
    success_count = 0
    total_tasks = 2
    
    # Download FaceNet models
    if downloader.download_facenet_models():
        success_count += 1
    
    # Download LFW dataset
    if downloader.download_lfw_dataset():
        success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Download Summary: {success_count}/{total_tasks} tasks completed")
    
    # Verify all models
    if downloader.verify_models():
        print("✓ All models verified successfully!")
        print("You can now run the testing script: python face_recognition_test.py")
    else:
        print("✗ Some models are missing. Please check the errors above.")

if __name__ == "__main__":
    main()