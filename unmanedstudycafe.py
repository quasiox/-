#!/usr/bin/env python3
"""
무인 스터디카페 UnmannedStudyCafe
C03팀 기획서 기반 구현
"""
from __future__ import annotations          #mac 사용자를 위한 구문

import hashlib
import os
import sys
import math
from datetime import datetime, timedelta

try:
    from getpass import getpass
except ImportError:
    getpass = input

# ═══════════════════════════════════════════
#  상수
# ═══════════════════════════════════════════
DEFAULT_ROWS = 4
DEFAULT_COLS = 3
SHUTDOWN_SEAT_ID   = 0
SHUTDOWN_TICKET_ID = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "Database")

USER_FILE = os.path.join(DB_DIR, "UserRelation.txt")
TICKET_FILE = os.path.join(DB_DIR, "TicketRelation.txt")
SEAT_FILE = os.path.join(DB_DIR, "SeatRelation.txt")
SESSION_FILE = os.path.join(DB_DIR, "SessionRelation.txt")
RESERVATION_FILE = os.path.join(DB_DIR, "ReservationRelation.txt")
USERTICKET_FILE = os.path.join(DB_DIR, "UserTicketRelation.txt")

# 우선순위 패널티 (단위: 초)
_PENALTY_TICKET = {1: 30 * 60, 2: 0, 3: 90 * 60, 4: 60 * 60}
#                  정기권+30분  시간권  종일권+90분  기간권+60분
_PENALTY_MULTI   = 15 * 60   # 복수 좌석 예약 +15분
_PENALTY_MOVE    = 30 * 60   # 자리 이동 예약 +30분

DT_FMT = "%Y-%m-%d %H:%M"
DT_FMT_SEC = "%Y-%m-%d %H:%M:%S"

ADMIN_ID = "admin"
ADMIN_PW = "qwert1234"
ADMIN_PHONE = "010-0000-0000"

TICKET_TYPE_NAMES = {0: "없음", 1: "정기권", 2: "시간권", 3: "종일권", 4: "기간권"}

DEFAULT_TICKETS = [
    (1, 1, 10, 20000), (2, 1, 30, 58000), (3, 1, 50, 95000), (4, 1, 100, 180000),
    (5, 2, 2, 4500), (6, 2, 3, 6500), (7, 2, 4, 8500), (8, 2, 6, 11500), (9, 2, 8, 15200),
    (10, 3, 1, 12000),
    (11, 4, 7, 55000), (12, 4, 14, 90000), (13, 4, 30, 150000),
    (14, 4, 90, 360000), (15, 4, 180, 600000),
]

SPECIAL_CHARS = set("!@#$%^&*")
ALLOWED_PW_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*")


# ═══════════════════════════════════════════
#  유틸리티
# ═══════════════════════════════════════════
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_input(prompt=""):
    """EOF 발생 시 None 반환"""
    try:
        return input(prompt)
    except EOFError:
        return None

def safe_getpass(prompt=""):
    try:
        return getpass(prompt)
    except EOFError:
        return None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear') 

def fmt_minutes(minutes: int) -> str:
    """분을 'H시간 M분' 형태로"""
    h = minutes // 60
    m = minutes % 60
    return f"{h}시간 {m:02d}분"

def fmt_price(price: int) -> str:
    return f"{price:,}원"

def normalize_phone(raw: str) -> str | None:
    """전화번호를 정규화. 실패 시 None"""
    digits = raw.replace("-", "")
    has_hyphen = "-" in raw

    if has_hyphen:
        parts = raw.split("-")
        if len(parts) != 3:
            return None
        if not all(p.isdigit() for p in parts):
            return None
        first, mid, last = parts
    else:
        if not digits.isdigit():
            return None
        first = digits[:3]
        if len(digits) == 11:
            mid = digits[3:7]
            last = digits[7:11]
        elif len(digits) == 10:
            mid = digits[3:6]
            last = digits[6:10]
        else:
            return None

    if len(first) != 3 or not first.startswith("01"):
        return None
    if first[2] not in "016789":
        return None
    if len(mid) not in (3, 4) or not mid.isdigit():
        return None
    if len(last) != 4 or not last.isdigit():
        return None
    if first == "010" and len(mid) == 3:
        return None

    return f"{first}-{mid}-{last}"

def validate_id(uid: str) -> str | None:
    """아이디 유효성 검사. 오류 메시지 반환, 정상이면 None"""
    if uid == ADMIN_ID:
        return None  # admin은 특수 허용    ?? 회원가입도? 
    if len(uid) < 6 or len(uid) > 20:
        return "아이디는 6자 이상 20자 이하여야 합니다."
    if not uid[0].isalpha() or not uid[0].islower():
        return "아이디의 첫 글자는 영문 소문자여야 합니다."
    for ch in uid:
        if not (ch.islower() or ch.isdigit()):
            return "아이디에는 영문 소문자와 숫자만 사용할 수 있습니다."
    return None

def validate_password(pw: str, uid: str) -> str | None:
    """비밀번호 유효성 검사"""
    if len(pw) < 8 or len(pw) > 20:
        return "비밀번호는 8자 이상 20자 이하여야 합니다."
    for ch in pw:
        if ch not in ALLOWED_PW_CHARS:
            return f"비밀번호에 허용되지 않는 문자 '{ch}'가 포함되어 있습니다."
    categories = 0
    if any(c.isupper() for c in pw):
        categories += 1
    if any(c.islower() for c in pw):
        categories += 1
    if any(c.isdigit() for c in pw):
        categories += 1
    if any(c in SPECIAL_CHARS for c in pw):
        categories += 1
    if categories < 2:
        return "비밀번호는 영문 대소문자, 숫자, 특수문자(!@#$%^&*) 중 2종 이상을 포함해야 합니다."
    if pw == uid:
        return "아이디와 동일한 비밀번호는 사용할 수 없습니다."
    return None
 
def _ticket_priority(ticket_type: int) -> int:
    return {2: 0, 1: 1, 4: 2, 3: 3}.get(ticket_type, 99)

class UserTicketEntry:
    def __init__(self, userticket_id: int, user_id:str, ticket_id: int, is_reserved: bool = False):
        self.userticket_id = userticket_id
        self.user_id = user_id
        self.ticket_id = ticket_id
        self.is_reserved = is_reserved
        
    def to_line(self) -> str:
        return (f"{self.userticket_id}.{self.user_id}."
                f"{self.ticket_id}.{1 if self.is_reserved else 0}")

    @staticmethod
    def from_line(line: str):
        parts = line.split(".")
        if len(parts) != 4:
            return None
        try:
            return UserTicketEntry(
                int(parts[0]), parts[1], int(parts[2]), parts[3] == "1")
        except Exception:
            return None



# ═══════════════════════════════════════════
#  모델 클래스
# ═══════════════════════════════════════════
class User:
    def __init__(self, uid, pw_hash, phone, ticket_id=0, remain=0,
                 start_time=None, away_start=None):
        self.id: str = uid
        self.pw_hash: str = pw_hash
        self.phone: str = phone
        self.ticket_id: int = ticket_id
        self.remain: int = remain
        self.start_time: datetime | None = start_time
        self.away_start: datetime | None = away_start
        self.away_time: int = 0
        self.time_offset = timedelta(0)

    def is_admin(self):
        return self.id == ADMIN_ID

    def is_entered(self, sessions: list) -> bool:
        """매니저가 넘겨준 장부(sessions)를 보고 판단"""
        for s in sessions:
            # Session 클래스의 is_shutdown_record를 User가 모를 수 있으므로 
            # 단순히 admin 0번 좌석인지 확인
            is_shutdown = (s.user_id == "admin" and s.seat_id == 0)
            if not is_shutdown and s.user_id == self.id and s.exit_time is None:
                return True
        return False

    def is_away(self):
        return self.away_start is not None

    def has_ticket(self):
        return self.ticket_id != 0

    def to_line(self):
        st = self.start_time.strftime(DT_FMT) if self.start_time else ""
        aw = self.away_start.strftime(DT_FMT) if self.away_start else ""
        return f"{self.id}.{self.pw_hash}.{self.phone}.{self.ticket_id}.{self.remain}.{st}.{aw}"

    @staticmethod
    def from_line(line):
        parts = line.split(".")
        if len(parts) != 7:
            return None
        try:
            uid = parts[0]
            pw_hash = parts[1]
            phone = parts[2]
            ticket_id = int(parts[3])
            remain = int(parts[4])
            st = datetime.strptime(parts[5], DT_FMT) if parts[5] else None
            aw = datetime.strptime(parts[6], DT_FMT) if parts[6] else None
            return User(uid, pw_hash, phone, ticket_id, remain, st, aw)
        except Exception:
            return None


class Seat:
    def __init__(self, sid: int, user_id: str = "", disabled: bool = False):
        self.id = sid
        self.user_id = user_id
        self.disabled = disabled

    def is_empty(self):
        return self.user_id == "" and not self.disabled

    def to_line(self):
        d = "1" if self.disabled else "0"
        return f"{self.id}.{self.user_id}.{d}"

    @staticmethod
    def from_line(line):
        parts = line.split(".")
        try:
            sid = int(parts[0])
            uid = parts[1] if len(parts) > 1 else ""
            disabled = (parts[2] == "1") if len(parts) > 2 else False
            return Seat(sid, uid, disabled)
        except Exception:
            return None


