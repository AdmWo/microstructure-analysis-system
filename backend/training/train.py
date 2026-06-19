import os
import cv2
import glob
import json
import shutil
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import albumentations as A

import sys

# Reconfigure stdout/stderr to use UTF-8 to prevent UnicodeEncodeError crashes on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Set random seeds for reproducibility
np.random.seed(42)
torch.manual_seed(42)

# =====================================================================
# 1. Dataset Preprocessing & Mask Generation
# =====================================================================

def prepare_dataset(s1_thresh, s3_thresh, local_thresh):
    """
    Generate ground-truth binary masks for S1, S2, S3, and local datasets,
    storing them under backend/training/masks/.
    """
    print("=== Step 1: Preprocessing Dataset & Generating Ground-Truth Masks ===")
    
    # Define directories
    os.makedirs("backend/training/masks/S1", exist_ok=True)
    os.makedirs("backend/training/masks/S2/train", exist_ok=True)
    os.makedirs("backend/training/masks/S2/val", exist_ok=True)
    os.makedirs("backend/training/masks/S3", exist_ok=True)
    os.makedirs("backend/training/images/local", exist_ok=True)
    os.makedirs("backend/training/masks/local", exist_ok=True)
    
    # 1. S1 dataset: Apply intensity thresholding
    s1_images = glob.glob("backend/training/images/S1/*.tif")
    print(f"S1: Generating masks for {len(s1_images)} images (threshold < {s1_thresh})...")
    for img_path in s1_images:
        filename = os.path.basename(img_path)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        mask = np.zeros_like(img)
        mask[img < s1_thresh] = 255
        mask_path = os.path.join("backend/training/masks/S1", filename.replace(".tif", ".png"))
        cv2.imwrite(mask_path, mask)
        
    # 2. S2 dataset: Parse polygon annotations from via_region_data.json
    for split in ["train", "val"]:
        json_path = f"backend/training/images/S2/{split}/via_region_data.json"
        if not os.path.exists(json_path):
            print(f"Warning: S2 JSON not found at {json_path}")
            continue
        with open(json_path, "r") as f:
            via_data = json.load(f)
            
        print(f"S2 {split}: Parsing polygons for {len(via_data)} patches...")
        for key, entry in via_data.items():
            filename = entry.get("filename", "")
            if not filename:
                continue
            img_path = f"backend/training/images/S2/{split}/{filename}"
            if not os.path.exists(img_path):
                continue
                
            img = cv2.imread(img_path)
            h, w = img.shape[:2]
            mask = np.zeros((h, w), dtype=np.uint8)
            
            regions = entry.get("regions", [])
            if isinstance(regions, dict):
                regions = list(regions.values())
                
            for region in regions:
                shape_attr = region.get("shape_attributes", {})
                if shape_attr.get("name") == "polygon":
                    xs = shape_attr.get("all_points_x", [])
                    ys = shape_attr.get("all_points_y", [])
                    if len(xs) > 2:
                        # Draw filled polygon on mask
                        pts = np.array([list(zip(xs, ys))], dtype=np.int32)
                        cv2.fillPoly(mask, pts, 255)
                        
            mask_path = f"backend/training/masks/S2/{split}/{filename}"
            cv2.imwrite(mask_path, mask)
            
    # 3. S3 dataset: Apply intensity thresholding
    s3_images = glob.glob("backend/training/images/S3/*.tif")
    print(f"S3: Generating masks for {len(s3_images)} images (threshold < {s3_thresh})...")
    for img_path in s3_images:
        filename = os.path.basename(img_path)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        mask = np.zeros_like(img)
        mask[img < s3_thresh] = 255
        mask_path = os.path.join("backend/training/masks/S3", filename.replace(".tif", ".png"))
        cv2.imwrite(mask_path, mask)
        
    # 4. Local SEM images: Copy from data/ and apply thresholding
    local_source = glob.glob("data/M_m*.jpg")
    print(f"Local: Copying and generating masks for {len(local_source)} SEM images (threshold < {local_thresh})...")
    for img_path in local_source:
        filename = os.path.basename(img_path)
        dest_img_path = os.path.join("backend/training/images/local", filename)
        shutil.copy(img_path, dest_img_path)
        
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        # Set pixels below local_thresh (representing dark pores) to 255 (white)
        mask = np.zeros_like(img)
        mask[img < local_thresh] = 255
        mask_path = os.path.join("backend/training/masks/local", filename.replace(".jpg", ".png"))
        cv2.imwrite(mask_path, mask)
        
    print("Dataset preparation complete.\n")

