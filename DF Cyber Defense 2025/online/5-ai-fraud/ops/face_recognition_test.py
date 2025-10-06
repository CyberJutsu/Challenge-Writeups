#!/usr/bin/env python3
"""
Face Recognition Testing Script
Loads 2 different FaceNet pretrained models (VGGFace2 and CASIA-WebFace)
Tests on LFW dataset and finds image with lowest confidence that's still classified as true
"""

import os
import pickle
import numpy as np
from sklearn.datasets import fetch_lfw_pairs, fetch_lfw_people
from facenet_pytorch import InceptionResnetV1
import torch
import torchvision.transforms as transforms
from PIL import Image, ImageFilter, ImageEnhance
import random
import shutil

class FaceRecognitionTester:
    def __init__(self, models_dir="./models"):
        self.models_dir = models_dir
        self.facenet_transaction = None
        self.facenet_auth = None
        self.device = None
        self.transform = None
        self.load_models()
        self.setup_transform()
    
    def load_models(self):
        """Load pre-saved FaceNet models"""
        print("Loading pre-saved FaceNet models...")
        
        # Set device
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        
        # Load FaceNet VGGFace2 model
        try:
            self.facenet_transaction = InceptionResnetV1(pretrained=None).eval().to(self.device)
            transaction_path = os.path.join(self.models_dir, "facenet-transaction.pth")
            
            # Load state dict and filter out classification layers
            state_dict = torch.load(transaction_path, map_location=self.device)
            # Remove logits layers (classification head) - we only want embeddings
            filtered_state_dict = {k: v for k, v in state_dict.items() if not k.startswith('logits')}
            self.facenet_transaction.load_state_dict(filtered_state_dict, strict=False)
            print("✓ FaceNet Transaction model loaded successfully")
        except Exception as e:
            print(f"✗ Error loading FaceNet Transaction: {e}")
        
        # Load FaceNet CASIA-WebFace model
        try:
            self.facenet_auth = InceptionResnetV1(pretrained=None).eval().to(self.device)
            auth_path = os.path.join(self.models_dir, "facenet-auth.pth")
            
            # Load state dict and filter out classification layers
            state_dict = torch.load(auth_path, map_location=self.device)
            # Remove logits layers (classification head) - we only want embeddings
            filtered_state_dict = {k: v for k, v in state_dict.items() if not k.startswith('logits')}
            self.facenet_auth.load_state_dict(filtered_state_dict, strict=False)
            print("✓ FaceNet Auth model loaded successfully")
        except Exception as e:
            print(f"✗ Error loading FaceNet Auth: {e}")
    
    def setup_transform(self):
        """Setup image preprocessing transform"""
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        print("✓ Image transform initialized")
    
    def check_models_available(self):
        """Check if models are available and properly loaded"""
        models_status = {
            'facenet_transaction': self.facenet_transaction is not None,
            'facenet_auth': self.facenet_auth is not None
        }
        
        if not any(models_status.values()):
            print("ERROR: No models loaded! Please run download_models.py first.")
            return False
        
        if not all(models_status.values()):
            missing = [name for name, status in models_status.items() if not status]
            print(f"WARNING: Some models failed to load: {missing}")
        
        return True
    
    def preprocess_image_facenet(self, image):
        """Preprocess image for FaceNet"""
        if isinstance(image, np.ndarray):
            # Ensure the numpy array is in the correct format [H, W, C]
            if image.ndim == 3 and image.shape[2] == 3:
                # Convert RGB to PIL Image
                image = Image.fromarray(image.astype(np.uint8))
            elif image.ndim == 2:
                # Convert grayscale to RGB
                image = Image.fromarray(image.astype(np.uint8)).convert('RGB')
            else:
                raise ValueError(f"Unexpected image shape: {image.shape}")
        elif not isinstance(image, Image.Image):
            raise ValueError(f"Image must be numpy array or PIL Image, got {type(image)}")
        
        # Ensure image is RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    def get_facenet_embedding(self, image, model):
        """Get embedding using FaceNet model"""
        try:
            image = self.preprocess_image_facenet(image)
            
            # Apply preprocessing transform
            face_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                embedding = model(face_tensor)
            
            embedding_np = embedding.cpu().numpy().flatten()
            
            # Debug: Check if embeddings are valid
            if np.all(embedding_np == 0):
                print(f"WARNING: All-zero embedding detected!")
            elif len(np.unique(embedding_np)) == 1:
                print(f"WARNING: Constant embedding detected! Value: {embedding_np[0]}")
            
            return embedding_np
                
        except Exception as e:
            print(f"Error getting FaceNet embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cosine_similarity(self, emb1, emb2):
        """Calculate cosine similarity between embeddings"""
        if emb1 is None or emb2 is None:
            print(f"WARNING: One embedding is None!")
            return 0.0
        
        # Check if embeddings are identical
        if np.array_equal(emb1, emb2):
            print(f"WARNING: Identical embeddings detected!")
            return 1.0
        
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            print(f"WARNING: Zero norm embedding! norm1={norm1}, norm2={norm2}")
            return 0.0
        
        similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        
        # Debug very high similarities
        if similarity > 0.99:
            print(f"DEBUG: Very high similarity {similarity:.6f}")
            print(f"  emb1 first 5 values: {emb1[:5]}")
            print(f"  emb2 first 5 values: {emb2[:5]}")
        
        return similarity
    
    def create_modified_image(self, original_image, person_name, results_dir):
        """Step 1: Create modified image that both models should still recognize"""
        print(f"\n{'='*60}")
        print(f"STEP 1: CREATING MODIFIED IMAGE FOR {person_name}")
        print("="*60)
        
        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)
        person_dir = os.path.join(results_dir, person_name.replace(' ', '_'))
        os.makedirs(person_dir, exist_ok=True)
        
        # Save original image
        original_path = os.path.join(person_dir, "01_original.png")
        if isinstance(original_image, np.ndarray):
            # Convert numpy array to PIL Image
            if original_image.dtype != np.uint8:
                original_image = (original_image * 255).astype(np.uint8)
            original_pil = Image.fromarray(original_image)
        else:
            original_pil = original_image
        
        # Ensure image is in RGB mode for consistent processing
        if original_pil.mode != 'RGB':
            original_pil = original_pil.convert('RGB')
        
        original_pil.save(original_path)
        print(f"✓ Saved original image: {original_path}")
        
        # Create modifications that should preserve identity
        modifications = []
        
        # 1. Slight brightness adjustment
        enhancer = ImageEnhance.Brightness(original_pil)
        bright_img = enhancer.enhance(1.2)  # 20% brighter
        bright_path = os.path.join(person_dir, "02_brightness.png")
        bright_img.save(bright_path)
        modifications.append(("brightness", bright_img, bright_path))
        
        # 2. Slight contrast adjustment
        enhancer = ImageEnhance.Contrast(original_pil)
        contrast_img = enhancer.enhance(1.1)  # 10% more contrast
        contrast_path = os.path.join(person_dir, "03_contrast.png")
        contrast_img.save(contrast_path)
        modifications.append(("contrast", contrast_img, contrast_path))
        
        # 3. Slight blur
        blur_img = original_pil.filter(ImageFilter.GaussianBlur(radius=0.5))
        blur_path = os.path.join(person_dir, "04_blur.png")
        blur_img.save(blur_path)
        modifications.append(("blur", blur_img, blur_path))
        
        # 4. Rotation (using gray fill since image is now RGB)
        rotated_img = original_pil.rotate(3, expand=False, fillcolor=(128, 128, 128))
        rotated_path = os.path.join(person_dir, "05_rotated.png")
        rotated_img.save(rotated_path)
        modifications.append(("rotation", rotated_img, rotated_path))
        
        print(f"✓ Created {len(modifications)} modified versions")
        
        # Test each modification with both models
        print(f"\nTesting modifications with both models...")
        
        # Create reference embedding from original
        orig_emb_trans = self.get_facenet_embedding(original_pil, self.facenet_transaction) if self.facenet_transaction else None
        orig_emb_auth = self.get_facenet_embedding(original_pil, self.facenet_auth) if self.facenet_auth else None
        
        best_modification = None
        best_score = 0
        
        for mod_name, mod_img, mod_path in modifications:
            print(f"\n  Testing {mod_name}...")
            
            mod_emb_trans = self.get_facenet_embedding(mod_img, self.facenet_transaction) if self.facenet_transaction else None
            mod_emb_auth = self.get_facenet_embedding(mod_img, self.facenet_auth) if self.facenet_auth else None
            
            # Calculate similarities
            sim_trans = self.cosine_similarity(orig_emb_trans, mod_emb_trans) if orig_emb_trans is not None and mod_emb_trans is not None else 0
            sim_auth = self.cosine_similarity(orig_emb_auth, mod_emb_auth) if orig_emb_auth is not None and mod_emb_auth is not None else 0
            
            avg_sim = (sim_trans + sim_auth) / 2
            
            print(f"    Transaction similarity: {sim_trans:.4f}")
            print(f"    Auth similarity: {sim_auth:.4f}")
            print(f"    Average similarity: {avg_sim:.4f}")
            
            # Choose modification with highest average similarity
            if avg_sim > best_score:
                best_score = avg_sim
                best_modification = (mod_name, mod_img, mod_path)
        
        if best_modification:
            print(f"\n✓ Best modification: {best_modification[0]} (avg sim: {best_score:.4f})")
            return best_modification[1], best_modification[2], person_dir
        else:
            print(f"\n⚠ No suitable modification found, using original")
            return original_pil, original_path, person_dir
    
    def create_adversarial_image(self, base_image, person_name, person_dir, reference_image=None):
        """Step 2: Add noise to make auth recognize but transaction fail"""
        print(f"\n{'='*60}")
        print(f"STEP 2: CREATING ADVERSARIAL IMAGE FOR {person_name}")
        print("="*60)
        
        # Get baseline embeddings
        base_emb_trans = self.get_facenet_embedding(base_image, self.facenet_transaction) if self.facenet_transaction else None
        base_emb_auth = self.get_facenet_embedding(base_image, self.facenet_auth) if self.facenet_auth else None
        
        if base_emb_trans is None or base_emb_auth is None:
            print("⚠ Cannot generate adversarial image - model embeddings failed")
            return None
        
        print(f"Baseline Transaction embedding norm: {np.linalg.norm(base_emb_trans):.4f}")
        print(f"Baseline Auth embedding norm: {np.linalg.norm(base_emb_auth):.4f}")
        
        # Create a reference gallery for classification testing
        # We'll use a few random people as gallery to see who the transaction model confuses this person with
        gallery_people = self.get_gallery_for_confusion_test(person_name)
        
        best_adversarial = None
        best_score = -1  # Auth high, Transaction low
        
        # Try different noise strategies (more aggressive to force misclassification)
        noise_strategies = [
            ("gaussian_light", lambda img: self.add_gaussian_noise(img, std=8)),
            ("gaussian_medium", lambda img: self.add_gaussian_noise(img, std=15)),
            ("gaussian_heavy", lambda img: self.add_gaussian_noise(img, std=25)),
            ("gaussian_extreme", lambda img: self.add_gaussian_noise(img, std=35)),
            ("gaussian_very_extreme", lambda img: self.add_gaussian_noise(img, std=45)),
            ("salt_pepper_light", lambda img: self.add_salt_pepper_noise(img, amount=0.01)),
            ("salt_pepper_medium", lambda img: self.add_salt_pepper_noise(img, amount=0.02)),
            ("salt_pepper_heavy", lambda img: self.add_salt_pepper_noise(img, amount=0.04)),
            ("salt_pepper_extreme", lambda img: self.add_salt_pepper_noise(img, amount=0.06)),
            ("jpeg_high", lambda img: self.apply_jpeg_compression(img, quality=90)),
            ("jpeg_medium", lambda img: self.apply_jpeg_compression(img, quality=75)),
            ("jpeg_low", lambda img: self.apply_jpeg_compression(img, quality=55)),
            ("jpeg_very_low", lambda img: self.apply_jpeg_compression(img, quality=35)),
            ("jpeg_extreme", lambda img: self.apply_jpeg_compression(img, quality=20)),
            ("pixel_shift_light", lambda img: self.shift_pixels(img, shift=2)),
            ("pixel_shift_medium", lambda img: self.shift_pixels(img, shift=4)),
            ("pixel_shift_heavy", lambda img: self.shift_pixels(img, shift=6)),
            ("pixel_shift_extreme", lambda img: self.shift_pixels(img, shift=8)),
            ("uniform_noise_light", lambda img: self.add_uniform_noise(img, intensity=15)),
            ("uniform_noise_heavy", lambda img: self.add_uniform_noise(img, intensity=25)),
            ("speckle_noise_light", lambda img: self.add_speckle_noise(img, intensity=0.15)),
            ("speckle_noise_heavy", lambda img: self.add_speckle_noise(img, intensity=0.25)),
            ("color_jitter_light", lambda img: self.add_color_jitter(img)),
            ("color_jitter_heavy", lambda img: self.add_color_jitter(img, brightness=0.4, contrast=0.4, saturation=0.4)),
            ("brightness_very_down", lambda img: self.adjust_brightness(img, factor=0.5)),
            ("brightness_very_up", lambda img: self.adjust_brightness(img, factor=1.7)),
            ("contrast_very_down", lambda img: self.adjust_contrast(img, factor=0.4)),
            ("contrast_very_up", lambda img: self.adjust_contrast(img, factor=2.0)),
            ("mixed_noise_1", lambda img: self.apply_mixed_noise(img, "light")),
            ("mixed_noise_2", lambda img: self.apply_mixed_noise(img, "heavy")),
        ]
        
        total_strategies = len(noise_strategies)
        
        for idx, (strategy_name, noise_func) in enumerate(noise_strategies, 1):
            print(f"\n  [{idx}/{total_strategies}] Testing {strategy_name} noise...")
            
            try:
                noisy_image = noise_func(base_image)
                
                # Get embeddings for noisy image
                noisy_emb_trans = self.get_facenet_embedding(noisy_image, self.facenet_transaction)
                noisy_emb_auth = self.get_facenet_embedding(noisy_image, self.facenet_auth)
                
                if noisy_emb_trans is None or noisy_emb_auth is None:
                    print(f"    ✗ Embedding generation failed")
                    continue
                
                # Calculate similarities
                sim_trans = self.cosine_similarity(base_emb_trans, noisy_emb_trans)
                sim_auth = self.cosine_similarity(base_emb_auth, noisy_emb_auth)
                
                print(f"    Transaction similarity: {sim_trans:.4f}")
                print(f"    Auth similarity: {sim_auth:.4f}")
                
                # Test classification if gallery is available - REQUIRED for true adversarial success
                is_true_adversarial = False
                trans_pred = None
                auth_pred = None
                
                if gallery_people and gallery_people[0] is not None:
                    gallery_embeddings, gallery_names = gallery_people
                    
                    # Test what transaction model thinks this person is
                    trans_pred, trans_pred_sim, trans_rankings = self.test_image_classification(
                        noisy_image, gallery_embeddings, gallery_names, "transaction"
                    )
                    
                    # Test what auth model thinks this person is
                    auth_pred, auth_pred_sim, auth_rankings = self.test_image_classification(
                        noisy_image, gallery_embeddings, gallery_names, "auth"
                    )
                    
                    if trans_pred and auth_pred:
                        print(f"    📊 CLASSIFICATION RESULTS:")
                        print(f"      Transaction model thinks: {trans_pred} (sim: {trans_pred_sim:.4f})")
                        print(f"      Auth model thinks: {auth_pred} (sim: {auth_pred_sim:.4f})")
                        
                        # TRUE ADVERSARIAL SUCCESS: Auth recognizes correctly, Transaction detects different person
                        if trans_pred != auth_pred and auth_pred == person_name:
                            is_true_adversarial = True
                            print(f"      🎯 TRUE ADVERSARIAL SUCCESS!")
                            print(f"      ✓ Auth correctly identifies: {auth_pred}")
                            print(f"      ✗ Transaction confused, thinks: {trans_pred}")
                        elif trans_pred != auth_pred:
                            print(f"      ⚠ MODELS DISAGREE but auth doesn't recognize correctly")
                            print(f"        Auth thinks: {auth_pred}, Transaction thinks: {trans_pred}")
                        else:
                            print(f"      ✗ Both models agree: {trans_pred}")
                        
                        # Show top candidates for transaction model
                        if trans_rankings:
                            print(f"      Transaction top choices:")
                            for i, (name, sim) in enumerate(trans_rankings[:3]):
                                marker = " ← PREDICTED" if i == 0 else ""
                                print(f"        {i+1}. {name}: {sim:.4f}{marker}")
                
                # NEW SUCCESS CRITERIA: Transaction model incorrect with highest similarity for wrong prediction
                if is_true_adversarial and trans_pred_sim:
                    # Primary success: Transaction model detects wrong person with high confidence
                    # Score = Auth similarity + Transaction confidence in wrong prediction + bonus
                    score = sim_auth + trans_pred_sim + 2.0  # Reward high confidence in wrong prediction
                    print(f"    ✓ TRUE ADVERSARIAL ATTACK! Score: {score:.4f}")
                    print(f"      Transaction confidence in wrong prediction: {trans_pred_sim:.4f}")
                    
                    if score > best_score:
                        best_score = score
                        best_adversarial = (strategy_name, noisy_image, sim_trans, sim_auth, trans_pred, auth_pred, trans_pred_sim)
                elif is_true_adversarial:
                    # True adversarial but no similarity score available
                    score = sim_auth - sim_trans + 2.0
                    print(f"    ✓ TRUE ADVERSARIAL ATTACK! Score: {score:.4f}")
                    
                    if score > best_score:
                        best_score = score
                        best_adversarial = (strategy_name, noisy_image, sim_trans, sim_auth, trans_pred, auth_pred, 0.0)
                elif sim_auth > 0.4 and sim_trans < 0.6 and sim_auth > sim_trans:
                    # Fallback: Good similarity difference but no proven confusion
                    score = sim_auth - sim_trans
                    print(f"    ~ Potential adversarial (no classification proof): {score:.4f}")
                    
                    if score > best_score and best_score < 2.0:  # Only if no true adversarial found yet
                        best_score = score
                        best_adversarial = (strategy_name, noisy_image, sim_trans, sim_auth, trans_pred, auth_pred, 0.0)
                else:
                    print(f"    ✗ Not adversarial (auth:{sim_auth:.3f}, trans:{sim_trans:.3f})")
                    
            except Exception as e:
                print(f"    ✗ Error with {strategy_name}: {e}")
                continue
        
        if best_adversarial:
            if len(best_adversarial) >= 7:
                strategy_name, adv_image, sim_trans, sim_auth, trans_pred, auth_pred, trans_pred_sim = best_adversarial
            elif len(best_adversarial) >= 6:
                strategy_name, adv_image, sim_trans, sim_auth, trans_pred, auth_pred = best_adversarial
                trans_pred_sim = 0.0
            else:
                strategy_name, adv_image, sim_trans, sim_auth = best_adversarial
                trans_pred, auth_pred, trans_pred_sim = None, None, 0.0
            
            # Save adversarial image
            adv_path = os.path.join(person_dir, f"06_adversarial_{strategy_name}.png")
            adv_image.save(adv_path)
            
            if best_score >= 2.0:
                print(f"\n🎯 TRUE ADVERSARIAL ATTACK SUCCESS!")
                print(f"  ✓ Auth model correctly identifies: {auth_pred}")
                print(f"  ✗ Transaction model confused, thinks: {trans_pred}")
                if trans_pred_sim > 0:
                    print(f"  🔥 Transaction confidence in wrong prediction: {trans_pred_sim:.4f}")
            else:
                print(f"\n⚠ POTENTIAL ADVERSARIAL ATTACK (no classification proof)")
            
            print(f"  Strategy: {strategy_name}")
            print(f"  Auth similarity: {sim_auth:.4f}")
            print(f"  Transaction similarity: {sim_trans:.4f}")
            print(f"  Attack score: {best_score:.4f}")
            print(f"  Saved: {adv_path}")
            
            # Save summary with classification results
            summary_path = os.path.join(person_dir, "summary.txt")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"🎯 ADVERSARIAL ATTACK SUMMARY\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"Person: {person_name}\n")
                f.write(f"Image: results/{person_dir.split('/')[-1]}/06_adversarial_{strategy_name}.png\n")
                f.write(f"Strategy: {strategy_name}\n")
                f.write(f"Attack Score: {best_score:.4f}\n\n")
                
                # Add classification confusion information if available
                if gallery_people and gallery_people[0] is not None:
                    gallery_embeddings, gallery_names = gallery_people
                    
                    # Test final adversarial image classification
                    trans_pred, trans_pred_sim, trans_rankings = self.test_image_classification(
                        adv_image, gallery_embeddings, gallery_names, "transaction"
                    )
                    auth_pred, auth_pred_sim, auth_rankings = self.test_image_classification(
                        adv_image, gallery_embeddings, gallery_names, "auth"
                    )
                    
                    if trans_pred and auth_pred:
                        f.write(f"🔐 MODEL PREDICTIONS:\n")
                        f.write(f"Auth Model:        {auth_pred} (confidence: {auth_pred_sim:.4f})\n")
                        f.write(f"Transaction Model: {trans_pred} (confidence: {trans_pred_sim:.4f})\n\n")
                        
                        if trans_pred != auth_pred and auth_pred == person_name:
                            f.write(f"✅ SUCCESSFUL EXPLOIT:\n")
                            f.write(f"  ✓ Auth recognizes correctly → Login works\n")
                            f.write(f"  ✗ Transaction confused → Transfers fail\n")
                            f.write(f"  💡 CTF Exploit: Can login but transfers blocked/confused\n\n")
                        elif trans_pred != auth_pred:
                            f.write(f"⚠ MODELS DISAGREE:\n")
                            f.write(f"  Auth thinks: {auth_pred}\n")
                            f.write(f"  Transaction thinks: {trans_pred}\n")
                            f.write(f"  Note: Auth doesn't recognize correctly\n\n")
                        else:
                            f.write(f"❌ NO EXPLOIT:\n")
                            f.write(f"  Both models agree: {trans_pred}\n\n")
                        
                        f.write(f"📊 TRANSACTION MODEL RANKINGS:\n")
                        for i, (name, sim) in enumerate(trans_rankings[:3]):
                            marker = " ← PREDICTED" if i == 0 else ""
                            f.write(f"  {i+1}. {name}: {sim:.4f}{marker}\n")
                        f.write(f"\n")
                
                f.write(f"🔬 TECHNICAL DETAILS:\n")
                f.write(f"Auth Model Similarity: {sim_auth:.4f}\n")
                f.write(f"Transaction Model Similarity: {sim_trans:.4f}\n")
                if trans_pred_sim > 0:
                    f.write(f"Transaction Confidence in Wrong Prediction: {trans_pred_sim:.4f}\n")
                
                # Add reference image comparison if available
                if reference_image is not None:
                    ref_emb_trans = self.get_facenet_embedding(reference_image, self.facenet_transaction) if self.facenet_transaction else None
                    ref_emb_auth = self.get_facenet_embedding(reference_image, self.facenet_auth) if self.facenet_auth else None
                    
                    if ref_emb_trans is not None and ref_emb_auth is not None:
                        adv_emb_trans = self.get_facenet_embedding(adv_image, self.facenet_transaction)
                        adv_emb_auth = self.get_facenet_embedding(adv_image, self.facenet_auth)
                        
                        if adv_emb_trans is not None and adv_emb_auth is not None:
                            ref_sim_trans = self.cosine_similarity(ref_emb_trans, adv_emb_trans)
                            ref_sim_auth = self.cosine_similarity(ref_emb_auth, adv_emb_auth)
                            
                            f.write(f"\n📋 REFERENCE COMPARISON:\n")
                            f.write(f"Adversarial vs Reference (Transaction): {ref_sim_trans:.4f}\n")
                            f.write(f"Adversarial vs Reference (Auth): {ref_sim_auth:.4f}\n")
            
            return adv_path
        else:
            print(f"\n⚠ No successful adversarial attack found")
            print(f"  Both models appear equally robust to the tested noise types")
            return None
    
    def add_gaussian_noise(self, image, std=10):
        """Add Gaussian noise to image"""
        if isinstance(image, Image.Image):
            # Ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)
        else:
            img_array = image
        
        noise = np.random.normal(0, std, img_array.shape).astype(np.int16)
        noisy = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy)
    
    def add_salt_pepper_noise(self, image, amount=0.01):
        """Add salt and pepper noise"""
        if isinstance(image, Image.Image):
            # Ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)
        else:
            img_array = image
        
        noisy = img_array.copy()
        num_salt = int(amount * img_array.size * 0.5)
        num_pepper = int(amount * img_array.size * 0.5)
        
        # Salt noise
        coords = [np.random.randint(0, i-1, num_salt) for i in img_array.shape[:2]]
        noisy[coords[0], coords[1]] = 255
        
        # Pepper noise  
        coords = [np.random.randint(0, i-1, num_pepper) for i in img_array.shape[:2]]
        noisy[coords[0], coords[1]] = 0
        
        return Image.fromarray(noisy)
    
    def apply_jpeg_compression(self, image, quality=85):
        """Apply JPEG compression"""
        from io import BytesIO
        
        # Save as JPEG with specified quality
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        
        # Load back
        compressed = Image.open(buffer)
        return compressed.convert('RGB')
    
    def shift_pixels(self, image, shift=1):
        """Shift pixels slightly"""
        if isinstance(image, Image.Image):
            # Ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)
        else:
            img_array = image
        
        # Random pixel shifts
        shifted = img_array.copy()
        h, w = img_array.shape[:2]
        
        for i in range(h):
            for j in range(w):
                if random.random() < 0.1:  # 10% of pixels
                    new_i = max(0, min(h-1, i + random.randint(-shift, shift)))
                    new_j = max(0, min(w-1, j + random.randint(-shift, shift)))
                    shifted[i, j] = img_array[new_i, new_j]
        
        return Image.fromarray(shifted)
    
    def get_gallery_for_confusion_test(self, target_person):
        """Get a small gallery of people for confusion testing (optimized to prevent hanging)"""
        try:
            print(f"    Building gallery for {target_person}...")
            from sklearn.datasets import fetch_lfw_people
            
            # Use smaller dataset and timeout to prevent hanging
            lfw_people = fetch_lfw_people(min_faces_per_person=1)
            
            # Use the actual Vietnamese names from account.json
            vietnamese_names_list = [
                "Nguyễn Minh Thắng", "Nguyễn Tuấn Anh", "Lê Phương Minh", 
                "Võ Trần Đức", "Phạm Đình Hưng", "Trần Đình Lĩnh",
                "Bùi Quang Khánh", "Hoàng Văn Vân", "Ngô Hữu Tùng", "Đinh Kim Minh"
            ]
            
            # Get 3 different Vietnamese names for gallery (including target if available)
            if target_person in vietnamese_names_list:
                # Include target person and 2 others
                other_viet_names = [name for name in vietnamese_names_list if name != target_person]
                selected_names = [target_person] + random.sample(other_viet_names, min(2, len(other_viet_names)))
            else:
                # Just get 3 random Vietnamese names
                selected_names = random.sample(vietnamese_names_list, min(3, len(vietnamese_names_list)))
            
            # Get available LFW people with enough images for gallery
            available_lfw_ids = []
            for person_id in range(len(lfw_people.target_names)):
                person_images = lfw_people.images[lfw_people.target == person_id]
                if len(person_images) > 0:
                    available_lfw_ids.append(person_id)
            
            # Select random LFW IDs for the gallery names
            selected_lfw_ids = random.sample(available_lfw_ids, min(len(selected_names), len(available_lfw_ids)))
            
            gallery_embeddings = {'transaction': [], 'auth': []}
            gallery_names = []
            
            print(f"    Processing {len(selected_names)} gallery members...")
            
            for idx, viet_name in enumerate(selected_names):
                try:
                    # Use corresponding LFW person's images but display Vietnamese name
                    if idx < len(selected_lfw_ids):
                        lfw_id = selected_lfw_ids[idx]
                        lfw_name = lfw_people.target_names[lfw_id]
                        print(f"      [{idx+1}/{len(selected_names)}] Processing {viet_name} (using {lfw_name} ID:{lfw_id})...")
                        
                        # Get first image of this LFW person
                        person_images = lfw_people.images[lfw_people.target == lfw_id]
                    else:
                        print(f"      [{idx+1}/{len(selected_names)}] No LFW images available for {viet_name}")
                        continue
                    
                    if len(person_images) > 0:
                        person_image = person_images[0]
                        
                        # Convert to PIL if needed
                        if isinstance(person_image, np.ndarray):
                            if person_image.dtype != np.uint8:
                                person_image = (person_image * 255).astype(np.uint8)
                            person_pil = Image.fromarray(person_image)
                        else:
                            person_pil = person_image
                        
                        if person_pil.mode != 'RGB':
                            person_pil = person_pil.convert('RGB')
                        
                        
                        # Get embeddings with error handling
                        trans_emb = self.get_facenet_embedding(person_pil, self.facenet_transaction) if self.facenet_transaction else None
                        auth_emb = self.get_facenet_embedding(person_pil, self.facenet_auth) if self.facenet_auth else None
                        
                        if trans_emb is not None and auth_emb is not None:
                            gallery_embeddings['transaction'].append(trans_emb)
                            gallery_embeddings['auth'].append(auth_emb)
                            gallery_names.append(viet_name)  # Use Vietnamese name for display
                            print(f"        ✓ Added {viet_name} to gallery")
                        else:
                            print(f"        ✗ Failed to generate embeddings for {viet_name}")
                    else:
                        print(f"        ✗ No images found for {viet_name}")
                        
                except Exception as e:
                    print(f"        ✗ Error processing {viet_name}: {e}")
                    continue
            
            print(f"    ✓ Gallery ready with {len(gallery_names)} members")
            return gallery_embeddings, gallery_names
            
        except Exception as e:
            print(f"Warning: Could not create gallery for confusion test: {e}")
            return None, None
    
    def test_image_classification(self, image, gallery_embeddings, gallery_names, model_name="transaction"):
        """Test what person the model thinks this image is"""
        if not gallery_embeddings or not gallery_names:
            return None, None, []
        
        model = self.facenet_transaction if model_name == "transaction" else self.facenet_auth
        if model is None:
            return None, None, []
        
        # Get embedding for test image
        test_emb = self.get_facenet_embedding(image, model)
        if test_emb is None:
            return None, None, []
        
        # Calculate similarities to all gallery people
        similarities = []
        for ref_emb in gallery_embeddings[model_name]:
            sim = self.cosine_similarity(test_emb, ref_emb)
            similarities.append(sim)
        
        if not similarities:
            return None, None, []
        
        # Get top prediction
        predicted_id = np.argmax(similarities)
        predicted_name = gallery_names[predicted_id]
        max_similarity = similarities[predicted_id]
        
        # Get all similarities with names
        name_sim_pairs = list(zip(gallery_names, similarities))
        name_sim_pairs.sort(key=lambda x: x[1], reverse=True)  # Sort by similarity desc
        
        return predicted_name, max_similarity, name_sim_pairs
    
    def add_uniform_noise(self, image, intensity=10):
        """Add uniform noise to image"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)
        else:
            img_array = image
        
        noise = np.random.uniform(-intensity, intensity, img_array.shape).astype(np.int16)
        noisy = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy)
    
    def add_speckle_noise(self, image, intensity=0.1):
        """Add speckle noise to image"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)
        else:
            img_array = image
        
        noise = np.random.randn(*img_array.shape) * intensity
        noisy = img_array + img_array * noise
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy)
    
    def add_color_jitter(self, image, brightness=0.2, contrast=0.2, saturation=0.2):
        """Add heavy color jitter to image"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        # Random adjustments within specified ranges
        brightness_factor = random.uniform(1-brightness, 1+brightness)
        contrast_factor = random.uniform(1-contrast, 1+contrast)
        saturation_factor = random.uniform(1-saturation, 1+saturation)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness_factor)
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)
        
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(saturation_factor)
        
        return image
    
    def adjust_brightness(self, image, factor=1.0):
        """Adjust image brightness"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    
    def adjust_contrast(self, image, factor=1.0):
        """Adjust image contrast"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    def apply_mixed_noise(self, image, intensity="light"):
        """Apply combination of different noise types"""
        if isinstance(image, Image.Image):
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        # Start with the image
        noisy = image
        
        if intensity == "light":
            # Light mixed noise
            noisy = self.add_gaussian_noise(noisy, std=8)
            noisy = self.add_salt_pepper_noise(noisy, amount=0.005)
            noisy = self.adjust_brightness(noisy, factor=random.uniform(0.8, 1.2))
        else:
            # Heavy mixed noise
            noisy = self.add_gaussian_noise(noisy, std=20)
            noisy = self.add_salt_pepper_noise(noisy, amount=0.02)
            noisy = self.apply_jpeg_compression(noisy, quality=random.randint(40, 60))
            noisy = self.adjust_brightness(noisy, factor=random.uniform(0.6, 1.4))
            noisy = self.adjust_contrast(noisy, factor=random.uniform(0.6, 1.4))
        
        return noisy

def load_account_data(account_file="../challenge/data/account.json"):
    """Load account data from challenge"""
    import json
    try:
        with open(account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading account data: {e}")
        return None

def run_adversarial_workflow(tester):
    """Run complete adversarial attack workflow"""
    print("\n" + "="*60)
    print("ADVERSARIAL ATTACK WORKFLOW")
    print("="*60)
    print("This will perform all 3 steps:")
    print("Step 0: Get account data from challenge")
    print("Step 1: Create modified images both models recognize")  
    print("Step 2: Create adversarial images to fool transaction model")
    print("-" * 60)
    
    results_dir = "./results"
    
    # Load account data from challenge
    account_data = load_account_data()
    if not account_data:
        print("Failed to load account data from challenge")
        return
    
    # Step 0: Create stable 1:1 mapping between usernames, Vietnamese names, and LFW IDs
    vietnamese_mappings = {}
    for username, user_info in account_data.items():
        vietnamese_mappings[username] = {
            "name": user_info["name"], 
            "lfw_id": None,
            "id": user_info["id"],
            "balance": user_info["balance"],
            "image_path": user_info["image_path"]
        }
    
    # Load LFW data for getting reference images
    try:
        from sklearn.datasets import fetch_lfw_people
        lfw_data = fetch_lfw_people(min_faces_per_person=2, download_if_missing=True)
        print(f"Loaded LFW dataset with {len(lfw_data.target_names)} people")
    except Exception as e:
        print(f"Failed to load LFW dataset: {e}")
        return
    
    # Get LFW people with enough images for stable mapping
    available_lfw_people = []
    for person_id in range(len(lfw_data.target_names)):
        person_images = lfw_data.images[lfw_data.target == person_id]
        if len(person_images) >= 2:
            available_lfw_people.append((person_id, lfw_data.target_names[person_id]))
    
    if len(available_lfw_people) < len(vietnamese_mappings):
        print(f"Warning: Only {len(available_lfw_people)} LFW people available, but need {len(vietnamese_mappings)}")
    
    # Create stable 1:1 mapping
    usernames = list(vietnamese_mappings.keys())
    for idx, username in enumerate(usernames):
        if idx < len(available_lfw_people):
            lfw_id, lfw_name = available_lfw_people[idx]
            vietnamese_mappings[username]["lfw_id"] = lfw_id
            print(f"Mapped {username} ({vietnamese_mappings[username]['name']}) → LFW ID {lfw_id} ({lfw_name})")
    
    # Process each person
    successful_attacks = 0
    
    for username in usernames:
        try:
            mapping = vietnamese_mappings[username]
            person_name = mapping["name"]
            lfw_id = mapping["lfw_id"]
            
            print(f"\n{'='*60}")
            print(f"PROCESSING: {username} ({person_name})")
            print("="*60)
            
            if lfw_id is None:
                print(f"No LFW mapping available for {username}")
                continue
            
            # Get images from mapped LFW person
            person_images = lfw_data.images[lfw_data.target == lfw_id]
            lfw_name = lfw_data.target_names[lfw_id]
            
            print(f"Using images from LFW person '{lfw_name}' (ID: {lfw_id}) for {username} ({person_name})")
            
            if len(person_images) < 2:
                print(f"Need at least 2 images for {username}, found {len(person_images)}")
                continue
            
            # Use first image for crafting payload, second for comparison
            payload_image = person_images[0]  # Image to modify/craft adversarial payload
            reference_image = person_images[1]  # Unmodified reference for comparison
            
            print(f"Using image 1 for payload crafting, image 2 as reference for {username}")
            
            # Step 1: Create modified image from payload image (use username for folder)
            modified_image, modified_path, person_dir = tester.create_modified_image(
                payload_image, username, results_dir  # Use username instead of person_name
            )
            
            # Save reference image for comparison
            if isinstance(reference_image, np.ndarray):
                if reference_image.dtype != np.uint8:
                    reference_image = (reference_image * 255).astype(np.uint8)
                reference_pil = Image.fromarray(reference_image)
            else:
                reference_pil = reference_image
            
            if reference_pil.mode != 'RGB':
                reference_pil = reference_pil.convert('RGB')
            
            reference_path = os.path.join(person_dir, "00_reference_unmodified.png")
            reference_pil.save(reference_path)
            print(f"Saved reference image: {reference_path}")
            
            # Step 2: Create adversarial image from modified payload (use person_name for actual testing)
            adversarial_path = tester.create_adversarial_image(
                modified_image, person_name, person_dir, reference_image=reference_pil
            )
            
            if adversarial_path:
                successful_attacks += 1
                print(f"\n🎯 SUCCESS: Adversarial attack created for {username} ({person_name})")
            else:
                print(f"\n❌ FAILED: No adversarial attack found for {username} ({person_name})")
                
        except Exception as e:
            print(f"\n❌ ERROR processing {username} ({person_name}): {e}")
            import traceback
            traceback.print_exc()
    
    # Generate clean summary report
    generate_summary_report(results_dir, len(vietnamese_mappings), successful_attacks)

def generate_summary_report(results_dir, total_people, successful_attacks):
    """Generate a clean summary report of all adversarial attacks"""
    import glob
    
    print(f"\n{'='*80}")
    print("🎯 ADVERSARIAL ATTACK SUMMARY REPORT")
    print("="*80)
    
    # Find all summary files
    summary_files = glob.glob(os.path.join(results_dir, "*/summary.txt"))
    
    if not summary_files:
        print("❌ No summary files found")
        return
    
    successful_exploits = []
    failed_attacks = []
    
    for summary_path in sorted(summary_files):
        folder_name = os.path.basename(os.path.dirname(summary_path))
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse key information
            person_name = "Unknown"
            strategy = "unknown"
            auth_pred = "Unknown"
            trans_pred = "Unknown"
            trans_confidence = 0.0
            
            lines = content.split('\n')
            for line in lines:
                if line.startswith('Person:'):
                    person_name = line.split(':', 1)[1].strip()
                elif line.startswith('Strategy:'):
                    strategy = line.split(':', 1)[1].strip()
                elif 'Auth Model:' in line and 'confidence:' in line:
                    auth_pred = line.split(':')[1].split('(')[0].strip()
                elif 'Transaction Model:' in line and 'confidence:' in line:
                    parts = line.split(':')
                    trans_pred = parts[1].split('(')[0].strip()
                    if 'confidence:' in line:
                        conf_part = line.split('confidence:')[1].strip().rstrip(')')
                        trans_confidence = float(conf_part)
            
            # Check if it's a successful exploit
            if "✅ SUCCESSFUL EXPLOIT:" in content:
                successful_exploits.append((folder_name, person_name, strategy, auth_pred, trans_pred, trans_confidence))
            else:
                failed_attacks.append((folder_name, person_name))
                
        except Exception as e:
            print(f"Error parsing {summary_path}: {e}")
    
    # Print successful exploits
    print("✅ SUCCESSFUL EXPLOITS:")
    print("-" * 50)
    
    if successful_exploits:
        for i, (folder, person, strategy, auth_pred, trans_pred, confidence) in enumerate(successful_exploits, 1):
            print(f"{i}. {folder} ({person})")
            print(f"   📁 Image: results/{folder}/06_adversarial_{strategy}.png")
            print(f"   🔐 Auth Model:        {auth_pred} ✓")
            print(f"   💳 Transaction Model: {trans_pred} ✗ (conf: {confidence:.4f})")
            print(f"   🎯 Exploit: Login works, transfers confused")
            print()
    else:
        print("   None found")
    
    # Print failed attacks
    print("❌ FAILED ATTACKS:")
    print("-" * 50)
    
    if failed_attacks:
        for i, (folder, person) in enumerate(failed_attacks, 1):
            print(f"{i}. {folder} ({person}) - Both models equally robust")
    else:
        print("   None found")
    
    # Print summary statistics
    success_rate = (len(successful_exploits) / total_people * 100) if total_people > 0 else 0
    
    print(f"\n📊 SUMMARY STATISTICS:")
    print("-" * 50)
    print(f"Total people tested:     {total_people}")
    print(f"Successful exploits:     {len(successful_exploits)}")
    print(f"Failed attacks:          {len(failed_attacks)}")
    print(f"Success rate:            {success_rate:.1f}%")
    
    print(f"\n🔑 KEY FINDING:")
    print("-" * 50)
    if successful_exploits:
        print("Multiple exploitable adversarial images found!")
        print("These images can:")
        print("  ✓ Pass authentication (Auth model recognizes correctly)")
        print("  ✗ Confuse transaction verification (Transaction model fails)")
        print("  💡 Potential CTF exploit: Login works but transfers fail/blocked")
    else:
        print("No exploitable adversarial images found.")
        print("Both models appear equally robust.")
    
    print("=" * 80)

def main():
    """Main function to run adversarial workflow only"""
    print("Face Recognition Testing Script")
    print("Testing 2 different FaceNet models (Transaction vs Auth) on LFW dataset")
    print("-" * 60)
    
    # Initialize tester
    tester = FaceRecognitionTester()
    
    # Check if models are available
    if not tester.check_models_available():
        print("\nPlease ensure models are available in ./models/ directory.")
        return
    
    # Run only the adversarial workflow (option 7)
    run_adversarial_workflow(tester)

if __name__ == "__main__":
    main()