class Ticket:
    def __init__(self, tid: int, ttype: int, duration: int, price: int):
        self.id = tid
        self.type = ttype
        self.duration = duration
        self.price = price

    def type_name(self):
        return TICKET_TYPE_NAMES.get(self.type, "알수없음")

    def duration_str(self):
        if self.type in (1, 2):
            return f"{self.duration}시간"
        elif self.type == 3:
            return f"{self.duration}일"
        elif self.type == 4:
            return f"{self.duration}일"
        return str(self.duration)

    def to_line(self):
        return f"{self.id}.{self.type}.{self.duration}.{self.price}"

    @staticmethod
    def from_line(line):
        parts = line.split(".")
        if len(parts) != 4:
            return None
        try:
            return Ticket(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        except Exception:
            return None


class Session:
    def __init__(self, user_id, ticket_id, seat_id, enter_time,
                 exit_time=None, usage_min=0):
        self.user_id = user_id
        self.ticket_id = ticket_id
        self.seat_id = seat_id
        self.enter_time: datetime = enter_time
        self.exit_time: datetime | None = exit_time
        self.usage_min: int = usage_min
    

    
    def to_line(self):
        et = self.enter_time.strftime(DT_FMT_SEC)
        xt = self.exit_time.strftime(DT_FMT_SEC) if self.exit_time else ""
        return f"{self.user_id}.{self.ticket_id}.{self.seat_id}.{et}.{xt}.{self.usage_min}"

    @staticmethod
    def from_line(line):
        parts = line.split(".")
        if len(parts) != 6:
            return None
        try:
            uid = parts[0]
            tid = int(parts[1])
            sid = int(parts[2])
            enter = datetime.strptime(parts[3], DT_FMT_SEC)
            exit_t = datetime.strptime(parts[4], DT_FMT_SEC) if parts[4] else None
            usage = int(parts[5])
            return Session(uid, tid, sid, enter, exit_t, usage)
        except Exception:
            return None
    def is_shutdown_record(self):
        """admin + 좌석 0번 세션 = 종료 기록"""
        return self.user_id == ADMIN_ID and self.seat_id == SHUTDOWN_SEAT_ID

class ReservationItem:
    """
    예약 항목 1건.
    status   : 0=waiting, 1=fulfilled, 2=cancelled
    seat_id  : 0=아무자리나, N=특정좌석
    userticket_id : 0=현재 활성 이용권(UserRelation), N=UserTicketRelation 참조
    group_id : 같은 유저가 묶은 복수 좌석 예약 그룹 번호
    """
    def __init__(self, item_id: int, group_id: int, user_id: str,
                 seat_id: int, userticket_id: int,
                 reserved_at: "datetime", status: int = 0):
        self.item_id       = item_id
        self.group_id      = group_id
        self.user_id       = user_id
        self.seat_id       = seat_id
        self.userticket_id = userticket_id
        self.reserved_at   = reserved_at
        self.status        = status

    def is_waiting(self) -> bool:
        return self.status == 0

    def is_extension(self) -> bool:
        """자기 좌석 연장 예약 여부 (UserTicketRelation 이용권 사용)"""
        return self.userticket_id != 0

    def to_line(self) -> str:
        ra = self.reserved_at.strftime(DT_FMT_SEC)
        return (f"{self.item_id}.{self.group_id}.{self.user_id}."
                f"{self.seat_id}.{self.userticket_id}.{ra}.{self.status}")

    @staticmethod
    def from_line(line: str) -> "ReservationItem | None":
        parts = line.split(".")
        if len(parts) != 7:
            return None
        try:
            return ReservationItem(
                item_id       = int(parts[0]),
                group_id      = int(parts[1]),
                user_id       = parts[2],
                seat_id       = int(parts[3]),
                userticket_id = int(parts[4]),
                reserved_at   = datetime.strptime(parts[5], DT_FMT_SEC),
                status        = int(parts[6]),
            )
        except Exception:
            return None



# ═══════════════════════════════════════════
#  메인 프로그램
# ═══════════════════════════════════════════
class StudyCafe:
    def __init__(self):
        self.users: list[User] = []
        self.seats: list[Seat] = []
        self.tickets: list[Ticket] = []
        self.sessions: list[Session] = []
        self.reservations: list[ReservationItem] = []
        self._processing_seats: set = set()   # 재귀 방지용
        self.current_user: User | None = None
        self.running = True
        self.time_offset = timedelta(0)
        self.last_shutdown: datetime | None = None
        self.userticket_entries: list[UserTicketEntry] = []
        self._next_userticket_id: int = 1
        self.rows: int = DEFAULT_ROWS
        self.cols: int = DEFAULT_COLS
        self.total_seats: int = DEFAULT_ROWS * DEFAULT_COLS

    # ─── 파일 I/O ───
    def _ensure_db_dir(self):
        if not os.path.isdir(DB_DIR):
            try:
                os.makedirs(DB_DIR)
            except OSError:
                print("!!! 오류: Database 디렉토리를 생성하지 못했습니다! 프로그램을 종료합니다.")
                sys.exit(1)

    def _init_file(self, filepath, filename):
        if os.path.isfile(filepath):
            if not os.access(filepath, os.R_OK | os.W_OK):
                print(f"!!! 오류: {filename} 파일에 대한 읽기/쓰기 권한이 없습니다!")
                print("    프로그램을 종료합니다.")
                sys.exit(1)
        else:
            print(f"..! 경고: {filename} 파일이 없습니다.")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    pass
                print(f"... 빈 파일을 새로 생성했습니다: {filepath}")
            except OSError:
                print(f"!!! 오류: 파일을 생성하지 못했습니다! 프로그램을 종료합니다.")
                sys.exit(1)

    def _read_lines(self, filepath):
        lines = []
        with open(filepath, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n").rstrip("\r")
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
        return lines

    def init_files(self):
        self._ensure_db_dir()
        for fp, fn in [
            (USER_FILE, "UserRelation.txt"),
            (TICKET_FILE, "TicketRelation.txt"),
            (SEAT_FILE, "SeatRelation.txt"),
            (SESSION_FILE, "SessionRelation.txt"),
            (RESERVATION_FILE, "ReservationRelation.txt"),
            (USERTICKET_FILE, "UserTicketRelation.txt"),
        ]:
            self._init_file(fp, fn)

    def load_data(self):
        # Tickets
        lines = self._read_lines(TICKET_FILE)
        if not lines:
            # 기본 이용권 생성
            self.tickets = [Ticket(t[0], t[1], t[2], t[3]) for t in DEFAULT_TICKETS]
            self._save_tickets()
        else:
            self.tickets = []
            for i, line in enumerate(lines, 1):
                t = Ticket.from_line(line)
                if t is None:
                    print(f"!!! 오류: TicketRelation.txt {i}행 형식 오류: {line}")
                    sys.exit(1)
                self.tickets.append(t)

        # Users
        lines = self._read_lines(USER_FILE)
        self.users = []
        for i, line in enumerate(lines, 1):
            u = User.from_line(line)
            if u is None:
                print(f"!!! 오류: UserRelation.txt {i}행 형식 오류: {line}")
                sys.exit(1)
            self.users.append(u)
        # 이진 탐색(_find_user)을 위해 아이디 기준 정렬 보장
        self.users.sort(key=lambda u: u.id)

        # Seats — 첫 줄: rows, 둘째 줄: cols, 이후: 좌석 데이터
        raw_seat_lines = []
        if os.path.isfile(SEAT_FILE):
            with open(SEAT_FILE, "r", encoding="utf-8") as f:
                raw_seat_lines = [l.rstrip("\n").rstrip("\r") for l in f
                                  if l.strip() and not l.startswith("#")]

        if len(raw_seat_lines) >= 2 and raw_seat_lines[0].isdigit() and raw_seat_lines[1].isdigit():
            self.rows = int(raw_seat_lines[0])
            self.cols = int(raw_seat_lines[1])
            self.total_seats = self.rows * self.cols
            seat_lines = raw_seat_lines[2:]
        else:
            # 파일이 없거나 헤더 없는 기존 파일 → 기본값
            self.rows = DEFAULT_ROWS
            self.cols = DEFAULT_COLS
            self.total_seats = DEFAULT_ROWS * DEFAULT_COLS
            seat_lines = raw_seat_lines  # 혹시 기존 데이터가 있으면 그대로 시도

        if not seat_lines:
            self.seats = [Seat(i + 1) for i in range(self.total_seats)]
            self._save_seats()
        else:
            self.seats = []
            for i, line in enumerate(seat_lines, 1):
                s = Seat.from_line(line)
                if s is None:
                    print(f"!!! 오류: SeatRelation.txt {i + 2}행 형식 오류: {line}")
                    sys.exit(1)
                self.seats.append(s)
            if len(self.seats) != self.total_seats:
                print(f"!!! 오류: SeatRelation.txt 좌석 수({len(self.seats)})가 "
                      f"ROWS×COLS({self.total_seats})와 일치하지 않습니다.")
                sys.exit(1)

        # Sessions
        lines = self._read_lines(SESSION_FILE)
        self.sessions = []
        for i, line in enumerate(lines, 1):
            s = Session.from_line(line)
            if s is None:
                print(f"!!! 오류: SessionRelation.txt {i}행 형식 오류: {line}")
                sys.exit(1)
            self.sessions.append(s)
        
        self.last_shutdown = None
        for s in reversed(self.sessions):
            if s.is_shutdown_record() and s.exit_time is not None:
                    self.last_shutdown = s.exit_time
                    break
        
        if self._find_user(ADMIN_ID) is None:
            admin_user = User(ADMIN_ID, sha256(ADMIN_PW), ADMIN_PHONE)
            idx = self._find_user_index(ADMIN_ID)
            self.users.insert(idx, admin_user)
            self._save_users()
            print(f"... 관리자 계정({ADMIN_ID})이 자동 생성되었습니다.")

        # Reservations
        lines = self._read_lines(RESERVATION_FILE)
        self.reservations = []
        for i, line in enumerate(lines, 1):
            r = ReservationItem.from_line(line)
            if r is None:
                print(f"!!! 오류: ReservationRelation.txt {i}행 형식 오류: {line}")
                sys.exit(1)
            self.reservations.append(r)
        lines = self._read_lines(USERTICKET_FILE)
        self.userticket_entries = []
        for i, line in enumerate(lines, 1):
            e = UserTicketEntry.from_line(line)
            if e is None:
                print(f"!!! 오류: UserTicketRelation.txt {i}행 형식 오류: {line}")
                sys.exit(1)
            self.userticket_entries.append(e)
        if self.userticket_entries:
            self._next_userticket_id = (
                max(e.userticket_id for e in self.userticket_entries)+1)

    def _save_file(self, filepath, items):
        with open(filepath, "w", encoding="utf-8") as f:
            for item in items:
                f.write(item.to_line() + "\n")

    def _save_users(self):
        self._save_file(USER_FILE, self.users)

    def _save_seats(self):
        with open(SEAT_FILE, "w", encoding="utf-8") as f:
            f.write(f"{self.rows}\n{self.cols}\n")
            for seat in self.seats:
                f.write(seat.to_line() + "\n")

    def _save_tickets(self):
        self._save_file(TICKET_FILE, self.tickets)

    def _save_sessions(self):
        self._save_file(SESSION_FILE, self.sessions)
    def _write_shutdown_record(self, now: datetime):
        """종료 시각 기록 + 입장 중인 모든 유저의 remain 갱신"""
        for u in self.users:
            # 입장 중인 유저만 대상 (start_time이 있으면 입장 중)
            if u.start_time and u.ticket_id != 0:
                ticket = self._find_ticket(u.ticket_id)
                if ticket and ticket.type in (1, 2):
                    # 💡 똑똑해진 _calc_deduction이 모든 상황을 판별해서 값을 줍니다.
                    deduction = self._calc_deduction(u, ticket, now)
                    u.remain = max(0, u.remain - deduction)

                    if u.away_start:
                        u.away_start = now
                    

        # 종료 기록 세션 추가 (이 exit_time이 다음 실행 시 last_shutdown이 됨)
        shutdown_session = Session(
            user_id    = ADMIN_ID,
            ticket_id  = SHUTDOWN_TICKET_ID,
            seat_id    = SHUTDOWN_SEAT_ID,
            enter_time = now,
            exit_time  = now, # 💡 이 시각이 다음번 실행 시 기준점이 됨
            usage_min  = 0,
        )
        self.sessions.append(shutdown_session)
        self._save_users()
        self._save_sessions()

    # 종료 기록 세션 추가 (enter = exit = now)
   

    def save_all(self):
        self._save_users()
        self._save_seats()
        self._save_sessions()
        self._save_reservations()
        self._save_userticket()

    # ─── 예약 파일 저장 ───
    def _save_reservations(self):
        self._save_file(RESERVATION_FILE, self.reservations)

    def _save_userticket(self):
        self._save_file(USERTICKET_FILE, self.userticket_entries)

    # ─── ID 생성 ───
    def _next_item_id(self) -> int:
        if not self.reservations:
            return 1
        return max(r.item_id for r in self.reservations) + 1

    def _next_group_id(self) -> int:
        if not self.reservations:
            return 1
        return max(r.group_id for r in self.reservations) + 1

    # ─── 우선순위 점수 계산 ───
    def _calc_priority_score(self, item: ReservationItem) -> float:
        """
        낮을수록 우선순위 높음.
        기본 점수 = reserved_at (epoch 초)
        패널티A   = 이용권 타입 (시간권 유리, 종일권 불리)
        패널티B   = 복수 좌석 예약 +15분
        패널티C   = 자리 이동 예약(착석 중) +30분
        """
        base = item.reserved_at.timestamp()

        user = self._find_user(item.user_id)

        # 패널티A: 이용권 타입
        if user and user.has_ticket():
            ticket = self._find_ticket(user.ticket_id)
            if ticket:
                base += _PENALTY_TICKET.get(ticket.type, 0)

        # 패널티B: 같은 그룹에 waiting 항목이 2개 이상
        group_count = sum(
            1 for r in self.reservations
            if r.user_id == item.user_id
            and r.group_id == item.group_id
            and r.is_waiting()
        )
        if group_count > 1:
            base += _PENALTY_MULTI

        # 패널티C: 현재 다른 좌석 사용 중 (자리 이동 예약)
        if user and user.start_time is not None:
            base += _PENALTY_MOVE

        return base

    # ─── 자동 입장 처리 ───
    def _auto_enter(self, user: "User", seat_id: int,
                    item: ReservationItem, now: "datetime"):
        """예약 자동 입장. 자리 이동 시 기존 좌석 먼저 퇴장."""
        seat = self.seats[seat_id - 1]
        freed_seat_id = None

        # 자리 이동: 기존 좌석 퇴장
        if user.start_time is not None:
            old_seat = self._find_seat_by_user(user.id)
            if old_seat:
                freed_seat_id = old_seat.id
            ticket = self._find_ticket(user.ticket_id)
            if ticket:
                self._do_exit(user, now)
            else:
                user.start_time = None
                user.away_start = None
                if old_seat:
                    old_seat.user_id = ""

            # 퇴장 후 이용권 만료 확인
            if user.remain <=0:
                if not self._activate_next_ticket(user):
                    user.ticket_id = 0
                    user.remain = 0
                    item.status = 2
                    print(f"..! 안내: {user.id}님의 이용권이 만료되어 예약이 취소되었습니다")
                    self.save_all()
                    if freed_seat_id:
                        self._process_seat_available(freed_seat_id, now)
                    return

        # 입장 처리
        seat.user_id    = user.id
        user.start_time = now
        user.away_start = None
        self.sessions.append(Session(user.id, user.ticket_id, seat_id, now))

        # 예약 상태 갱신: 이 항목 fulfilled
        item.status = 1
        # 같은 그룹 나머지 → cancelled
        for r in self.reservations:
            if (r.user_id == item.user_id
                    and r.group_id == item.group_id
                    and r.item_id != item.item_id
                    and r.is_waiting()):
                r.status = 2

        self.save_all()
        print(f"... [예약] {user.id}님이 {seat_id}번 좌석에 자동 입장하였습니다.")

        # 자리 이동으로 비워진 좌석도 처리
        if freed_seat_id:
            self._process_seat_available(freed_seat_id, now)

    # ─── 좌석이 빌 때 예약 처리 ───
    def _process_seat_available(self, seat_id: int, now: "datetime"):
        """
        좌석 seat_id가 비었을 때 호출.
        우선순위 1위 예약자 자동 입장.
        """
        if seat_id in self._processing_seats:
            return
        self._processing_seats.add(seat_id)
        try:
            seat = self.seats[seat_id - 1]
            if not seat.is_empty():
                return

            modified = False

            # 1순위: 연장 예약 (userticket_id != 0) → 무조건 최우선
            for item in self.reservations:
                if (item.is_waiting()
                        and item.seat_id == seat_id
                        and item.is_extension()):
                    user = self._find_user(item.user_id)
                    if user is None:
                        item.status = 2
                        modified = True
                        continue

                    ut_entry = next(
                        (e for e in self.userticket_entries
                         if e.userticket_id == item.userticket_id), None)

                    if ut_entry is None:
                        item.status = 2
                        modified = True
                        continue

                    # 이용권 활성화
                    next_ticket = self._find_ticket(ut_entry.ticket_id)
                    user.ticket_id  = ut_entry.ticket_id
                    user.remain     = self._max_remain(next_ticket) if next_ticket else 0
                    user.away_start = None

                    # 대기열에서 제거
                    self.userticket_entries = [
                        e for e in self.userticket_entries
                        if e.userticket_id != ut_entry.userticket_id]

                    # Time Gap 방지: 직전 세션 exit_time을 새 세션 enter_time으로 사용
                    enter_time = now
                    for s in reversed(self.sessions):
                        if (s.user_id == item.user_id
                                and s.seat_id == seat_id
                                and s.exit_time is not None
                                and not s.is_shutdown_record()):
                            enter_time = s.exit_time
                            break

                    self._auto_enter(user, seat_id, item, enter_time)
                    return

            # 2순위: 일반 대기자 (연장 예약 제외)
            candidates = [
                r for r in self.reservations
                if r.is_waiting()
                and (r.seat_id == seat_id or r.seat_id == 0)
                and not r.is_extension()
            ]

            if not candidates:
                if modified:
                    self._save_reservations()
                return

            candidates.sort(key=self._calc_priority_score)

            for item in candidates:
                user = self._find_user(item.user_id)
                if user is None or not user.has_ticket():
                    item.status = 2
                    modified = True
                    continue
                self._auto_enter(user, seat_id, item, now)
                return

            if modified:
                self._save_reservations()

        finally:
            self._processing_seats.discard(seat_id)

    # ═══════════════════════════════════════════
    #  릴레이션 무결성 검사
    #  순서: 유저 > 티켓 > 좌석 > 세션
    # ═══════════════════════════════════════════
    def _integrity_exit(self, relation: str, line_num: int, reason: str, content: str = ""):
        """무결성 오류 발생 시 위치·사유 출력 후 종료"""
        print(f"!!! 무결성 오류: {relation}Relation.txt {line_num}행")
        print(f"    사유: {reason}")
        if content:
            print(f"    내용: {content}")
        print("    프로그램을 종료합니다.")
        sys.exit(1)

    def verify_integrity(self):
        """릴레이션 무결성 검사 (유저 > 티켓 > 좌석 > 세션 순)"""
        print("... 릴레이션 무결성 검사를 시작합니다.")
        self._verify_user_relation()
        self._verify_ticket_relation()
        self._verify_seat_relation()
        self._verify_session_relation()
        self._verify_reservation_relation()
        self._verify_userticket_relation()
        print("... 무결성 검사가 완료되었습니다.")
     
    def _verify_user_relation(self):
        """유저 릴레이션: 아이디 형식, 비밀번호 존재 여부, 전화번호 형식,
        이용권 아이디 형식, 잔여시간, 사용시점"""
        seen_ids = set()
        seen_phones = set()
        ticket_ids = {t.id for t in self.tickets}
        now = self.get_now()
        seat_user_ids = {s.user_id for s in self.seats if s.user_id}

        for i, u in enumerate(self.users, 1):
            line = u.to_line()

            # 아이디 형식 (admin은 특수 허용)
            if u.id != ADMIN_ID:
                err = validate_id(u.id)
                if err:
                    self._integrity_exit("User", i, f"아이디 형식 오류 - {err}", line)

            # 아이디 중복
            if u.id in seen_ids:
                self._integrity_exit("User", i, f"중복된 아이디: {u.id}", line)
            seen_ids.add(u.id)

            # 비밀번호 존재 여부 + SHA-256 해시 형식(64자리 16진수)
            if not u.pw_hash:
                self._integrity_exit("User", i, "비밀번호 해시가 비어있습니다.", line)
            if len(u.pw_hash) != 64:
                self._integrity_exit("User", i,
                    f"비밀번호 해시 길이 오류 (SHA-256은 64자): {len(u.pw_hash)}자", line)
            if not all(c in "0123456789abcdef" for c in u.pw_hash.lower()):
                self._integrity_exit("User", i,
                    "비밀번호 해시에 16진수가 아닌 문자가 포함됨", line)

            # 전화번호 형식 (정규화 결과와 원본이 동일해야 함)
            if u.phone == ADMIN_PHONE and u.id == ADMIN_ID:
                pass  # admin은 고정 번호 허용
            else:
                norm = normalize_phone(u.phone)
                if norm is None or norm != u.phone:
                    self._integrity_exit("User", i,
                        f"전화번호 형식 오류: {u.phone}", line)
                # 전화번호 중복
                if u.phone in seen_phones:
                    self._integrity_exit("User", i,
                        f"중복된 전화번호: {u.phone}", line)
                seen_phones.add(u.phone)
         

            # 이용권 아이디 형식: 0(미보유) 또는 티켓릴레이션에 존재하는 값
            if u.ticket_id < 0:
                self._integrity_exit("User", i,
                    f"이용권 아이디는 음수일 수 없음: {u.ticket_id}", line)
            if u.ticket_id != 0 and u.ticket_id not in ticket_ids:
                self._integrity_exit("User", i,
                    f"존재하지 않는 이용권 아이디 참조: {u.ticket_id}", line)

            # 잔여시간
            if u.remain < 0:
                self._integrity_exit("User", i,
                    f"잔여시간은 음수일 수 없음: {u.remain}", line)
            if u.ticket_id == 0 and u.remain != 0:
                self._integrity_exit("User", i,
                    f"이용권이 없는데 잔여시간이 있음: remain={u.remain}", line)
                
            self._verify_remain_range(u,i)

            # 사용시점 (start_time, away_start) — from_line에서 형식은 이미 검증됨.
            # 추가로 논리적 일관성을 본다.
            if u.away_start and not u.start_time:
                self._integrity_exit("User", i,
                    "자리비움 시작 시각은 있는데 입장 시각이 없음", line)
            if u.away_start and u.start_time and u.away_start < u.start_time:
                self._integrity_exit("User", i,
                    "자리비움 시작 시각이 입장 시각보다 빠름", line)
            if u.start_time and u.start_time > now:
                self._integrity_exit("User", i,
                    f"사용시점이 현재시각보다 미래임: "
                    f"start_time={u.start_time.strftime(DT_FMT)}, "
                    f"현재시각={now.strftime(DT_FMT)}", line)

            if u.away_start and u.away_start > now:
                self._integrity_exit("User", i,
                    f"자리비움시점이 현재시각보다 미래임: "
                    f"away_start={u.away_start.strftime(DT_FMT)}, "
                    f"현재시각={now.strftime(DT_FMT)}", line)
            if u.away_start and u.ticket_id != 0:
                ticket = self._find_ticket(u.ticket_id)
                if ticket and ticket.type == 1:
                    self._integrity_exit("User", i,
                        f"정기권 사용자에게 자리비움 시각이 기록되어 있음 "
                        f"(정기권은 pause 불가): "
                        f"away_start={u.away_start.strftime(DT_FMT)}",line)
            if not u.start_time and u.id in seat_user_ids:
                self._integrity_exit("User", i,
                        f"입장 중 아니지만 (start_time 없음) 좌석릴레이션에 있음: {u.id}", line)
            if u.start_time and u.id not in seat_user_ids:
                ticket = self._find_ticket(u.ticket_id)
                if ticket and ticket.type in (1, 2):
                    self._integrity_exit("User", i,
                            f"입장 중 이지만 (start_time 있음) 좌석릴레이션에 없음: {u.id}", line)
    
    def _verify_remain_range(self, user: User, i: int):
        """이용권 종류별 잔여시간 가능 범위 검사"""
        if user.ticket_id == 0:
             return  # 이용권 없음 → 이미 위에서 remain==0 검사함

        ticket = self._find_ticket(user.ticket_id)
        if ticket is None:
            return  # 이미 위에서 참조 무결성 검사함

        line = user.to_line()

        if ticket.type == 1:  # 정기권: 0 < remain ≤ duration × 60
            max_remain = ticket.duration * 60
            if not (0 < user.remain <= max_remain):
                self._integrity_exit("User", i,
                    f"정기권 잔여시간 범위 오류: remain={user.remain}분 "
                    f"(허용 범위: 1 ~ {max_remain}분)", line)

        elif ticket.type == 2:  # 시간권: 0 < remain ≤ duration × 60
            max_remain = ticket.duration * 60
            if not (0 < user.remain <= max_remain):
                self._integrity_exit("User", i,
                    f"시간권 잔여시간 범위 오류: remain={user.remain}분 "
                    f"(허용 범위: 1 ~ {max_remain}분)", line)

        elif ticket.type == 3:  # 종일권: remain == 1 고정
            if user.remain != 1:
                self._integrity_exit("User", i,
                    f"종일권 잔여시간 오류: remain={user.remain} "
                    f"(종일권은 반드시 1이어야 함)", line)

        elif ticket.type == 4:  # 기간권: 0 < remain ≤ duration
            if not (0 < user.remain <= ticket.duration):
                self._integrity_exit("User", i,
                    f"기간권 잔여일수 범위 오류: remain={user.remain}일 "
                    f"(허용 범위: 1 ~ {ticket.duration}일)", line)

    def _verify_ticket_relation(self):
        """티켓 릴레이션: 고유번호 형식, 종류, 기간(1 이상), 가격(음수가 아닌 정수)"""
        seen_ids = set()
        for i, t in enumerate(self.tickets, 1):
            line = t.to_line()

            # 고유번호 형식: 1 이상의 자연수 + 유일성
            if t.id < 1:
                self._integrity_exit("Ticket", i,
                    f"이용권 고유번호는 1 이상의 자연수여야 함: {t.id}", line)
            if t.id in seen_ids:
                self._integrity_exit("Ticket", i, f"중복된 고유번호: {t.id}", line)
            seen_ids.add(t.id)

            if t.type not in (1,2,3,4) or t.type != int(t.type):
                self._integrity_exit("Ticket", i,
                    f"이용권 종류는 1~4 중 하나여야 함: {t.type}", line)

            # 기간 (1 이상)
            if t.duration < 1:
                self._integrity_exit("Ticket", i,
                    f"이용권 기간은 1 이상이어야 함: {t.duration}", line)

            # 가격 (음수가 아닌 정수)
            if t.price < 0:
                self._integrity_exit("Ticket", i,
                    f"이용권 가격은 음수일 수 없음: {t.price}", line)


    def _verify_seat_relation(self):
        """좌석 릴레이션: 좌석번호(12 이하 자연수),
        사용자 아이디(유저릴레이션상에 있는지, 이용권이 있는지)"""
        seen_ids = set()
        seen_users = set()
        user_map = {u.id: u for u in self.users}
        session_map = {s.user_id: s for s in self.sessions if not s.is_shutdown_record()}
        num = 0

        for i, s in enumerate(self.seats, 1):
            num += 1
            line = s.to_line()

            # 좌석번호: 1 ≤ id ≤ 12 (self.total_seats)
            if s.id != num:
                self._integrity_exit("Seat", i,
                    f"좌석번호는 {num} 이어야 함: {s.id}", line)
            if s.id > self.total_seats:
                self._integrity_exit("Seat", i,
                    f"좌석번호는 {self.total_seats} 이하여야 함: {s.id}", line)
            if s.id in seen_ids:
                self._integrity_exit("Seat", i, f"중복된 좌석번호: {s.id}", line)
            seen_ids.add(s.id)

            # 사용자 아이디 검증 (빈 좌석은 통과)
            if s.user_id:
                user = user_map.get(s.user_id)
                # 유저릴레이션상에 있는지
                if user is None:
                    self._integrity_exit("Seat", i,
                        f"좌석 사용자가 유저릴레이션에 없음: {s.user_id}", line)
                # 이용권이 있는지
                if not user.has_ticket():
                    self._integrity_exit("Seat", i,
                        f"좌석 사용자 '{s.user_id}'가 이용권을 보유하지 않음", line)
                # 한 유저가 두 좌석을 차지할 수 없음
                if s.user_id in seen_users:
                    self._integrity_exit("Seat", i,
                        f"사용자 '{s.user_id}'가 복수 좌석을 점유 중", line)
                if s.user_id not in session_map:
                    self._integrity_exit("Seat", i,
                        f"사용자 '{s.user_id}'가 세션에 존재하지 않음", line)
                elif session_map[s.user_id].exit_time is not None:
                    self._integrity_exit("Seat", i,
                        f"사용자 '{s.user_id}'가 세션에 존재하지만 좌석을 점유하지 않음", line)
                elif session_map[s.user_id].seat_id != s.id:
                    self._integrity_exit("Seat", i,
                        f"사용자 '{s.user_id}'가 세션에 존재하지만 좌석이 일치하지 않음", line)
                seen_users.add(s.user_id)

    def _verify_session_relation(self):
        """세션 릴레이션: 유저 아이디, 이용권 고유번호(종류 1~len(self.ticket)),
        좌석번호(≤12 + 좌석릴레이션 유저와 일치), 입장/퇴장 일시 형식,
        입장 시각 공백 아님, (현재시각 - 입장일시) > 시간권×2 이면 자동 퇴장,
        이용시간 = 퇴장 - 입장(분) 일치 여부"""
        user_map = {u.id: u for u in self.users}
        ticket_map = {t.id: t for t in self.tickets}
        seat_map = {s.id: s for s in self.seats}
        now = self.get_now()
        modified = False
        active_users = set()

        

        for i, s in enumerate(self.sessions, 1):
            line = s.to_line()
            if s.is_shutdown_record():
                if s.exit_time is None or s.exit_time != s.enter_time:
                    self._integrity_exit("Session", i,
                    "종료 기록 세션 형식 오류 "
                    "(enter_time == exit_time 이어야 함)", line)
                continue  # 나머지 검사 건너뜀
            # 유저가 릴레이션상에 있는지
            user = user_map.get(s.user_id)
            if user is None:
                self._integrity_exit("Session", i,
                    f"유저릴레이션에 존재하지 않는 사용자: {s.user_id}", line)

            # 이용권 고유번호: 티켓릴레이션에 존재
            ticket = ticket_map.get(s.ticket_id)
            if ticket is None:
                self._integrity_exit("Session", i,
                    f"존재하지 않는 이용권 고유번호: {s.ticket_id}", line)
            if ticket.type not in (1,2,3,4):
                self._integrity_exit("Session", i,
                    f"세션의 이용권 종류는 1~{len(self.tickets)} 중 하나여야 함: type={ticket.type}", line)

            # 좌석번호: 12 이하
            if s.seat_id < 1 or s.seat_id > self.total_seats:
                self._integrity_exit("Session", i,
                    f"좌석번호가 범위를 벗어남: {s.seat_id} (1~{self.total_seats})", line)

            # 입장 시각 공백 아님 (from_line이 None 반환하면 load 단계에서 이미 종료,
            # 여기선 방어적 재확인)
            if s.enter_time is None:
                self._integrity_exit("Session", i, "입장 시각이 비어있음", line)

        

            # 진행 중 세션: 좌석릴레이션상의 유저와 동일한지
            if s.exit_time is None:
                if s.user_id in active_users:
                    self._integrity_exit("Session", i,
                        f"유저('{s.user_id}')의 진행 중인 세션(퇴장시간 없음)이 2개 이상 존재합니다.", line)
                active_users.add(s.user_id)
                seat = seat_map.get(s.seat_id)
                if seat is None:
                    self._integrity_exit("Session", i,
                        f"좌석번호 {s.seat_id}이(가) 좌석릴레이션에 없음", line)
                if seat.user_id != s.user_id:
                    self._integrity_exit("Session", i,
                        f"진행 중 세션의 좌석 사용자 불일치: "
                        f"session={s.user_id} vs seat={seat.user_id or '(빈 좌석)'}", line)
            if s.enter_time > now:
                self._integrity_exit("Session", i,
                        f"입장 시각이 현재시각보다 미래임: "
                        f"enter_time={s.enter_time.strftime(DT_FMT_SEC)}", line)
            # 입장/퇴장 순서
            if s.exit_time is not None and s.exit_time < s.enter_time:
                self._integrity_exit("Session", i,
                    "퇴장 시각이 입장 시각보다 빠름", line)

            # (현재시각 - 입장일시) > 시간권 × 2 이면 퇴장일시 기록 (자동 마감)
            if s.exit_time is None and ticket.type == 2:
                limit = timedelta(hours=ticket.duration * 2)
                if (now - s.enter_time) > limit:
                    s.exit_time = s.enter_time + limit
                    s.usage_min = int(
                        (s.exit_time - s.enter_time).total_seconds() // 60)
                    modified = True
                    print(f"..! 안내: SessionRelation.txt {i}행 - "
                          f"시간권 최대 이용시간(×2) 초과로 자동 퇴장 처리됨")

            # 이용시간 = 퇴장 - 입장(분). 일치하지 않으면 오류 후 종료
            if s.exit_time is not None:
                expected = int((s.exit_time - s.enter_time).total_seconds() // 60)
                if s.usage_min != expected:
                    self._integrity_exit("Session", i,
                        f"이용시간 불일치: 저장값={s.usage_min}분, "
                        f"계산값(퇴장-입장)={expected}분", line)


        if modified:
            self._save_sessions()

    def _verify_reservation_relation(self):
        """예약 릴레이션 기본 무결성 검사"""
        user_ids   = {u.id for u in self.users}
        seen_items = set()

        for i, r in enumerate(self.reservations, 1):
            line = r.to_line()

            # item_id 고유성
            if r.item_id in seen_items:
                self._integrity_exit("Reservation", i,
                    f"중복된 item_id: {r.item_id}", line)
            seen_items.add(r.item_id)

            # item_id, group_id 양수
            if r.item_id < 1:
                self._integrity_exit("Reservation", i,
                    f"item_id는 1 이상이어야 함: {r.item_id}", line)
            if r.group_id < 1:
                self._integrity_exit("Reservation", i,
                    f"group_id는 1 이상이어야 함: {r.group_id}", line)

            # user_id 존재
            if r.user_id not in user_ids:
                self._integrity_exit("Reservation", i,
                    f"존재하지 않는 user_id: {r.user_id}", line)

            # seat_id 범위
            if r.seat_id < 0 or r.seat_id > self.total_seats:
                self._integrity_exit("Reservation", i,
                    f"seat_id 범위 오류 (0~{self.total_seats}): {r.seat_id}", line)

            # userticket_id 음수 불가
            if r.userticket_id < 0:
                self._integrity_exit("Reservation", i,
                    f"userticket_id는 0 이상이어야 함: {r.userticket_id}", line)

            # status 유효성
            if r.status not in (0, 1, 2):
                self._integrity_exit("Reservation", i,
                    f"status는 0/1/2 중 하나여야 함: {r.status}", line)

    def _verify_userticket_relation(self):
        user_map   = {u.id: u for u in self.users}
        ticket_ids = {t.id for t in self.tickets}
        seen_ids   = set()
        user_reserved: dict[str, int] = {}

        for i, e in enumerate(self.userticket_entries, 1):
            line = e.to_line()

            if e.userticket_id < 1:
                self._integrity_exit("UserTicket", i,
                    f"userticket_id는 1 이상이어야 함: {e.userticket_id}", line)
            if e.userticket_id in seen_ids:
                self._integrity_exit("UserTicket", i,
                    f"중복된 userticket_id: {e.userticket_id}", line)
            seen_ids.add(e.userticket_id)

            user = user_map.get(e.user_id)
            if user is None:
                self._integrity_exit("UserTicket", i,
                    f"UserRelation에 없는 user_id: {e.user_id}", line)

            if e.ticket_id not in ticket_ids:
                self._integrity_exit("UserTicket", i,
                    f"TicketRelation에 없는 ticket_id: {e.ticket_id}", line)

            if user and not user.has_ticket():
                self._integrity_exit("UserTicket", i,
                    f"현재 이용권이 없는 유저({e.user_id})의 대기 이용권 항목", line)

            if e.is_reserved:
                user_reserved[e.user_id] = user_reserved.get(e.user_id, 0) + 1
                if user_reserved[e.user_id] > 1:
                    self._integrity_exit("UserTicket", i,
                        f"유저({e.user_id})의 is_reserved=True 항목이 2개 이상", line)

    # ─── 사용자 검색 (이진 탐색) ───
    def _find_user(self, uid: str) -> User | None:
        lo, hi = 0, len(self.users) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.users[mid].id == uid:
                return self.users[mid]
            elif self.users[mid].id < uid:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    def _find_user_index(self, uid: str) -> int:
        """Upper bound 위치 반환 (삽입용)"""
        lo, hi = 0, len(self.users)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.users[mid].id <= uid:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _find_ticket(self, tid: int) -> Ticket | None:
        for t in self.tickets:
            if t.id == tid:
                return t
        return None

    def _find_seat_by_user(self, uid: str) -> Seat | None:
        for s in self.seats:
            if s.user_id == uid:
                return s
        return None

    # ─── 이용권 시간 계산 ───
    def _calc_effective_remain(self, user: User, now: datetime = None) -> int:
        """현재 시점 기준 실질 잔여 시간(분) 반환"""
        if now is None:
            now = self.get_now()
        ticket = self._find_ticket(user.ticket_id)
        if ticket is None:
            return 0

        if ticket.type == 1:  # 정기권: 입장 중일 때만 차감
            if user.is_entered(self.sessions):
                elapsed = self._calc_deduction(user, ticket, now)
                return max(0, user.remain - elapsed)
            return user.remain

        elif ticket.type == 2:  # 시간권: 시작 후 계속 차감
            if user.start_time:
                elapsed = self._calc_deduction(user, ticket, now)
                return max(0, user.remain - elapsed + user.away_time)
            return user.remain + user.away_time
            return user.remain

        elif ticket.type == 3:  # 종일권
            return user.remain

        elif ticket.type == 4:  # 기간권
            return user.remain

        return user.remain

    def _calc_deduction(self, user: User, ticket: Ticket, now: datetime = None) -> int:
        """start_time 기준 차감할 분 수 계산"""
        if user.start_time is None:
            return 0

        if now is None:
            now = self.get_now()
        
        calc_start = user.start_time
        if self.last_shutdown and self.last_shutdown > user.start_time:
            calc_start = self.last_shutdown
        
        if calc_start >= now:
            return 0

        if ticket.type == 2 and user.away_start:
            # 시간권 + 자리비움: 절반 차감
            active_end = max(calc_start, user.away_start)
            active_sec = (active_end - calc_start).total_seconds()
            
            # away 구간: active_end 부터 현재(now) 까지
            away_sec = (now - active_end).total_seconds()

            return math.ceil(active_sec / 60) + math.ceil(away_sec / 60 / 2)
        else:
            # 정기권이거나 자리비움 아님: 전체 차감
            elapsed_sec = (now - calc_start).total_seconds()
            return math.ceil(elapsed_sec / 60)

    def _check_expiry(self, user: User, now: datetime = None):
            if now is None:
                now = self.get_now()
            if not user.has_ticket():
                return False

            ticket = self._find_ticket(user.ticket_id)
            if ticket is None:
                user.ticket_id = 0
                user.remain = 0
                return True

            expired = False
            expired_time = None
            if ticket.type in (1, 2):
                eff = self._calc_effective_remain(user, now)
                if eff <= 0:
                    expired = True
                    
                    if user.away_start is None:
                        # 1. 정기권이거나, 자리비움을 한 번도 안 한 시간권 (1:1 정상 속도)
                        expired_time = user.start_time + timedelta(minutes=user.remain)
                    else:
                        # 2. 자리비움 중에 만료된 시간권
                        calc_start = user.start_time
                        if self.last_shutdown and self.last_shutdown > user.start_time:
                            calc_start = self.last_shutdown

                        active_sec = (user.away_start - calc_start).total_seconds()
                        active_min = math.ceil(active_sec / 60)
                        
                        if user.remain <= active_min:
                            expired_time = calc_start + timedelta(minutes=user.remain)
                        else:
                            leftover = user.remain - active_min
                            expired_time = user.away_start + timedelta(minutes=leftover * 2)

            elif ticket.type == 3:
                if user.start_time and user.start_time.date() != now.date():
                    expired_time = user.start_time.replace(hour=23, minute=59, second=59)
                    expired = True

            elif ticket.type == 4:
                if user.start_time:
                    expire_date = user.start_time.date() + timedelta(days=ticket.duration)
                    if now.date() >= expire_date:
                        from datetime import time
                        expired_time = datetime.combine(expire_date-timedelta(days=1), time(23,59,59))
                        expired = True

            if expired:
                for s in reversed(self.sessions):
                    if s.user_id == user.id and s.exit_time is None:
                        s.exit_time = expired_time
                        s.usage_min += math.floor((expired_time - s.enter_time).total_seconds() / 60)
                        break

                if self._activate_next_ticket(user, activation_time=expired_time):
                    next_ticket = self._find_ticket(user.ticket_id)
                    next_name   = next_ticket.type_name() if next_ticket else "알수없음"
                    print(f"..! 안내: 이용권이 만료되어 대기 이용권({next_name})이 "
                          f"자동 활성화되었습니다.")
                    self._save_users()
                    self._save_sessions()
                    self._save_userticket()
                    return False

                user.ticket_id  = 0
                user.remain     = 0
                user.start_time = None
                user.away_start = None
                seat = self._find_seat_by_user(user.id)
                if seat:
                    seat.user_id = ""
                return True
            return False

    # ─── 퇴장 처리 핵심 로직 ───
    def _do_exit(self, user: User, now: "datetime | None" = None) -> tuple[int, int]:
        """퇴장 처리. (이용시간분, 잔여분) 반환"""
        if now is None:
            now = self.get_now()

        ticket = self._find_ticket(user.ticket_id)
        seat = self._find_seat_by_user(user.id)

        deduction = 0
        if ticket and ticket.type == 1:  # 정기권
            deduction = self._calc_deduction(user, ticket, now)
            user.remain = max(0, user.remain - deduction)
            user.start_time = None
        elif ticket and ticket.type == 2:  # 시간권
            deduction = self._calc_deduction(user, ticket, now)
            user.remain = max(0, user.remain - deduction)
            user.start_time = now

        # 종일권/기간권: 별도 차감 없음

        user.away_start = None

        # 좌석 반납 전 — 연장 예약 취소 ("핑퐁" 방지)
        if seat:
            for r in self.reservations:
                if (r.user_id == user.id
                        and r.seat_id == seat.id
                        and r.is_waiting()
                        and r.is_extension()):
                    r.status = 2
                    for e in self.userticket_entries:
                        if e.userticket_id == r.userticket_id:
                            e.is_reserved = False
                            break
            seat.user_id = ""

        # 세션 업데이트
        usage_min = math.floor((now - self._get_session_enter(user)).total_seconds() / 60) \
            if self._get_session_enter(user) else 0
        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None and not s.is_shutdown_record():
                s.exit_time = now
                s.usage_min = usage_min
                break
        self._save_sessions()

        return deduction, user.remain

    

    def _get_session_enter(self, user: User) -> datetime | None:
        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None and not s.is_shutdown_record():
                return s.enter_time
        return None
    
    # ═══════════════════════════════════════════
    #  중복 이용권 핵심 로직
    # ═══════════════════════════════════════════
    def _user_ut_entries(self, user: User) -> list:
        return [e for e in self.userticket_entries if e.user_id == user.id]

    def _has_queue(self, user: User) -> bool:
        return any(e.user_id == user.id for e in self.userticket_entries)

    def _sorted_queue(self, user: User) -> list:
        def key(e):
            t = self._find_ticket(e.ticket_id)
            prio = _ticket_priority(t.type) if t else 99
            return (prio, e.userticket_id)
        return sorted(self._user_ut_entries(user), key=key)

    def _max_remain(self, ticket: Ticket) -> int:
        if ticket.type in (1, 2): return ticket.duration * 60
        elif ticket.type == 3:    return 1
        else:                     return ticket.duration

    def _enqueue_ticket(self, user: User, ticket: Ticket):
        # 이용권 없으면 바로 활성화
        if not user.has_ticket():
            user.ticket_id  = ticket.id
            user.remain     = self._max_remain(ticket)
            user.start_time = None
            user.away_start = None
            return

        cur_ticket = self._find_ticket(user.ticket_id)
        cur_prio   = _ticket_priority(cur_ticket.type) if cur_ticket else 99
        new_prio   = _ticket_priority(ticket.type)
        is_seated  = (user.start_time is not None)

        # 미착석 상태에서만 우선순위 스왑 적용
        # (착석 중에는 현재 이용권이 소진될 때까지 바뀌지 않음)
        if new_prio < cur_prio and not is_seated:
            # 기존 이용권 대기열로 이동
            old_entry = UserTicketEntry(
                self._next_userticket_id, user.id, user.ticket_id, False)
            self._next_userticket_id += 1
            self.userticket_entries.append(old_entry)

            # 새 이용권 활성화
            user.ticket_id  = ticket.id
            user.remain     = self._max_remain(ticket)
            user.start_time = None
            user.away_start = None

            if cur_ticket:
                print(f"    ※ 새로 구매한 {ticket.type_name()}이(가) "
                      f"기존 {cur_ticket.type_name()}보다 우선순위가 높아 "
                      f"현재 이용권으로 설정되었습니다.")
                print(f"    ※ 기존 {cur_ticket.type_name()}은(는) 대기열로 이동되었습니다.")
        else:
            # 착석 중이거나 우선순위 같거나 낮으면 대기열에 추가
            new_entry = UserTicketEntry(
                self._next_userticket_id, user.id, ticket.id, False)
            self._next_userticket_id += 1
            self.userticket_entries.append(new_entry)

    def _activate_next_ticket(self, user: User,
                               activation_time: datetime = None) -> bool:
        candidates = [e for e in self._sorted_queue(user) if not e.is_reserved]
        if not candidates:
            return False

        if activation_time is None:
            activation_time = self.get_now()

        next_entry  = candidates[0]
        next_ticket = self._find_ticket(next_entry.ticket_id)

        user.ticket_id  = next_entry.ticket_id
        user.remain     = self._max_remain(next_ticket) if next_ticket else 0
        user.away_start = None

        self.userticket_entries = [
            e for e in self.userticket_entries
            if e.userticket_id != next_entry.userticket_id]

        seat = self._find_seat_by_user(user.id)
        if seat:
            user.start_time = activation_time          # now → activation_time
            self.sessions.append(
                Session(user.id, user.ticket_id, seat.id, activation_time))
        else:
            user.start_time = None

        return True

    # ─── 프롬프트 ───
    def _prompt(self) -> str:
        if self.current_user:
            return f"선택 [{self.current_user.id}] > "
        return "선택 > "

    def _show_cmds_logged_out(self):
        print("-------------------------------------------------------------------")
        print("명령어군           | 올바른 인자들         | 설명")
        print("-------------------+----------------------+------------------------")
        print("login 로그인       | 없음                 | 로그인합니다")
        print("register 회원가입  | 없음                 | 회원가입을 시작합니다")
        print("help 도움말        | 없거나, 명령어 1개   | 전체/명령어별 도움말")
        print("end 종료           | 없음                 | 프로그램을 종료합니다")
        print("-------------------------------------------------------------------")

    def _show_cmds_logged_in(self):
        print("-------------------------------------------------------------------")
        print("명령어군             | 올바른 인자들       | 설명")
        print("---------------------+--------------------+------------------------")
        print("seat 좌석조회        | 없음               | 전체 좌석 현황을 출력")
        print("enter 입장           | 없음               | 이용권 선택→좌석 배정")
        print("exit 퇴장            | 없음               | 좌석 반납 및 시간 차감")
        print("buy 이용권구매       | 없음               | 이용권 구매")
        print("myinfo 내정보        | 없음               | 계정/이용권/좌석 정보")
        print("admin 관리자         | 없음               | 관리자 전용 메뉴")
        print("logout 로그아웃      | 없음               | 로그아웃")
        print("move 자리이동        | 없음               | 다른 좌석으로 이동")
        print("pause 자리비움       | 없음               | 자리비움 상태로 변경")
        print("resume 자리비움해제  | 없음               | 자리비움 해제")
        print("reserve 예약         | 없음               | 좌석 예약")
        print("myreserv 예약현황    | 없음               | 예약 현황")
        print("cancelreserv 예약취소| 없음               | 예약 취소")
        print("help 도움말          | 없거나, 명령어 1개 | 전체/명령어별 도움말")
        print("end 종료             | 없음               | 프로그램을 종료합니다")
        print("-------------------------------------------------------------------")

    def _show_available_cmds(self):
        if self.current_user:
            self._show_cmds_logged_in()
        else:
            self._show_cmds_logged_out()

    CMDS_ALWAYS = {"help", "end","time"}
    CMDS_LOGGED_OUT = {"login", "register"}
    CMDS_LOGGED_IN = {"seat", "enter", "exit", "buy", "myinfo", "admin",
                       "logout", "pause", "resume", "move", "reserve", "myreserv", "cancelreserv"}
    # 한글 동의어 매핑
    CMD_ALIASES = {
        "도움말": "help", "종료": "end", "로그인": "login", "회원가입": "register",
        "좌석조회": "seat", "입장": "enter", "퇴장": "exit", "이용권구매": "buy",
        "내정보": "myinfo", "관리자": "admin", "로그아웃": "logout",
        "자리이동": "move", "자리비움": "pause", "자리비움해제": "resume",
        "예약": "reserve", "예약현황": "myreserv", "예약취소": "cancelreserv",
    }

    def _available_cmds(self) -> set:
        cmds = set(self.CMDS_ALWAYS)
        if self.current_user:
            cmds |= self.CMDS_LOGGED_IN
        else:
            cmds |= self.CMDS_LOGGED_OUT
        return cmds

    def _resolve_cmd(self, word: str) -> str:
        """한글/영문 명령어를 영문으로 통일"""
        if word in self.CMD_ALIASES:
            return self.CMD_ALIASES[word]
        return word

    # ─── 좌석 출력 ───
    def _print_seats(self):
        now = self.get_now()
        changed = False
        freed_seats = []

        for seat in self.seats:
            if seat.is_empty() or seat.disabled:
                continue
            user = self._find_user(seat.user_id)
            if user is None:
                continue
            seat_id = seat.id           # 만료 처리 전에 기억
            if self._check_expiry(user, now):
                changed = True
                freed_seats.append(seat_id)

        if changed:
            self._save_users()
            self._save_seats()

        # 만료로 빈 좌석에 대해 예약 처리
        for seat_id in freed_seats:
            self._process_seat_available(seat_id, now)

        # ── 좌석 현황 출력 ──
        print("=== 좌석 현황 ===")
        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                idx = r * self.cols + c
                seat = self.seats[idx]
                if seat.disabled:
                    row_str += f"[{seat.id:2d}: 불가  ] "
                elif seat.user_id == "":
                    row_str += f"[{seat.id:2d}:       ] "
                elif self.current_user and seat.user_id == self.current_user.id:
                    row_str += f"[{seat.id:2d}: 내좌석] "
                else:
                    uid = seat.user_id
                    label = uid if len(uid) <= 6 else uid[:4] + "…"
                    row_str += f"[{seat.id:2d}: {label:<6s}] "
            print(row_str)

    # ═══════════════════════════════════════════
    #  명령어 핸들러
    # ═══════════════════════════════════════════

    def cmd_help(self, args: list[str]):
        if len(args) > 1:
            print(".!! 오류: 인자가 너무 많습니다. 명령어를 최대 1개만 입력하세요.")
            return

        if len(args) == 0:
            self._show_available_cmds()
            return

        cmd = self._resolve_cmd(args[0])
        avail = self._available_cmds()
        if cmd not in avail:
            print(f".!! 오류: '{args[0]}'은(는) 현재 상태에서 유효한 명령어가 아닙니다.")
            self._show_available_cmds()
            return

        help_texts = {
            "help": "전체 혹은 특정 명령어별 도움말을 출력합니다.\n동의어: help 도움말\n인자: 없거나, 명령어 1개",
            "end": "프로그램을 즉시 종료합니다.\n동의어: end 종료\n인자: 없음",
            "login": "아이디, 비밀번호를 받아 로그인합니다.\n동의어: login 로그인\n인자: 없음",
            "register": "회원가입 절차를 시작합니다.\n동의어: register 회원가입\n인자: 없음",
            "seat": "전체 좌석 현황을 출력합니다.\n동의어: seat 좌석조회\n인자: 없음",
            "enter": "이용권 선택 → 좌석 배정 절차를 시작합니다.\n동의어: enter 입장\n인자: 없음\n동작: 유효한 이용권 보유 후 미입장 상태에서만 사용 가능",
            "exit": "좌석을 반납하고 이용권 시간을 차감합니다.\n동의어: exit 퇴장\n인자: 없음",
            "buy": "이용권 구매 절차를 시작합니다.\n동의어: buy 이용권구매\n인자: 없음",
            "myinfo": "계정·이용권·좌석 정보를 출력합니다.\n동의어: myinfo 내정보\n인자: 없음",
            "admin": "관리자 전용 메뉴를 출력합니다.\n동의어: admin 관리자\n인자: 없음",
            "logout": "로그아웃합니다.\n동의어: logout 로그아웃\n인자: 없음",
            "move": "현재 입장 중인 좌석에서 다른 빈 좌석으로 이동합니다.\n동의어: move 자리이동\n인자: 없음",
            "pause": "자리비움 상태로 전환합니다.\n동의어: pause 자리비움\n인자: 없음",
            "resume": "자리비움 상태를 해제합니다.\n동의어: resume 자리비움해제\n인자: 없음",
        }
        print(f"... {help_texts.get(cmd, '도움말 없음')}")

    def cmd_end(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        now = self.get_now()
        if self.current_user:
            user = self.current_user
            ticket = self._find_ticket(user.ticket_id)
            if ticket and user.is_entered(self.sessions):
                if ticket.type == 1:  # 정기권
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
                elif ticket.type == 2:  # 시간권
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
                    user.start_time = now
                    if user.is_away():
                        user.away_start = now
        for s in self.sessions:
            if s.exit_time is None and not s.is_shutdown_record():
                s.usage_min = math.floor((now - s.enter_time).total_seconds() / 60)
        
        self._write_shutdown_record(now)
        self.save_all()
        print("(프로그램 종료)")
        self.running = False

    def cmd_login(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        uid_input = safe_input("선택: 아이디 > ")
        if uid_input is None:
            self._handle_eof()
            return

        pw_input = safe_getpass("선택: 비밀번호 > ")
        if pw_input is None:
            self._handle_eof()
            return

        user = self._find_user(uid_input)                   
        if user is None or user.pw_hash != sha256(pw_input):
            print(".!! 오류: 아이디 또는 비밀번호가 올바르지 않습니다.")
            return

        self.current_user = user
        now = self.get_now()

        # 만료 확인
        expired = self._check_expiry(user, now)

        print(f"... {user.id}님, 환영합니다.")
        if expired:
            print(f"..! 안내: 보유 이용권이 만료되었습니다.")
        elif self._has_queue(user):
            cnt = len(self._user_ut_entries(user))
            print(f"..! 안내: 대기열에 {cnt}개의 이용권이 있습니다. 'myinfo'로 확인하세요.")

    def cmd_register(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        # 아이디 입력
        while True:
            uid_input = safe_input("선택: 사용할 아이디 > ")
            if uid_input is None:
                self._handle_eof()
                return
            uid = uid_input         
            err = validate_id(uid)
            if err:
                print(f".!! 오류: {err}")
                continue
            if self._find_user(uid):
                print(".!! 오류: 이미 사용 중인 아이디입니다. 다른 아이디를 입력하세요.")
                continue
            break

        # 비밀번호 입력
        while True:
            pw_input = safe_getpass("선택: 비밀번호 > ")
            if pw_input is None:
                self._handle_eof()
                return
            err = validate_password(pw_input, uid)
            if err:
                print(f".!! 오류: {err}")
                continue

            print("... 비밀번호를 한 번 더 입력하세요.")
            pw_confirm = safe_getpass("선택: 비밀번호 확인 > ")
            if pw_confirm is None:
                self._handle_eof()
                return
            if pw_input != pw_confirm:
                print(".!! 오류: 비밀번호가 일치하지 않습니다. 처음부터 다시 입력하세요.")
                continue
            break

        # 전화번호 입력
        while True:
            phone_input = safe_input("선택: 전화번호 > ")
            if phone_input is None:
                self._handle_eof()
                return
            phone = normalize_phone(phone_input)
            if phone is None:
                print(".!! 오류: 올바른 전화번호 형식이 아닙니다. (010-XXXX-XXXX 또는 01X-XXX-XXXX)")
                continue
            # 중복 확인
            dup = False
            for u in self.users:
                if u.phone == phone:
                    dup = True
                    break
            if dup:
                print(".!! 오류: 이미 등록된 전화번호입니다.")
                continue
            break

        # 확인
        print("... 입력한 정보를 확인해 주세요:")
        print(f"    아이디   : {uid}")
        print(f"    전화번호 : {phone}")
        confirm = safe_input("선택: 이대로 가입하시겠습니까? (Yes/yes/y...) > ")
        if confirm is None:
            self._handle_eof()
            return
        if confirm != "Yes" and confirm !="yes" and confirm !="y":      
            print("... 회원가입을 취소하였습니다.")
            return

        new_user = User(uid, sha256(pw_input), phone)
        # 정렬 삽입
        idx = self._find_user_index(uid)
        self.users.insert(idx, new_user)
        self._save_users()
        print(f"... 회원가입이 완료되었습니다. '{uid}'님 환영합니다!")

    def cmd_seat(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return
        self._print_seats()

    def cmd_enter(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return
        now  = self.get_now()
        user = self.current_user
        if self._check_expiry(user, now):
            print(".!! 오류: 보유하신 이용권의 기한이 만료되었습니다. 새로 구매해 주세요.")
            return
        if not user.has_ticket():
            print(".!! 오류: 유효한 이용권이 없습니다. 먼저 이용권을 구매하세요.")
            return
        if user.is_entered(self.sessions):
            print(".!! 오류: 이미 입장 중입니다. 먼저 퇴장 후 다시 시도하세요.")
            return
        # 좌석 선택
        print("=== 좌석 선택 ===")
        self._print_seats()

        while True:
            seat_input = safe_input("선택: 좌석 번호 선택 > ")
            if seat_input is None:
                self._handle_eof()
                return
            seat_input = seat_input
            if not seat_input.isdigit() or seat_input.startswith("0"):
                print(".!! 오류: 유효하지 않은 좌석 번호입니다. (1 이상의 정수)")
                continue
            seat_num = int(seat_input)
            if seat_num < 1 or seat_num > self.total_seats:
                print(f".!! 오류: 유효하지 않은 좌석 번호입니다. (1~{self.total_seats})")
                continue
            seat = self.seats[seat_num - 1]
            if not seat.is_empty():
                print(f".!! 오류: {seat_num}번 좌석은 이미 사용 중입니다.")
                continue
            break

        now = self.get_now()
        seat.user_id = user.id
        if user.start_time is None:
            user.start_time = now

        # 세션 추가
        self.sessions.append(Session(user.id, user.ticket_id, seat.id, now))
        self._save_sessions()
        self._save_seats()
        self._save_users()

        print(f"... {seat_num}번 좌석에 입장하였습니다. 이용을 시작합니다.")

    def cmd_exit(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        if not user.is_entered(self.sessions):
            print(".!! 오류: 현재 입장 중이 아닙니다.")
            return

        now = self.get_now()
        seat = self._find_seat_by_user(user.id)
        seat_num = seat.id if seat else "?"
        ticket = self._find_ticket(user.ticket_id)

        # 시간권은 중도 퇴장 불가 — _do_exit 호출 전에 차단해야 함
        if ticket and ticket.type == 2:
            print(".!! 오류: 시간권은 중도 퇴장이 불가합니다.")
            return

        deduction, remain = self._do_exit(user, now)

        if ticket and ticket.type == 1:
            print(f"... {seat_num}번 좌석에서 퇴장하였습니다.")
            print(f"    이용 시간: {fmt_minutes(deduction)} / 잔여 시간: {fmt_minutes(remain)} ({ticket.type_name()})")
        else:
            print(f"... {seat_num}번 좌석에서 퇴장하였습니다.")

        # 만료 확인
        if user.has_ticket() and user.remain <= 0:
            user.ticket_id = 0
            user.remain = 0
            user.start_time = None
            print("..! 안내: 이용권이 만료되었습니다.")

        self.save_all()
        if isinstance(seat_num, int):
            self._process_seat_available(seat_num, now)

    def cmd_buy(self, args: list[str]):
        now = self.get_now()
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        self._check_expiry(user, now)

        total_held = (1 if user.has_ticket() else 0) + len(self._user_ut_entries(user))
        if total_held > 0:
            print(f"=== 현재 보유 이용권 ({total_held}개) ===")
            if user.has_ticket():
                cur_t = self._find_ticket(user.ticket_id)
                if cur_t:
                    if cur_t.type in (1, 2):
                        eff = self._calc_effective_remain(user, now)
                        print(f"  [현재] {cur_t.type_name()} (잔여 {fmt_minutes(eff)})")
                    elif cur_t.type == 3:
                        print(f"  [현재] 종일권 (당일 자정까지)")
                    elif cur_t.type == 4:
                        print(f"  [현재] 기간권 (잔여 {user.remain}일)")
            for e in self._sorted_queue(user):
                qt = self._find_ticket(e.ticket_id)
                if qt:
                    tag = " [예약 묶임]" if e.is_reserved else ""
                    if qt.type in (1, 2):
                        print(f"  [대기] {qt.type_name()} ({fmt_minutes(qt.duration * 60)}){tag}")
                    elif qt.type == 3:
                        print(f"  [대기] 종일권{tag}")
                    elif qt.type == 4:
                        print(f"  [대기] 기간권 ({qt.duration}일){tag}")

        print("\n=== 이용권 구매 ===")
        print("[1] 정기권  [2] 시간권  [3] 종일권  [4] 기간권  [0] 취소")
        type_input = safe_input("선택 > ")
        if type_input is None:
            self._handle_eof()
            return
        if type_input == "0":
            print("... 구매를 취소하였습니다.")
            return
        if type_input not in ("1", "2", "3", "4"):
            print(".!! 오류: 유효하지 않은 선택입니다.")
            return

        ttype     = int(type_input)
        type_name = TICKET_TYPE_NAMES[ttype]
        available = [t for t in self.tickets if t.type == ttype]
        if not available:
            print(f".!! 오류: 현재 구매 가능한 {type_name}이(가) 없습니다.")
            return

        print(f"=== {type_name} 선택 ===")
        for i, t in enumerate(available, 1):
            unit_price = t.price // t.duration if t.duration > 0 else 0
            if ttype in (1, 2):
                print(f"[{i}] {t.duration}시간 - {fmt_price(t.price)} (시간당 {fmt_price(unit_price)})")
            elif ttype == 3:
                print(f"[{i}] 종일권 - {fmt_price(t.price)}")
            elif ttype == 4:
                print(f"[{i}] {t.duration}일 - {fmt_price(t.price)} (일당 {fmt_price(unit_price)})")
        print("[0] 뒤로 가기")

        sel_input = safe_input("선택 > ")
        if sel_input is None:
            self._handle_eof()
            return
        sel_input = sel_input.strip()
        if sel_input == "0":
            return
        if not sel_input.isdigit() or int(sel_input) < 1 or int(sel_input) > len(available):
            print(".!! 오류: 유효하지 않은 선택입니다.")
            return

        selected = available[int(sel_input) - 1]

        print("=== 결제 확인 ===")
        print(f"    상품명 : {selected.type_name()} {selected.duration_str()}")
        print(f"    금  액 : {fmt_price(selected.price)}")
        if user.has_ticket():
            print("    안내   : 우선순위에 따라 자동으로 활성화 순서가 결정됩니다.")
        confirm = safe_input("결제하시겠습니까? [y/n] > ")
        if confirm is None:
            self._handle_eof()
            return
        if confirm.lower() != "y":
            print("... 구매를 취소하였습니다.")
            return

        self._enqueue_ticket(user, selected)
        self._save_users()
        self._save_userticket()

        is_now_current = (user.ticket_id == selected.id)
        tag = "[현재 이용권으로 활성화]" if is_now_current else "[대기 이용권으로 등록]"

        if selected.type in (1, 2):
            print(f".>> {tag} {selected.type_name()} {selected.duration_str()} 구매 완료.")
            if is_now_current:
                print(f"    잔여 시간: {fmt_minutes(self._max_remain(selected))}")
        elif selected.type == 3:
            print(f".>> {tag} 종일권 구매 완료.")
        elif selected.type == 4:
            print(f".>> {tag} 기간권 {selected.duration}일 구매 완료.")

    def cmd_myinfo(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        now = self.get_now()
        self._check_expiry(user, now)
        seat = self._find_seat_by_user(user.id)
        ticket = self._find_ticket(user.ticket_id)

        print("=== 내 정보 ===")
        print(f"    아이디   : {user.id}")
        print(f"    전화번호 : {user.phone}")

        if seat:
            print(f"    현재 좌석 : {seat.id}번 (입장 중)")
        else:
            print(f"    현재 좌석 : 없음 (미입장)")

        if not user.has_ticket() or ticket is None:
            print(f"    이용권   : 이용권 없음")
        elif ticket.type in (1, 2):
            eff = self._calc_effective_remain(user, now)
            print(f"    이용권   : {ticket.type_name()} (잔여 {fmt_minutes(eff)})")
        elif ticket.type == 3:
            print(f"    이용권   : 종일권 (당일 자정까지 이용 가능)")
        elif ticket.type == 4:
            if user.start_time:
                expire = user.start_time.date() + timedelta(days=ticket.duration)
                remain_days = (expire - now.date()).days
                print(f"    이용권   : 기간권 (잔여 {remain_days}일)")
            else:
                print(f"    이용권   : 기간권 (잔여 {user.remain}일)")

        if user.is_entered(self.sessions) and user.start_time:
            print(f"    입장 시각 : {user.start_time.strftime(DT_FMT_SEC)}")

        if user.is_away():
            print(f"    자리비움 : 자리비움 중 ({user.away_start.strftime(DT_FMT)}부터)")
        
        ut_list = self._user_ut_entries(user)
        if ut_list:
            print(f"    대기 이용권 ({len(ut_list)}개, 우선순위 순):")
            for e in self._sorted_queue(user):
                qt = self._find_ticket(e.ticket_id)
                if qt:
                    tag = " [예약 묶임]" if e.is_reserved else ""
                    if qt.type in (1, 2):
                        print(f"      - {qt.type_name()} ({fmt_minutes(qt.duration * 60)}){tag}")
                    elif qt.type == 3:
                        print(f"      - 종일권{tag}")
                    elif qt.type == 4:
                        print(f"      - 기간권 ({qt.duration}일){tag}")

    def cmd_admin(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        if not self.current_user.is_admin():
            print(".!! 오류: 관리자 권한이 없습니다.")
            return

        while True:
            print("=== 관리자 메뉴 ===")
            print("[1] 전체 유저 목록 조회")
            print("[2] 특정 유저 강제 퇴장")
            print("[3] 세션 조회")
            print("[4] 좌석 인덱스 편집")
            print("[5] 예약 현황 조회")
            print("[6] 돌아가기")

            sel = safe_input("선택 > ")
            if sel is None:
                self._handle_eof()
                return

            if sel == "1":
                self._admin_user_list()
            elif sel == "2":
                self._admin_force_exit()
            elif sel == "3":
                self._admin_session_list()
            elif sel == "4":
                self._admin_edit_seats()
            elif sel == "5":
                self._admin_reservation_list()
            elif sel == "6":
                break
            else:
                print(".!! 오류: 유효하지 않은 선택입니다.")

    def _admin_user_list(self):
        print("=== 전체 유저 목록 ===")
        print(f"{'아이디':<20s} {'좌석':>4s} {'이용권 정보':<30s} {'대기'}")
        print("-" * 70)
        for u in self.users:
            seat = self._find_seat_by_user(u.id)
            seat_str = str(seat.id) if seat else "-"
            ticket = self._find_ticket(u.ticket_id)
            if ticket and ticket.type in (1, 2):
                eff = self._calc_effective_remain(u)
                t_str = f"{ticket.type_name()} (잔여 {fmt_minutes(eff)})"
            elif ticket and ticket.type == 3:
                t_str = "종일권"
            elif ticket and ticket.type == 4:
                if u.start_time:
                    expire = u.start_time.date() + timedelta(days=ticket.duration)
                    remain_days = (expire - self.get_now().date()).days
                    t_str = f"기간권 ({remain_days}일 남음)"
                else:
                    t_str = f"기간권 ({u.remain}일)"
            else:
                t_str = "없음"
            q_cnt = len(self._user_ut_entries(u))
            q_str = f"{q_cnt}개 대기" if q_cnt else "-"
            print(f"{u.id:<20s} {seat_str:>4s} {t_str:<30s} {q_str}")

    def _admin_force_exit(self):
        uid_input = safe_input("퇴장시킬 아이디 > ")
        if uid_input is None:
            self._handle_eof()
            return
        uid = uid_input
        user = self._find_user(uid)
        if user is None:
            print(f".!! 오류: '{uid}' 사용자를 찾을 수 없습니다.")
            return
        if not user.is_entered(self.sessions):
            print(f".!! 오류: '{uid}'은(는) 현재 입장 중이 아닙니다.")
            return

        now = self.get_now()
        seat = self._find_seat_by_user(uid)
        seat_num = seat.id if seat else "?"
        self._do_exit(user, now)
        self.save_all()
        print(f"... '{uid}'을(를) {seat_num}번 좌석에서 강제 퇴장하였습니다.")
        if isinstance(seat_num, int):
            self._process_seat_available(seat_num, self.get_now())

    def _admin_session_list(self):
        print("=== 세션 기록 ===")
        # 종료 기록 세션 제외
        real_sessions = [s for s in self.sessions if not s.is_shutdown_record()]
        if not real_sessions:
            print("    기록이 없습니다.")
            return
        now = self.get_now()
        for s in real_sessions:
            et = s.enter_time.strftime(DT_FMT_SEC)
            xt = s.exit_time.strftime(DT_FMT_SEC) if s.exit_time else "(이용 중)"
            ut = s.usage_min if s.exit_time else int((now - s.enter_time).total_seconds() // 60)
            print(f"    {s.user_id} | 이용권:{s.ticket_id} | 좌석:{s.seat_id} | "
                f"입장:{et} | 퇴장:{xt} | {ut}분")

    # ─── 좌석 인덱스 편집 ───
    def _admin_edit_seats(self):
        while True:
            disabled = [s.id for s in self.seats if s.disabled]
            self._print_seats()
            print(f"=== 좌석 인덱스 편집 === (현재: {self.rows}행 × {self.cols}열, 총 {self.total_seats}석)")
            print(f"    사용 불가 좌석: {', '.join(str(x) for x in disabled) if disabled else '없음'}")
            print("[1] 행 추가  [2] 행 삭제  [3] 열 추가  [4] 열 삭제")
            print("[5] 좌석 사용 불가  [6] 좌석 사용 가능  [7] 돌아가기")
            sel = safe_input("선택 > ")
            if sel is None:
                self._handle_eof()
                return
            if sel == "1":
                self._seat_add_row()
            elif sel == "2":
                self._seat_del_row()
            elif sel == "3":
                self._seat_add_col()
            elif sel == "4":
                self._seat_del_col()
            elif sel == "5":
                self._seat_set_disabled(True)
            elif sel == "6":
                self._seat_set_disabled(False)
            elif sel == "7":
                break
            else:
                print(".!! 오류: 유효하지 않은 선택입니다.")

    def _seat_add_row(self):
        """맨 뒤에 열(cols)개 좌석 추가"""
        new_ids = range(self.total_seats + 1, self.total_seats + self.cols + 1)
        self.seats.extend(Seat(i) for i in new_ids)
        self.rows += 1
        self.total_seats = self.rows * self.cols
        self._save_seats()
        print(f"... 행 추가 완료 → {self.rows}행 × {self.cols}열 (총 {self.total_seats}석)")

    def _seat_del_row(self):
        """맨 뒤 행(cols개 좌석) 삭제. 이용 중이면 거부."""
        if self.rows <= 1:
            print(".!! 오류: 행이 1개뿐이라 삭제할 수 없습니다.")
            return
        last_row = self.seats[-self.cols:]
        occupied = [s for s in last_row if s.user_id]
        if occupied:
            print(f".!! 오류: 마지막 행에 이용 중인 좌석이 있습니다: {[s.id for s in occupied]}")
            return
        self.seats = self.seats[:-self.cols]
        self.rows -= 1
        self.total_seats = self.rows * self.cols
        self._save_seats()
        print(f"... 행 삭제 완료 → {self.rows}행 × {self.cols}열 (총 {self.total_seats}석)")

    def _seat_add_col(self):
        """각 행 맨 끝에 좌석 1개씩 추가 (열 추가)"""
        new_seats = []
        sid = 1
        for r in range(self.rows):
            for c in range(self.cols):
                new_seats.append(self.seats[r * self.cols + c])
                new_seats[-1].id = sid
                sid += 1
            new_seats.append(Seat(sid))
            sid += 1
        self.seats = new_seats
        self.cols += 1
        self.total_seats = self.rows * self.cols
        self._save_seats()
        print(f"... 열 추가 완료 → {self.rows}행 × {self.cols}열 (총 {self.total_seats}석)")

    def _seat_del_col(self):
        """각 행 마지막 좌석 삭제 (열 삭제). 이용 중이면 거부."""
        if self.cols <= 1:
            print(".!! 오류: 열이 1개뿐이라 삭제할 수 없습니다.")
            return
        last_col = [self.seats[r * self.cols + (self.cols - 1)] for r in range(self.rows)]
        occupied = [s for s in last_col if s.user_id]
        if occupied:
            print(f".!! 오류: 마지막 열에 이용 중인 좌석이 있습니다: {[s.id for s in occupied]}")
            return
        new_seats = []
        sid = 1
        for r in range(self.rows):
            for c in range(self.cols - 1):
                seat = self.seats[r * self.cols + c]
                seat.id = sid
                new_seats.append(seat)
                sid += 1
        self.seats = new_seats
        self.cols -= 1
        self.total_seats = self.rows * self.cols
        self._save_seats()
        print(f"... 열 삭제 완료 → {self.rows}행 × {self.cols}열 (총 {self.total_seats}석)")

    def _seat_set_disabled(self, disable: bool):
        """특정 좌석을 사용 불가/가능으로 전환"""
        action = "사용 불가" if disable else "사용 가능"
        self._print_seats()
        inp = safe_input(f"{action}로 설정할 좌석 번호 > ")
        if inp is None:
            self._handle_eof()
            return
        if not inp.isdigit() or inp.startswith("0"):
            print(".!! 오류: 유효하지 않은 좌석 번호입니다.")
            return
        num = int(inp)
        if num < 1 or num > self.total_seats:
            print(f".!! 오류: 좌석 번호는 1~{self.total_seats} 사이여야 합니다.")
            return
        seat = self.seats[num - 1]
        if disable and seat.user_id:
            print(f".!! 오류: {num}번 좌석은 이용 중({seat.user_id})입니다. 먼저 강제 퇴장 후 설정하세요.")
            return
        seat.disabled = disable
        self._save_seats()
        print(f"... {num}번 좌석을 {action}으로 설정하였습니다.")

    def _admin_reservation_list(self):
        """관리자: 전체 예약 현황 조회"""
        print("=== 전체 예약 현황 ===")
        if not self.reservations:
            print("    예약 내역이 없습니다.")
            return

        STATUS_NAMES = {0: "대기중", 1: "입장완료", 2: "취소됨"}
        for r in self.reservations:
            seat_str   = f"{r.seat_id}번" if r.seat_id else "아무자리나"
            ext_str    = "(연장)" if r.is_extension() else ""
            status_str = STATUS_NAMES.get(r.status, "?")
            print(f"  항목{r.item_id:3d} | 그룹{r.group_id:3d} | {r.user_id:<20s} | "
                  f"{seat_str:<8s}{ext_str:<5s} | "
                  f"{r.reserved_at.strftime(DT_FMT_SEC)} | {status_str}")

    def cmd_logout(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return
        
        print("... 로그아웃 되었습니다.")
        self.current_user = None

    def cmd_reserve(self, args: list[str]):
        """좌석 예약"""
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        now  = self.get_now()

        if not user.has_ticket():
            print(".!! 오류: 이용권이 없습니다. 먼저 이용권을 구매하세요.")
            return

        # ── 좌석 선택 ──
        print("=== 좌석 예약 ===")
        print(f"예약할 좌석 번호를 입력하세요. (1~{self.total_seats}, 0=아무 자리나)")
        self._print_seats()

        seat_input = safe_input("선택: 좌석 번호 > ")
        if seat_input is None:
            self._handle_eof()
            return
        if not seat_input.isdigit():
            print(".!! 오류: 숫자를 입력하세요.")
            return

        seat_id = int(seat_input)
        if seat_id < 0 or seat_id > self.total_seats:
            print(f".!! 오류: 0~{self.total_seats} 사이의 번호를 입력하세요.")
            return

        userticket_id = 0   # 기본: 현재 활성 이용권

        if seat_id > 0:
            seat = self.seats[seat_id - 1]

            # 빈 좌석
            if seat.is_empty():
                print(".!! 오류: 해당 좌석은 현재 비어있습니다. 'enter' 명령어로 바로 입장하세요.")
                return

            # 자기 좌석 → 연장 예약
            if seat.user_id == user.id:
                print("... 현재 본인이 사용 중인 좌석입니다.")
                print("... 이용권 만료 후 같은 자리를 이어서 사용하는 연장 예약입니다.")

                available_ut = [e for e in self._sorted_queue(user)
                                if not e.is_reserved]
                if not available_ut:
                    print(".!! 오류: 연장 예약에 사용할 대기 이용권이 없습니다.")
                    print("    'buy' 명령어로 이용권을 먼저 구매하세요.")
                    return

                print("=== 연장에 사용할 이용권 선택 ===")
                for i, e in enumerate(available_ut, 1):
                    qt = self._find_ticket(e.ticket_id)
                    if qt:
                        if qt.type in (1, 2):
                            print(f"[{i}] {qt.type_name()} ({fmt_minutes(qt.duration * 60)})")
                        elif qt.type == 3:
                            print(f"[{i}] 종일권")
                        elif qt.type == 4:
                            print(f"[{i}] 기간권 ({qt.duration}일)")
                print("[0] 취소")

                sel = safe_input("선택 > ")
                if sel is None:
                    self._handle_eof()
                    return
                if sel == "0":
                    print("... 예약을 취소하였습니다.")
                    return
                if not sel.isdigit() or int(sel) < 1 or int(sel) > len(available_ut):
                    print(".!! 오류: 유효하지 않은 선택입니다.")
                    return

                selected_ut = available_ut[int(sel) - 1]
                selected_ut.is_reserved = True
                userticket_id = selected_ut.userticket_id
                self._save_userticket()

                new_item = ReservationItem(
                    item_id       = self._next_item_id(),
                    group_id      = self._next_group_id(),
                    user_id       = user.id,
                    seat_id       = seat_id,
                    userticket_id = userticket_id,
                    reserved_at   = now,
                    status        = 0,
                )
                self.reservations.append(new_item)
                self._save_reservations()

                qt = self._find_ticket(selected_ut.ticket_id)
                qt_name = qt.type_name() if qt else "이용권"
                print(f"... {seat_id}번 좌석 연장 예약이 완료되었습니다.")
                print(f"    사용 이용권: {qt_name} | 신청 시각: {now.strftime(DT_FMT_SEC)}")
                return

        # seat_id=0 인데 빈 좌석이 있으면 안내
        if seat_id == 0:
            empty = [s for s in self.seats if s.is_empty()]
            if empty:
                seats_str = ", ".join(str(s.id) for s in empty)
                print(f".!! 오류: 빈 좌석({seats_str}번)이 있습니다.")
                print("    'enter' 명령어로 바로 입장하세요.")
                return

        # 이미 동일 좌석 예약이 있는지 확인
        dup = any(r for r in self.reservations
                  if r.user_id == user.id
                  and r.seat_id == seat_id
                  and r.is_waiting())
        if dup:
            seat_str = f"{seat_id}번" if seat_id else "아무자리나"
            print(f".!! 오류: {seat_str} 좌석에 이미 대기 중인 예약이 있습니다.")
            return

        # ── 그룹 선택 ──
        my_groups: dict[int, list[ReservationItem]] = {}
        for r in self.reservations:
            if r.user_id == user.id and r.is_waiting() and not r.is_extension():
                my_groups.setdefault(r.group_id, []).append(r)

        group_id = None

        if my_groups:
            print("=== 기존 예약 그룹 ===")
            group_list = list(my_groups.items())
            for i, (gid, items) in enumerate(group_list, 1):
                seats_str = ", ".join(
                    f"{ri.seat_id}번" if ri.seat_id else "아무자리나"
                    for ri in items
                )
                print(f"[{i}] 그룹 {gid}: {seats_str}")
            print(f"[{len(group_list) + 1}] 새 그룹 생성")

            sel = safe_input("선택 > ")
            if sel is None:
                self._handle_eof()
                return
            if not sel.isdigit() or int(sel) < 1 or int(sel) > len(group_list) + 1:
                print(".!! 오류: 유효하지 않은 선택입니다.")
                return
            idx = int(sel) - 1
            if idx < len(group_list):
                group_id = group_list[idx][0]

        if group_id is None:
            group_id = self._next_group_id()

        # ── 예약 생성 ──
        new_item = ReservationItem(
            item_id       = self._next_item_id(),
            group_id      = group_id,
            user_id       = user.id,
            seat_id       = seat_id,
            userticket_id = userticket_id,
            reserved_at   = now,
            status        = 0,
        )
        self.reservations.append(new_item)
        self._save_reservations()

        seat_str = f"{seat_id}번" if seat_id else "아무 자리나"
        print(f"... {seat_str} 좌석 예약이 완료되었습니다.")
        print(f"    그룹 번호: {group_id} | 신청 시각: {now.strftime(DT_FMT_SEC)}")

    def cmd_myreserv(self, args: list[str]):
        """내 예약 현황 조회"""
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        my_items = [r for r in self.reservations if r.user_id == user.id]

        if not my_items:
            print("... 예약 내역이 없습니다.")
            return

        STATUS_NAMES = {0: "대기중", 1: "입장완료", 2: "취소됨"}

        print("=== 내 예약 현황 ===")
        groups: dict[int, list[ReservationItem]] = {}
        for r in my_items:
            groups.setdefault(r.group_id, []).append(r)

        for gid, items in sorted(groups.items()):
            waiting_count = sum(1 for r in items if r.is_waiting())
            print(f"  [그룹 {gid}] (대기 중: {waiting_count}개)")
            for item in sorted(items, key=lambda r: r.item_id):
                seat_str   = f"{item.seat_id}번" if item.seat_id else "아무자리나"
                ext_str    = " (연장예약)" if item.is_extension() else ""
                status_str = STATUS_NAMES.get(item.status, "?")
                print(f"    항목 {item.item_id}: {seat_str}{ext_str} | "
                      f"신청: {item.reserved_at.strftime(DT_FMT_SEC)} | "
                      f"상태: {status_str}")

    def cmd_cancelreserv(self, args: list[str]):
        """예약 취소 (항목 단위)"""
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        my_waiting = [r for r in self.reservations
                      if r.user_id == user.id and r.is_waiting()]

        if not my_waiting:
            print("... 취소할 수 있는 대기 중 예약이 없습니다.")
            return

        print("=== 예약 취소 ===")
        for i, item in enumerate(my_waiting, 1):
            seat_str = f"{item.seat_id}번" if item.seat_id else "아무자리나"
            ext_str  = " (연장예약)" if item.is_extension() else ""
            print(f"[{i}] 항목 {item.item_id} | 그룹 {item.group_id} | "
                  f"{seat_str}{ext_str} | 신청: {item.reserved_at.strftime(DT_FMT_SEC)}")
        print("[0] 취소하지 않음")

        sel = safe_input("선택 > ")
        if sel is None:
            self._handle_eof()
            return
        if sel == "0":
            print("... 취소하지 않았습니다.")
            return
        if not sel.isdigit() or int(sel) < 1 or int(sel) > len(my_waiting):
            print(".!! 오류: 유효하지 않은 선택입니다.")
            return

        target = my_waiting[int(sel) - 1]
        target.status = 2

        if target.is_extension():
            for e in self.userticket_entries:
                if e.userticket_id == target.userticket_id:
                    e.is_reserved = False
                    break
            self._save_userticket()
        self._save_reservations()

        seat_str = f"{target.seat_id}번" if target.seat_id else "아무자리나"
        print(f"... 항목 {target.item_id} ({seat_str}) 예약이 취소되었습니다.")

    def cmd_move(self, args: list[str]):
        """현재 좌석에서 다른 빈 좌석으로 이동."""
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user

        if not user.is_entered(self.sessions):
            print(".!! 오류: 현재 입장 중이 아닙니다. 자리이동은 입장 중에만 사용할 수 있습니다.")
            return

        if user.is_away():
            print(".!! 오류: 자리비움 중에는 자리이동이 불가합니다. 먼저 'resume'으로 자리비움을 해제하세요.")
            return

        cur_seat = self._find_seat_by_user(user.id)
        if cur_seat is None:
            print(".!! 오류: 현재 좌석 정보를 찾을 수 없습니다.")
            return

        # 빈 좌석 목록 확인
        empty_seats = [s for s in self.seats if s.is_empty()]
        if not empty_seats:
            print(".!! 오류: 이동 가능한 빈 좌석이 없습니다.")
            return

        print(f"... 현재 좌석: {cur_seat.id}번")
        print("=== 이동할 좌석 선택 ===")
        self._print_seats()

        while True:
            seat_input = safe_input("이동할 좌석 번호 > ")
            if seat_input is None:
                self._handle_eof()
                return
            if not seat_input.isdigit() or seat_input.startswith("0"):
                print(".!! 오류: 유효하지 않은 좌석 번호입니다.")
                continue
            seat_num = int(seat_input)
            if seat_num < 1 or seat_num > self.total_seats:
                print(f".!! 오류: 좌석 번호는 1~{self.total_seats} 사이여야 합니다.")
                continue
            new_seat = self.seats[seat_num - 1]
            if new_seat.id == cur_seat.id:
                print(".!! 오류: 현재 좌석과 동일한 번호입니다.")
                continue
            if not new_seat.is_empty():
                print(f".!! 오류: {seat_num}번 좌석은 이미 사용 중입니다.")
                continue
            break

        now = self.get_now()

        # 기존 세션 종료
        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None and not s.is_shutdown_record():
                s.exit_time = now
                s.usage_min = math.floor((now - s.enter_time).total_seconds() / 60)
                break

        # 좌석 교체
        cur_seat.user_id = ""
        new_seat.user_id = user.id

        # 새 세션 시작
        self.sessions.append(Session(user.id, user.ticket_id, new_seat.id, now))

        self._save_sessions()
        self._save_seats()

        print(f"... {cur_seat.id}번 → {new_seat.id}번 좌석으로 이동하였습니다.")

    def cmd_pause(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return
        user = self.current_user
        ticket = self._find_ticket(user.ticket_id)
        if ticket is None or ticket.type != 2:
            print(".!! 오류: 시간권만 자리비움이 가능합니다.")
            return

        
        if not user.is_entered(self.sessions):
            print(".!! 오류: 현재 입장 중이 아닙니다. 자리비움은 입장 중에만 사용할 수 있습니다.")
            return
        if user.is_away():
            print(".!! 오류: 이미 자리비움 상태입니다. 'resume' 명령어로 자리비움을 해제하세요.")
            return

        user.away_start = self.get_now()
        self._save_users()
        print("... 자리비움을 시작합니다. 이용 시간이 절반 속도로 차감됩니다.")

    def cmd_resume(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        if not user.is_entered(self.sessions):
            print(".!! 오류: 현재 입장 중이 아닙니다.")
            return
        if not user.is_away():
            print(".!! 오류: 현재 자리비움 상태가 아닙니다.")
            return

        now    = self.get_now()
        ticket = self._find_ticket(user.ticket_id)

        if ticket and ticket.type == 2:
            # 자리비움 구간
            away_sec   = (now - user.away_start).total_seconds()
            away_min   = math.ceil(away_sec / 60)
            half_deduct = math.ceil(away_min / 2)

            # 입장 ~ 자리비움 시작 구간
            active_sec    = (user.away_start - user.start_time).total_seconds()
            active_deduct = math.ceil(active_sec / 60)

            total_deduct  = active_deduct + half_deduct
            user.remain   = max(0, user.remain - total_deduct)
            user.start_time = now   # 이후 차감 기준을 지금으로 초기화
            user.away_start = None

            print(f"... 자리비움이 해제되었습니다.")
            print(f"    자리비움 시간: {fmt_minutes(away_min)} / "
                  f"차감 시간: {fmt_minutes(half_deduct)} / "
                  f"잔여 시간: {fmt_minutes(user.remain)} ({ticket.type_name()})")
        self._save_users()

    # ─── EOF 처리 ───
    def _handle_eof(self):
        print("\n... EOF 감지. 프로그램을 종료합니다.")
        now = self.get_now()
        if self.current_user:
            user = self.current_user
            ticket = self._find_ticket(user.ticket_id)
            if ticket and user.is_entered(self.sessions):
                if ticket.type == 1:
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
                elif ticket.type == 2:
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
        for s in self.sessions:
            if s.exit_time is None and not s.is_shutdown_record():  # ← 조건 추가
                s.usage_min = math.floor((now - s.enter_time).total_seconds() / 60)

        self._write_shutdown_record(now)
        self.save_all()
        self.running = False


    def cmd_set_time(self, args: list[str]):
        """
        현재 프로그램 시각에 입력한 만큼의 시간을 추가합니다.
        입력 형식: time HH:MM (예: time 01:30 -> 1시간 30분 추가)
        """
        if len(args) < 1:
            print(".!! 추가할 시간을 입력하세요. (예: time 01:00)")
            return

        time_str = args[0]

        try:
            if ":" not in time_str:
                print(".!! 오류: 시간 형식은 HH:MM 이어야 합니다. (예: 12:00)")
                return

            h_str, m_str = time_str.split(":")
            hours = int(h_str)
            minutes = int(m_str)

            if hours < 0 or minutes < 0:
                print(".!! 오류: 0 이상의 시간만 추가할 수 있습니다.")
                return

            added_delta = timedelta(hours=hours, minutes=minutes)
            self.time_offset += added_delta

            print(f"... 시각이 변경되었습니다. ({hours}시간 {minutes}분 추가)")
            print(f"... 현재 프로그램 시각: {self.get_now().strftime('%Y-%m-%d %H:%M')}")

        except ValueError:
            print(".!! 오류: 숫자 형식이 올바르지 않습니다. (예: time 12:00)")

    def get_now(self):
        """시스템 시각에 오프셋이 적용된 '현재 시각'을 반환합니다."""
        return datetime.now() + self.time_offset

    # ─── 메인 루프 ───
    def run(self):
        print("====================================")
        print("   무인 스터디카페 관리 시스템")
        print("====================================")

        self.init_files()
        self.load_data()
        self.verify_integrity()

        cmd_map = {
            "help": self.cmd_help,
            "end": self.cmd_end,
            "login": self.cmd_login,
            "register": self.cmd_register,
            "seat": self.cmd_seat,
            "enter": self.cmd_enter,
            "exit": self.cmd_exit,
            "buy": self.cmd_buy,
            "myinfo": self.cmd_myinfo,
            "admin": self.cmd_admin,
            "logout": self.cmd_logout,
            "move": self.cmd_move,
            "pause": self.cmd_pause,
            "resume": self.cmd_resume,
            "time":self.cmd_set_time,
            "reserve": self.cmd_reserve,
            "myreserv": self.cmd_myreserv,
            "cancelreserv": self.cmd_cancelreserv,
        }
        last_activity_time = self.get_now()

        while self.running:
            self._print_seats() 
            print(f"현재시각 : {self.get_now().strftime(DT_FMT_SEC)}입니다")
            print("====================================")
            line = safe_input(self._prompt())
            current_time = self.get_now()
            inactive_seconds = (current_time - last_activity_time).total_seconds()
            if self.current_user and inactive_seconds >= 180: 
                print(f"\n[안내] 3분 이상 미활동으로 자동 로그아웃되었습니다.") 
                self.cmd_logout([]) 
                last_activity_time = self.get_now()
                continue

            if line is None:
                self._handle_eof()
                break

            tokens = line.split()
            if not tokens:
                self._show_available_cmds()
                continue

            raw_cmd = tokens[0].lower()
            cmd = self._resolve_cmd(raw_cmd)
            args = tokens[1:]

            avail = self._available_cmds()

            # 유효한 명령어인지 확인
            all_cmds = self.CMDS_ALWAYS | self.CMDS_LOGGED_OUT | self.CMDS_LOGGED_IN
            if cmd not in all_cmds:
                self._show_available_cmds()
                last_activity_time = self.get_now()
                continue
            last_activity_time = self.get_now()

            # 상태 오류 확인
            if cmd in self.CMDS_LOGGED_OUT and self.current_user:
                print(".!! 오류: 이미 로그인된 상태입니다. 먼저 로그아웃 후 다시 시도하세요.")
                continue
            if cmd in self.CMDS_LOGGED_IN and not self.current_user:
                print(".!! 오류: 로그인 상태에서만 사용 가능한 명령어입니다.")
                continue

            handler = cmd_map.get(cmd)
            if handler:
                handler(args)
            last_activity_time = self.get_now()


# ═══════════════════════════════════════════
#  엔트리 포인트
# ═══════════════════════════════════════════
if __name__ == "__main__":
    cafe = StudyCafe()
    cafe.run()
