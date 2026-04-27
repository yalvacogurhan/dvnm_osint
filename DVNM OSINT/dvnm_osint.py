import sys
import asyncio
import aiohttp
import ssl
import os
import traceback
import urllib.parse
import json
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QFileDialog, QGroupBox, QTextBrowser, 
                             QProgressBar, QComboBox, QMessageBox, QSplashScreen, QTabWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from qasync import QEventLoop, asyncSlot

# --- HARİCİ MODÜLLERİN İÇERİ AKTARILMASI ---
try:
    from instagram_osint import InstagramDerinAnaliz
    from exif_osint import ExifKonumAnalizi
    from visual_osint import VisualImageSearch
except ImportError as e:
    print(f"HATA: Bazı modül dosyaları bulunamadı! {e}")

# --- GÜNCELLEME AYARLARI ---
MEVCUT_SURUM = "1.0.0"
SURUM_KONTROL_URL = "{
  "version": "1.1.0",
  "url": "https://github.com/yalvacogurhan/dvnm_osint/releases/download/1.1.0/dvnm_osint.exe"
}" # ÖRN: https://raw.githubusercontent.com/.../version.json

# ==========================================
# EXE UYUMLULUĞU İÇİN DOSYA YOLU BULUCU
# ==========================================
def resource_path(relative_path):
    """ PyInstaller ile paketlendiğinde dosyaların geçici dizinden okunmasını sağlar. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# ANA UYGULAMA VE SEKME YÖNETİCİSİ
# ==========================================
class DVNM_OSINT_Uygulama(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DVNM OSINT - Dark Edition")
        
        icon_path = resource_path("dvnm_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.initUI()

    def initUI(self):
        # --- GLOBAL STYLESHEET (Dark & Green Theme) ---
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Arial; }
            QGroupBox { border: 2px solid #1db954; border-radius: 8px; margin-top: 15px; padding: 10px; font-weight: bold; color: #1db954; }
            QLineEdit { background-color: #1e1e1e; border: 1px solid #333; padding: 8px; border-radius: 4px; color: #ffffff; }
            QPushButton { background-color: #1db954; color: #000; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #1ed760; }
            QPushButton#saveBtn { background-color: #333; color: #fff; }
            QTextBrowser { background-color: #0b0b0b; border: 1px solid #1db954; border-radius: 4px; font-family: 'Consolas', monospace; }
            QProgressBar { border: 1px solid #333; border-radius: 5px; text-align: center; background-color: #1e1e1e; }
            QProgressBar::chunk { background-color: #1db954; }
            QComboBox { background-color: #1e1e1e; border: 1px solid #333; padding: 5px; color: #fff; }
            QTabBar::tab { background: #1e1e1e; color: white; padding: 10px 20px; border: 1px solid #333; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #1db954; color: black; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #333; }
        """)

        # --- 1. SEKME: STANDART TARAMA (DORK / API) ---
        standart_tarama_sekmesi = QWidget()
        standart_layout = QVBoxLayout()

        user_input_group = QGroupBox("DVNM OSINT TERMINAL")
        user_input_layout = QVBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Hedef Kullanıcı Adı (isim1, isim2...)")
        self.username_input.returnPressed.connect(self.search_username)
        
        self.uni_input = QLineEdit()
        self.uni_input.setPlaceholderText("Üniversite Adı (Dork Taraması İçin Opsiyonel)")
        
        user_input_layout.addWidget(QLabel("Hedef Kullanıcı Adları:"))
        user_input_layout.addWidget(self.username_input)
        user_input_layout.addWidget(QLabel("Üniversite Adı:"))
        user_input_layout.addWidget(self.uni_input)
        user_input_group.setLayout(user_input_layout)

        category_layout = QHBoxLayout()
        self.category_selector = QComboBox()
        self.category_selector.addItems(["Hepsi", "Sosyal Medya", "Forumlar", "Video Platformları", "Üniversite Ağı"])
        category_layout.addWidget(QLabel("Kapsam Seçimi:"))
        category_layout.addWidget(self.category_selector)

        button_layout = QHBoxLayout()
        self.search_button = QPushButton("TARAMAYI BAŞLAT")
        self.search_button.clicked.connect(self.search_username)
        self.save_button = QPushButton("RAPORU DIŞA AKTAR")
        self.save_button.setObjectName("saveBtn")
        self.save_button.clicked.connect(self.save_results)
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.save_button)

        self.progress_bar = QProgressBar()

        # Alt Panel Yerleşimi (Sonuçlar + Operasyonel Notlar)
        bottom_horizontal_layout = QHBoxLayout()
        self.result_area = QTextBrowser()
        self.result_area.setOpenExternalLinks(True)
        
        self.info_panel = QTextBrowser()
        self.info_panel.setFixedWidth(230)
        self.info_panel.setStyleSheet("border: 1px solid #f39c12; color: #f39c12; font-size: 11px;")
        self.info_panel.setHtml("""
            <b style='color: #f39c12; font-size: 12px;'>⚠️ OSINT OPERASYONEL NOTLAR</b><br><br>
            <b>1. EXIF VERİLERİ:</b><br>
            WhatsApp, Instagram ve X gibi platformlar üzerinden gelen resimlerde konum verisi 
            genellikle <i>'EXIF Stripping'</i> yöntemiyle silinir.<br><br>
            <b>2. DOĞRU GPS ANALİZİ:</b><br>
            Koordinat tespiti için görselin orijinal (e-posta veya kablo ile aktarılmış) 
            olması şarttır.<br><br>
            <b>3. LENS MANTIĞI:</b><br>
            Görsel eşleştirme sekmesinde, görseldeki tabela, mimari veya bitki örtüsünü 
            Google Lens veritabanı ile eşleştirerek konum doğrulaması yapabilirsiniz.<br><br>
            <b>4. INSTAGRAM GÜVENLİK:</b><br>
            Sahte/Bot hesabınızın banlanmaması için ardışık ve aşırı sorgudan kaçının.<br><br>
            <hr>
            <i>DVNM OSINT v1.0.0 - Dark Edition</i>
        """)

        bottom_horizontal_layout.addWidget(self.result_area, 7)
        bottom_horizontal_layout.addWidget(self.info_panel, 3)

        standart_layout.addWidget(user_input_group)
        standart_layout.addLayout(category_layout)
        standart_layout.addLayout(button_layout)
        standart_layout.addWidget(self.progress_bar)
        standart_layout.addLayout(bottom_horizontal_layout)
        standart_tarama_sekmesi.setLayout(standart_layout)

        # --- SEKME YÖNETİCİSİ (TAB WIDGET) ---
        self.tabs = QTabWidget()
        self.tabs.addTab(standart_tarama_sekmesi, "Çoklu Dork/Hızlı Tarama")
        self.tabs.addTab(InstagramDerinAnaliz(), "Instagram Derin Analiz")
        self.tabs.addTab(ExifKonumAnalizi(), "EXIF (Konum Çıkarıcı)")
        self.tabs.addTab(VisualImageSearch(), "Görsel Eşleştirme (Dedektif)")

        # Ana Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.setFixedSize(850, 750)

    @asyncSlot()
    async def search_username(self):
        raw_input = self.username_input.text().strip()
        if not raw_input:
            QMessageBox.warning(self, "Hata", "Hedef belirlenmedi!")
            return

        usernames = [u.strip() for u in raw_input.split(',') if u.strip()]
        self.result_area.clear()
        self.progress_bar.setValue(0)
        self.search_button.setEnabled(False)

        selected_category = self.category_selector.currentText()
        
        for username in usernames:
            self.result_area.append(f"<span style='color:#1db954;'>[>] '{username}' için DVNM protokolü çalıştırılıyor...</span><br>")
            await self.run_search(username, selected_category)
        
        self.search_button.setEnabled(True)
        self.result_area.append("<br><span style='color:#1db954;'>[+] Tarama başarıyla tamamlandı.</span>")

    async def run_search(self, username, category):
        sites = [
            {"name": "GitHub", "url": f"https://api.github.com/users/{username}", "api": True, "category": "Hepsi"},
            {"name": "Instagram", "url": f"https://www.instagram.com/{username}/", "api": False, "category": "Sosyal Medya"},
            {"name": "Reddit", "url": f"https://www.reddit.com/user/{username}", "api": False, "category": "Forumlar"},
            {"name": "X", "url": f"https://www.x.com/{username}", "api": False, "category": "Sosyal Medya"},
            {"name": "TikTok", "url": f"https://www.tiktok.com/@{username}", "api": False, "category": "Sosyal Medya"},
            {"name": "Google Dork (Instagram)", "url": f"https://www.google.com/search?q=site:instagram.com+intext:{username}", "api": False, "category": "Extra Sosyal Medya"},
            {"name": "X Gelişmiş Tarama", "url": f"https://www.google.com/search?q=site:x.com+OR+site:twitter.com+intext:{username}", "api": False, "category": "Extra Sosyal Medya"},
        ]

        uni_name = self.uni_input.text().strip()
        if uni_name and category in ["Hepsi", "Üniversite Ağı"]:
            dork_query = f'site:linkedin.com/in intitle:"{username}" "{uni_name}"'
            encoded_query = urllib.parse.quote(dork_query)
            sites.append({
                "name": "LinkedIn Üniversite Dork", 
                "url": f"https://www.google.com/search?q={encoded_query}", 
                "api": False, "category": "Üniversite Ağı", "is_dork": True 
            })

        if category != "Hepsi":
            sites = [site for site in sites if site['category'] == category]

        if not sites: return

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        async with aiohttp.ClientSession(headers=headers) as session:
            for index, site in enumerate(sites):
                if site.get('api'):
                    res = await self.search_api(site, session)
                elif site.get('is_dork'):
                    res = f'<div><span style="color:#f39c12;">[HAZIR]</span> <span style="color:#ffffff;">{site["name"]}:</span> <a style="color:#1db954;" href="{site["url"]}">Google\'da Gör</a></div>'
                else:
                    res = await self.search_website(site, session)
                
                self.result_area.append(res)
                self.progress_bar.setValue(int(((index + 1) / len(sites)) * 100))

    async def search_api(self, site, session):
        try:
            async with session.get(site['url']) as response:
                return self.format_result(site['name'], site['url'], response.status == 200)
        except: return self.format_result(site['name'], site['url'], False)

    async def search_website(self, site, session):
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            async with session.get(site["url"], ssl=ssl_context, timeout=7) as response:
                return self.format_result(site["name"], site["url"], response.status == 200)
        except: return self.format_result(site["name"], site["url"], False)

    def format_result(self, site_name, url, found):
        if found:
            return f'<div><span style="color:#1db954;">[FOUND]</span> <span style="color:#ffffff;">{site_name}:</span> <a style="color:#1db954;" href="{url}">{url}</a></div>'
        return f'<div><span style="color:#ff3333;">[MISS]</span> <span style="color:#888888;">{site_name}</span></div>'

    def save_results(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", "", "Metin Dosyası (*.txt)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("DVNM OSINT ARAŞTIRMA ÇIKTISI\n" + "="*30 + "\n")
                f.write(self.result_area.toPlainText())
            QMessageBox.information(self, "Başarılı", "Rapor kaydedildi.")

# ==========================================
# GÜNCELLEME KONTROLÜ VE SPLASH EKRANI
# ==========================================
async def baslangic_kontrolu(splash, ana_uygulama):
    # 1. Arka planda sunucudan sürüm kontrolü yap
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SURUM_KONTROL_URL, timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sunucu_surumu = data.get("version", "1.0.0")
                    indirme_linki = data.get("url", "")
                    
                    if sunucu_surumu > MEVCUT_SURUM:
                        print(f"[!] Yeni sürüm bulundu: {sunucu_surumu}")
                        # Güncelleyici arayüzünü (updater.exe) tetikle ve ana programı kapat
                        subprocess.Popen(["updater.exe", indirme_linki, "dvnm_osint.exe"])
                        sys.exit()
    except Exception as e:
        print(f"[-] Güncelleme kontrolü atlandı (İnternet yok veya sunucu yanıt vermiyor).")

    # 2. Eğer güncelleme yoksa, 3 saniye splash ekranını göster ve uygulamaya geç
    await asyncio.sleep(3)
    if splash is not None:
        splash.finish(ana_uygulama)
    ana_uygulama.show()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        splash_path = resource_path("load.png")
        splash = None
        
        if os.path.exists(splash_path):
            splash = QSplashScreen(QPixmap(splash_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation), Qt.WindowStaysOnTopHint)
            splash.setFont(QFont("Segoe UI", 12, QFont.Bold))
            splash.showMessage(f"DVNM OSINT v{MEVCUT_SURUM} Yükleniyor...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            splash.show()
        
        dvnm = DVNM_OSINT_Uygulama()
        
        # Başlangıç görevini (Update kontrolü + Splash ekranı beklemesi) tetikle
        loop.create_task(baslangic_kontrolu(splash, dvnm))
        
        with loop:
            loop.run_forever()
            
    except Exception as e:
        print("\n[!!!] KRİTİK BİR HATA YAKALANDI [!!!]")
        traceback.print_exc()
        input("Çıkış için Enter'a basın...")