# =====================================================================
# 2. Patch Extraction & Data Leakage Avoidance
# =====================================================================

def get_train_val_image_paths():
    """
    Split the high-resolution images into train/val subsets BEFORE patching
    to prevent data leakage. S2 train/val splits are pre-defined on disk.
    """
    # S2 Split
    s2_train = glob.glob("backend/training/images/S2/train/*.png")
    s2_train = [p for p in s2_train if "via_region_data" not in p]
    s2_val = glob.glob("backend/training/images/S2/val/*.png")
    s2_val = [p for p in s2_val if "via_region_data" not in p]
    
    # S1 Split (12 images -> 10 train, 2 val)
    s1_all = sorted(glob.glob("backend/training/images/S1/*.tif"))
    s1_train = s1_all[:10]
    s1_val = s1_all[10:]
    
    # S3 Split (40 images -> 32 train, 8 val)
    s3_all = sorted(glob.glob("backend/training/images/S3/*.tif"))
    s3_train = s3_all[:32]
    s3_val = s3_all[32:]
    
    # Local Split (3 images -> 2 train, 1 val)
    local_all = sorted(glob.glob("backend/training/images/local/*.jpg"))
    local_train = local_all[:2]
    local_val = local_all[2:]
    
    train_paths = s2_train + s1_train + s3_train + local_train
    val_paths = s2_val + s1_val + s3_val + local_val
    
    print(f"Splits summary:")
    print(f"  S1: {len(s1_train)} train, {len(s1_val)} val")
    print(f"  S2: {len(s2_train)} train, {len(s2_val)} val")
    print(f"  S3: {len(s3_train)} train, {len(s3_val)} val")
    print(f"  Local: {len(local_train)} train, {len(local_val)} val")
    
    return train_paths, val_paths

