import os
import sys
import subprocess

dosya_konumu = os.path.dirname(os.path.abspath(__file__))
os.chdir(dosya_konumu)
gercek_python = sys.executable

print("="*60)
print(f"[+] Çalışma Klasörü: {dosya_konumu}")
print("="*60)

print("\n[1] PyInstaller modülü kontrol ediliyor...")
subprocess.run([gercek_python, "-m", "pip", "install", "pyinstaller"])

print("\n[2] DVNM OSINT EXE dosyası derleniyor...")
print("LÜTFEN DİKKAT: Windows Defender'ın gerçek zamanlı korumasını geçici olarak kapattığınızdan emin olun!\n")

derleme_komutu = [
    gercek_python, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--icon", "dvnm_icon.ico",
    "--add-data", "dvnm_icon.ico;.",
    "--add-data", "load.png;.",
    "dvnm_osint.py"
]

islem = subprocess.run(derleme_komutu)

print("\n[3] Updater (Otomatik Güncelleyici) derleniyor...")
updater_komutu = [
    gercek_python, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "updater.py"
]
subprocess.run(updater_komutu)

if islem.returncode == 0:
    print("\n" + "="*60)
    print("[+] BAŞARILI! Uygulamanız hazır.")
    print("Lütfen sol taraftaki 'dist' isimli klasörün içine girin.")
    print("dvnm_osint.exe dosyanız orada sizi bekliyor!")
    print("="*60)
else:
    print("\n" + "="*60)
    print("[!] HATA: Derleme başarısız.")
    print("="*60)
