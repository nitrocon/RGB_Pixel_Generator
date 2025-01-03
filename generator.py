import subprocess
import sys
import os
import logging
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image
import psutil
import threading
import torch
import numpy as np
import gc
from concurrent.futures import ThreadPoolExecutor
import time

# Configure logging to output to console
def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]  # Log output to console
    )

configure_logging()

sys.setrecursionlimit(100000)

# Stop generation flag
stop_generation = False

# CUDA optimization: Pixel values generation
def generate_pixel_values(num_colors_start, num_colors_end, device):
    try:
        logging.info(f"Generating pixel values from {num_colors_start} to {num_colors_end} on {device}.")
        # Create a range of pixel values (r, g, b)
        num_colors_range = torch.arange(num_colors_start, num_colors_end + 1, device=device)
        r = num_colors_range % 256
        g = torch.div(num_colors_range, 256, rounding_mode='trunc') % 256
        b = torch.div(num_colors_range, 256 * 256, rounding_mode='trunc') % 256
        logging.info("Pixel values generated successfully.")
        return r, g, b
    except Exception as e:
        logging.error(f"Error in generate_pixel_values: {e}")
        raise

# Get available memory (RAM and GPU) and adjust batch size accordingly
def get_available_memory():
    try:
        logging.info("Getting available memory.")
        # Get available system RAM
        available_ram = psutil.virtual_memory().available / (1024 ** 2)  # in MB
        if torch.cuda.is_available():
            # Get available GPU memory
            gpu_memory = torch.cuda.memory_allocated() / (1024 ** 2)  # in MB
            max_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)  # in MB
            available_gpu_memory = max_gpu_memory - gpu_memory
            logging.info(f"Available RAM: {available_ram} MB, Available GPU Memory: {available_gpu_memory} MB.")
            return available_ram, available_gpu_memory
        else:
            logging.info(f"Available RAM: {available_ram} MB, No GPU available.")
            return available_ram, 0
    except Exception as e:
        logging.error(f"Error in get_available_memory: {e}")
        raise

# Dynamically adjust the batch size based on available memory
def get_batch_size(available_ram, available_gpu_memory, base_batch_size=30000):
    try:
        logging.info("Adjusting batch size based on available memory.")
        # Estimate batch size based on available resources
        estimated_batch_size = base_batch_size
        if available_gpu_memory > 500:  # If more than 500mb GPU memory is available, use larger batch
            estimated_batch_size = base_batch_size * 2
        elif available_ram > 400:  # If more than 400mb system RAM is available, increase batch size
            estimated_batch_size = base_batch_size * 1.5
        logging.info(f"Batch size set to {estimated_batch_size}.")
        return int(estimated_batch_size)
    except Exception as e:
        logging.error(f"Error in get_batch_size: {e}")
        raise

# Handle generation of images
def generate_single_color_image(image_width, image_height, color):
    """
    Generates a single color image with the specified color.
    """
    img = Image.new("RGB", (image_width, image_height), color)
    return img

def generate_mandala_pattern(image_width, image_height, base_color, num_additional_colors):
    """
    Generates a mandala pattern with the specified base color and number of additional random colors.
    """
    img = Image.new("RGB", (image_width, image_height), base_color)
    pixels = img.load()

    # Generate random additional colors
    additional_colors = [(np.random.randint(0, 256), np.random.randint(0, 256), np.random.randint(0, 256)) for _ in range(num_additional_colors)]
    colors = [base_color] + additional_colors
    num_colors = len(colors)
    center_x, center_y = image_width // 2, image_height // 2

    for y in range(image_height):
        for x in range(image_width):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            color_index = int(distance) % num_colors
            next_color_index = (color_index + 1) % num_colors

            # Calculate the blend factor
            blend_factor = distance % 1

            # Blend the colors smoothly
            r = int(colors[color_index][0] * (1 - blend_factor) + colors[next_color_index][0] * blend_factor)
            g = int(colors[color_index][1] * (1 - blend_factor) + colors[next_color_index][1] * blend_factor)
            b = int(colors[color_index][2] * (1 - blend_factor) + colors[next_color_index][2] * blend_factor)

            pixels[x, y] = (r, g, b)

    return img

