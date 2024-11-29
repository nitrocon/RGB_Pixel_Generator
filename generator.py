import os
import time
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image
import psutil  # Für Ressourcenschonung
import threading
import torch
import sys
sys.setrecursionlimit(100000)

# Stoppen der Generierung Flag
stop_generation = False

# Funktion zur Generierung der Bilder
def generate_images(output_dir, gray_start, gray_end, num_colors_start, num_colors_end, progress_label, progress_bar, info_label):
    global stop_generation
    try:
        os.makedirs(output_dir, exist_ok=True)
        total_images = (gray_end - gray_start + 1) * (num_colors_end - num_colors_start + 1)
        images_generated = 0
        skipped_images = 0
        start_time = time.time()

        def update_progress():
            # Update the progress bar in a thread-safe way
            if images_generated > 0:
                elapsed_time = time.time() - start_time
                estimated_time = (elapsed_time / images_generated) * (total_images - images_generated)
                elapsed_seconds = time.time() - start_time
                remaining_images = total_images - images_generated
                pixel_per_second = (images_generated * 1) / elapsed_seconds  # Annahme 1 Pixel pro Bild
                progress_label.config(text=f"Fortschritt: {images_generated}/{total_images} Bilder generiert. "
                                          f"Verbleibende Zeit: {format_time(estimated_time)} | {pixel_per_second:.2f} Pixel/s")
                progress_bar['value'] = (images_generated / total_images) * 100
            else:
                progress_label.config(text=f"Fortschritt: {images_generated}/{total_images} Bilder generiert. "
                                          f"Verbleibende Zeit: Berechne...")

            root.update_idletasks()

        # Dynamisch das Gerät auswählen (GPU oder CPU) für Berechnungen
        device = get_device()

        total_pixels = 0  # Variable zur Berechnung der durchschnittlichen Pixel

        for gray in range(gray_start, gray_end):
            if stop_generation:
                break

            # Ordnername: Hexadezimal des Grauwerts
            gray_hex = f"{gray:02X}"
            gray_folder = os.path.join(output_dir, gray_hex)
            os.makedirs(gray_folder, exist_ok=True)

            for num_colors in range(num_colors_start, num_colors_end + 1):
                if stop_generation:
                    break

                r, g, b = (num_colors % 256, (num_colors // 256) % 256, (num_colors // (256 * 256)) % 256)
                gray_value = int(0.299 * r + 0.587 * g + 0.114 * b)
                hex_color = f"{r:02X}{g:02X}{b:02X}"
                result_color = f"{gray_value:02X}{gray_value:02X}{gray_value:02X}"

                # Dateiname: GraustufenHexa-FarbeHexa-GemischteFarbeHexa.png
                file_name = f"{gray_hex}-{hex_color}-{result_color}.png"
                file_path = os.path.join(gray_folder, file_name)

                # Wenn die Datei bereits existiert, überspringen
                if os.path.exists(file_path):
                    skipped_images += 1
                    info_label.config(text=f"Übersprungene Bilder: {skipped_images}")
                    update_progress()
                    continue  # überspringe die Erstellung dieses Bildes

                # Bild erstellen und speichern
                img = Image.new("RGB", (1, 1), (gray_value, gray_value, gray_value))
                img.save(file_path)

                # Update Fortschritt
                images_generated += 1
                total_pixels += img.width * img.height  # Pixel zur Durchschnittsberechnung hinzufügen
                update_progress()

                # Ressourcenschonung: CPU-Auslastung überwachen und ggf. pausieren
                if psutil.cpu_percent() > 90:  # Wenn die CPU-Auslastung über 90% liegt
                    time.sleep(0.1)  # Pausiert die Verarbeitung für 100ms, um die CPU zu entlasten

        if not stop_generation:
            avg_pixels = total_pixels / images_generated if images_generated > 0 else 0
            messagebox.showinfo("Fertig", f"Die Bilder wurden erfolgreich generiert! Durchschnittliche Pixel: {avg_pixels:.2f}")
        else:
            messagebox.showinfo("Abgebrochen", "Die Bildgenerierung wurde gestoppt.")
        
    except Exception as e:
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")

# Funktion zur Formatierung der verbleibenden Zeit
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"

# Funktion zur Auswahl des Ausgabeordners
def select_output_folder():
    folder = filedialog.askdirectory()
    if folder:
        output_dir_var.set(folder)

# Funktion, die den Bildgenerierungsprozess in einem separaten Thread ausführt
def start_generation():
    global stop_generation
    stop_generation = False  # Setze das Stop-Flag auf False, bevor die Generierung startet
    threading.Thread(target=generate_images, args=(
        output_dir_var.get(),
        gray_start_var.get(),
        gray_end_var.get(),
        num_colors_start_var.get(),
        num_colors_end_var.get(),
        progress_label,
        progress_bar,
        info_label
    ), daemon=True).start()

# Funktion zum Stoppen der Bildgenerierung
def stop_generation_process():
    global stop_generation
    stop_generation = True  # Setze das Stop-Flag auf True, um die Generierung zu stoppen

# Funktion zur Auswahl von CUDA oder CPU
def get_device():
    try:
        # Überprüfen, ob CUDA verfügbar ist
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print("Verwenden von CUDA")
        else:
            device = torch.device("cpu")
            print("Verwenden der CPU")
        return device
    except Exception as e:
        print(f"Fehler bei der Gerätewahl: {e}")
        return torch.device("cpu")

# Hauptfenster erstellen
root = Tk()
root.title("RGB_Pixel_Generator")
root.geometry("550x330")
root.resizable(False, False)  # Fenstergröße fixieren

# Farben für das Design
bg_color = "#1D3557"        # Hintergrundfarbe des Hauptfensters
label_color = "#457B9D"     # Farbe der Labels
entry_bg_color = "#A8DADC"  # Hintergrundfarbe der Eingabefelder
button_color = "#E63946"    # Hintergrundfarbe der Buttons
button_text_color = "white" # Textfarbe der Buttons
entry_text_color = "black"  # Textfarbe der Eingabefelder

# Hauptfenster-Hintergrund
root.configure(bg=bg_color)

# GUI-Komponenten
Label(root, text="Ausgabeordner:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
output_dir_var = StringVar()
output_dir_entry = Entry(root, textvariable=output_dir_var, width=40, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
output_dir_entry.grid(row=0, column=1, padx=10, pady=10)
output_dir_button = Button(root, text="Auswählen", command=select_output_folder, bg=button_color, fg=button_text_color, font=("Arial", 10, "bold"))
output_dir_button.grid(row=0, column=2, padx=10, pady=10)

Label(root, text="Graustufenbereich:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=W)
gray_start_var = IntVar(value=0)
gray_end_var = IntVar(value=256)  # Hier ist der Endwert auf 256 gesetzt
gray_start_entry = Entry(root, textvariable=gray_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
gray_start_entry.grid(row=1, column=1, padx=10, pady=10, sticky=W)
Label(root, text="bis", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=70, pady=10, sticky=W)
gray_end_entry = Entry(root, textvariable=gray_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
gray_end_entry.grid(row=1, column=1, padx=100, pady=10, sticky=W)

Label(root, text="Farbbereich:", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=W)
num_colors_start_var = IntVar(value=0)
num_colors_end_var = IntVar(value=16777215)  # Hier auf den maximalen RGB-Wert gesetzt
num_colors_start_entry = Entry(root, textvariable=num_colors_start_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_start_entry.grid(row=2, column=1, padx=10, pady=10, sticky=W)
Label(root, text="bis", bg=label_color, fg="white", font=("Arial", 10, "bold")).grid(row=2, column=1, padx=70, pady=10, sticky=W)
num_colors_end_entry = Entry(root, textvariable=num_colors_end_var, width=10, bg=entry_bg_color, fg=entry_text_color, font=("Arial", 10))
num_colors_end_entry.grid(row=2, column=1, padx=100, pady=10, sticky=W)

# Fortschrittsanzeige
progress_label = Label(root, text="Fortschritt: 0/0 Bilder generiert.", bg=bg_color, fg="white", font=("Arial", 10))
progress_label.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

info_label = Label(root, text="Übersprungene Bilder: 0", bg=bg_color, fg="white", font=("Arial", 10))
info_label.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

# Buttons (Starten und Stoppen)
button_frame = Frame(root, bg=bg_color)
button_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=20)

start_button = Button(button_frame, text="Generieren Starten", command=start_generation, bg=button_color, fg=button_text_color, font=("Arial", 12))
start_button.grid(row=0, column=0, padx=10)

stop_button = Button(button_frame, text="Generieren Stoppen", command=stop_generation_process, bg=button_color, fg=button_text_color, font=("Arial", 12))
stop_button.grid(row=0, column=1, padx=10)

root.mainloop()
