import os
import webbrowser
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QGroupBox, QTextBrowser, QFileDialog)

class VisualImageSearch(QWidget):
    def __init__(self):
        super().__init__()
        self.dosya_yolu = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        grup_kutusu = QGroupBox("GÖRSEL EŞLEŞTİRME VE LENS ANALİZİ")
        grup_layout = QVBoxLayout()

        self.bilgi_label = QLabel("Videodaki dedektiflik mantığı: Görseldeki ipuçlarını (tabela, mimari, doğa) \n"
                                   "dünya çapındaki veri tabanlarıyla eşleştirin.")
        self.bilgi_label.setStyleSheet("color: #888; font-style: italic;")
        
        self.secilen_dosya_label = QLabel("Analiz için bir görsel seçilmedi.")
        self.secilen_dosya_label.setStyleSheet("color: #1db954; font-weight: bold;")

        buton_layout = QHBoxLayout()
        self.dosya_sec_btn = QPushButton("GÖRSELİ SİSTEME YÜKLE")
        self.dosya_sec_btn.clicked.connect(self.gorsel_sec)
        
        buton_layout.addWidget(self.dosya_sec_btn)

        grup_layout.addWidget(self.bilgi_label)
        grup_layout.addWidget(self.secilen_dosya_label)
        grup_layout.addLayout(buton_layout)
        grup_kutusu.setLayout(grup_layout)

        # Arama Motoru Butonları
        self.search_group = QGroupBox("ARAMA MOTORLARI (GÖRSEL EŞLEŞTİRME)")
        self.search_group.setEnabled(False) # Görsel seçilmeden basılamaz
        search_layout = QVBoxLayout()

        self.btn_google = QPushButton("GOOGLE LENS İLE EŞLEŞTİR (En İyi Konum Tespiti)")
        self.btn_yandex = QPushButton("YANDEX IMAGES İLE EŞLEŞTİR (En İyi Yüz/Nesne Tespiti)")
        self.btn_bing = QPushButton("BING VISUAL SEARCH İLE ARA")
        
        self.btn_google.clicked.connect(lambda: self.arama_yap("google"))
        self.btn_yandex.clicked.connect(lambda: self.arama_yap("yandex"))
        self.btn_bing.clicked.connect(lambda: self.arama_yap("bing"))

        search_layout.addWidget(self.btn_google)
        search_layout.addWidget(self.btn_yandex)
        search_layout.addWidget(self.btn_bing)
        self.search_group.setLayout(search_layout)

        # OSINT İpuçları Paneli
        self.tip_area = QTextBrowser()
        self.tip_area.setStyleSheet("background-color: #0b0b0b; border: 1px dashed #1db954; color: #aaa;")
        self.tip_area.setHtml("""
            <b style='color: #1db954;'>DEDEKTİF MANTIĞI İPUÇLARI:</b><br>
            - <b>Tabelalar:</b> Görseldeki yazıların dilini ve şehir isimlerini Google'da aratın.<br>
            - <b>Mimari:</b> Pencerelerin şekli veya çatı tipleri ülkeleri ele verir.<br>
            - <b>Bitki Örtüsü:</b> Palmiye ağaçları mı var yoksa çam ormanları mı? Bu coğrafyayı daraltır.<br>
            - <b>Google Maps:</b> Lens'ten gelen sonuçlardaki dükkan isimlerini Maps'te 'Street View' ile doğrulayın.
        """)

        layout.addWidget(grup_kutusu)
        layout.addWidget(self.search_group)
        layout.addWidget(self.tip_area)

        self.setLayout(layout)

    def gorsel_sec(self):
        dosya, _ = QFileDialog.getOpenFileName(self, "Görsel Seç", "", "Resim Dosyaları (*.jpg *.jpeg *.png)")
        if dosya:
            self.dosya_yolu = dosya
            self.secilen_dosya_label.setText(f"Yüklendi: {os.path.basename(dosya)}")
            self.search_group.setEnabled(True)

    def arama_yap(self, engine):
        # Not: Modern tarayıcı güvenliği nedeniyle, yerel bir dosyayı 
        # Python içinden doğrudan Google Lens'in 'upload' kutusuna fırlatmak kısıtlıdır.
        # Bu yüzden en stabil yöntem: Kullanıcıyı ilgili motorun yükleme sayfasına yönlendirmektir.
        
        urls = {
            "google": "https://lens.google.com/search?p=",
            "yandex": "https://yandex.com/images/search?rpt=imageview",
            "bing": "https://www.bing.com/visualsearch"
        }
        
        # Kullanıcıya klasörü açıp görseli sürüklemesi gerektiğini hatırlatabiliriz
        QMessageBox.information(self, "Bilgi", f"Şimdi {engine.capitalize()} sayfası açılacak. \n"
                                               "Lütfen açılan sayfadaki 'Kamera/Yükle' simgesine basıp görseli seçin.")
        webbrowser.open(urls[engine])