# RGB Pixel Generator

A powerful Python tool for generating RGB pixel images, optimized for CUDA and parallel processing.

## 📋 Installation

Follow these steps to set up the project:

```bash
git clone https://github.com/nitrocon/RGB_Pixel_Generator.git
cd RGB_Pixel_Generator
python -m venv venv
source venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
python generator.py
```

## 🛠 Features

- Efficient Image Generation: Utilizes CUDA for faster pixel computation.
- Dynamic Memory Adjustment: Automatically adapts batch size based on available memory.
- User-Friendly GUI: Provides an intuitive interface for configuring and monitoring the process.
- Scalable Processing: Supports both CPU and GPU for optimal performance.

## 📄 Usage

1. Run the `generator.py` script.
2. Use the GUI to set parameters such as greyscale range, color range, and output directory.
3. Start the generation process and monitor progress via the GUI.

## 🧑‍💻 Requirements

- Python 3.6 or higher
- `torch` library (for CUDA support)
- `psutil` library (for memory management)
- `PIL` (Python Imaging Library) for image generation
- Tkinter (for GUI)

✉️ Contact
For questions or suggestions, reach out via:

GitHub: nitrocon

Let me know if you need further refinements!
