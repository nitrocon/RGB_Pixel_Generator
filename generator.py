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
def generate_pixel_values(gray_value, num_colors_start, num_colors_end, device):
    num_colors_range = torch.arange(num_colors_start, num_colors_end + 1, device=device)
    r = num_colors_range % 256
    g = torch.div(num_colors_range, 256, rounding_mode='trunc') % 256
    b = torch.div(num_colors_range, 256 * 256, rounding_mode='trunc') % 256
    gray_tensor = 0.299 * r + 0.587 * g + 0.114 * b
    return gray_tensor.int().clamp(0, 255), r, g, b

# Get available memory (RAM and GPU) and adjust batch size accordingly
def get_available_memory():
    available_ram = psutil.virtual_memory().available / (2048 ** 2)  # in MB
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated() / (2048 ** 2)  # in MB
        max_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (2048 ** 2)  # in MB
        available_gpu_memory = max_gpu_memory - gpu_memory
        return available_ram, available_gpu_memory
    return available_ram, 0

# Dynamically adjust the batch size based on available memory
def get_batch_size(available_ram, available_gpu_memory, base_batch_size=30000):
    # Use system RAM and GPU memory to estimate a safe batch size
    estimated_batch_size = base_batch_size
    if available_gpu_memory > 500:  # If more than 5GB GPU memory is available, use larger batch
        estimated_batch_size = base_batch_size * 2
    elif available_ram > 400:  # If more than 4GB system RAM is available, increase batch size
        estimated_batch_size = base_batch_size * 1.5
    return int(estimated_batch_size)

# Handle generation of images
def generate_images(output_dir, gray_start, gray_end, num_colors_start, num_colors_end, progress_label, progress_bar, info_label, elapsed_label, update_progress_callback):
    global stop_generation
    try:
        os.makedirs(output_dir, exist_ok=True)
        total_images = (gray_end - gray_start + 1) * (num_colors_end - num_colors_start)
        images_generated = 0
        skipped_images = 0
        start_time = time.time()

        def update_progress():
            if images_generated > 0:
                elapsed_time = time.time() - start_time
                estimated_time = (elapsed_time / images_generated) * (total_images - images_generated)

                # Calculate pixels per second (average number of pixels generated per second)
                pixels_per_second = images_generated / elapsed_time if elapsed_time > 0 else 0
        
                # Call the callback function to update the GUI
                update_progress_callback(images_generated, total_images, estimated_time, pixels_per_second, skipped_images, elapsed_time)


        # Dynamically select the device (GPU or CPU)
        device = get_device()

        def process_batch(batch_idx, start_idx, end_idx, gray, gray_folder):
            nonlocal images_generated, skipped_images
            gray_tensor, r_values, g_values, b_values = generate_pixel_values(gray, start_idx, end_idx, device)

            for idx, (r, g, b, gray_value) in enumerate(zip(r_values.cpu().numpy(), g_values.cpu().numpy(),
                                                                b_values.cpu().numpy(), gray_tensor.cpu().numpy())):
                if stop_generation:
                    break

                hex_color = f"{r:02X}{g:02X}{b:02X}"
                result_color = f"{gray_value:02X}{gray_value:02X}{gray_value:02X}"
                file_name = f"{gray:02X}-{hex_color}-{result_color}.png"
                file_path = os.path.join(gray_folder, file_name)

                if os.path.exists(file_path):
                    skipped_images += 1
                    update_progress()  # Update even when skipping an image
                    continue

                # Generate the image
                img = Image.new("RGB", (1, 1), (gray_value, gray_value, gray_value))
                img.save(file_path)
                images_generated += 1
                update_progress()

            # Free GPU memory after processing the batch
            torch.cuda.empty_cache()

        # Executor for parallel processing of batches
        with ThreadPoolExecutor() as executor:
            for gray in range(gray_start, gray_end + 1):
                if stop_generation:
                    break

                gray_hex = f"{gray:02X}"
                gray_folder = os.path.join(output_dir, gray_hex)
                os.makedirs(gray_folder, exist_ok=True)

                # Get available memory and adjust batch size accordingly
                available_ram, available_gpu_memory = get_available_memory()
                batch_size = get_batch_size(available_ram, available_gpu_memory)  # Adjust batch size dynamically
                total_colors = num_colors_end - num_colors_start + 1
                batches = total_colors // batch_size + (1 if total_colors % batch_size != 0 else 0)

                futures = []
                for batch_idx in range(batches):
                    if stop_generation:
                        break

                    start_idx = num_colors_start + batch_idx * batch_size
                    end_idx = min(num_colors_start + (batch_idx + 1) * batch_size - 1, num_colors_end)

                    futures.append(executor.submit(process_batch, batch_idx, start_idx, end_idx, gray, gray_folder))

                # Wait for all futures to complete
                for future in futures:
                    future.result()

                # Free up memory after each batch, clear any unused memory
                gc.collect()

        if not stop_generation:
            messagebox.showinfo("Finished", "The images have been successfully generated!")
        else:
            messagebox.showinfo("Aborted", "The image generation has been stopped.")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# Format time function
