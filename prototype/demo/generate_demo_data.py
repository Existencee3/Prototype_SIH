"""
Generate synthetic demo dataset & model
"""
import os
import json
import numpy as np
from PIL import Image
import torch
import torch.nn as nn


class TinyCNN(nn.Module):
    """A tiny 3-layer CNN for demo purposes."""
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 3)
        self.conv2 = nn.Conv2d(16, 32, 3)
        self.fc = nn.Linear(32 * 220 * 220, 5)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        return self.fc(x)


def generate_data():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    annotations = []

    # 50 normal images
    for i in range(50):
        img_array = np.random.randint(100, 200, (224, 224, 3), dtype=np.uint8)

        # Inject 5 poisoned samples (Trigger — black corner patch)
        if i < 5:
            img_array[:10, :10] = 0

        img = Image.fromarray(img_array)
        img_path = os.path.join(images_dir, f"img_{i:03d}.png")
        img.save(img_path)

        # Flip 5 labels
        label = i % 5
        if 5 <= i < 10:
            label = (label + 1) % 5

        annotations.append({
            "image_id": i,
            "category_id": label,
            "id": i,
            "bbox": [10, 10, 50, 50]
        })

    # 3 Near duplicates of image 5 (created after img_005 exists)
    for j, idx in enumerate([10, 11, 12]):
        src_img = np.array(Image.open(os.path.join(images_dir, "img_005.png")))
        noisy = np.clip(src_img.astype(np.int16) + np.random.randint(-3, 4, src_img.shape), 0, 255).astype(np.uint8)
        Image.fromarray(noisy).save(os.path.join(images_dir, f"img_{idx:03d}.png"))

    # 2 OOD samples (very dark noise)
    for idx in [48, 49]:
        ood = np.random.randint(0, 10, (224, 224, 3), dtype=np.uint8)
        Image.fromarray(ood).save(os.path.join(images_dir, f"img_{idx:03d}.png"))

    coco_format = {
        "images": [{"id": i, "file_name": f"images/img_{i:03d}.png"} for i in range(50)],
        "annotations": annotations,
        "categories": [{"id": i, "name": f"class_{i}"} for i in range(5)]
    }

    with open(os.path.join(base_dir, "annotations.json"), "w") as f:
        json.dump(coco_format, f)

    print(f"Generated 50 images (5 poisoned, 5 label-flipped, 3 near-dupes, 2 OOD)")


def generate_model():
    model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(model_dir, exist_ok=True)

    model = TinyCNN()

    # Save as TorchScript (avoids pickling issues with local classes)
    scripted = torch.jit.script(model)
    scripted.save(os.path.join(model_dir, "model.pt"))
    print(f"Saved TorchScript model to models/model.pt")

    # Save ONNX (optional — requires onnxscript)
    try:
        dummy_input = torch.randn(1, 3, 224, 224)
        torch.onnx.export(model, dummy_input, os.path.join(model_dir, "model.onnx"),
                          input_names=["input"], output_names=["output"])
        print(f"Saved ONNX model to models/model.onnx")
    except Exception as e:
        print(f"ONNX export skipped (install onnxscript for ONNX support): {e}")


if __name__ == "__main__":
    generate_data()
    generate_model()
    print("Demo data and models generated successfully.")
