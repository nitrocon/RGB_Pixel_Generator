# RGB_Pixel_Generator
Generates 1x1 Pixel of all colors multiplied with every greyscale

This App is in alpha status. 
Uses CUDA but works without too. (only CPU Mode)

This Python APP generates 256 folders for every greyscale. Its mixing every color with every greyscale.

How to use (with CUDA 12.4 Support):

```Bash
git clone https://github.com/nitrocon/RGB_Pixel_Generator.git
cd RGB_Pixel_Generator
python -m venv venv
source venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
python generator.py
```

CUDA: It is tested with CUDA 12.4, if you have another CUDA Version please install the correct pytorch (see a list from their website)
Attention: Creating 16.7 million Pixel would be at least about 300TB of data, as of 1x1 Pixel is 69 bytes.
