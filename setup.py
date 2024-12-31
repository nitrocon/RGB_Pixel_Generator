import subprocess
import sys
import logging

# Configure logging to output to console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]  # Log output to console
)

def install_requirements():
    """Install required Python packages from requirements.txt."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements from requirements.txt have been successfully installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error while installing requirements: {e}")
        logging.error(f"Error while installing requirements: {e}")
        sys.exit(1)

def setup():
    """Main setup function to install required packages."""
    install_requirements()

if __name__ == "__main__":
    setup()