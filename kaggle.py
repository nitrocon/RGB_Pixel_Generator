import subprocess
import sys
import os
import logging
from PIL import Image
import psutil
import threading
import torch
import numpy as np
import gc
from concurrent.futures import ThreadPoolExecutor
import time

# === EINSTELLUNGEN ===
PATTERN_TYPE = "single"  # "single" oder "mandala"
NUM_COLORS_START = 0
NUM_COLORS_END = 10000
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 360
COLORS_PER_IMAGE = 5
OUTPUT_DIR = "/kaggle/working"
# =====================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

sys.setrecursionlimit(100000)

def generate_pixel_values(num_colors_start, num_colors_end, device):
    num_colors_range = torch.arange(num_colors_start, num_colors_end + 1, device=device)
    r = num_colors_range % 256
    g = torch.div(num_colors_range, 256, rounding_mode='trunc') % 256
    b = torch.div(num_colors_range, 256 * 256, rounding_mode='trunc') % 256
    return r, g, b

def get_available_memory():
    available_ram = psutil.virtual_memory().available / (1024 ** 2)
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated() / (1024 ** 2)
        max_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
        available_gpu_memory = max_gpu_memory - gpu_memory
        return available_ram, available_gpu_memory
    return available_ram, 0

def get_batch_size(available_ram, available_gpu_memory, base_batch_size=30000):
    if available_gpu_memory > 500:
        return int(base_batch_size * 2)
    elif available_ram > 400:
        return int(base_batch_size * 1.5)
    return int(base_batch_size)

def generate_single_color_image(image_width, image_height, color):
    return Image.new("RGB", (image_width, image_height), color)

def generate_mandala_pattern(image_width, image_height, base_color, num_additional_colors):
    img = Image.new("RGB", (image_width, image_height), base_color)
    pixels = img.load()
    additional_colors = [(np.random.randint(0, 256), np.random.randint(0, 256), np.random.randint(0, 256)) for _ in range(num_additional_colors)]
    colors = [base_color] + additional_colors
    num_colors = len(colors)
    center_x, center_y = image_width // 2, image_height // 2

    for y in range(image_height):
        for x in range(image_width):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            color_index = int(distance) % num_colors
            next_color_index = (color_index + 1) % num_colors
            blend_factor = distance % 1
            r = int(colors[color_index][0] * (1 - blend_factor) + colors[next_color_index][0] * blend_factor)
            g = int(colors[color_index][1] * (1 - blend_factor) + colors[next_color_index][1] * blend_factor)
            b = int(colors[color_index][2] * (1 - blend_factor) + colors[next_color_index][2] * blend_factor)
            pixels[x, y] = (r, g, b)
    return img

def generate_images(output_dir, num_colors_start, num_colors_end, image_width, image_height, colors_per_image, pattern_type):
    if not output_dir.endswith("RGB_Colors"):
        output_dir = os.path.join(output_dir, "RGB_Colors")
    os.makedirs(output_dir, exist_ok=True)

    pattern_folder = os.path.join(output_dir, pattern_type.capitalize())
    os.makedirs(pattern_folder, exist_ok=True)

    size_folder = f"{image_width}x{image_height}"
    color_folder = os.path.join(pattern_folder, size_folder)
    os.makedirs(color_folder, exist_ok=True)

    total_images = (num_colors_end - num_colors_start)
    images_generated = 0

    device = "cuda" if torch.cuda.is_available() else "cpu"

    def process_batch(start_idx, end_idx, color_folder):
        nonlocal images_generated
        r_values, g_values, b_values = generate_pixel_values(start_idx, end_idx, device)

        for idx in range(len(r_values)):
            base_color = (r_values[idx].item(), g_values[idx].item(), b_values[idx].item())
            hex_color = f"{r_values[idx].item():02X}{g_values[idx].item():02X}{b_values[idx].item():02X}"
            file_name = f"{hex_color}.png"
            file_path = os.path.join(color_folder, file_name)

            if os.path.exists(file_path):
                continue

            img = generate_mandala_pattern(image_width, image_height, base_color, colors_per_image - 1) if pattern_type == "mandala" else generate_single_color_image(image_width, image_height, base_color)

            img.save(file_path)
            images_generated += 1

        torch.cuda.empty_cache()

    with ThreadPoolExecutor(max_workers=4) as executor:
        available_ram, available_gpu_memory = get_available_memory()
        batch_size = get_batch_size(available_ram, available_gpu_memory)
        total_colors = num_colors_end - num_colors_start
        batches = total_colors // batch_size + (1 if total_colors % batch_size != 0 else 0)

        futures = []
        for batch_idx in range(batches):
            start_idx = num_colors_start + batch_idx * batch_size
            end_idx = min(num_colors_start + (batch_idx + 1) * batch_size - 1, num_colors_end - 1)
            futures.append(executor.submit(process_batch, start_idx, end_idx, color_folder))

        for future in futures:
            future.result()

        gc.collect()

def start_generation():
    threading.Thread(target=generate_images, args=(OUTPUT_DIR, NUM_COLORS_START, NUM_COLORS_END, IMAGE_WIDTH, IMAGE_HEIGHT, COLORS_PER_IMAGE, PATTERN_TYPE)).start()

start_generation()

