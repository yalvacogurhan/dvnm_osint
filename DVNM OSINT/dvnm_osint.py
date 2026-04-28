import sys
import asyncio
import aiohttp
import ssl
import os
import traceback
import urllib.parse
import json
import aiofiles
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QFileDialog, QGroupBox, QTextBrowser, 
                             QProgressBar, QComboBox, QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap
from qasync import QEventLoop, asyncSlot

# --- HARİCİ MODÜLLERİN İÇERİ AKTARILMASI ---
try:
    from instagram_osint import InstagramDerinAnaliz
    from exif_osint import ExifKonumAnalizi
    from visual_osint import VisualImageSearch
except ImportError as e:
    print(f"HATA: Bazı modül dosyaları bulunamadı! {e}")

# ==========================================
# EXE UYUMLULUĞU İÇİN DOSYA YOLU BULUCU
# ==========================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# ARKA PLAN KENDİ KENDİNİ GÜNCELLEME (BAT) SİSTEMİ
# ==========================================
def create_and_run_updater(new_exe_path):
    """Yeni inen exe dosyasını eskisinin yerine koyar ve programı yeniden başlatır."""
    if not getattr(sys, 'frozen', False): return
    
    current_exe = sys.executable
    current_dir = os.path.dirname(current_exe)
    current_name = os.path.basename(current_exe)
    new_exe_name = os.path.basename(new_exe_path)
    
    bat_path = os.path.join(current_dir, "dvnm_updater.bat")
    
    # 2 Saniye bekle -> Eski exe'yi sil -> Yenisinin adını eski yap -> Yenisini başlat -> Kendini sil
    bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
del "{current_name}"
ren "{new_exe_name}" "{current_name}"
start "" "{current_name}"
del "%~f0"
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
        
    # CMD penceresi tamamen görünmez (Gizli) olarak çalışsın
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x08000000 
        
    subprocess.Popen([bat_path], shell=True, cwd=current_dir, **kwargs)
    sys.exit(0)

