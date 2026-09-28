"""
Dataset loaders for COCO and YOLO formats.
"""
import os
import json
from typing import Iterator, Dict, Any, List
from PIL import Image

class DatasetLoader:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
    def load_coco(self, annotation_file: str) -> Iterator[Dict[str, Any]]:
        """Load COCO format dataset."""
        with open(annotation_file, 'r') as f:
            coco_data = json.load(f)
            
        images = {img['id']: img for img in coco_data.get('images', [])}
        annotations = coco_data.get('annotations', [])
        
        # Group annotations by image
        img_to_anns = {}
        for ann in annotations:
            img_id = ann['image_id']
            if img_id not in img_to_anns:
                img_to_anns[img_id] = []
            img_to_anns[img_id].append(ann)
            
        for img_id, img_info in images.items():
            img_path = os.path.join(self.data_dir, img_info['file_name'])
            yield {
                "sample_id": str(img_id),
                "image_path": img_path,
                "annotations": img_to_anns.get(img_id, []),
                "metadata": {"format": "coco"}
            }

    def load_yolo(self, images_dir: str, labels_dir: str) -> Iterator[Dict[str, Any]]:
        """Load YOLO format dataset."""
        if not os.path.exists(images_dir):
            return
            
        for filename in os.listdir(images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(images_dir, filename)
                base_name = os.path.splitext(filename)[0]
                label_path = os.path.join(labels_dir, base_name + ".txt")
                
                annotations = []
                if os.path.exists(label_path):
                    with open(label_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                bbox = [float(x) for x in parts[1:5]]
                                annotations.append({
                                    "category_id": class_id,
                                    "bbox": bbox
                                })
                
                yield {
                    "sample_id": base_name,
                    "image_path": img_path,
                    "annotations": annotations,
                    "metadata": {"format": "yolo"}
                }