def slice_and_patch(image_paths, patch_size=256, stride=128, empty_keep_ratio=0.15, is_train=True):
    """
    Extract overlapping 256x256 patches from images. Border patches slide back
    to align exactly with dimensions. Empty patches are sub-sampled in training
    to prevent background bias.
    """
    patches = []
    
    for img_path in image_paths:
        # Determine mask path: Replace 'images' with 'masks' and change ext to .png
        mask_path = img_path.replace("images", "masks")
        base, _ = os.path.splitext(mask_path)
        mask_path = base + ".png"
        
        if not os.path.exists(mask_path):
            continue
            
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        
        if img is None or mask is None:
            continue
            
        H, W = img.shape[:2]
        
        # Resize small images (like S3) to at least patch_size
        if H < patch_size or W < patch_size:
            img = cv2.resize(img, (patch_size, patch_size), interpolation=cv2.INTER_AREA)
            mask = cv2.resize(mask, (patch_size, patch_size), interpolation=cv2.INTER_NEAREST)
            H, W = patch_size, patch_size
            
        # Determine overlapping patch coordinates
        y_coords = list(range(0, H - patch_size + stride, stride))
        if len(y_coords) == 0 or y_coords[-1] + patch_size < H:
            y_coords.append(H - patch_size)
        elif y_coords[-1] + patch_size > H:
            y_coords[-1] = H - patch_size
            
        x_coords = list(range(0, W - patch_size + stride, stride))
        if len(x_coords) == 0 or x_coords[-1] + patch_size < W:
            x_coords.append(W - patch_size)
        elif x_coords[-1] + patch_size > W:
            x_coords[-1] = W - patch_size
            
        for y in y_coords:
            for x in x_coords:
                img_patch = img[y:y+patch_size, x:x+patch_size]
                mask_patch = mask[y:y+patch_size, x:x+patch_size]
                
                pore_pixels = (mask_patch == 255).sum()
                
                patches.append({
                    "image": img_patch,
                    "mask": mask_patch,
                    "pore_pixels": pore_pixels
                })
                
    # Balance background bias by filtering empty patches in training
    if is_train:
        pore_patches = [p for p in patches if p["pore_pixels"] > 10]
        empty_patches = [p for p in patches if p["pore_pixels"] <= 10]
        
        if len(pore_patches) > 0 and len(empty_patches) > 0:
            # target empty ratio = num_empty / (num_pore + num_empty)
            num_empty_to_keep = int(len(pore_patches) * (empty_keep_ratio / (1.0 - empty_keep_ratio)))
            num_empty_to_keep = min(num_empty_to_keep, len(empty_patches))
            
            # Select empty patches randomly
            keep_indices = np.random.choice(len(empty_patches), num_empty_to_keep, replace=False)
            filtered_empty = [empty_patches[i] for i in keep_indices]
            
            final_patches = pore_patches + filtered_empty
        else:
            final_patches = patches
            
        print(f"  Train Patches: {len(final_patches)} (Pore-containing: {len(pore_patches)}, Empty kept: {len(final_patches) - len(pore_patches)})")
    else:
        # Keep all validation patches for unbiased stats
        final_patches = patches
        print(f"  Val Patches: {len(final_patches)}")
        
    return final_patches

# =====================================================================
# 3. PyTorch Custom Dataset & Albumentations Augmentations
# =====================================================================

class MicrostructureDataset(Dataset):
    def __init__(self, patches, transform=None):
        self.patches = patches
        self.transform = transform
        
    def __len__(self):
        return len(self.patches)
        
    def __getitem__(self, idx):
        patch = self.patches[idx]
        img = patch["image"]
        mask = patch["mask"]
        
        # Albumentations standard RGB expectations
        img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        
        if self.transform:
            augmented = self.transform(image=img_rgb, mask=mask)
            img_aug = augmented["image"]
            mask_aug = augmented["mask"]
        else:
            img_aug = img_rgb
            mask_aug = mask
            
        # Convert back to grayscale channel 0, normalize to [0, 1]
        img_gray = img_aug[:, :, 0]
        
        img_tensor = torch.tensor(img_gray, dtype=torch.float32).unsqueeze(0) / 255.0
        mask_tensor = torch.tensor(mask_aug, dtype=torch.float32).unsqueeze(0) / 255.0
        
        return img_tensor, mask_tensor

# =====================================================================
# 4. Standard Lightweight U-Net Architecture (CNN-based)
# =====================================================================

