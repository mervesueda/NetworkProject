import socket
import threading
import sqlite3
from datetime import datetime
from databasefunction.db_handler import (
    add_user, check_login, update_status,
    save_private_message, get_private_history, get_previous_contacts,
    create_or_update_chat_relation, is_chat_accepted, get_user_id_by_nickname, create_chat_request,
    save_general_message, get_general_chat_history
)

host = '127.0.0.1'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

clients = []
user_data = {}           # socket: (id, nickname)
active_private_chats = {}  # socket: active_partner_socket

pending_requests = {}    # target_socket: requester_socket

def broadcast(message, exclude=None):
    for client in clients:
        if client != exclude:
            try:
                client.send(message.encode())
            except:
                clients.remove(client)

def check_chat_relation(user1_id, user2_id):
    conn = sqlite3.connect("db/chat.db")
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM chat_relations
        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
    """, (user1_id, user2_id, user2_id, user1_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def find_user_socket(target_nickname):
    for sock, (_, nick) in user_data.items():
        if nick == target_nickname:
            return sock
    return None

def handle(client):
    logged_in = False
    user_info = None

    while True:
        try:
            message = client.recv(1024).decode().strip()

            # Kullanıcı kaydı
            if message.startswith("REGISTER"):
                try:
                    parts = message.split(" ", 2)
                    if len(parts) != 3:
                        client.send("Hatalı komut. REGISTER <kullanıcı> <şifre>\n".encode())
                        continue
                    _, nick, pwd = parts
                    if add_user(nick, pwd):
                        client.send("Kayıt başarılı\n".encode())
                    else:
                        client.send("Bu kullanıcı zaten var.\n".encode())
                except:
                    client.send("Hatalı komut. REGISTER ali 1234\n".encode())

            # Kullanıcı girişi
            elif message.startswith("LOGIN"):
                try:
                    parts = message.split(" ", 2)
                    if len(parts) != 3:
                        client.send("LOGIN komutu hatalı. LOGIN <kullanıcı> <şifre>\n".encode())
                        continue
                    _, nick, pwd = parts
                    user = check_login(nick, pwd)
                    if user:
                        logged_in = True
                        user_info = user
                        user_data[client] = user_info
                        update_status(user[0], "online")
                        if client not in clients:
                            clients.append(client)

                        client.send(f"Hoş geldin, {nick}.\n".encode())

                        # Genel chat geçmişi
                        history = get_general_chat_history(20)
                        if history:
                            client.send("\n--- Genel Chat Geçmişi ---\n".encode())
                            for sender_id, nickname, msg, time in history:
                                client.send(f"[{time}] {nickname}: {msg}\n".encode())
                            client.send("--- Geçmiş sonu ---\n".encode())

                        # BÜYÜK DEĞİŞİKLİK: Gelen istekleri kontrol et ve gönder
                        conn = sqlite3.connect("db/chat.db")
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT u.nickname
                            FROM chat_relations cr
                            JOIN users u ON cr.user1_id = u.id
                            WHERE cr.user2_id = ? AND cr.accepted = 0
                        """, (user[0],))
                        incoming_requests = cursor.fetchall()
                        conn.close()

                        # Her bir gelen istek için GUI'ye bildirim gönder
                        for (sender_nick,) in incoming_requests:
                            client.send(f"{sender_nick} sana özel sohbet isteği gönderdi\n".encode())

                        client.send(
                            "\nKullanabileceğin komutlar:\n"
                            "- WHO → Şu anda online olan kullanıcıları listeler. Örnek: WHO\n"
                            "- SEND <mesaj> → Genel sohbete mesaj gönderir. Örnek: SEND Merhaba herkese!\n"
                            "- REQUEST <kullanıcı> → Belirtilen kullanıcıya özel sohbet isteği yollar. Örnek: REQUEST ahmet\n"
                            "- ACCEPT <kullanıcı> → Gelen özel sohbet isteğini kabul eder. Örnek: ACCEPT ahmet\n"
                            "- OPEN CHAT <kullanıcı> → Önceden onayladığınız biriyle özel sohbeti başlatır. Örnek: OPEN CHAT ahmet\n"
                            "- PRIVATE SEND <mesaj> → Aktif özel sohbet içindeki kullanıcıya mesaj gönderir. Örnek: PRIVATE SEND selam naber\n"
                            "- CLOSE CHAT → Açık olan özel sohbeti kapatır.\n"
                            "- DISCONNECT → Oturumdan çıkış yapar, ana menüye döner. Bağlantı kapanmaz.\n"
                            "- EXIT → Sistemden tamamen çıkar ve bağlantıyı kapatır.\n".encode()
                        )

                        # Geçmiş chatler
                        contacts = get_previous_contacts(user[0])
                        if contacts:
                            client.send("\nGeçmiş Chatler:\n".encode())
                            for name in contacts:
                                conn = sqlite3.connect("db/chat.db")
                                cursor = conn.cursor()
                                cursor.execute("SELECT status FROM users WHERE nickname = ?", (name,))
                                row = cursor.fetchone()
                                conn.close()
                                durum = "(online)" if row and row[0] == "online" else "(offline)"
                                client.send(f"- {name} {durum}\n".encode())
                        else:
                            client.send("\nHiç özel sohbet yapılmamış.\n".encode())

                    else:
                        client.send("Giriş başarısız.\n".encode())
                except:
                    client.send("LOGIN komutu hatalı.\n".encode())

            # Genel sohbete mesaj gönderme
            elif message.startswith("SEND ") and logged_in:
                content = message[5:]
                sender = user_info[1]
                sender_id = user_info[0]
                timestamp = datetime.now().strftime("%H:%M")

                # Veritabanına kaydet
                save_general_message(sender_id, content)

                # Tüm kullanıcılara mesaj gönder
                full_message = f"[{timestamp}] {sender}: {content}\n"
                for c in clients:
                    try:
                        c.send(full_message.encode())
                    except Exception as e:
                        print(f"[SEND ERROR] {e}")

            # Online kullanıcıları listele
            elif message.strip().upper() == "WHO" and logged_in:
                user_id = user_info[0]
                current_nick = user_info[1]
                conn = sqlite3.connect("db/chat.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT u.nickname
                    FROM chat_relations cr
                    JOIN users u ON (
                        (cr.user1_id = ? AND cr.user2_id = u.id) OR
                        (cr.user2_id = ? AND cr.user1_id = u.id)
                    )
                    WHERE cr.accepted = 1 AND u.status = 'online'
                """, (user_id, user_id))

                friends = cursor.fetchall()
                conn.close()

                seen = set()
                for (nick,) in friends:
                    if nick != current_nick and nick not in seen:
                        client.send(f"- {nick} (online)\n".encode())
                        seen.add(nick)


            # REQUEST Komutunun Son Hali
            elif message.startswith("REQUEST ") and logged_in:
                try:
                    _, target_nick = message.split(" ", 1)
                    target_nick = target_nick.strip()

                    user_id = user_info[0]
                    nickname = user_info[1]

                    print(f"[SERVER DEBUG] {nickname} -> {target_nick} isteği işleniyor")

                    # Hedef kullanıcı var mı?
                    target_id = get_user_id_by_nickname(target_nick)
                    if not target_id:
                        client.send("Kullanıcı bulunamadı.".encode())
                        continue

                    # Zaten arkadaşlar mı?
                    if is_chat_accepted(user_id, target_id):
                        client.send("Zaten arkadaşsınız.".encode())
                        continue

                    # Daha önce istek gönderilmiş mi?
                    conn = sqlite3.connect("db/chat.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                                        SELECT 1 FROM chat_relations
                                        WHERE ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
                                        AND accepted = 0
                                    """, (user_id, target_id, target_id, user_id))
                    existing_request = cursor.fetchone()
                    conn.close()

                    if existing_request:
                        client.send("Zaten bir istek gönderilmiş.".encode())
                        continue

                    # Yeni ilişki oluştur (accepted=False)
                    create_or_update_chat_relation(user_id, target_id, accepted=False)
                    client.send("İstek gönderildi.".encode())

                    print(f"[SERVER DEBUG] Veritabanına kaydedildi: {nickname} -> {target_nick}")

                    # ANLIK BİLDİRİM KISMI
                    target_socket = find_user_socket(target_nick)
                    print(f"[SERVER DEBUG] Socket arama sonucu: {target_socket is not None}")

                    if target_socket:
                        try:
                            mesaj = f"{nickname} sana özel sohbet isteği gönderdi\n"
                            target_socket.send(mesaj.encode())
                            print(f"[SERVER DEBUG] Anlık bildirim gönderildi: {mesaj.strip()}")
                        except Exception as e:
                            print(f"[SERVER ERROR] Anlık bildirim hatası: {e}")
                    else:
                        print(f"[SERVER DEBUG] {target_nick} çevrimdışı veya socket bulunamadı")

                except Exception as e:
                    print(f"[SERVER ERROR] REQUEST işleme hatası: {e}")
                    client.send("İstek işlenirken hata oluştu.".encode())

            # Özel sohbet isteği kabulü
            elif message.startswith("ACCEPT ") and logged_in:
                try:
                    _, requester_nick = message.split(" ", 1)

                    requester_id = get_user_id_by_nickname(requester_nick)
                    if not requester_id:
                        client.send("Kullanıcı bulunamadı.\n".encode())
                        continue

                    # İlişkiyi güncelle
                    create_or_update_chat_relation(user_info[0], requester_id, 1)
                    create_or_update_chat_relation(requester_id, user_info[0], 1)

                    client.send("İstek kabul edildi.\n".encode())

                    # Hedef kullanıcı çevrimiçiyse haber ver
                    target_socket = find_user_socket(requester_nick)
                    if target_socket:
                        target_socket.send(f"{user_info[1]} isteğini kabul etti.".encode())

                except Exception as e:
                    print(f"ACCEPT hatası: {e}")
                    client.send("ACCEPT sırasında bir hata oluştu.\n".encode())

            # İstek reddetme
            elif message.startswith("DECLINE ") and logged_in:
                try:
                    _, requester_nick = message.split(" ", 1)

                    requester_id = get_user_id_by_nickname(requester_nick)
                    if not requester_id:
                        client.send("Kullanıcı bulunamadı.\n".encode())
                        continue

                    # İlişkiyi tamamen sil
                    conn = sqlite3.connect("db/chat.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM chat_relations
                        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                    """, (user_info[0], requester_id, requester_id, user_info[0]))
                    conn.commit()
                    conn.close()

                    client.send(f"{requester_nick} isteğini reddettiniz.\n".encode())

                    # Karşı tarafa mesaj gönder
                    target_socket = find_user_socket(requester_nick)
                    if target_socket:
                        target_socket.send(f"{user_info[1]} isteğini reddetti.".encode())

                except Exception as e:
                    print(f"DECLINE hatası: {e}")
                    client.send("Reddetme sırasında hata oluştu.\n".encode())

            # Arkadaş listesi yükleme
            elif message == "LOAD FRIENDS" and logged_in:
                try:
                    user_id = user_info[0]
                    conn = sqlite3.connect("db/chat.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT u.nickname
                        FROM chat_relations cr
                        JOIN users u ON 
                            (cr.user1_id = ? AND cr.user2_id = u.id)
                            OR (cr.user2_id = ? AND cr.user1_id = u.id)
                        WHERE cr.accepted = 1 AND u.id != ?
                    """, (user_id, user_id, user_id))

                    friends = cursor.fetchall()

                    for (nickname,) in friends:
                        client.send(f"FRIEND {nickname}\n".encode())

                    conn.close()

                except Exception as e:
                    print(f"[SERVER] LOAD FRIENDS hatası: {e}")
                    client.send("Arkadaş listesi alınamadı.\n".encode())

            # Geçmiş özel sohbetleri görme ve yeniden başlatma
            # Geçmiş özel sohbetleri görme ve yeniden başlatma
            elif message.startswith("OPEN CHAT ") and logged_in:
                parts = message.split(" ", 2)
                if len(parts) != 3:
                    client.send("Hatalı kullanım. Örnek: OPEN CHAT ahmet\n".encode())
                    continue
                _, _, target_nick = parts
                target_id = get_user_id_by_nickname(target_nick)
                if not target_id:
                    client.send("Kullanıcı bulunamadı.\n".encode())
                    continue
                if is_chat_accepted(user_info[0], target_id):
                    # String olarak kaydet
                    active_private_chats[client] = target_nick

                    print(f"[SERVER] {user_info[1]} kullanıcısı {target_nick} ile özel sohbet başlattı")

                    # ÖNCE başlatma onayı gönder
                    client.send(f"CHAT_STARTED:{target_nick}\n".encode())

                    # Kısa bir bekleme süresi ver (GUI'nin hazır olması için)
                    import time
                    time.sleep(0.1)

                    # Geçmiş mesajları al
                    history = get_private_history(user_info[0], target_id)

                    # Her mesajı tek tek gönder (GUI'nin parse etmesi için)
                    for sender_id, msg, time in history:
                        sender_name = user_info[1] if sender_id == user_info[0] else target_nick
                        # Özel format kullan ki GUI tanısın
                        client.send(f"HISTORY_MSG:{sender_name}:{msg}:{time}\n".encode())
                        print(f"[SERVER] Geçmiş mesaj gönderildi: {sender_name}: {msg}")

                else:
                    client.send("Bu kullanıcı ile onaylanmış sohbetiniz yok.\n".encode())


                    # Özel mesaj gönderme
            elif message.startswith("PRIVATE SEND ") and logged_in:
                parts = message.split(" ", 2)
                if len(parts) != 3:
                    client.send("Hatalı kullanım. Örnek: PRIVATE SEND mesaj\n".encode())
                    continue
                _, _, content = parts

                # Aktif partner kontrolü
                partner_nick = active_private_chats.get(client)
                if not partner_nick:
                    client.send("Aktif özel sohbet yok. Önce OPEN CHAT kullan.\n".encode())
                    continue

                # Partner'ın ID'sini al
                receiver_id = get_user_id_by_nickname(partner_nick)
                if not receiver_id:
                    client.send("Alıcı bulunamadı.\n".encode())
                    continue

                # Mesajı veritabanına kaydet
                save_private_message(user_info[0], receiver_id, content)

                # Zaman damgası
                timestamp = datetime.now().strftime("%H:%M")

                # Gönderen için onay mesajı (terminal için)
                client.send(f"SENT_OK:{partner_nick}:{content}:{timestamp}\n".encode())
                print(f"[SERVER] Özel mesaj gönderildi: {user_info[1]} -> {partner_nick}: {content}")

                # Alıcıya mesajı gönder (eğer online ise)
                receiver_socket = find_user_socket(partner_nick)
                if receiver_socket:
                    try:
                        # Alıcı için özel format
                        receiver_socket.send(f"PRIVATE_MSG:{user_info[1]}:{content}:{timestamp}\n".encode())
                        print(f"[SERVER] Mesaj alıcıya iletildi: {partner_nick}")
                    except Exception as e:
                        print(f"[SERVER ERROR] Özel mesaj gönderme hatası: {e}")
                else:
                    print(f"[SERVER DEBUG] {partner_nick} çevrimdışı")

            # Chat durumu yenileme
            elif message.strip().upper() == "CHAT DURUM YENILE" and logged_in:
                contacts = get_previous_contacts(user_info[0])
                if contacts:
                    client.send("\nGeçmişte sohbet ettiğiniz kullanıcılar (durumları güncellenmiştir):\n".encode())
                    for name in contacts:
                        conn = sqlite3.connect("db/chat.db")
                        cursor = conn.cursor()
                        cursor.execute("SELECT status FROM users WHERE nickname = ?", (name,))
                        row = cursor.fetchone()
                        conn.close()
                        durum = "(online)" if row and row[0] == "online" else "(offline)"
                        client.send(f"- {name} {durum}\n".encode())
                else:
                    client.send("\nDaha önce özel sohbet yaptığınız bir kullanıcı bulunmamaktadır.\n".encode())

            # Oturumu kapat ama bağlantıyı kesme
            elif message.strip().upper() == "DISCONNECT" and logged_in:
                update_status(user_info[0], "offline")
                client.send("Bağlantı sonlandırıldı. Ana menüye dönüyorsunuz...\n".encode())
                logged_in = False
                user_info = None
                if client in active_private_chats:
                    del active_private_chats[client]

            # Oturum sonlandırma
            elif message.strip().upper() == "EXIT":
                if logged_in:
                    update_status(user_info[0], "offline")
                if client in clients:
                    clients.remove(client)
                if client in user_data:
                    del user_data[client]
                if client in active_private_chats:
                    del active_private_chats[client]
                client.send("Çıkış yapıldı.\n".encode())
                client.close()
                break

            # Genel chat geçmişini gösterme
            elif message.strip().upper() == "HISTORY" and logged_in:
                try:
                    history = get_general_chat_history(20)
                    if history:
                        for sender_id, nickname, msg, time in history:
                            client.send(f"[{time}] {nickname}: {msg}\n".encode())
                    else:
                        client.send("Henüz genel chat'te mesaj yok.\n".encode())
                except Exception as e:
                    print(f"HISTORY hatası: {e}")
                    client.send("Geçmiş yüklenirken hata oluştu.\n".encode())

        except Exception as e:
            print(f"Handle fonksyonunda hata: {e}")
            break

    # Bağlantı kapandığında temizlik
    try:
        if logged_in and user_info:
            update_status(user_info[0], "offline")
        if client in clients:
            clients.remove(client)
        if client in user_data:
            del user_data[client]
        if client in active_private_chats:
            del active_private_chats[client]
        client.close()
    except:
        pass

# Yeni bağlantıları kabul eden sunucu döngüsü
def receive():
    print("[Sunucu başlatıldı] Dinleniyor...")
    while True:
        client, addr = server.accept()
        print(f"Bağlantı geldi: {addr}")
        threading.Thread(target=handle, args=(client,)).start()

receive()