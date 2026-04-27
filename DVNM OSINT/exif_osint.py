import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QTextBrowser, QFileDialog)
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

class ExifKonumAnalizi(QWidget):
    def __init__(self):
        super().__init__()
        self.dosya_yolu = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        grup_kutusu = QGroupBox("EXIF & GPS METADATA ANALİZİ")
        grup_layout = QVBoxLayout()

        self.bilgi_label = QLabel("Analiz etmek istediğiniz fotoğrafı sisteme yükleyin.\nSistem sadece fotoğrafta kayıtlı bir konum verisi varsa bunu haritaya dönüştürür.")
        self.bilgi_label.setStyleSheet("color: #888; font-style: italic;")
        
        self.secilen_dosya_label = QLabel("Henüz dosya seçilmedi.")
        self.secilen_dosya_label.setStyleSheet("color: #f39c12; font-weight: bold;")

        buton_layout = QHBoxLayout()
        self.dosya_sec_btn = QPushButton("FOTOĞRAF YÜKLE")
        self.dosya_sec_btn.clicked.connect(self.fotograf_sec)
        
        self.analiz_et_btn = QPushButton("METADATA ÇIKART")
        self.analiz_et_btn.setEnabled(False) 
        self.analiz_et_btn.clicked.connect(self.analizi_baslat)

        buton_layout.addWidget(self.dosya_sec_btn)
        buton_layout.addWidget(self.analiz_et_btn)

        grup_layout.addWidget(self.bilgi_label)
        grup_layout.addWidget(self.secilen_dosya_label)
        grup_layout.addLayout(buton_layout)
        grup_kutusu.setLayout(grup_layout)

        self.sonuc_ekrani = QTextBrowser()
        self.sonuc_ekrani.setOpenExternalLinks(True) 
        self.sonuc_ekrani.append("<span style='color:#888;'>Sistem Hazır. EXIF verileri bekleniyor...</span>")

        layout.addWidget(grup_kutusu)
        layout.addWidget(self.sonuc_ekrani)
        self.setLayout(layout)

    def fotograf_sec(self):
        dosya, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Resim Dosyaları (*.jpg *.jpeg *.png *.tiff)")
        if dosya:
            self.dosya_yolu = dosya
            self.secilen_dosya_label.setText(f"Seçilen Dosya: {os.path.basename(dosya)}")
            self.analiz_et_btn.setEnabled(True)
            self.sonuc_ekrani.clear()
            self.sonuc_ekrani.append(f"<span style='color:#1db954;'>[+] Dosya yüklendi, analize hazır.</span>")

    def dms_to_decimal(self, dms_degerleri, yon):
        derece, dakika, saniye = float(dms_degerleri[0]), float(dms_degerleri[1]), float(dms_degerleri[2])
        ondalik = derece + (dakika / 60.0) + (saniye / 3600.0)
        if yon in ['S', 'W']: ondalik = -ondalik
        return ondalik

    def analizi_baslat(self):
        if not self.dosya_yolu: return
        self.sonuc_ekrani.clear()
        self.sonuc_ekrani.append(f"<span style='color:#f39c12;'>[>] Taranıyor...</span><br>")

        try:
            image = Image.open(self.dosya_yolu)
            exif_raw = image._getexif()

            if not exif_raw:
                self.sonuc_ekrani.append("<span style='color:#ff3333;'>[-] Bu fotoğrafta EXIF metadata kaydı bulunamadı.</span>")
                return

            exif_verileri, gps_verileri = {}, {}
            for tag_id, deger in exif_raw.items():
                etiket = TAGS.get(tag_id, tag_id)
                if etiket == "GPSInfo":
                    for t in deger: gps_verileri[GPSTAGS.get(t, t)] = deger[t]
                else: exif_verileri[etiket] = deger

            cihaz = f"{exif_verileri.get('Make', 'Bilinmiyor')} {exif_verileri.get('Model', '')}"
            tarih = exif_verileri.get('DateTimeOriginal', 'Bilinmiyor')

            self.sonuc_ekrani.append(f"<span style='color:#1db954;'><b>[+] DONANIM:</b></span><br><span style='color:#fff;'><b>Cihaz:</b> {cihaz}</span><br><span style='color:#fff;'><b>Tarih/Saat:</b> {tarih}</span><br>")

            if not gps_verileri or 'GPSLatitude' not in gps_verileri:
                self.sonuc_ekrani.append("<span style='color:#ff3333;'>[-] KONUM (GPS) verisi bulunamadı.</span>")
                return

            enlem = self.dms_to_decimal(gps_verileri['GPSLatitude'], gps_verileri['GPSLatitudeRef'])
            boylam = self.dms_to_decimal(gps_verileri['GPSLongitude'], gps_verileri['GPSLongitudeRef'])
            maps_link = f"https://www.google.com/maps?q={enlem},{boylam}"

            self.sonuc_ekrani.append(f"<span style='color:#1db954;'><b>[+] KONUM TESPİT EDİLDİ!</b></span><br><span style='color:#fff;'><b>Koordinat:</b> {enlem}, {boylam}</span>")
            self.sonuc_ekrani.append(f"<br><a href='{maps_link}' style='color:#1db954; font-size: 14px; font-weight: bold;'>[ HARİTADA GÖRÜNTÜLE ]</a>")

        except Exception as e:
            self.sonuc_ekrani.append(f"<br><span style='color:#ff3333;'>[KRİTİK HATA] {str(e)}</span>")