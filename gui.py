from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QStackedWidget, QSpacerItem, QSizePolicy, QListWidget, QTabWidget, QTextEdit, QListWidgetItem,
    QScrollArea, QStackedLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot

import socket
import sys
import threading
.mert
class ChatClient:
    def __init__(self, host='127.0.0.1', port=55555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((host, port))
        except ConnectionRefusedError:
            print("Sunucuya bağlanılamadı.")
            sys.exit()
        self.listening = True
        self.messages_callback = None
        self.last_sent_command = None

    def start_listening(self):
        thread = threading.Thread(target=self.receive)
        thread.daemon = True
        thread.start()

    def receive(self):
        buffer = ""
        while self.listening:
            try:
                chunk = self.client.recv(1024).decode('utf-8')
                if chunk:
                    buffer += chunk
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            print(f"[Sunucudan]: {line}")
                            self.messages_callback(line)
            except Exception as e:
                print("Socket receive hatası:", e)
                break

    def send(self, message):
        try:
            self.last_sent_command = message.strip().split()[0].upper()
            self.client.send(message.encode('utf-8'))
        except Exception as e:
            print("Mesaj gönderme hatası:", e)

class LoginRegisterWindow(QWidget):
    server_signal = pyqtSignal(str)

    input_style = """
        QLineEdit {
            background-color: #2C2F33;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            min-height: 36px;
        }
        QLineEdit:focus {
            border: 1px solid #7289DA;
        }
        """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Uygulaması")
        self.setFixedSize(1200, 800)
        self.setStyleSheet("background-color: #0d1b2a; color: white;")

        # --------------------------------------------------
        # UI Oluşumu: önce login/register/chat widget'ları oluştur
        # --------------------------------------------------
        self.username = ""
        self.logged_in=False
        self.stack = QStackedWidget()

        self.login_widget    = self.create_login_widget()
        self.register_widget = self.create_register_widget()
        self.chat_widget     = self.create_chat_widget()

        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.register_widget)
        self.stack.addWidget(self.chat_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        # --------------------------------------------------
        # Socket dinleme: UI tamamen hazır olduktan sonra başlat
        # --------------------------------------------------
        self.client = ChatClient()
        self.server_signal.connect(self.handle_server_message)
        self.client.messages_callback = lambda msg: self.server_signal.emit(msg)
        self.client.start_listening()


    #giriş ekranını oluşturur
    def create_login_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: #1b263b;")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        title = QLabel("Giriş Yap")
        title.setFont(QFont("Arial", 24))
        title.setAlignment(Qt.AlignCenter)

        #kullanıcı adı ve şifre için alanlar
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Kullanıcı Adı")
        self.login_username.setStyleSheet(self.input_style)
        self.login_username.setFixedHeight(36)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Şifre")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setStyleSheet(self.input_style)
        self.login_password.setFixedHeight(36)

        #giriş yap butonu
        login_button = QPushButton("Giriş Yap")
        login_button.setStyleSheet("""
    QPushButton {
        background-color: #7289DA;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5B6EAE;
    }
""")
        login_button.clicked.connect(self.handle_login)

        #kayıt ol butonu
        go_register = QPushButton("Kayıt Ol")
        go_register.setStyleSheet("""
    QPushButton {
        background-color: #7289DA;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5B6EAE;
    }
""")
        go_register.clicked.connect(lambda: self.stack.setCurrentWidget(self.register_widget))

        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(title)
        layout.addWidget(self.login_username)
        layout.addWidget(self.login_password)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)
        btn_layout.addWidget(login_button)
        btn_layout.addWidget(go_register)
        layout.addLayout(btn_layout)
        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget

    #kullanıcı kayıt sayfası
    def create_register_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: #1b263b;")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        title = QLabel("Kayıt Ol")
        title.setFont(QFont("Arial", 24))
        title.setAlignment(Qt.AlignCenter)

        #kullanıcı adı, şifre, şifre onay alanları
        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Kullanıcı Adı")
        self.register_username.setStyleSheet(self.input_style)
        self.register_username.setFixedHeight(36)

        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Şifre")
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_password.setStyleSheet(self.input_style)
        self.register_password.setFixedHeight(36)

        self.register_confirm = QLineEdit()
        self.register_confirm.setPlaceholderText("Şifreyi Onayla")
        self.register_confirm.setEchoMode(QLineEdit.Password)
        self.register_confirm.setStyleSheet(self.input_style)
        self.register_confirm.setFixedHeight(36)

        #kaydı tamamla ve geri dön butonları
        register_button = QPushButton("Kaydı Tamamla")
        register_button.setStyleSheet("""
    QPushButton {
        background-color: #7289DA;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5B6EAE;
    }
""")
        register_button.clicked.connect(self.handle_register)

        go_back = QPushButton("Geri Dön")
        go_back.setStyleSheet("""
    QPushButton {
        background-color: #7289DA;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5B6EAE;
    }
""")
        go_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.login_widget))

        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(title)
        layout.addWidget(self.register_username)
        layout.addWidget(self.register_password)
        layout.addWidget(self.register_confirm)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)
        btn_layout.addWidget(register_button)
        btn_layout.addWidget(go_back)
        layout.addLayout(btn_layout)
        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget


    #sohbet alanı
    def create_chat_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: #0d1b2a; color: white;")
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        #sol panel
        sidebar = QWidget()
        sidebar.setFixedWidth(350)
        sidebar.setStyleSheet("background-color: #1b263b;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(10)

        #kullanıcı arama
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara kullanıcı...")
        self.search_input.setStyleSheet(self.input_style)
        self.search_input.textChanged.connect(self.filter_users)
        side_layout.addWidget(self.search_input)

        #kullanıcı takip butonu
        btn_follow = QPushButton("Takip Et")
        btn_follow.setStyleSheet(
            "QPushButton { background-color: #0077b6; color: white; border: none; border-radius: 6px; padding: 6px; }"
            "QPushButton:hover { background-color: #005f8e; }"
        )
        btn_follow.clicked.connect(self.send_follow_request)
        side_layout.addWidget(btn_follow)

        #takip istekleri alanı
        lbl_reqs = QLabel("TAKİP İSTEKLERİ")
        lbl_reqs.setFont(QFont("Arial", 12, QFont.Bold))
        side_layout.addWidget(lbl_reqs)

        self.request_list = QListWidget()
        self.request_list.setStyleSheet("""
            QListWidget { background: #16213e; border: none; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: #7289DA; }
        """)
        self.request_list.itemClicked.connect(self.handle_request_click)
        side_layout.addWidget(self.request_list, 1)

        #arkadaşlar alanı
        lbl_friends = QLabel("ARKADAŞLAR")
        lbl_friends.setFont(QFont("Arial", 12, QFont.Bold))
        side_layout.addWidget(lbl_friends)

        self.friend_list = QListWidget()
        self.friend_list.setStyleSheet("""
            QListWidget { background-color: #16213e; border: none; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #7289DA; }
        """)
        self.friend_list.itemClicked.connect(self.handle_friend_click)
        side_layout.addWidget(self.friend_list, 1)

        #çevrimiçi kullanıcılar alanı
        lbl_online = QLabel("ÇEVRİMİÇİ KULLANICILAR")
        lbl_online.setFont(QFont("Arial", 12, QFont.Bold))
        side_layout.addWidget(lbl_online)

        self.online_list = QListWidget()
        self.online_list.setStyleSheet("""
            QListWidget { background-color: #16213e; border: none; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #7289DA; }
        """)
        side_layout.addWidget(self.online_list, 1)

        #yenileme butonu
        btn_refresh = QPushButton("Yenile")
        btn_refresh.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; border: none; border-radius: 6px; padding: 6px; }"
            "QPushButton:hover { background-color: #218838; }"
        )
        btn_refresh.clicked.connect(self.load_online_users)
        side_layout.addWidget(btn_refresh)

        main_layout.addWidget(sidebar)

        # SAĞ PANEL
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(10, 10, 10, 10)
        right_panel.setSpacing(10)

        header = QHBoxLayout()
        self.lbl_user = QLabel(f"Hoş geldin, {self.username}")
        self.lbl_user.setFont(QFont("Arial", 14, QFont.Bold))
        header.addWidget(self.lbl_user)
        header.addStretch()
        btn_logout = QPushButton("Çıkış Yap")
        btn_logout.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: white; border: none; border-radius: 6px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #c82333; }"
        )
        btn_logout.clicked.connect(self.handle_disconnect)
        header.addWidget(btn_logout)
        right_panel.addLayout(header)

        # CHAT TABS
        self.chat_tabs = QTabWidget()
        self.chat_tabs.setTabPosition(QTabWidget.North)
        self.chat_tabs.setStyleSheet("""
            QTabBar::tab {
                background: #1b263b;
                color: white;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 14px;
                border: 2px solid transparent;
            }
            QTabBar::tab:selected {
                background: #0d1b2a;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #7289DA;
            }
            QTabWidget::pane {
                background: #0d1b2a;
                border: none;
            }
        """)

        self.chat_tabs.addTab(self.create_general_chat_tab(), "Genel Sohbet")
        self.chat_tabs.addTab(self.create_private_chat_tab(), "Özel Sohbetler")

        right_panel.addWidget(self.chat_tabs, 1)
        main_layout.addLayout(right_panel)

        return widget

    #genel sohbetler
    def create_general_chat_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Baloncukları tutacak alan
        self.general_chat_display_widget = QWidget()
        self.general_chat_layout = QVBoxLayout()
        self.general_chat_layout.setAlignment(Qt.AlignTop)
        self.general_chat_display_widget.setLayout(self.general_chat_layout)

        # Scrollable görünüm
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.general_chat_display_widget)

        # Mesaj yazma alanı
        input_box = QHBoxLayout()
        self.general_input = QLineEdit()
        btn_send = QPushButton("Gönder")
        btn_send.clicked.connect(self.send_general_message)
        input_box.addWidget(self.general_input)
        input_box.addWidget(btn_send)

        # Her şeyi birleştir
        layout.addWidget(scroll)
        layout.addLayout(input_box)

        return widget

    #özel sohbet fonksiyonu

    def open_private_chat(self, item):
        friend = item.text()
        self.active_private_friend = friend
        self.lbl_active_user.setText(friend)

        print(f"[DEBUG] Özel chat açılıyor: {friend}")

        # Önce ekranı temizle
        self.clear_private_chat_display()

        # Yeni layout oluştur ve ata
        self.private_chat_display_layout = QVBoxLayout()
        self.private_chat_display_layout.setAlignment(Qt.AlignTop)
        self.private_chat_display_layout.setContentsMargins(10, 10, 10, 10)
        self.private_chat_display_layout.setSpacing(5)

        self.private_chat_display_widget.setLayout(self.private_chat_display_layout)

        # Chat ekranını göster
        self.private_chat_stack.setCurrentIndex(1)

        # Artık özel chat hazır
        self.private_chat_ready = True

        # Sunucuya "chat ekranını aç" komutunu gönder
        #QTimer.singleShot(100, lambda: self.client.send(f"OPEN CHAT {friend}".encode()))

    #özel sohbet alanını temizlemeye yarar
    def clear_private_chat_display(self):
        """Özel sohbet alanını temizle"""
        if hasattr(self, "private_chat_display_widget"):
            old_layout = self.private_chat_display_widget.layout()
            if old_layout is not None:
                while old_layout.count():
                    child = old_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                # Layout'u widget'tan ayırmak yerine boşaltmak yeterlidir
                # setLayout(None) YAPMA!
                # Eski layout'u sil
                old_layout.deleteLater()

    #özel sohbet tab
    def create_private_chat_tab(self):
        widget = QWidget()
        self.private_chat_stack = QStackedLayout(widget)

        # -----------------------------------------
        # EKRAN 1: Kişi listesi (sohbet edilenler)
        # -----------------------------------------
        list_screen = QWidget()
        list_layout = QVBoxLayout(list_screen)
        list_layout.setContentsMargins(10, 10, 10, 10)

        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                color: white;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px;
            }
            QListWidget::item:selected {
                background-color: #7289DA;
                color: white;
            }
        """)
        self.chat_list_widget.itemClicked.connect(self.open_private_chat)
        list_layout.addWidget(self.chat_list_widget)

        self.private_chat_stack.addWidget(list_screen)

        # -----------------------------------------
        # EKRAN 2: Kişiyle sohbet ekranı
        # -----------------------------------------
        chat_screen = QWidget()
        chat_layout = QVBoxLayout(chat_screen)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(10)

        # Üst panel: Geri tuşu + isim
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("← Geri")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #7289DA;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5B6EAE;
            }
        """)
        self.btn_back.clicked.connect(lambda: self.private_chat_stack.setCurrentIndex(0))
        top_bar.addWidget(self.btn_back)

        self.lbl_active_user = QLabel("")
        self.lbl_active_user.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_active_user)
        chat_layout.addLayout(top_bar)

        # Mesaj geçmişi (scrollable alan)
        self.private_chat_display_widget = QWidget()
        self.private_chat_display_layout = QVBoxLayout()
        self.private_chat_display_layout.setAlignment(Qt.AlignTop)
        self.private_chat_display_widget.setLayout(self.private_chat_display_layout)

        self.private_chat_scroll = QScrollArea()
        self.private_chat_scroll.setWidgetResizable(True)
        self.private_chat_scroll.setWidget(self.private_chat_display_widget)
        self.private_chat_scroll.setStyleSheet("border: none;")
        chat_layout.addWidget(self.private_chat_scroll, 1)

        # Mesaj giriş alanı
        input_box = QHBoxLayout()
        self.private_input = QLineEdit()
        self.private_input.setPlaceholderText("Mesajınızı yazın...")
        self.private_input.setStyleSheet(self.input_style)

        btn_send = QPushButton("Gönder")
        btn_send.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #117a8b;
            }
        """)
        btn_send.clicked.connect(self.send_private_message)

        input_box.addWidget(self.private_input)
        input_box.addWidget(btn_send)
        chat_layout.addLayout(input_box)

        self.private_chat_stack.addWidget(chat_screen)

        return widget

    def handle_friend_click(self, item):
        self.open_private_chat(item)

    # --- Yardımcı metotlar ---



    def filter_users(self, text):
        """
        Arama çubuğuna yazılan metne göre online_list filtresi uygulayın.
        """
        for i in range(self.online_list.count()):
            item = self.online_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def send_follow_request(self):
        target = self.search_input.text().strip()
        print(f"[DEBUG] Takip isteği gönderilmeye çalışılıyor: {target}")

        # Boş giriş
        if not target:
            self.show_message("Hata", "Lütfen takip etmek istediğiniz kullanıcı adını girin.")
            return

        # Kendinize istek atmayın
        if target == self.username:
            self.show_message("Hata", "Kendinize takip isteği gönderemezsiniz.")
            return

        # Sunucuya REQUEST komutu gönder
        print(f"[DEBUG] Sunucuya gönderilen komut: REQUEST {target}")
        self.client.send(f"REQUEST {target}")

        # Input'u temizle
        self.search_input.clear()

        # Kullanıcıya başarı mesajı göster
        self.show_message("Bilgi", f"{target} kullanıcısına takip isteği gönderildi.")

    def load_friends(self):
        print("[DEBUG] LOAD FRIENDS gönderildi")
        self.client.send("LOAD FRIENDS")  # sunucuya komut gönder

    def load_online_users(self):
        if not self.logged_in:
            return
        self.client.send("WHO")
        print("[DEBUG] WHO komutu gönderildi.")

        """Sunucuya WHO komutunu yollayıp gelen listeyi sidebar'a basar."""
        self.client.send("WHO")
        # Mantık: handle_server_message içinde WHO cevabını parse edip
        # self.online_list ve self.request_list güncellersin.

    def handle_search(self):
        self.send_follow_request()

    def handle_request_click(self, item):
        widget = self.request_list.itemWidget(item)
        if widget:
            label = widget.findChild(QLabel)
            if label:
                nickname = label.text().strip()
                self.client.send(f"ACCEPT {nickname}")

    def send_general_message(self):
        msg = self.general_input.text().strip()
        if msg:
            self.client.send(f"SEND {msg}")
            self.general_input.clear()

    def send_private_message(self):
        if not hasattr(self, 'active_private_friend') or not self.active_private_friend:
            self.show_message("Hata", "Aktif özel sohbet yok.")
            return

        msg = self.private_input.text().strip()
        if not msg:
            return

        def do_send():
            self.client.send(f"PRIVATE SEND {msg}")
            self.private_input.clear()
            timestamp = datetime.now().strftime("%H:%M")
            self.add_message_bubble(
                self.private_chat_display_layout,
                f"[{timestamp}] {msg}",
                True
            )
            QApplication.processEvents()
            self.private_chat_scroll.verticalScrollBar().setValue(
                self.private_chat_scroll.verticalScrollBar().maximum()
            )

        if hasattr(self, "private_chat_display_layout") and self.private_chat_display_layout:
            do_send()
        else:
            QTimer.singleShot(300, do_send)

    def handle_disconnect(self):
        # Sunucuya çıkış bildir
        self.private_chat_stack.setCurrentIndex(0)
        try:
            self.client.send("DISCONNECT")
        except:
            pass  # Bağlantı zaten kesilmiş olabilir

        # Soket bağlantısını kapat
        try:
            self.client.client.close()
        except:
            pass

        self.client.listening = False

        # GUI temizliği
        self.login_username.clear()
        self.login_password.clear()
        self.general_input.clear()
        self.private_input.clear()
        self.search_input.clear()
        self.online_list.clear()
        self.request_list.clear()
        self.friend_list.clear()
        self.chat_list_widget.clear()
        self.username = ""
        self.logged_in = False

        while self.general_chat_layout.count():
            child = self.general_chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.clear_private_chat_display()

        self.stack.setCurrentWidget(self.login_widget)

    def handle_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        if not username or not password:
            self.show_message("Hata", "Boş alan bırakmayınız.")
            return

        self.username = username

        # Önce varsa eski socketi kapat
        try:
            self.client.client.close()
            self.client.listening = False
        except:
            pass

        # Eski sinyali bağlantıdan kopar
        try:
            self.server_signal.disconnect()
        except:
            pass

        # Yeni bağlantı başlat
        self.client = ChatClient()
        self.server_signal.connect(self.handle_server_message)
        self.client.messages_callback = lambda msg: self.server_signal.emit(msg)
        self.client.start_listening()

        self.client.send(f"LOGIN {username} {password}")

    def handle_register(self):
        username = self.register_username.text().strip()
        password = self.register_password.text().strip()
        confirm = self.register_confirm.text().strip()

        if not username or not password or not confirm:
            self.show_message("Hata", "Tüm alanları doldurun.")
            return
        if password != confirm:
            self.show_message("Hata", "Şifreler eşleşmiyor.")
            return

        self.client.send(f"REGISTER {username} {password}")
        self.private_chat_stack.setCurrentIndex(0)

    def add_request_item(self, sender):
        for i in range(self.request_list.count()):
            widget = self.request_list.itemWidget(self.request_list.item(i))
            if widget:
                label = widget.findChild(QLabel)
                if label and label.text() == sender:
                    return

        item_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)  # butonlar arası boşluk
        item_widget.setMinimumWidth(240)  # genişlik garantisi
        item_widget.setMinimumHeight(60)  # ← Yükseklik garantisi

        label = QLabel(sender)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        btn_accept = QPushButton("✔")
        btn_decline = QPushButton("✖")

        btn_accept.setFixedSize(30, 30)
        btn_decline.setFixedSize(30, 30)

        # Kabul et butonuna basınca sunucuya ACCEPT <kullanıcı> komutu gönder
        btn_accept.clicked.connect(lambda: self.client.send(f"ACCEPT {sender}"))

        # Reddet butonuna basınca bu öğeyi listeden çıkar
        def handle_decline(self, sender, widget):
            self.client.send(f"DECLINE {sender}")
            self.remove_request_item(widget)

        layout.addWidget(label)
        layout.addWidget(btn_accept)
        layout.addWidget(btn_decline)

        item_widget.setLayout(layout)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())

        self.request_list.addItem(item)
        self.request_list.setItemWidget(item, item_widget)

    def remove_request_item(self, widget):
        for i in range(self.request_list.count()):
            if self.request_list.itemWidget(self.request_list.item(i)) == widget:
                self.request_list.takeItem(i)
                break

    @pyqtSlot(str)
    def handle_server_message(self, raw):
        print(f"[DEBUG GUI] Gelen mesaj: '{raw}'")
        msg = raw.strip()
        lower = msg.lower()

        # 1) GİRİŞ ÖNCESİ KONTROLÜ
        if not self.logged_in:
            if "kayıt başarılı" in lower:
                self.show_message("Bilgi", "Kayıt başarılı! Giriş yapabilirsiniz.")
                self.stack.setCurrentWidget(self.login_widget)

            elif "zaten var" in lower:
                self.show_message("Hata", "Bu kullanıcı adı zaten alınmış.")

            elif "giriş başarısız" in lower:
                self.show_message("Hata", "Kullanıcı adı veya şifre hatalı.")
                self.stack.setCurrentWidget(self.login_widget)

            elif "hoş geldin" in lower:
                self.show_message("Bilgi", "Giriş başarılı!")
                self.stack.setCurrentWidget(self.chat_widget)
                self.logged_in = True
                self.lbl_user.setText(f"Hoş geldin, {self.username}")

                # Listeleri temizle ve yeniden başlat
                self.friend_list.clear()
                self.chat_list_widget.clear()
                self._friend_list_initialized = False

                # Online kullanıcıları ve arkadaşları yükle
                self.load_online_users()

                # Biraz gecikme ile arkadaş listesini yükle
                QTimer.singleShot(500, self.load_friends)

        # ► Takip isteği başarıyla iletildiyse
        if raw.startswith("İstek gönderildi"):
            self.show_message("Başarılı", "Takip isteğiniz alındı.")
            return

                # Geçmiş mesaj formatı
        if raw.startswith("PRIVATE_MSG:"):
            parts = raw.split(":", 3)
            if len(parts) == 4:
                _, sender, message, time = parts
                is_own = (sender.strip() == self.username)

                def append():
                    if hasattr(self, "private_chat_display_layout") and self.private_chat_display_layout:
                        self.add_message_bubble(
                            self.private_chat_display_layout,
                            f"[{time}] {message}",
                            is_own
                        )
                        QApplication.processEvents()
                        self.private_chat_scroll.verticalScrollBar().setValue(
                            self.private_chat_scroll.verticalScrollBar().maximum()
                        )

                if hasattr(self, "private_chat_display_layout") and self.private_chat_display_layout:
                    append()
                else:
                    QTimer.singleShot(300, append)
            return

        # Chat başlatma onayı
        if raw.startswith("CHAT_STARTED:"):
            target = raw.split(":", 1)[1]
            print(f"[DEBUG] Chat başlatıldı: {target}")
            self.private_chat_ready = True

        # Zaten arkadaşsınızsa
        if "zaten arkadaşsınız" in lower:
            self.show_message("Bilgi", "Bu kullanıcı zaten arkadaş listenizde.")
            return

        # Zaten istek gönderilmişse
        if "zaten bir istek gönderilmiş" in lower:
            self.show_message("Bilgi", "Bu kullanıcıya zaten bir istek göndermişsiniz.")
            return

        if raw.startswith("HISTORY_MSG:"):
            parts = raw.split(":", 3)  # PRIVATE_MSG:sender:message:time
            if len(parts) == 4:
                _, sender, message, time = parts

                print(f"[DEBUG] Yeni özel mesaj alındı: {sender}: {message}")

                # Eğer özel chat ekranındaysak ve doğru kişiden geliyorsa
                if (hasattr(self, "active_private_friend") and
                        self.active_private_friend == sender and
                        hasattr(self, "private_chat_display_layout") and
                        self.private_chat_display_layout is not None):

                    # Mesajı GUI'ye ekle
                    def append_message():
                        self.add_message_bubble(
                            self.private_chat_display_layout,
                            f"[{time}] {message}",
                            is_own
                        )
                        QApplication.processEvents()
                        self.private_chat_scroll.verticalScrollBar().setValue(
                            self.private_chat_scroll.verticalScrollBar().maximum()
                        )

                    # Layout hazır değilse bekletip sonra ekle
                    if hasattr(self, "private_chat_display_layout") and self.private_chat_display_layout:
                        append_message()
                    else:
                        QTimer.singleShot(300, append_message)
                return

        # Gönderilen mesaj onayı
        if raw.startswith("SENT_OK:"):
            parts = raw.split(":", 3)  # SENT_OK:target:message:time
            if len(parts) == 4:
                _, target, message, time = parts
                print(f"[DEBUG] Mesaj gönderme onayı alındı: {target}: {message}")
                # Bu onayı GUI'ye eklemeyin, çünkü send_private_message'da zaten ekliyorsunuz
            return


    # ► Hedef bulunamazsa
        if "kullanıcı bulunamadı" in lower:
            self.show_message("Hata", "Kullanıcı bulunamadı.")
            return

        # ► Kendinize istek atmaya kalktıysa
        if "kendine istek gönderemezsin" in lower:
            self.show_message("Hata", "Kendinize istek gönderemezsiniz.")
            return

        # ► Sunucu tarafından arkadaş listesi yeniden yüklenmesi istenirse
        if raw.strip() == "LOAD_FRIENDS_TRIGGER":
            self.load_friends()
            return

        # ► Eğer istek kabul edildiyse ya da kabul mesajı geldiyse
        if "isteğini kabul etti" in lower:
            self.show_message("Bilgi", msg)
            self.clear_request_item(msg)
            self.load_friends()
            self.load_online_users()
            return

        if "isteğini reddetti" in lower:
            self.show_message("Bilgi", msg)
            self.clear_request_item(msg)
            return

        # FRIEND mesajları için düzeltilmiş kod
        if raw.startswith("FRIEND "):
            nick = raw.replace("FRIEND ", "").strip()
            print(f"[DEBUG] FRIEND mesajı alındı: {nick}")

            # Arkadaş listesi başlatılmamışsa temizle
            if not hasattr(self, "_friend_list_initialized"):
                self.friend_list.clear()
                self.chat_list_widget.clear()
                self._friend_list_initialized = True

            # Arkadaş listesine ekle (eğer yoksa)
            existing_friends = [self.friend_list.item(i).text() for i in range(self.friend_list.count())]
            if nick not in existing_friends:
                self.friend_list.addItem(nick)
                print(f"[DEBUG] Arkadaş listesine eklendi: {nick}")

            # Özel sohbet listesine ekle (eğer yoksa)
            existing_chats = [self.chat_list_widget.item(i).text() for i in range(self.chat_list_widget.count())]
            if nick not in existing_chats:
                self.chat_list_widget.addItem(nick)
                print(f"[DEBUG] Chat listesine eklendi: {nick}")
            return

        # *** YENİ EKLENENLER ***

        # Özel sohbet geçmişi başlığı
        if "=== " in raw and "ile geçmiş mesajlar ===" in raw:
            print(f"[DEBUG] Geçmiş mesajlar başlığı alındı")
            return

        # Geçmiş mesajlar sonu
        if "=== Geçmiş mesajlar sonu ===" in raw:
            print(f"[DEBUG] Geçmiş mesajlar sonu")
            return

        # Özel sohbet başlatma onayı
        if "ile özel sohbet başlatıldı" in raw:
            print(f"[DEBUG] Özel sohbet başlatma onayı: {raw}")
            return

        # Kendi mesajlarınızın onayı (terminalde görünen formatı)
        if raw.startswith("[") and "] Sen -> " in raw:
            # Format: [10:30] Sen -> ahmet: Merhaba
            print(f"[DEBUG GUI] Kendi mesajının terminalde onayı geldi: {raw}")
            # Bu mesajları GUI'ye eklemeyin çünkü zaten send_private_message'da ekliyorsunuz
            return

        # ~HISTORY~ mesajları
        if raw.startswith("~HISTORY~ "):
            content = raw.split("~HISTORY~ ", 1)[1]
            if ':' not in content:
                print("[HATA] Geçmiş mesaj formatı hatalı:", content)
                return
            sender, msg = content.split(":", 1)
            self.add_message_bubble(
                self.private_chat_display_layout,
                msg.strip(),
                sender.strip() == self.username
            )
            return

        # ► BÜYÜK DEĞİŞİKLİK: Gelen istek bildirimi (anlık)
        if "sana özel sohbet isteği gönderdi" in msg:
            # "kullanici_adi sana özel sohbet isteği gönderdi" formatında
            sender = msg.split()[0]
            self.add_request_item(sender)
            self.show_message("Yeni İstek", f"{sender} size sohbet isteği gönderdi.")
            return

        # Özel sohbet mesajları (gelen mesajlar) - DÜZELTİLMİŞ VERSİYON
        if raw.lower().startswith("(özel)"):
            content = raw.split(")", 1)[1].strip()
            sender = content.split(":", 1)[0].strip()
            message = content.split(":", 1)[1].strip()

            if not hasattr(self, "private_chat_display_layout") or self.private_chat_display_layout is None:
                print("[HATA] Layout yok, mesaj GUI’ye eklenemedi:", message)
                return

            self.add_message_bubble(
                self.private_chat_display_layout,
                message,
                sender == self.username
            )

            QApplication.processEvents()
            self.private_chat_scroll.verticalScrollBar().setValue(
                self.private_chat_scroll.verticalScrollBar().maximum()
            )
            return

        # WHO cevabı: "- kullanıcı (online/offline)" satırları
        if raw.startswith("- "):
            self.online_list.clear()
            seen_users = set()

            for line in raw.splitlines():
                if "(online)" in line:
                    nick = line[2:].split()[0]

                    # Kendi ismini ve tekrarları listeye ekleme
                    if nick != self.username and nick not in seen_users:
                        self.online_list.addItem(nick)
                        seen_users.add(nick)
            return

        # Genel sohbet mesajları
        if raw.startswith("[") and "]" in raw and "] Sen -> " not in raw:
            content = raw.split("]", 1)[1].strip()
            sender = content.split(":", 1)[0]
            message = content.split(":", 1)[1].strip()
            self.add_message_bubble(
                self.general_chat_layout,
                f"{sender.strip()}: {message.strip()}",
                sender.strip() == self.username
            )
            return

        # Diğer (sistem/hata vb.) mesajlar debug için
        print(f"Ignored server message: {msg}")

    def show_message(self, title, message):
        print(f"[UYARI]: {title} - {message}")
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(message)
        box.exec_()

    def add_message_bubble(self, layout, text, align_right=False):
        print(f"[DEBUG] Baloncuk eklendi: {text} / Sağ mı? {align_right}")
        container = QVBoxLayout()
        container.setContentsMargins(10, 5, 10, 5)

        # Mesaj baloncuğu
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setStyleSheet(f"""
            background-color: {'#0077b6' if align_right else '#3a3a3a'};
            color: white;
            padding: 8px 12px;
            border-radius: 12px;
            max-width: 300px;
        """)

        # 🕓 Zaman etiketi
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        date_label = QLabel()
        date_label.setStyleSheet("color: gray; font-size: 10px;")
        date_label.setText(time_str)

        date_label.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)

        # Baloncuk + tarih etiketi
        container.addWidget(bubble)
        container.addWidget(date_label)

        # Sağ/sol hizalama
        wrapper = QHBoxLayout()
        if align_right:
            wrapper.addStretch()
            wrapper.addLayout(container)
        else:
            wrapper.addLayout(container)
            wrapper.addStretch()

        layout.addLayout(wrapper)

    def clear_request_item(self, message):
        """
        İstek kabul edildiğinde ilgili kişiyi istekler listesinden siler.
        """
        for i in range(self.request_list.count()):
            item = self.request_list.item(i)
            widget = self.request_list.itemWidget(item)
            if widget:
                label = widget.findChild(QLabel)
                if label:
                    label_text = label.text()
                    if label_text in message:
                        self.request_list.takeItem(i)
                        break

    def get_chat_history(self, friend):
        # Bu fonksiyon, veritabanından iki kullanıcı arasındaki geçmiş sohbeti alır
        history = []

        # Veritabanından mesaj geçmişini al
        self.client.send(f"GET PRIVATE HISTORY {friend}")

        # Örnek veri (gerçek veritabanı sorgusuyla değiştirilmeli)
        # [(sender, message, time)]
        return [
            ("ahmet", "Merhaba!", "10:05"),
            ("me", "Nasılsın?", "10:06"),
            ("ahmet", "İyi, sen?", "10:07")
        ]


app = QApplication(sys.argv)
window = LoginRegisterWindow()
window.show()
sys.exit(app.exec_())
