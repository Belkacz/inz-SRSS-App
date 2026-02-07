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
    def __init__(self, ws_url: str, user_handler: UserHandler,
                 reconnect_delay: float = 5.0, empty_msg_delay:float = 0.1, error_delay: float = 0.5) -> None:
        self.ws_url = ws_url
        self.card_list = []
        self.active = True
        self.connected = False
        
        # Timeouty
        self.reconnect_delay = reconnect_delay
        self.empty_msg_delay = empty_msg_delay
        self.error_delay = error_delay
        
        self.user_handler = user_handler
        self.human_in = False
        
        # Inicjalizuj jako puste listy
        self.users_in = []
        self.users_out = []
        
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)

    def startThread(self):
        self.thread.start()
        
    def _ws_listener(self):
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                print(f"[CardMonitor] Połączono z {self.ws_url}")
                self.connected = True
                
                while self.connected:
                    msg = ws.recv()
                    
                    if not msg:
                        time.sleep(self.empty_msg_delay)
                        continue
                    try:
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
                            print(f"[CardMonitor] Błąd bazy danych: {db_error}", flush=True)
                    except Exception as error:
                        print(f"[CardMonitor] Błąd przetwarzania: {error}", flush=True)
                        time.sleep(self.error_delay)
            except Exception as exception:
                self.users_in, self.users_out = self.user_handler.create_list_in_n_out(
                    self.card_list, [])
                print(f"[CardMonitor] Błąd: {exception}, ponawiam połączenie za {self.reconnect_delay}s...")
                self.connected = False
                time.sleep(self.reconnect_delay)