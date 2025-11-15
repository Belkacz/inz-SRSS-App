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
# from ultralytics import YOLO
import cv2
from typing import List
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
    privilage_id_fk: Mapped[int] = mapped_column(Integer, ForeignKey("privilage.id"))

    def __repr__(self) -> str:
        return f"<User {self.first_name} {self.second_name} ({self.card_number})>"

class UserHandler:
    # def __init__(self, db_url: str):
        # self.engine = create_engine(db_url)

    def get_users(self):
        # with Session(self.engine) as session:
        #     return session.query(User).all()
        return [
            User(
                id=1,
                card_number=1111,
                first_name=self.hash_str("Jan"),
                second_name=self.hash_str("Kowalski"),
                email=self.hash_str("jan.kowalski@example.com"),
                supervisor=self.hash_str("Manager1"),
                privilage_id_fk=1
            ),
            User(
                id=2,
                card_number=2222,
                first_name=self.hash_str("Adam"),
                second_name=self.hash_str("Nowak"),
                email=self.hash_str("adam.nowak@example.com"),
                supervisor=self.hash_str("Manager2"),
                privilage_id_fk=2
            ),
        ]
    # def crete_unknow_users(self, card_list, users_list):
    #     found_cards = []
    #     unknown_users = []
    #     for user in users_list:
    #         found_cards.append(user.card_number)
    #     for card in card_list:
    #         if card not in found_cards:
    #             unknown_user = User(
    #                 id=users_list[-1].id+1,
    #                 card_number=card,
    #                 first_name="Unknown",
    #                 second_name="Card",
    #                 email=None,
    #                 supervisor=None,
    #                 privilage_id_fk=None,
    #                 )
    #             unknown_users.append(unknown_user)
    #     return unknown_users

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
        # print(f'users_in : {user_in}')
        return users_in, users_out


class CardMonitor:
    def __init__(self, ws_url: str, user_handler: UserHandler) -> None:
        self.ws_url = ws_url
        # self.frame_queue = queue.Queue(maxsize=1)
        self.thread = threading.Thread(target=self._ws_listener, daemon=True)
        self.card_list = []
        self.active = True
        self.connected = False
        
        self.user_handler = user_handler
        self.human_in = False
        self.users_in = []
        self.users_out = []

    def startThread(self):
        self.thread.start()

    def _ws_listener(self):
        print("[DEBUG] Wątek ws_listener wystartował!", flush=True)
        while self.active:
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                print(f"[CardMonitor] Połączono z {self.ws_url}")
                self.connected = True
                while self.connected:
                    msg = ws.recv()
                    if not msg:
                        continue
                    if msg:
                        try:
                            data = json.loads(msg)
                            cardCounter = data.get('cardCounter')
                            self.card_list = []
                            for key, value in data.items():
                                if re.match(r"card\d+", key) and key != "cardCounter":
                                        self.card_list.append(value)
                            if len(self.card_list) > 0:
                                self.human_in = True
                            else:
                                self.human_in = False
                            db_users = self.user_handler.get_users()
                            self.users_in, self.users_out = self.user_handler.create_list_in_n_out(self.card_list, db_users)
                            print(f"[dane] {data}")
                        except Exception:
                            print(f"[RAW] {msg}")
            except Exception as exeption:
                print(f"[CamMonitor] [BŁĄD] {exeption}, ponawiam połączenie za 5s...")
                self.connected = False
                self.stremed_frame = None
                time.sleep(5)