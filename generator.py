import os 
import time
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image
import psutil  # For resource management
import threading
import torch
import numpy as np
import sys
import gc
from concurrent.futures import ThreadPoolExecutor

sys.setrecursionlimit(100000)

# Stop generation flag
stop_generation = False

# CUDA optimization: Pixel values generation
def generate_pixel_values(num_colors_start, num_colors_end, device):
    # Create a range of pixel values (r, g, b)
    num_colors_range = torch.arange(num_colors_start, num_colors_end + 1, device=device)
    r = num_colors_range % 256
    g = torch.div(num_colors_range, 256, rounding_mode='trunc') % 256
    b = torch.div(num_colors_range, 256 * 256, rounding_mode='trunc') % 256
    return r, g, b

# Get available memory (RAM and GPU) and adjust batch size accordingly
def get_available_memory():
    # Get available system RAM
    available_ram = psutil.virtual_memory().available / (2048 ** 2)  # in MB
    if torch.cuda.is_available():
        # Get available GPU memory
        gpu_memory = torch.cuda.memory_allocated() / (2048 ** 2)  # in MB
        max_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (2048 ** 2)  # in MB
        available_gpu_memory = max_gpu_memory - gpu_memory
        return available_ram, available_gpu_memory
    return available_ram, 0

# Dynamically adjust the batch size based on available memory
def get_batch_size(available_ram, available_gpu_memory, base_batch_size=30000):
    # Estimate batch size based on available resources
    estimated_batch_size = base_batch_size
    if available_gpu_memory > 500:  # If more than 5GB GPU memory is available, use larger batch
        estimated_batch_size = base_batch_size * 2
    elif available_ram > 400:  # If more than 4GB system RAM is available, increase batch size
        estimated_batch_size = base_batch_size * 1.5
    return int(estimated_batch_size)

# Handle generation of images
def generate_images(output_dir, num_colors_start, num_colors_end, image_width, image_height, progress_label, progress_bar, info_label, elapsed_label, update_progress_callback):
    global stop_generation
    try:
        # Create the main 'RGB_Colors' folder if it doesn't exist
        rgb_colors_dir = os.path.join(output_dir, "RGB_Colors")
        os.makedirs(rgb_colors_dir, exist_ok=True)

        # Create the subfolder named after the image size (e.g., 1x1 or 2x3) inside the RGB_Colors folder
        size_folder = f"{image_width}x{image_height}"
        color_folder = os.path.join(rgb_colors_dir, size_folder)
        os.makedirs(color_folder, exist_ok=True)  # Ensure the subfolder for the size is created

        total_images = num_colors_end - num_colors_start + 1
        images_generated = 0
        skipped_images = 0
        start_time = time.time()

        # Function to update progress
        def update_progress():
            if images_generated > 0:
                elapsed_time = time.time() - start_time
                estimated_time = (elapsed_time / images_generated) * (total_images - images_generated)

                images_per_second = images_generated / elapsed_time if elapsed_time > 0 else 0
        
                update_progress_callback(images_generated, total_images, estimated_time, images_per_second, skipped_images, elapsed_time)

        # Dynamically select the device (GPU or CPU)
        device = get_device()

        # Function to process a batch of images
        def process_batch(batch_idx, start_idx, end_idx, color_folder):
            nonlocal images_generated, skipped_images
            r_values, g_values, b_values = generate_pixel_values(start_idx, end_idx, device)

            # Generate images for the batch
            for idx, (r, g, b) in enumerate(zip(r_values.cpu().numpy(), g_values.cpu().numpy(), b_values.cpu().numpy())):
                if stop_generation:
                    break

                # Create hex color code for the RGB values
                hex_color = f"{r:02X}{g:02X}{b:02X}"
                file_name = f"{hex_color}.png"
                file_path = os.path.join(color_folder, file_name)

                # Skip if the image already exists
                if os.path.exists(file_path):
                    skipped_images += 1
                    update_progress()  # Update even when skipping an image
                    continue

                # Generate the image with the specified size (e.g., 1x1 or 2x3)
                img = Image.new("RGB", (image_width, image_height), (r, g, b))
                img.save(file_path)
                images_generated += 1
                update_progress()

            # Free GPU memory after processing the batch
            torch.cuda.empty_cache()

        # Executor for parallel processing of batches
        with ThreadPoolExecutor() as executor:
            # Get available memory to determine batch size
            available_ram, available_gpu_memory = get_available_memory()
            batch_size = get_batch_size(available_ram, available_gpu_memory)
            total_colors = num_colors_end - num_colors_start + 1
            batches = total_colors // batch_size + (1 if total_colors % batch_size != 0 else 0)

            # Submit batch processing jobs
            futures = []
            for batch_idx in range(batches):
                if stop_generation:
                    break

                start_idx = num_colors_start + batch_idx * batch_size
                end_idx = min(num_colors_start + (batch_idx + 1) * batch_size - 1, num_colors_end)

                futures.append(executor.submit(process_batch, batch_idx, start_idx, end_idx, color_folder))

            # Wait for all futures to complete
            for future in futures:
                future.result()

            gc.collect()

        # Show completion message
        if not stop_generation:
            messagebox.showinfo("Finished", "The images have been successfully generated!")
        else:
            messagebox.showinfo("Aborted", "The image generation has been stopped.")

    except Exception as e:
        # Handle errors
        messagebox.showerror("Error", f"An error occurred: {e}")