# ==========================================
# YENİ NESİL AÇILIŞ (SPLASH) EKRANI (İlerleme Çubuklu)
# ==========================================
class CustomSplashScreen(QWidget):
    def __init__(self, image_path):
        super().__init__()
        # Çerçevesiz, görev çubuğunda görünmeyen ve hep üstte kalan ekran
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground) # Arka planı şeffaf yapar
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        self.bg_label = QLabel()
        self.bg_label.setAlignment(Qt.AlignCenter)
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.bg_label.setPixmap(pixmap)
            
        self.info_label = QLabel("Sistem Başlatılıyor...")
        self.info_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background-color: rgba(0, 0, 0, 150); padding: 5px; border-radius: 5px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        
        self.progress_bar = QProgressBar()
        # Senin istediğin "Siyah (şeffaf) arka planlı, kalın beyaz detaylı" bar tasarımı
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ffffff;
                border-radius: 6px;
                text-align: center;
                background-color: rgba(0, 0, 0, 100);
                color: #ffffff;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #ffffff;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide() # Başlangıçta gizli
        
        layout.addWidget(self.bg_label)
        layout.addWidget(self.info_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

# Asenkron Açılış Kontrolü
async def check_startup_update(splash, app_instance):
    splash.info_label.setText("Sürüm Kontrol Ediliyor...")
    await asyncio.sleep(1) 
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(app_instance.UPDATE_JSON_URL, timeout=4) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    remote_version = data.get("version")
                    download_url = data.get("url")
                    
                    remote_v_tuple = tuple(map(int, remote_version.replace('v', '').split('.')))
                    current_v_tuple = tuple(map(int, app_instance.CURRENT_VERSION.replace('v', '').split('.')))
                    
                    # YENİ SÜRÜM VARSA OTOMATİK İNDİR VE KUR
                    if remote_v_tuple > current_v_tuple:
                        splash.info_label.setText(f"Yeni Sürüm (v{remote_version}) İndiriliyor...")
                        splash.progress_bar.show()
                        
                        if getattr(sys, 'frozen', False):
                            save_path = os.path.join(os.path.dirname(sys.executable), "dvnm_update_temp.exe")
                        else:
                            save_path = "dvnm_update_temp.exe"
                            
                        async with session.get(download_url) as res:
                            if res.status == 200:
                                total_size = int(res.headers.get('content-length', 0))
                                downloaded_size = 0
                                
                                async with aiofiles.open(save_path, 'wb') as f:
                                    async for chunk in res.content.iter_chunked(1024 * 64):
                                        await f.write(chunk)
                                        downloaded_size += len(chunk)
                                        if total_size:
                                            percent = int((downloaded_size / total_size) * 100)
                                            splash.progress_bar.setValue(percent)
                                            
                                splash.info_label.setText("Kurulum Tamamlanıyor. Yeniden Başlatılacak...")
                                await asyncio.sleep(2)
                                
                                if getattr(sys, 'frozen', False):
                                    create_and_run_updater(save_path) # Bat dosyasını çalıştır ve çık!
                                    return
                                else:
                                    splash.info_label.setText("IDE Modu: Güncelleme Atlandı.")
                                    await asyncio.sleep(1)
    except Exception:
        pass # Hata olursa sessizce uygulamayı açmaya devam et
        
    # GÜNCELLEME YOKSA VEYA BİTTİYSE UYGULAMAYI AÇ
    splash.info_label.setText("DVNM OSINT Başlatılıyor...")
    await asyncio.sleep(1)
    splash.close()
    app_instance.show()

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
        # --- GÜNCELLEME DEĞİŞKENLERİ ---
        self.CURRENT_VERSION = "1.0.0" # Test için 1.0.0
        self.UPDATE_JSON_URL = "https://raw.githubusercontent.com/yalvacogurhan/dvnm_osint/main/DVNM%20OSINT/version.json"

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

        # Alt Panel Yerleşimi
        bottom_horizontal_layout = QHBoxLayout()
        self.result_area = QTextBrowser()
        self.result_area.setOpenExternalLinks(True)
        
        self.info_panel = QTextBrowser()
        self.info_panel.setFixedWidth(230)
        self.info_panel.setStyleSheet("border: 1px solid #f39c12; color: #f39c12; font-size: 11px;")
        self.info_panel.setHtml("""
            <b style='color: #f39c12; font-size: 12px;'>⚠️ OSINT OPERASYONEL NOTLAR</b><br><br>
            <b>1. EXIF VERİLERİ:</b><br>
            WhatsApp, Instagram ve X gibi platformlar üzerinden gelen resimlerde konum verisi genellikle <i>'EXIF Stripping'</i> yöntemiyle silinir.<br><br>
            <b>2. DOĞRU GPS ANALİZİ:</b><br>
            Koordinat tespiti için görselin orijinal olması şarttır.<br><br>
            <b>3. LENS MANTIĞI:</b><br>
            Görsel eşleştirme sekmesinde, görseldeki unsurları Google Lens veritabanı ile eşleştirerek konum doğrulaması yapabilirsiniz.<br><br>
            <b>4. INSTAGRAM GÜVENLİK:</b><br>
            Sahte hesabınızın banlanmaması için aşırı sorgudan kaçının.<br><br>
            <hr>
            <i>DVNM OSINT - Dark Edition</i>
        """)

        bottom_horizontal_layout.addWidget(self.result_area, 7)
        bottom_horizontal_layout.addWidget(self.info_panel, 3)

        standart_layout.addWidget(user_input_group)
        standart_layout.addLayout(category_layout)
        standart_layout.addLayout(button_layout)
        standart_layout.addWidget(self.progress_bar)
        standart_layout.addLayout(bottom_horizontal_layout)
        standart_tarama_sekmesi.setLayout(standart_layout)

        # --- 5. SEKME: GÜNCELLEME VE SİSTEM ---
        self.update_sekmesi = QWidget()
        self.setup_update_tab()

        # --- SEKME YÖNETİCİSİ (TAB WIDGET) ---
        self.tabs = QTabWidget()
        self.tabs.addTab(standart_tarama_sekmesi, "Çoklu Dork/Hızlı Tarama")
        
        try:
            self.tabs.addTab(InstagramDerinAnaliz(), "Instagram Derin Analiz")
            self.tabs.addTab(ExifKonumAnalizi(), "EXIF (Konum Çıkarıcı)")
            self.tabs.addTab(VisualImageSearch(), "Görsel Eşleştirme (Dedektif)")
        except NameError:
            pass
            
        self.tabs.addTab(self.update_sekmesi, "⚙️ Sistem & Güncelleme")

        # Ana Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.setFixedSize(850, 750)

    # ==========================================
    # GÜNCELLEME SEKME FONKSİYONLARI (MANUEL KONTROL İÇİN)
    # ==========================================
    def setup_update_tab(self):
        layout = QVBoxLayout()
        
        info_group = QGroupBox("Sistem ve Sürüm Bilgisi")
        info_layout = QVBoxLayout()
        self.lbl_current_version = QLabel(f"Mevcut Sürüm: v{self.CURRENT_VERSION}")
        self.lbl_current_version.setStyleSheet("font-size: 14px; color: #1db954; font-weight: bold;")
        self.lbl_new_version = QLabel("Durum: Güncel")
        self.lbl_new_version.setStyleSheet("font-size: 14px; color: #e0e0e0;")
        
        info_layout.addWidget(self.lbl_current_version)
        info_layout.addWidget(self.lbl_new_version)
        info_group.setLayout(info_layout)
        
        self.changelog_area = QTextBrowser()
        self.changelog_area.setPlaceholderText("Uygulamanız ilk açılışta güncellemeleri otomatik kontrol eder.\n\nDilerseniz manuel olarak da kontrol edebilirsiniz.")
        
        self.update_progress = QProgressBar()
        self.update_progress.hide()
        
        btn_layout = QHBoxLayout()
        self.btn_check_update = QPushButton("🔄 Manuel Kontrol Et")
        self.btn_check_update.clicked.connect(self.start_check_update)
        
        self.btn_download_update = QPushButton("⬇️ Şimdi Yükle ve Başlat")
        self.btn_download_update.setEnabled(False)
        self.btn_download_update.clicked.connect(self.start_download_update)
        
        btn_layout.addWidget(self.btn_check_update)
        btn_layout.addWidget(self.btn_download_update)
        
        layout.addWidget(info_group)
        layout.addWidget(QLabel("📝 Sürüm Notları:"))
        layout.addWidget(self.changelog_area)
        layout.addWidget(self.update_progress)
        layout.addLayout(btn_layout)
        
        self.update_sekmesi.setLayout(layout)

    @asyncSlot()
    async def start_check_update(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Kontrol Ediliyor...")
        self.changelog_area.setText("Sunucuya bağlanılıyor...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.UPDATE_JSON_URL, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        remote_version = data.get("version")
                        self.download_url = data.get("url")
                        changelog = data.get("changelog", "Sürüm notu bulunamadı.")
                        
                        remote_v_tuple = tuple(map(int, remote_version.replace('v', '').split('.')))
                        current_v_tuple = tuple(map(int, self.CURRENT_VERSION.replace('v', '').split('.')))
                        
                        if remote_v_tuple > current_v_tuple:
                            self.lbl_new_version.setText(f"Durum: Yeni sürüm bulundu! (v{remote_version})")
                            self.lbl_new_version.setStyleSheet("font-size: 14px; color: #f39c12; font-weight: bold;")
                            self.changelog_area.setHtml(f"<b style='color:#1db954;'>YENİLİKLER v{remote_version}:</b><br><br>{changelog}")
                            self.btn_download_update.setEnabled(True)
                        else:
                            self.lbl_new_version.setText("Durum: En güncel sürümü kullanıyorsunuz.")
                            self.changelog_area.setText("Sisteminiz güncel. Herhangi bir aksiyona gerek yok.")
                    else:
                        self.changelog_area.setText("Bağlantı hatası: Sunucu yanıt vermedi.")
        except Exception as e:
            self.changelog_area.setText(f"Sunucuya ulaşılamadı. Hata: {str(e)}")
            
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔄 Manuel Kontrol Et")

    @asyncSlot()
    async def start_download_update(self):
        if not hasattr(self, 'download_url'): return
        
        # Manuel sekmeden tetiklendiğinde artık "Nereye Kaydedeyim?" demez, otomatik günceller.
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            save_path = os.path.join(base_dir, "dvnm_update_temp.exe")
        else:
            save_path = "dvnm_update_temp.exe"

        self.btn_download_update.setEnabled(False)
        self.update_progress.show()
        self.update_progress.setValue(0)
        self.changelog_area.append("<br><span style='color:#f39c12;'>İndirme başlatılıyor... Lütfen bekleyin.</span>")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.download_url) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded_size = 0
                        
                        async with aiofiles.open(save_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(1024 * 64): 
                                await f.write(chunk)
                                downloaded_size += len(chunk)
                                if total_size:
                                    percent = int((downloaded_size / total_size) * 100)
                                    self.update_progress.setValue(percent)
                                    
                        self.changelog_area.append("<br><span style='color:#1db954;'>✅ İndirme tamamlandı! Uygulama kendi kendini yeniden başlatıyor...</span>")
                        await asyncio.sleep(2)
                        
                        if getattr(sys, 'frozen', False):
                            create_and_run_updater(save_path)
                        else:
                            QMessageBox.information(self, "IDE Modu", "İndirme bitti ancak IDE'de çalışıyorsunuz. Otomatik yeniden başlatma kapalı.")
                    else:
                        self.changelog_area.append(f"<br>İndirme başarısız! HTTP Kod: {response.status}")
        except Exception as e:
            self.changelog_area.append(f"<br><span style='color:#ff3333;'>İndirme hatası: {str(e)}</span>")
            
        self.btn_download_update.setEnabled(True)

    # ==========================================
    # TARAMA FONKSİYONLARI (STANDART)
    # ==========================================
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

        headers = {'User-Agent': 'Mozilla/5.0'}
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
# ÇALIŞTIRMA KISMI (Buraya Dokunma)
# ==========================================
if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # 1. Ana uygulamayı yarat ama gösterme!
        dvnm = DVNM_OSINT_Uygulama()
        
        # 2. Splash (Açılış) Ekranını Yarat ve Göster
        splash_path = resource_path("load.png")
        splash = CustomSplashScreen(splash_path)
        splash.show()
        
        # 3. Arka plan kontrolünü (ve varsa indirmeyi) başlat
        asyncio.ensure_future(check_startup_update(splash, dvnm))
        
        # 4. Döngüyü çalıştır
        with loop:
            loop.run_forever()
            
    except Exception as e:
        print("\n[!!!] KRİTİK BİR HATA YAKALANDI [!!!]")
        traceback.print_exc()
        input("Çıkış için Enter'a basın...")
