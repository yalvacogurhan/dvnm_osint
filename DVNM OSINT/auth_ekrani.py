import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QMessageBox)
from PyQt5.QtCore import Qt
from supabase import create_client, Client

# --- DİKKAT: SUPABASE BİLGİLERİNİ BURAYA GİR ---
SUPABASE_URL = "https://tmmluxkjxooznkyaoshy.supabase.co"
SUPABASE_KEY = "sb_publishable_HL5gQ_HFB9bK1T9902j-3w_je5JfgpF"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase bağlantı hatası: {e}")
    supabase = None

class LoginEkrani(QWidget):
    def __init__(self):
        super().__init__()
        self.giris_basarili = False
        self.user_id = None  
        self.setWindowTitle("DVNM OSINT - Sistem Girişi")
        self.setFixedSize(350, 260)
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #1db954; font-family: 'Segoe UI', Arial; font-weight: bold;}
            QLineEdit { background-color: #1e1e1e; border: 1px solid #333; padding: 10px; border-radius: 5px; color: white;}
            QPushButton { background-color: #1db954; color: black; border-radius: 5px; padding: 10px; font-weight: bold;}
            QPushButton:hover { background-color: #1ed760; }
        """)

        layout = QVBoxLayout()

        self.lbl_baslik = QLabel("DVNM OSINT\nYetkilendirme Gerekli")
        self.lbl_baslik.setAlignment(Qt.AlignCenter)
        self.lbl_baslik.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-posta Adresiniz")
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Şifreniz")
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.btn_giris = QPushButton("GİRİŞ YAP")
        self.btn_kayit = QPushButton("YENİ KAYIT OL")
        self.btn_kayit.setStyleSheet("background-color: #333; color: white;")

        self.btn_giris.clicked.connect(self.giris_yap)
        self.btn_kayit.clicked.connect(self.kayit_ol)

        layout.addWidget(self.lbl_baslik)
        layout.addWidget(self.email_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.btn_giris)
        layout.addWidget(self.btn_kayit)

        self.setLayout(layout)

    def giris_yap(self):
        if not supabase:
            QMessageBox.critical(self, "Kritik Hata", "Supabase bağlantısı kurulamadı. Lütfen API anahtarlarını kontrol edin.")
            return

        email = self.email_input.text().strip()
        password = self.pass_input.text().strip()

        try:
            self.btn_giris.setText("Giriş Yapılıyor...")
            self.btn_giris.setEnabled(False)
            QApplication.processEvents()

            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            self.user_id = response.user.id  
            self.giris_basarili = True
            
            self.close()
            # YENİ EKLENEN KISIM: Uygulamaya "beklemeyi bırak ve devam et" diyoruz.
            QApplication.instance().exit() 
            
        except Exception as e:
            QMessageBox.warning(self, "Giriş Başarısız", "E-posta veya şifre hatalı!")
            self.btn_giris.setText("GİRİŞ YAP")
            self.btn_giris.setEnabled(True)

    def kayit_ol(self):
        if not supabase: return

        email = self.email_input.text().strip()
        password = self.pass_input.text().strip()

        if len(password) < 6:
            QMessageBox.warning(self, "Hata", "Şifre en az 6 karakter olmalıdır!")
            return

        try:
            self.btn_kayit.setText("Kayıt Olunuyor...")
            self.btn_kayit.setEnabled(False)
            QApplication.processEvents()

            response = supabase.auth.sign_up({"email": email, "password": password})
            QMessageBox.information(self, "Kayıt Başarılı", "Hesabınız oluşturuldu. Artık giriş yapabilirsiniz.")
        except Exception as e:
            QMessageBox.warning(self, "Kayıt Hatası", f"Bir hata oluştu:\n{str(e)}")
        finally:
            self.btn_kayit.setText("YENİ KAYIT OL")
            self.btn_kayit.setEnabled(True)

    # YENİ EKLENEN KISIM: Pencere "X" ile kapatılırsa arka planda askıda kalmasını engeller
    def closeEvent(self, event):
        QApplication.instance().exit()
        event.accept()