# Format time function
def format_time(seconds):
    # Convert seconds to days, hours, minutes, and seconds
    days, remainder = divmod(seconds, 86400)  # 1 day = 86400 seconds
    hours, remainder = divmod(remainder, 3600)  # 1 hour = 3600 seconds
    minutes, seconds = divmod(remainder, 60)  # 1 minute = 60 seconds

    # Ensure seconds are shown as whole numbers (no decimals)
    days = int(days)
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)
    
    if days > 0:
        return f"{days} Days, {hours} h"
    else:
        return f"{hours} h {minutes} min {seconds} sec"

# Folder selection dialog
def select_output_folder():
    folder = filedialog.askdirectory()
    if folder:
        output_dir_var.set(folder)

# Start generation
def start_generation():
    global stop_generation
    stop_generation = False
    threading.Thread(target=generate_images, args=(
        output_dir_var.get(),
        num_colors_start_var.get(),
        num_colors_end_var.get(),
        image_width_var.get(),
        image_height_var.get(),
        progress_label,
        progress_bar,
        elapsed_label,
        info_label,
        update_progress_gui
    ), daemon=True).start()

# Stop generation process
def stop_generation_process():
    global stop_generation
    stop_generation = True

# Update progress bar
def update_progress_gui(images_generated, total_images, estimated_time, images_per_second, skipped_images, elapsed_time):
    progress_label.config(
        text=f"Progress: {images_generated}/{total_images} "
             f"Remaining time: {format_time(estimated_time)}"
    )
    progress_bar['value'] = (images_generated / total_images) * 100
    info_label.config(text=f"Skipped Images: {skipped_images}")
    speed_label.config(text=f"Images per Second: {images_per_second:.2f}")
    elapsed_label.config(text=f"Elapsed Time: {format_time(elapsed_time)}")

# Get device (CPU or GPU)
def get_device():
    try:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            torch.backends.cudnn.benchmark = True
        else:
            device = torch.device("cpu")
        return device
    except Exception as e:
        print(f"Error in device selection: {e}")
        return torch.device("cpu")

# Create main window
root = Tk()
root.title("RGB_Pixel_Generator")
root.resizable(True, True)  # Allow window resizing

# Colors for the design
bg_color = "#1D3557"        # Background color of the main window
label_color = "#457B9D"     # Label color
entry_bg_color = "#A8DADC"  # Background color of entry fields
button_color = "#E63946"    # Button background color
button_text_color = "white" # Button text color
entry_text_color = "black"  # Entry text color

root.configure(bg=bg_color)

# Define labels and input fields
Label(root, text="Output dir:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
output_dir_var = StringVar()
output_dir_entry = Entry(root, textvariable=output_dir_var, width=40, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
output_dir_entry.grid(row=0, column=1, padx=10, pady=10)
output_dir_button = Button(root, text="Output", command=select_output_folder, bg=button_color, fg=button_text_color, font=("Arial", 10, "bold"))
output_dir_button.grid(row=0, column=2, padx=10, pady=10)

Label(root, text="Image size:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=W)
image_width_var = IntVar(value=1)
image_width_entry = Entry(root, textvariable=image_width_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
image_width_entry.grid(row=2, column=1, padx=10, pady=10, sticky=W)
Label(root, text="x", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=1, padx=70, pady=10, sticky=W)
image_height_var = IntVar(value=1)
image_height_entry = Entry(root, textvariable=image_height_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
image_height_entry.grid(row=2, column=1, padx=100, pady=10, sticky=W)

Label(root, text="Color range:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=3, column=0, padx=10, pady=10, sticky=W)
num_colors_start_var = IntVar(value=0)
num_colors_end_var = IntVar(value=16777215)
num_colors_start_entry = Entry(root, textvariable=num_colors_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_start_entry.grid(row=3, column=1, padx=10, pady=10, sticky=W)
Label(root, text="to", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=3, column=1, padx=70, pady=10, sticky=W)
num_colors_end_entry = Entry(root, textvariable=num_colors_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_end_entry.grid(row=3, column=1, padx=100, pady=10, sticky=W)

# Progress label and frame for speed and elapsed time
progress_label = Label(root, text="Progress: 0/0 images generated.", bg=bg_color, fg="white", font=("Arial", 10))
progress_label.grid(row=5, column=0, columnspan=3, pady=5)

speed_frame = Frame(root, bg=bg_color)
speed_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

speed_label = Label(speed_frame, text="Image per second: 0", bg=bg_color, fg="white", font=("Arial", 10))
speed_label.grid(row=0, column=0, columnspan=3, pady=0)

elapsed_label = Label(speed_frame, text="Elapsed Time: 00:00:00", bg=bg_color, fg="white", font=("Arial", 10))
elapsed_label.grid(row=1, column=0, columnspan=3, pady=0)

progress_bar = ttk.Progressbar(root, length=500, mode='determinate')
progress_bar.grid(row=6, column=0, columnspan=3, padx=10, pady=5)

info_label = Label(root, text="Skipped images: 0", bg=bg_color, fg="white", font=("Arial", 10))
info_label.grid(row=7, column=0, columnspan=3, pady=5)

# Buttons (Start and Stop)
button_frame = Frame(root, bg=bg_color)
button_frame.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

start_button = Button(button_frame, text="Start", command=start_generation, bg=button_color, fg=button_text_color, font=("Arial", 12))
start_button.grid(row=0, column=0, padx=10)

stop_button = Button(button_frame, text="Stop", command=stop_generation_process, bg=button_color, fg=button_text_color, font=("Arial", 12))
stop_button.grid(row=0, column=1, padx=10)

# Start the main loop of the Tkinter window
root.mainloop()

