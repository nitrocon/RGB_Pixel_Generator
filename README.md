# RGB_Pixel_Generator
Generates 1x1 Pixel of all colors multiplied with every greyscale

This App is in alpha status. 
Detects CUDA, if nor available it uses the CPU (CUDA not fully implemented yet)

This Python APP generates 256 folders for every greyscale. Its mixing every color with every greyscale.

How to use (with CUDA 11.3 Support):

```Bash
git clone https://github.com/nitrocon/RGB_Pixel_Generator.git
cd RGB_Pixel_Generator
python -m venv venv
source venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
python generator.py
```

CUDA: It is tested with CUDA 11.3, if you have another CUDA Version please install the correct pytorch (see a list from their website)
