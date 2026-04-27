import asyncio
import instaloader
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QGroupBox, QTextBrowser, QMessageBox, QCheckBox)
from qasync import asyncSlot

class InstagramDerinAnaliz(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        grup_kutusu = QGroupBox("INSTAGRAM DERİN ANALİZ (FULL OSINT MODÜLÜ)")
        grup_layout = QVBoxLayout()

        self.hedef_input = QLineEdit()
        self.hedef_input.setPlaceholderText("Hedef Kullanıcı Adı (Örn: john_doe)")
        
        self.sahte_hesap_user = QLineEdit()
        self.sahte_hesap_user.setPlaceholderText("Bot Hesap Kullanıcı Adı")
        
        self.sahte_hesap_pass = QLineEdit()
        self.sahte_hesap_pass.setPlaceholderText("Bot Hesap Şifresi")
        self.sahte_hesap_pass.setEchoMode(QLineEdit.Password) 

        grup_layout.addWidget(QLabel("Hedef:"))
        grup_layout.addWidget(self.hedef_input)
        grup_layout.addWidget(QLabel("Yetkilendirme (Bot Hesap):"))
        grup_layout.addWidget(self.sahte_hesap_user)
        grup_layout.addWidget(self.sahte_hesap_pass)
        
        self.cb_propic = QCheckBox("Profil Resmini İndir")
        self.cb_posts = QCheckBox("Tüm Gönderileri (Foto/Video) İndir")
        self.cb_stories = QCheckBox("Hikayeleri İndir")
        self.cb_followers = QCheckBox("Takipçi ve Takip Edilen Listesini Çek (.txt)")
        self.cb_propic.setChecked(True)
        
        grup_layout.addWidget(self.cb_propic)
        grup_layout.addWidget(self.cb_posts)
        grup_layout.addWidget(self.cb_stories)
        grup_layout.addWidget(self.cb_followers)
        grup_kutusu.setLayout(grup_layout)

        self.baslat_btn = QPushButton("ANALİZİ VE İNDİRMEYİ BAŞLAT")
        self.baslat_btn.clicked.connect(self.analizi_baslat)

        self.sonuc_ekrani = QTextBrowser()
        self.sonuc_ekrani.append("<span style='color:#888;'>Sistem Hazır. İndirme dizini: 'indirmeler/'</span>")

        layout.addWidget(grup_kutusu)
        layout.addWidget(self.baslat_btn)
        layout.addWidget(self.sonuc_ekrani)
        self.setLayout(layout)

    def full_osint_islem(self, username, password, target, options):
        L = instaloader.Instaloader(
            download_pictures=True, download_videos=True, download_video_thumbnails=False,
            download_geotags=True, download_comments=True, save_metadata=True
        )
        try:
            L.login(username, password)
            profile = instaloader.Profile.from_username(L.context, target)
            path = f"indirmeler/{target}"
            if not os.path.exists(path):
                os.makedirs(path)

            output = f"<br><b style='color:#1db954;'>[+] ANALİZ BAŞLADI: {target}</b><br>"
            
            if options['propic']:
                L.download_profile(target, profile_pic_only=True)
                output += "<span style='color:#ffffff;'>- Profil resmi indirildi.</span><br>"

            if options['posts']:
                if profile.is_private and not profile.followed_by_viewer:
                    output += "<span style='color:#ff3333;'>- HATA: Profil gizli! Gönderiler indirilemedi.</span><br>"
                else:
                    count = 0
                    for post in profile.get_posts():
                        L.download_post(post, target=path)
                        count += 1
                    output += f"<span style='color:#ffffff;'>- {count} gönderi '{path}' klasörüne indi.</span><br>"

            if options['stories']:
                try:
                    L.download_stories(userids=[profile.userid], filename_target=f"{path}/stories")
                    output += "<span style='color:#ffffff;'>- Varsa aktif hikayeler indirildi.</span><br>"
                except:
                    output += "<span style='color:#ff3333;'>- Hikaye bulunamadı veya indirilemedi.</span><br>"

            if options['followers']:
                if profile.is_private and not profile.followed_by_viewer:
                    output += "<span style='color:#ff3333;'>- HATA: Profil gizli! Takipçi listesi çekilemedi.</span><br>"
                else:
                    output += "<span style='color:#f39c12;'>- Takipçi listeleri çekiliyor...</span><br>"
                    try:
                        with open(f"{path}/{target}_takipciler.txt", "w", encoding="utf-8") as f:
                            f_count = 0
                            for follower in profile.get_followers():
                                f.write(follower.username + "\n")
                                f_count += 1
                                if f_count >= 1000: break
                                
                        with open(f"{path}/{target}_takip_edilenler.txt", "w", encoding="utf-8") as f:
                            fe_count = 0
                            for followee in profile.get_followees():
                                f.write(followee.username + "\n")
                                fe_count += 1
                                if fe_count >= 1000: break

                        output += f"<span style='color:#ffffff;'>- Listeler oluşturuldu.</span><br>"
                    except Exception as e:
                         output += f"<span style='color:#ff3333;'>- Listeler çekilirken sorun: {str(e)}</span><br>"

            output += f"<br><span style='color:#1db954;'><b>TEMEL VERİLER:</b></span><br>Takipçi: {profile.followers} | Takip Edilen: {profile.followees}<br>Biyo: {profile.biography}<br>ID: {profile.userid}<br>"
            return output

        except instaloader.exceptions.BadCredentialsException:
            return "<br><span style='color:#ff3333;'>[HATA] Bot hesabın şifresi veya adı yanlış!</span>"
        except Exception as e:
            return f"<br><span style='color:#ff3333;'>[KRİTİK HATA] {str(e)}</span>"

    @asyncSlot()
    async def analizi_baslat(self):
        hedef = self.hedef_input.text().strip()
        user = self.sahte_hesap_user.text().strip()
        password = self.sahte_hesap_pass.text().strip()

        if not hedef or not user or not password:
            QMessageBox.warning(self, "Hata", "Lütfen tüm bilgileri doldurun!")
            return

        options = {'propic': self.cb_propic.isChecked(), 'posts': self.cb_posts.isChecked(), 'stories': self.cb_stories.isChecked(), 'followers': self.cb_followers.isChecked()}
        self.baslat_btn.setEnabled(False)
        self.sonuc_ekrani.clear()
        self.sonuc_ekrani.append(f"<span style='color:#1db954;'>[>] '{hedef}' taranıyor...</span>")
        
        loop = asyncio.get_event_loop()
        sonuc = await loop.run_in_executor(None, self.full_osint_islem, user, password, hedef, options)

        self.sonuc_ekrani.append(sonuc)
        self.baslat_btn.setEnabled(True)