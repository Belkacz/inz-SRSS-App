import json
import re
import threading
import time
import websocket
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
        self.connection_attempts = 0  # NOWE
        
    def startThread(self):
        self.thread.start()

    def _ws_listener(self):
        print("[CardMonitor] Wątek ws_listener wystartował!", flush=True)
        while self.active:
            try:
                # NOWE: Dodaj timeout i retry logic
                self.connection_attempts += 1
                print(f"[CardMonitor] Próba połączenia #{self.connection_attempts}...", flush=True)
                
                ws = websocket.WebSocket()
                ws.settimeout(5.0)  # NOWE: timeout na operacje
                ws.connect(self.ws_url, timeout=10)
                
                print(f"[CardMonitor] ✓ Połączono z {self.ws_url}")
                self.connected = True
                self.connection_attempts = 0  # Reset po sukcesie
                
                while self.connected and self.active:
                    try:
                        msg = ws.recv()  # To teraz ma timeout
                        if not msg:
                            continue
                            
                        data = json.loads(msg)
                        self.card_list = []
                        
                        for key, value in data.items():
                            if re.match(r"card\d+", key) and key != "cardCounter":
                                self.card_list.append(value)
                        
                        self.human_in = len(self.card_list) > 0

                        try:
                            db_users = self.user_handler.get_users()
                            self.users_in, self.users_out = self.user_handler.create_list_in_n_out(
                                self.card_list, db_users
                            )
                        except Exception as db_error:
                            print(f"[CardMonitor][DB ERROR] {db_error}", flush=True)
                            
                    except websocket.WebSocketTimeoutException:
                        # Timeout na recv() - to normalne
                        continue
                    except json.JSONDecodeError as error:
                        print(f"[CardMonitor][JSON ERROR] {error}", flush=True)
                    
            except Exception as exception:
                self.users_in, self.users_out = self.user_handler.create_list_in_n_out(
                    self.card_list, []
                )
                print(f"[CardMonitor] [ERROR] {exception}", flush=True)
                self.connected = False
                
                # Exponential backoff dla reconnect
                wait_time = min(5 * self.connection_attempts, 30)
                print(f"[CardMonitor] Czekam {wait_time}s przed ponowną próbą...", flush=True)
                time.sleep(wait_time)