class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(DoubleConv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        return self.conv(x)

class UNet(nn.Module):
    def __init__(self, in_channels=1, out_channels=1):
        super(UNet, self).__init__()
        self.enc1 = DoubleConv(in_channels, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = DoubleConv(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = DoubleConv(64, 128)
        self.pool3 = nn.MaxPool2d(2)
        self.enc4 = DoubleConv(128, 256)
        self.pool4 = nn.MaxPool2d(2)
        
        self.bottleneck = DoubleConv(256, 512)
        
        self.up4 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec4 = DoubleConv(512, 256)
        
        self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec3 = DoubleConv(256, 128)
        
        self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec2 = DoubleConv(128, 64)
        
        self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.dec1 = DoubleConv(64, 32)
        
        self.final_conv = nn.Conv2d(32, out_channels, 1)

    def forward(self, x):
        x1 = self.enc1(x)
        x2 = self.enc2(self.pool1(x1))
        x3 = self.enc3(self.pool2(x2))
        x4 = self.enc4(self.pool3(x3))
        
        b = self.bottleneck(self.pool4(x4))
        
        u4 = self.up4(b)
        if u4.shape != x4.shape:
            u4 = F.interpolate(u4, size=x4.shape[2:], mode="bilinear", align_corners=True)
        d4 = self.dec4(torch.cat([u4, x4], dim=1))
        
        u3 = self.up3(d4)
        if u3.shape != x3.shape:
            u3 = F.interpolate(u3, size=x3.shape[2:], mode="bilinear", align_corners=True)
        d3 = self.dec3(torch.cat([u3, x3], dim=1))
        
        u2 = self.up2(d3)
        if u2.shape != x2.shape:
            u2 = F.interpolate(u2, size=x2.shape[2:], mode="bilinear", align_corners=True)
        d2 = self.dec2(torch.cat([u2, x2], dim=1))
        
        u1 = self.up1(d2)
        if u1.shape != x1.shape:
            u1 = F.interpolate(u1, size=x1.shape[2:], mode="bilinear", align_corners=True)
        d1 = self.dec1(torch.cat([u1, x1], dim=1))
        
        return self.final_conv(d1)

# =====================================================================
# 5. Joint Loss (BCE + Dice) & Metrics Evaluation
# =====================================================================

class BCEDiceLoss(nn.Module):
    def __init__(self, bce_weight=1.0, dice_weight=1.0):
        super(BCEDiceLoss, self).__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        
    def forward(self, inputs, targets):
        bce_loss = self.bce(inputs, targets)
        
        probs = torch.sigmoid(inputs)
        probs = probs.view(-1)
        targets = targets.view(-1)
        
        intersection = (probs * targets).sum()
        dice_loss = 1.0 - (2.0 * intersection + 1e-6) / (probs.sum() + targets.sum() + 1e-6)
        
        return self.bce_weight * bce_loss + self.dice_weight * dice_loss

def calculate_validation_metrics(model, dataloader, device):
    """
    Calculate average Intersection over Union (IoU) and Dice Coefficient (F1-score)
    over the validation dataset.
    """
    model.eval()
    total_iou = 0.0
    total_dice = 0.0
    count = 0
    
    with torch.no_grad():
        for imgs, masks in dataloader:
            imgs = imgs.to(device)
            masks = masks.to(device)
            
            logits = model(imgs)
            probs = torch.sigmoid(logits)
            preds = (probs > 0.5).float()
            
            for i in range(imgs.size(0)):
                pred_i = preds[i]
                mask_i = masks[i]
                
                intersection = (pred_i * mask_i).sum()
                union = pred_i.sum() + mask_i.sum() - intersection
                
                iou = (intersection + 1e-6) / (union + 1e-6)
                dice = (2.0 * intersection + 1e-6) / (pred_i.sum() + mask_i.sum() + 1e-6)
                
                total_iou += iou.item()
                total_dice += dice.item()
                count += 1
                
    return total_iou / count, total_dice / count

# =====================================================================
# 6. ONNX Export Module with Sigmoid Wrapper
# =====================================================================

class ONNXWrapper(nn.Module):
    """Wraps model to include the Sigmoid activation in the serialized ONNX output."""
    def __init__(self, model):
        super(ONNXWrapper, self).__init__()
        self.model = model
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        return self.sigmoid(self.model(x))

def serialize_to_onnx(model_weights_path, output_onnx_path):
    print("=== Step 3: Exporting Best Model to ONNX ===")
    os.makedirs(os.path.dirname(output_onnx_path), exist_ok=True)
    
    # Instantiate model and load checkpoint weights
    model = UNet(in_channels=1, out_channels=1)
    model.load_state_dict(torch.load(model_weights_path, map_location="cpu"))
    model.eval()
    
    # Wrap model with Sigmoid
    wrapped_model = ONNXWrapper(model)
    wrapped_model.eval()
    
    # Create dummy input of shape (1, 1, 256, 256)
    dummy_input = torch.randn(1, 1, 256, 256, dtype=torch.float32)
    
    # Export model
    torch.onnx.export(
        wrapped_model,
        dummy_input,
        output_onnx_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
    )
    print(f"Model successfully serialized and saved to: {output_onnx_path}")
    print(f"ONNX File Size: {os.path.getsize(output_onnx_path) / (1024*1024):.2f} MB\n")

# =====================================================================
# 7. Main Execution
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Train U-Net on ceramic SEM microstructures and export to ONNX")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs to train")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--stride", type=int, default=128, help="Patching stride")
    parser.add_argument("--s1-thresh", type=int, default=60, help="Intensity threshold for S1 pores (< value)")
    parser.add_argument("--s3-thresh", type=int, default=90, help="Intensity threshold for S3 pores (< value)")
    parser.add_argument("--local-thresh", type=int, default=50, help="Intensity threshold for Local pores (< value)")
    parser.add_argument("--empty-keep-ratio", type=float, default=0.15, help="Ratio of empty patches to keep")
    parser.add_argument("--skip-prep", action="store_true", help="Skip dataset preprocessing/mask generation")
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}\n")
    
    # Step 1: Preprocess and copy dataset
    if not args.skip_prep:
        prepare_dataset(args.s1_thresh, args.s3_thresh, args.local_thresh)
    else:
        print("Skipping dataset preparation step.\n")
        
    # Step 2: Patching & Slicing
    print("=== Step 2: Grid-Based Slicing & Patch Generation ===")
    train_paths, val_paths = get_train_val_image_paths()
    
    print("\nPatching train dataset...")
    train_patches = slice_and_patch(
        train_paths, 
        patch_size=256, 
        stride=args.stride, 
        empty_keep_ratio=args.empty_keep_ratio, 
        is_train=True
    )
    
    print("Patching validation dataset...")
    val_patches = slice_and_patch(
        val_paths, 
        patch_size=256, 
        stride=args.stride, 
        is_train=False
    )
    
    print(f"\nTotal Dataset Size: Train Patches = {len(train_patches)}, Val Patches = {len(val_patches)}")
    
    # Setup PyTorch datasets and dataloaders
    train_transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.5),
    ])
    
    train_dataset = MicrostructureDataset(train_patches, transform=train_transform)
    val_dataset = MicrostructureDataset(val_patches, transform=None)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Initialize U-Net model, loss function, and optimizer
    model = UNet(in_channels=1, out_channels=1).to(device)
    criterion = BCEDiceLoss(bce_weight=1.0, dice_weight=1.0)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)
    
    checkpoint_path = "backend/training/unet_checkpoint.pth"
    best_val_iou = 0.0
    
    print("\n=== Training U-Net Baseline ===")
    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        
        for batch_idx, (imgs, masks) in enumerate(train_loader):
            imgs = imgs.to(device)
            masks = masks.to(device)
            
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
        avg_train_loss = epoch_loss / len(train_loader)
        
        # Calculate validation metrics
        val_iou, val_dice = calculate_validation_metrics(model, val_loader, device)
        scheduler.step(val_iou)
        
        print(f"Epoch [{epoch:02d}/{args.epochs:02d}] "
              f"Train Loss: {avg_train_loss:.4f} | "
              f"Val IoU: {val_iou:.4f} | "
              f"Val Dice: {val_dice:.4f}")
              
        # Save best model
        if val_iou > best_val_iou:
            best_val_iou = val_iou
            torch.save(model.state_dict(), checkpoint_path)
            print(f"  --> Checkpoint saved! Improved Val IoU to {val_iou:.4f}")
            
    print(f"\nTraining completed. Best Validation IoU: {best_val_iou:.4f}")
    
    # Step 3: ONNX Export
    onnx_output_path = "backend/models/unet_resnet18_baseline.onnx"
    if os.path.exists(checkpoint_path):
        serialize_to_onnx(checkpoint_path, onnx_output_path)
    else:
        print("Error: Saved model weights checkpoint was not found. Skipping ONNX export.")

if __name__ == "__main__":
    main()