def generate_images(output_dir, num_colors_start, num_colors_end, image_width, image_height, colors_per_image, pattern_type, progress_label, progress_bar, info_label, elapsed_label, update_progress_callback):
    global stop_generation
    try:
        logging.info(f"Starting image generation. Output directory: {output_dir}, Color range: {num_colors_start}-{num_colors_end}, Image size: {image_width}x{image_height}, Colors per image: {colors_per_image}, Pattern type: {pattern_type}.")
        
        # Check if 'RGB_Colors' is already in the output_dir
        if not output_dir.endswith("RGB_Colors"):
            output_dir = os.path.join(output_dir, "RGB_Colors")
        
        # Create the main 'RGB_Colors' folder if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Created output directory: {output_dir}.")

        # Create the subfolder for the pattern type (e.g., Single or Mandala)
        pattern_folder = os.path.join(output_dir, pattern_type.capitalize())
        os.makedirs(pattern_folder, exist_ok=True)
        logging.info(f"Created pattern folder: {pattern_folder}.")

        # Create the subfolder named after the image size (e.g., 1x1 or 2x3) inside the pattern folder
        size_folder = f"{image_width}x{image_height}"
        color_folder = os.path.join(pattern_folder, size_folder)
        os.makedirs(color_folder, exist_ok=True)  # Ensure the subfolder for the size is created
        logging.info(f"Created size folder: {color_folder}.")

        total_images = (num_colors_end - num_colors_start + 1)
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
            for idx in range(len(r_values)):
                if stop_generation:
                    break

                base_color = (r_values[idx].item(), g_values[idx].item(), b_values[idx].item())
                hex_color = f"{r_values[idx].item():02X}{g_values[idx].item():02X}{b_values[idx].item():02X}"
                file_name = f"{hex_color}.png"
                file_path = os.path.join(color_folder, file_name)

                # Skip if the image already exists
                if os.path.exists(file_path):
                    skipped_images += 1
                    update_progress()  # Update even when skipping an image
                    continue

                # Generate the image based on the selected pattern type
                if pattern_type == "mandala":
                    img = generate_mandala_pattern(image_width, image_height, base_color, colors_per_image - 1)
                else:
                    img = generate_single_color_image(image_width, image_height, base_color)  # Single color image

                img.save(file_path)
                images_generated += 1
                update_progress()

            # Free GPU memory after processing the batch
            torch.cuda.empty_cache()
            logging.info(f"Batch {batch_idx} processed successfully.")

        # Executor for parallel processing of batches
        with ThreadPoolExecutor(max_workers=4) as executor:  # Begrenzung der parallelen Threads auf 4
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
            logging.info("Image generation completed successfully.")
        else:
            messagebox.showinfo("Aborted", "The image generation has been stopped.")
            logging.info("Image generation was stopped by the user.")

    except Exception as e:
        # Handle errors
        logging.error(f"Error during image generation: {e}", exc_info=True)
        messagebox.showerror("Error", f"An error occurred: {e}")

# Format time function
def format_time(seconds):
    try:
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
    except Exception as e:
        logging.error(f"Error in format_time: {e}")
        raise

