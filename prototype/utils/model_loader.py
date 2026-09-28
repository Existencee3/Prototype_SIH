"""
Model loaders for PyTorch and ONNX models.
"""
import numpy as np
from PIL import Image
from typing import Any


class UnifiedModelInterface:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model_type = "unknown"
        self.model = None

        if model_path.endswith('.onnx'):
            self._load_onnx()
        elif model_path.endswith('.pt') or model_path.endswith('.pth'):
            self._load_pytorch()
        else:
            raise ValueError("Unsupported model format")

    def _load_onnx(self):
        import onnxruntime as ort
        self.model_type = "onnx"
        self.model = ort.InferenceSession(self.model_path)

    def _load_pytorch(self):
        import torch
        self.model_type = "pytorch"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Try loading as TorchScript first, then fall back to regular torch.load
        try:
            self.model = torch.jit.load(self.model_path, map_location=self.device)
        except Exception:
            self.model = torch.load(self.model_path, map_location=self.device, weights_only=False)
        self.model.eval()

    def preprocess(self, image_path: str) -> np.ndarray:
        """Simple resize and normalize."""
        img = Image.open(image_path).convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img).astype(np.float32) / 255.0
        # HWC to CHW
        img_array = np.transpose(img_array, (2, 0, 1))
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def predict(self, input_data: np.ndarray) -> np.ndarray:
        if self.model_type == "onnx":
            input_name = self.model.get_inputs()[0].name
            result = self.model.run(None, {input_name: input_data})
            return result[0]
        elif self.model_type == "pytorch":
            import torch
            with torch.no_grad():
                tensor = torch.from_numpy(input_data).to(self.device)
                output = self.model(tensor)
                return output.cpu().numpy()
        return np.array([])
