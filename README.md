# RGB Pixel Generator

A Python tool for generating Images with adjustable pixelsize in RGB, optimized for CUDA and parallel processing.
I use this tool to train several AI models.

## 📋 Installation

Run autostart_script.bat (autoinstall, you need Python 3.12) or
follow these steps to set up the project:

```bash
git clone https://github.com/nitrocon/RGB_Pixel_Generator.git
cd RGB_Pixel_Generator
python -m venv venv
source venv/Scripts/activate
python.exe -m pip install --upgrade pip
python generator.py
```

## 🛠 Features

- Generating Images with an adjustable pixelsize
- Efficient Image Generation: Utilizes CUDA for faster pixel computation. 
- Is skipping already existing images
- Dynamic Memory Adjustment: Automatically adapts batch size based on available memory.
- User-Friendly GUI: Provides an intuitive interface for configuring and monitoring the process.
- Scalable Processing: Supports both CPU and GPU for optimal performance.

## 📄 Usage

1. Run the `generator.py` script.
2. Use the GUI to set parameters such as image size, color range, and output directory.
3. Start the generation process and monitor progress via the GUI.

## 🧑‍💻 Requirements

- Python 3.12 (autostart script is looking for it)
- `torch` library (for CUDA support)
- `psutil` library (for memory management)
- `PIL` (Python Imaging Library) for image generation

✉️ Contact
For questions or suggestions, reach out via:

GitHub: nitrocon

Let me know if you need further refinements!