# Folder selection dialog
def select_output_folder():
    try:
        folder = filedialog.askdirectory()
        if folder:
            app.output_dir_var.set(os.path.join(folder, "RGB_Colors"))
            logging.info(f"Output directory selected: {folder}/RGB_Colors")
    except Exception as e:
        logging.error(f"Error in select_output_folder: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Start generation
def start_generation():
    global stop_generation
    stop_generation = False
    try:
        logging.info("Starting image generation process.")
        threading.Thread(target=generate_images, args=(
            app.output_dir_var.get(),
            app.num_colors_start_var.get(),
            app.num_colors_end_var.get(),
            app.image_width_var.get(),
            app.image_height_var.get(),
            app.colors_per_image_var.get(),
            app.pattern_type_var.get(),
            app.progress_label,
            app.progress_bar,
            app.info_label,
            app.elapsed_label,
            app.update_progress_gui
        ), daemon=True).start()
    except RuntimeError as e:
        logging.error(f"Error in start_generation: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Stop generation process
def stop_generation_process():
    global stop_generation
    try:
        stop_generation = True
        logging.info("Stopping image generation process.")
    except Exception as e:
        logging.error(f"Error in stop_generation_process: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Update progress bar
def update_progress_gui(images_generated, total_images, estimated_time, images_per_second, skipped_images, elapsed_time):
    try:
        app.progress_label.config(
            text=f"Progress: {images_generated}/{total_images} "
                 f"Remaining time: {format_time(estimated_time)}"
        )
        app.progress_bar['value'] = (images_generated / total_images) * 100
        app.info_label.config(text=f"Skipped Images: {skipped_images}")
        app.speed_label.config(text=f"Images per Second: {images_per_second:.2f}")
        app.elapsed_label.config(text=f"Elapsed Time: {format_time(elapsed_time)}")
        logging.info(f"Progress: {images_generated}/{total_images}, Remaining time: {format_time(estimated_time)}, Images per second: {images_per_second:.2f}, Elapsed time: {format_time(elapsed_time)}, Skipped images: {skipped_images}")
    except Exception as e:
        logging.error(f"Error in update_progress_gui: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Get device (CPU or GPU)
def get_device():
    try:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            torch.backends.cudnn.benchmark = True
            logging.info("Using GPU for computation.")
        else:
            device = torch.device("cpu")
            logging.info("Using CPU for computation.")
        return device
    except Exception as e:
        logging.error(f"Error in device selection: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")
        return torch.device("cpu")

# GUI class
class RGBPixelGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RGB_Pixel_Generator")
        self.root.resizable(True, True)  # Allow window resizing

        # Colors for the design
        bg_color = "#1D3557"        # Background color of the main window
        label_color = "#457B9D"     # Label color
        entry_bg_color = "#A8DADC"  # Background color of entry fields
        button_color = "#E63946"    # Button background color
        button_text_color = "white" # Button text color
        entry_text_color = "black"  # Entry text color

        self.root.configure(bg=bg_color)

        # Define labels and input fields
        Label(self.root, text="Output dir:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
        self.output_dir_var = StringVar()
        output_dir_entry = Entry(self.root, textvariable=self.output_dir_var, width=40, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        output_dir_entry.grid(row=0, column=1, padx=10, pady=10)
        output_dir_button = Button(self.root, text="Output", command=select_output_folder, bg=button_color, fg=button_text_color, font=("Arial", 10, "bold"))
        output_dir_button.grid(row=0, column=2, padx=10, pady=10)

        Label(self.root, text="Image size:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=W)
        self.image_width_var = IntVar(value=1)
        image_width_entry = Entry(self.root, textvariable=self.image_width_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        image_width_entry.grid(row=2, column=1, padx=10, pady=10, sticky=W)
        Label(self.root, text="x", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=1, padx=70, pady=10, sticky=W)
        self.image_height_var = IntVar(value=1)
        image_height_entry = Entry(self.root, textvariable=self.image_height_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        image_height_entry.grid(row=2, column=1, padx=100, pady=10, sticky=W)

        Label(self.root, text="Color range:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=3, column=0, padx=10, pady=10, sticky=W)
        self.num_colors_start_var = IntVar(value=0)
        self.num_colors_end_var = IntVar(value=16777215)
        num_colors_start_entry = Entry(self.root, textvariable=self.num_colors_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        num_colors_start_entry.grid(row=3, column=1, padx=10, pady=10, sticky=W)
        Label(self.root, text="to", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=3, column=1, padx=70, pady=10, sticky=W)
        num_colors_end_entry = Entry(self.root, textvariable=self.num_colors_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        num_colors_end_entry.grid(row=3, column=1, padx=100, pady=10, sticky=W)

        Label(self.root, text="Colors per image:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=4, column=0, padx=10, pady=10, sticky=W)
        self.colors_per_image_var = IntVar(value=5)
        colors_per_image_entry = Entry(self.root, textvariable=self.colors_per_image_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        colors_per_image_entry.grid(row=4, column=1, padx=10, pady=10, sticky=W)

        Label(self.root, text="Pattern type:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=5, column=0, padx=10, pady=10, sticky=W)
        self.pattern_type_var = StringVar(value="single")
        pattern_type_menu = OptionMenu(self.root, self.pattern_type_var, "single", "mandala")
        pattern_type_menu.config(bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
        pattern_type_menu.grid(row=5, column=1, padx=10, pady=10, sticky=W)

        # Progress label and frame for speed and elapsed time
        self.progress_label = Label(self.root, text="Progress: 0/0 images generated.", bg=bg_color, fg="white", font=("Arial", 10))
        self.progress_label.grid(row=6, column=0, columnspan=3, pady=5)

        speed_frame = Frame(self.root, bg=bg_color)
        speed_frame.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

        self.speed_label = Label(speed_frame, text="Image per second: 0", bg=bg_color, fg="white", font=("Arial", 10))
        self.speed_label.grid(row=0, column=0, columnspan=3, pady=0)

        self.elapsed_label = Label(speed_frame, text="Elapsed Time: 00:00:00", bg=bg_color, fg="white", font=("Arial", 10))
        self.elapsed_label.grid(row=1, column=0, columnspan=3, pady=0)

        self.progress_bar = ttk.Progressbar(self.root, length=500, mode='determinate')
        self.progress_bar.grid(row=8, column=0, columnspan=3, padx=10, pady=5)

        self.info_label = Label(self.root, text="Skipped images: 0", bg=bg_color, fg="white", font=("Arial", 10))
        self.info_label.grid(row=9, column=0, columnspan=3, pady=5)

        # Buttons (Start and Stop)
        button_frame = Frame(self.root, bg=bg_color)
        button_frame.grid(row=10, column=0, columnspan=3, padx=10, pady=10)

        start_button = Button(button_frame, text="Start", command=start_generation, bg=button_color, fg=button_text_color, font=("Arial", 12))
        start_button.grid(row=0, column=0, padx=10)

        stop_button = Button(button_frame, text="Stop", command=stop_generation_process, bg=button_color, fg=button_text_color, font=("Arial", 12))
        stop_button.grid(row=0, column=1, padx=10)

    def update_progress_gui(self, images_generated, total_images, estimated_time, images_per_second, skipped_images, elapsed_time):
        try:
            self.progress_label.config(
                text=f"Progress: {images_generated}/{total_images} "
                     f"Remaining time: {format_time(estimated_time)}"
            )
            self.progress_bar['value'] = (images_generated / total_images) * 100
            self.info_label.config(text=f"Skipped Images: {skipped_images}")
            self.speed_label.config(text=f"Images per Second: {images_per_second:.2f}")
            self.elapsed_label.config(text=f"Elapsed Time: {format_time(elapsed_time)}")
            logging.info(f"Progress: {images_generated}/{total_images}, Remaining time: {format_time(estimated_time)}, Images per second: {images_per_second:.2f}, Elapsed time: {format_time(elapsed_time)}, Skipped images: {skipped_images}")
        except Exception as e:
            logging.error(f"Error in update_progress_gui: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

# Start the main loop of the Tkinter window
def start_gui():
    global app
    root = Tk()
    app = RGBPixelGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    # Start the GUI in the main thread
    start_gui()