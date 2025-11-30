import json
import re
import threading
import queue
import time
from typing import Tuple, Dict, Any
import numpy as np
import cv2
import websocket
from flask import Flask, Response
from sqlalchemy import BigInteger, create_engine, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class BaseSQL(DeclarativeBase):
    pass

class User(BaseSQL):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    card_number: Mapped[int] = mapped_column(Integer)
    first_name: Mapped[str] = mapped_column(String(100))
    second_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    supervisor: Mapped[str] = mapped_column(String(255))
    privilage_id_fk: Mapped[int] = mapped_column(Integer, ForeignKey("privilages.id"))

    def __repr__(self) -> str:
        return f"<User {self.first_name} {self.second_name} ({self.card_number})>"

class UserHandler:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def get_users(self):
        with Session(self.engine) as session:
            return session.query(User).all()

    def create_list_in_n_out(self, card_list, users_list):
        users_in = []
        users_out = []
        for user in users_list:
            if user.card_number in card_list:
                users_in.append(user)
            else:
                users_out.append(user)

        users_in_card_list = []
        for user_in in users_in:
            users_in_card_list.append(user_in.card_number)

        for card in card_list:
            if card not in users_in_card_list:
                unknown_user = User(
                    id=None,
                    card_number=card,
                    first_name="Not Registered",
                    second_name="Card",
                    email=None,
                    supervisor=None,
                    privilage_id_fk=None,
                    )
                users_in.append(unknown_user)
        print(f'[CARD MODULE] users_in: {users_in}', flush=True)
        return users_in, users_out


class CardMonitor:
    def __init__(self, ws_url: str, user_handler: UserHandler) -> None:
        self.ws_url = ws_url
        self.card_list = []
        self.active = True
        self.connected = False
        
        self.user_handler = user_handler
        self.human_in = False
        
        self.users_in = []
        self.users_out = []
        
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)

    def startThread(self):
        self.thread.start()

    def _ws_listener(self):
        print("[CardMonitor] Wątek ws_listener wystartował!", flush=True)
        while self.active:
            ws = None
            try:
                print(f"[CardMonitor] Łączę z {self.ws_url}...", flush=True)
                ws = websocket.WebSocket()
                
                # ZMIANA 1: Ustaw timeout na połączeniu
                ws.settimeout(2.0)  # 2 sekundy timeout
                
                ws.connect(self.ws_url)
                print(f"[CardMonitor] ✓ Połączono z {self.ws_url}", flush=True)
                self.connected = True
                
                last_message_time = time.time()
                
                while self.active and self.connected:
                    try:
                        # ZMIANA 2: recv() teraz ma timeout dzięki settimeout()
                        msg = ws.recv()
                        
                        if not msg:
                            continue
                        
                        last_message_time = time.time()
                        
                        try:
                            data = json.loads(msg)
                            print(f"[CardMonitor] Otrzymano: {data}", flush=True)
                            
                            cardCounter = data.get('cardCounter', 0)
                            
                            self.card_list = []
                            for key, value in data.items():
                                if re.match(r"card\d+", key) and key != "cardCounter":
                                    self.card_list.append(value)
                            
                            print(f'[CardMonitor] Lista kart: {self.card_list}', flush=True)
                            
                            if len(self.card_list) > 0:
                                self.human_in = True
                            else:
                                self.human_in = False
                            
                            print(f"[CardMonitor] human_in: {self.human_in}", flush=True)
                            
                            # Pobierz użytkowników z bazy
                            try:
                                db_users = self.user_handler.get_users()
                                print(f"[CardMonitor] Użytkowników w bazie: {len(db_users)}", flush=True)
                                
                                self.users_in, self.users_out = self.user_handler.create_list_in_n_out(
                                    self.card_list, db_users
                                )
                                print(f"[CardMonitor] W środku: {len(self.users_in)}, Na zewnątrz: {len(self.users_out)}", flush=True)
                            except Exception as db_error:
                                print(f"[CardMonitor] BŁĄD bazy danych: {db_error}", flush=True)
                                import traceback
                                traceback.print_exc()
                            
                        except json.JSONDecodeError as e:
                            print(f"[CardMonitor] BŁĄD JSON: {e}", flush=True)
                            print(f"[CardMonitor] RAW: {msg}", flush=True)
                    
                    except websocket.WebSocketTimeoutException:
                        # ZMIANA 3: Timeout jest NORMALNY - nie loguj jako błąd
                        # Sprawdź czy połączenie jeszcze żyje
                        current_time = time.time()
                        if current_time - last_message_time > 30:
                            print(f"[CardMonitor] Brak wiadomości przez 30s, reconnect...", flush=True)
                            break
                        # Kontynuuj pętlę - to normalny timeout
                        continue
                    
                    except Exception as inner_error:
                        print(f"[CardMonitor] Błąd w recv(): {inner_error}", flush=True)
                        import traceback
                        traceback.print_exc()
                        break
                            
            except websocket.WebSocketException as ws_error:
                print(f"[CardMonitor] WebSocket error: {ws_error}", flush=True)
                self.connected = False
                
            except Exception as exception:
                print(f"[CardMonitor] BŁĄD: {exception}", flush=True)
                import traceback
                traceback.print_exc()
                self.connected = False
            
            finally:
                # ZMIANA 4: Zawsze zamknij WebSocket
                if ws:
                    try:
                        ws.close()
                    except:
                        pass
                    ws = None
                
                self.connected = False
                
                if self.active:
                    print("[CardMonitor] Ponawiam połączenie za 5s...", flush=True)
                    time.sleep(5)
        
        print("[CardMonitor] Wątek zakończony", flush=True)