def format_time(seconds):
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
        gray_start_var.get(),
        gray_end_var.get(),
        num_colors_start_var.get(),
        num_colors_end_var.get(),
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
def update_progress_gui(images_generated, total_images, estimated_time, pixels_per_second, skipped_images, elapsed_time):
    progress_label.config(
        text=f"Progress: {images_generated}/{total_images} "
             f"Remaining time: {format_time(estimated_time)}"
    )
    progress_bar['value'] = (images_generated / total_images) * 100
    info_label.config(text=f"Skipped Images: {skipped_images}")
    speed_label.config(text=f"Pixels per Second: {pixels_per_second:.2f}")
    elapsed_label.config(text=f"Elapsed Time: {format_time(elapsed_time)}")

# Get device (CPU or GPU)
def get_device():
    try:
        if torch.cuda.is_available():
            # If CUDA is available, use GPU
            device = torch.device("cuda")
            # Maximize GPU utilization
            torch.backends.cudnn.benchmark = True
        else:
            # Use CPU if CUDA is not available
            device = torch.device("cpu")
        return device
    except Exception as e:
        print(f"Error in device selection: {e}")
        return torch.device("cpu")


# Hauptfenster erstellen
root = Tk()
root.title("RGB_Pixel_Generator")
root.resizable(True, True)  # Fenstergröße fixieren

# Farben für das Design
bg_color = "#1D3557"        # Hintergrundfarbe des Hauptfensters
label_color = "#457B9D"     # Farbe der Labels
entry_bg_color = "#A8DADC"  # Hintergrundfarbe der Eingabefelder
button_color = "#E63946"    # Hintergrundfarbe der Buttons
button_text_color = "white" # Textfarbe der Buttons
entry_text_color = "black"  # Textfarbe der Eingabefelder

root.configure(bg=bg_color)

Label(root, text="Output dir:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
output_dir_var = StringVar()
output_dir_entry = Entry(root, textvariable=output_dir_var, width=40, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
output_dir_entry.grid(row=0, column=1, padx=10, pady=10)
output_dir_button = Button(root, text="Output", command=select_output_folder, bg=button_color, fg=button_text_color, font=("Arial", 10, "bold"))
output_dir_button.grid(row=0, column=2, padx=10, pady=10)

Label(root, text="Greyscale range:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=W)
gray_start_var = IntVar(value=1)
gray_end_var = IntVar(value=256)
gray_start_entry = Entry(root, textvariable=gray_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
gray_start_entry.grid(row=1, column=1, padx=10, pady=10, sticky=W)
Label(root, text="bis", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=70, pady=10, sticky=W)
gray_end_entry = Entry(root, textvariable=gray_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
gray_end_entry.grid(row=1, column=1, padx=100, pady=10, sticky=W)

Label(root, text="Color range:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=W)
num_colors_start_var = IntVar(value=0)
num_colors_end_var = IntVar(value=16777215)
num_colors_start_entry = Entry(root, textvariable=num_colors_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_start_entry.grid(row=2, column=1, padx=10, pady=10, sticky=W)
Label(root, text="bis", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=1, padx=70, pady=10, sticky=W)
num_colors_end_entry = Entry(root, textvariable=num_colors_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_end_entry.grid(row=2, column=1, padx=100, pady=10, sticky=W)

progress_label = Label(root, text="Progress: 0/0 images generated.", bg=bg_color, fg="white", font=("Arial", 10))
progress_label.grid(row=3, column=0, columnspan=3, pady=5)

speed_frame = Frame(root, bg=bg_color)
speed_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

speed_label = Label(speed_frame, text="Pixel per second: 0", bg=bg_color, fg="white", font=("Arial", 10))
speed_label.grid(row=0, column=0, columnspan=3, pady=0)

elapsed_label = Label(speed_frame, text="Elapsed Time: 00:00:00", bg=bg_color, fg="white", font=("Arial", 10))
elapsed_label.grid(row=1, column=0, columnspan=3, pady=0)

progress_bar = ttk.Progressbar(root, length=500, mode='determinate')
progress_bar.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

info_label = Label(root, text="Skipped images: 0", bg=bg_color, fg="white", font=("Arial", 10))
info_label.grid(row=6, column=0, columnspan=3, pady=5)

# Buttons (Starten und Stoppen)
button_frame = Frame(root, bg=bg_color)
button_frame.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

start_button = Button(button_frame, text="Start", command=start_generation, bg=button_color, fg=button_text_color, font=("Arial", 12))
start_button.grid(row=0, column=0, padx=10)

stop_button = Button(button_frame, text="Stop", command=stop_generation_process, bg=button_color, fg=button_text_color, font=("Arial", 12))
stop_button.grid(row=0, column=1, padx=10)

root.mainloop()
