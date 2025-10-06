import os
import json
import base64
import numpy as np
from PIL import Image
import io
from flask import session
import torch
import torchvision.transforms as transforms
from facenet_pytorch import InceptionResnetV1


class BiometricAuthSystem:
    def __init__(self):
        self.account_data = self.load_account_data()
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.facenet_auth = None
        self.facenet_transaction = None
        self.transform = None
        self.load_facenet_models()
        self.setup_transform()

    def load_account_data(self):
        account_file_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "account.json"
        )
        try:
            with open(account_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {}

    def load_facenet_models(self):
        models_dir = os.path.join(os.path.dirname(__file__), "models")

        try:
            self.facenet_auth = (
                InceptionResnetV1(pretrained=None).eval().to(self.device)
            )
            auth_path = os.path.join(models_dir, "facenet-auth.pth")

            state_dict = torch.load(auth_path, map_location=self.device)
            filtered_state_dict = {
                k: v for k, v in state_dict.items() if not k.startswith("logits")
            }
            self.facenet_auth.load_state_dict(filtered_state_dict, strict=False)
        except Exception as e:
            pass

        try:
            self.facenet_transaction = (
                InceptionResnetV1(pretrained=None).eval().to(self.device)
            )
            transaction_path = os.path.join(models_dir, "facenet-transaction.pth")

            state_dict = torch.load(transaction_path, map_location=self.device)
            filtered_state_dict = {
                k: v for k, v in state_dict.items() if not k.startswith("logits")
            }
            self.facenet_transaction.load_state_dict(filtered_state_dict, strict=False)
        except Exception as e:
            pass

    def setup_transform(self):
        self.transform = transforms.Compose(
            [
                transforms.Resize((160, 160)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
            ]
        )

    def preprocess_image(self, image_data):
        try:
            if image_data.startswith("data:image"):
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))

            if image.mode != "RGB":
                image = image.convert("RGB")

            return image
        except Exception as e:
            return None

    def load_database_image(self, image_path):
        try:
            full_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "img", image_path
            )
            image = Image.open(full_path)

            if image.mode != "RGB":
                image = image.convert("RGB")

            return image
        except Exception as e:
            return None

    def get_facenet_embedding(self, image, model):
        try:
            if image is None or model is None:
                return None

            face_tensor = self.transform(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                embedding = model(face_tensor)

            return embedding.cpu().numpy().flatten()
        except Exception as e:
            return None

    def calculate_similarity(self, img1, img2, model):
        if img1 is None or img2 is None or model is None:
            return 0.0

        emb1 = self.get_facenet_embedding(img1, model)
        emb2 = self.get_facenet_embedding(img2, model)

        if emb1 is None or emb2 is None:
            return 0.0

        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        return float(similarity)

    def authenticate_user(self, image_data):
        if not self.account_data:
            return {"authenticated": False, "error": "No data"}

        input_image = self.preprocess_image(image_data)
        if input_image is None:
            return {"authenticated": False, "error": "Invalid image"}

        best_match = None
        best_similarity = 0.0

        for username, account_info in self.account_data.items():
            db_image = self.load_database_image(account_info["image_path"])
            if db_image is not None:
                similarity = self.calculate_similarity(
                    input_image, db_image, self.facenet_auth
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = username

        if best_similarity > 0.4:
            return {
                "authenticated": True,
                "user_id": best_match,
            }
        else:
            return {
                "authenticated": False,
                "error": "Auth failed",
            }

    def verify_transfer_authorization(self, image_data, from_account):
        if not self.account_data:
            return {"authorized": False, "error": "No data"}

        input_image = self.preprocess_image(image_data)
        if input_image is None:
            return {"authorized": False, "error": "Invalid image"}

        best_match = None
        best_similarity = 0.0

        for username, account_info in self.account_data.items():
            db_image = self.load_database_image(account_info["image_path"])
            if db_image is not None:
                similarity = self.calculate_similarity(
                    input_image, db_image, self.facenet_transaction
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = username

        if best_similarity > 0.4:
            if best_match == from_account:
                return {
                    "authorized": True,
                    "matched_user": best_match,
                }
            else:
                return {
                    "authorized": False,
                    "error": f"Wrong user: {best_match}",
                }
        else:
            return {
                "authorized": False,
                "error": "Auth failed",
            }


auth_system_instance = None


def get_auth_system():
    global auth_system_instance
    if auth_system_instance is None:
        auth_system_instance = BiometricAuthSystem()
    return auth_system_instance


def authenticate_user(image_data):
    return get_auth_system().authenticate_user(image_data)


def process_transfer(from_account, to_account, amount, image_data):
    auth_system = get_auth_system()

    auth_result = auth_system.verify_transfer_authorization(image_data, from_account)

    if not auth_result.get("authorized"):
        return {"success": False, "error": "Transfer failed"}

    return {
        "success": True,
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
    }
