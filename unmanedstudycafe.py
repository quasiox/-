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
ROWS = 4
COLS = 3
TOTAL_SEATS = ROWS * COLS
SHUTDOWN_SEAT_ID   = 0
SHUTDOWN_TICKET_ID = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "Database")

USER_FILE = os.path.join(DB_DIR, "UserRelation.txt")
TICKET_FILE = os.path.join(DB_DIR, "TicketRelation.txt")
SEAT_FILE = os.path.join(DB_DIR, "SeatRelation.txt")
SESSION_FILE = os.path.join(DB_DIR, "SessionRelation.txt")

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

    def is_entered(self):
        return self.start_time is not None

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
    def __init__(self, sid: int, user_id: str = ""):
        self.id = sid
        self.user_id = user_id

    def is_empty(self):
        return self.user_id == ""

    def to_line(self):
        return f"{self.id}.{self.user_id}"

    @staticmethod
    def from_line(line):
        parts = line.split(".", 1)
        try:
            sid = int(parts[0])
            uid = parts[1] if len(parts) > 1 else ""
            return Seat(sid, uid)
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



# ═══════════════════════════════════════════
#  메인 프로그램
# ═══════════════════════════════════════════
class StudyCafe:
    def __init__(self):
        self.users: list[User] = []
        self.seats: list[Seat] = []
        self.tickets: list[Ticket] = []
        self.sessions: list[Session] = []
        self.current_user: User | None = None
        self.running = True
        self.time_offset = timedelta(0)
        self.last_shutdown: datetime | None = None

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

        # Seats
        lines = self._read_lines(SEAT_FILE)
        if not lines:
            self.seats = [Seat(i + 1) for i in range(TOTAL_SEATS)]
            self._save_seats()
        else:
            self.seats = []
            for i, line in enumerate(lines, 1):
                s = Seat.from_line(line)
                if s is None:
                    print(f"!!! 오류: SeatRelation.txt {i}행 형식 오류: {line}")
                    sys.exit(1)
                self.seats.append(s)
            if len(self.seats) != TOTAL_SEATS:
                print(f"!!! 오류: SeatRelation.txt 좌석 수({len(self.seats)})가 "
                      f"ROWS×COLS({TOTAL_SEATS})와 일치하지 않습니다.")
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


    def _save_file(self, filepath, items):
        with open(filepath, "w", encoding="utf-8") as f:
            for item in items:
                f.write(item.to_line() + "\n")

    def _save_users(self):
        self._save_file(USER_FILE, self.users)

    def _save_seats(self):
        self._save_file(SEAT_FILE, self.seats)

    def _save_tickets(self):
        self._save_file(TICKET_FILE, self.tickets)

    def _save_sessions(self):
        self._save_file(SESSION_FILE, self.sessions)
    def _write_shutdown_record(self, now: datetime):
        """종료 시각 기록 + 자리비움 중 시간권 유저 remain 갱신"""

        for u in self.users:
            if u.away_start and u.ticket_id != 0:
                ticket = self._find_ticket(u.ticket_id)
                if ticket and ticket.type == 2:
                    # 직전 종료 기록이 있으면 그 이후 구간만 차감
                    calc_from = max(u.away_start,
                                    self.last_shutdown) if self.last_shutdown else u.away_start

                    away_sec    = max(0, (now - calc_from).total_seconds())
                    away_min    = math.ceil(away_sec / 60)
                    half_deduct = math.ceil(away_min / 2)

                    # active 구간: start_time → away_start
                    # 이미 차감된 경우(last_shutdown 이후 start_time 갱신) max(0,...)
                    if self.last_shutdown is None or u.start_time > self.last_shutdown:
                        active_sec    = (u.away_start - u.start_time).total_seconds()
                        active_deduct = math.ceil(active_sec / 60)
                    else:
                        active_deduct = 0

                    total_deduct = active_deduct + half_deduct
                    u.remain     = max(0, u.remain - total_deduct)

                    if total_deduct > 0:
                        print(f"..! 안내: '{u.id}' 자리비움 차감 — "
                            f"차감 {fmt_minutes(total_deduct)} / "
                            f"잔여 {fmt_minutes(u.remain)}")

        # 종료 기록 세션 추가 (enter = exit = now)
        shutdown_session = Session(
            user_id    = ADMIN_ID,
            ticket_id  = SHUTDOWN_TICKET_ID,
            seat_id    = SHUTDOWN_SEAT_ID,
            enter_time = now,
            exit_time  = now,
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

            # 좌석번호: 1 ≤ id ≤ 12 (TOTAL_SEATS)
            if s.id != num:
                self._integrity_exit("Seat", i,
                    f"좌석번호는 {num} 이어야 함: {s.id}", line)
            if s.id > TOTAL_SEATS:
                self._integrity_exit("Seat", i,
                    f"좌석번호는 {TOTAL_SEATS} 이하여야 함: {s.id}", line)
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
            if s.seat_id < 1 or s.seat_id > TOTAL_SEATS:
                self._integrity_exit("Session", i,
                    f"좌석번호가 범위를 벗어남: {s.seat_id} (1~{TOTAL_SEATS})", line)

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
            if user.is_entered():
                elapsed = self._calc_deduction(user, ticket, now)
                return max(0, user.remain - elapsed)
            return user.remain

        elif ticket.type == 2:  # 시간권: 시작 후 계속 차감
            if user.start_time:
                elapsed = self._calc_deduction(user, ticket, now)
                return max(0, user.remain - elapsed)
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

        if ticket.type == 2 and user.away_start:
            # 시간권 + 자리비움: 절반 차감
            active_sec = (user.away_start - user.start_time).total_seconds()
            away_sec = (now - user.away_start).total_seconds()
            return math.ceil(active_sec / 60) + math.ceil(away_sec / 60 / 2)
        else:
            # 정기권이거나 자리비움 아님: 전체 차감
            elapsed_sec = (now - user.start_time).total_seconds()
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
                        active_sec = (user.away_start - user.start_time).total_seconds()
                        active_min = math.ceil(active_sec / 60)
                        
                        if user.remain <= active_min:
                            # 자리비움 버튼을 누르기 "전"에 이미 정상 속도로 만료되었던 경우
                            expired_time = user.start_time + timedelta(minutes=user.remain)
                        else:
                            # 자리비움 "도중"에 만료된 경우
                            # 남은 시간(leftover)은 현실에서 2배 느리게 흐르므로 곱하기 2를 해줍니다.
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
                        # 기획서 공식: floor((퇴장-입장)/60) 
                        s.usage_min += math.floor((expired_time - s.enter_time).total_seconds() / 60)
                        break
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
            user.start_time = None
        # 종일권/기간권: 별도 차감 없음

        user.away_start = None

        # 좌석 반납
        if seat:
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
        print("pause 자리비움       | 없음               | 자리비움 상태로 변경")
        print("resume 자리비움해제  | 없음               | 자리비움 해제")
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
                       "logout", "pause", "resume"}
    # 한글 동의어 매핑
    CMD_ALIASES = {
        "도움말": "help", "종료": "end", "로그인": "login", "회원가입": "register",
        "좌석조회": "seat", "입장": "enter", "퇴장": "exit", "이용권구매": "buy",
        "내정보": "myinfo", "관리자": "admin", "로그아웃": "logout",
        "자리비움": "pause", "자리비움해제": "resume",
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
        for seat in self.seats:
            if seat.is_empty():
                continue
            user = self._find_user(seat.user_id)
            if user is None:
                continue
            if self._check_expiry(user, now):
                changed = True
        if changed:
            self._save_users()
            self._save_seats()
        print("=== 좌석 현황 ===")
        for r in range(ROWS):
            row_str = ""
            for c in range(COLS):
                idx = r * COLS + c
                seat = self.seats[idx]
                if seat.is_empty():
                    label = ""
                    row_str += f"[{seat.id:2d}: {label:<6s}]"
                elif self.current_user and seat.user_id == self.current_user.id:
                    label = "내좌석"
                    row_str += f"[{seat.id:2d}: {label}]"
                else:
                    uid = seat.user_id
                    label = uid if len(uid) <= 6 else uid[:4] + "…"
                    row_str += f"[{seat.id:2d}: {label:<6s}]"
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
            if ticket and user.is_entered():
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

        user = self.current_user
        if not user.has_ticket():
            print(".!! 오류: 유효한 이용권이 없습니다. 먼저 이용권을 구매하세요.")
            return
        if user.is_entered():
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
            if seat_num < 1 or seat_num > TOTAL_SEATS:
                print(f".!! 오류: 유효하지 않은 좌석 번호입니다. (1~{TOTAL_SEATS})")
                continue
            seat = self.seats[seat_num - 1]
            if not seat.is_empty():
                print(f".!! 오류: {seat_num}번 좌석은 이미 사용 중입니다.")
                continue
            break

        now = self.get_now()
        seat.user_id = user.id
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
        if not user.is_entered():
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

    def cmd_buy(self, args: list[str]):
        now = self.get_now()
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        if user.has_ticket():
            ticket = self._find_ticket(user.ticket_id)
            if ticket:
                print(".!! 오류: 이미 유효한 이용권(",end="")
                if ticket.type in (1, 2):
                    eff = self._calc_effective_remain(user, now)
                    print(f"{ticket.type_name()} (잔여 {fmt_minutes(eff)})을 보유 중입니다.")
                elif ticket.type == 3:
                    print(f"종일권 (당일 자정까지 이용 가능)을 보유 중입니다.")
                elif ticket.type == 4:
                    if user.start_time:
                        expire = user.start_time.date() + timedelta(days=ticket.duration)
                        remain_days = (expire - now.date()).days
                        print(f"기간권 (잔여 {remain_days}일)을 보유 중입니다.")
                    else:
                        print(f"기간권 (잔여 {user.remain}일)을 보유 중입니다.")
            else:
                print(".!! 오류: 이미 유효한 이용권을 보유 중입니다.")
            print("    현재 이용권을 모두 소진한 후 구매하세요.")
            return

        # 종류 선택
        print("=== 이용권 구매 ===")
        print("[1] 정기권  [2] 시간권  [3] 종일권  [4] 기간권  [0] 취소")
        type_input = safe_input("선택 > ")
        if type_input is None:
            self._handle_eof()
            return
        type_input = type_input
        if type_input == "0":
            print("... 구매를 취소하였습니다.")
            return
        if type_input not in ("1", "2", "3", "4"):
            print(".!! 오류: 유효하지 않은 선택입니다.")
            return

        ttype = int(type_input)
        type_name = TICKET_TYPE_NAMES[ttype]

        # 해당 종류 이용권 목록
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

        # 결제 확인
        print("=== 결제 확인 ===")
        print(f"    상품명 : {selected.type_name()} {selected.duration_str()}")
        print(f"    금  액 : {fmt_price(selected.price)}")
        confirm = safe_input("결제하시겠습니까? [y/n] > ")
        if confirm is None:
            self._handle_eof()
            return
        if confirm.lower() != "y":
            print("... 구매를 취소하였습니다.")
            return

        # 구매 처리
        user.ticket_id = selected.id
        if selected.type in (1, 2):
            user.remain = selected.duration * 60  # 시간→분 변환
        elif selected.type == 3:
            user.remain = 1  # 종일권: 유효
        elif selected.type == 4:
            user.remain = selected.duration  # 기간권: 일수

        user.start_time = None
        user.away_start = None
        self._save_users()

        if selected.type in (1, 2):
            print(f".>> {selected.type_name()} {selected.duration_str()} 구매가 완료되었습니다.")
            print(f"    잔여 시간: {fmt_minutes(user.remain)}")
        elif selected.type == 3:
            print(f".>> 종일권 구매가 완료되었습니다. 당일 자정까지 이용 가능합니다.")
        elif selected.type == 4:
            print(f".>> 기간권 {selected.duration}일 구매가 완료되었습니다.")
            print(f"    잔여 기간: {selected.duration}일")

    def cmd_myinfo(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        now = self.get_now()
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

        if user.is_entered() and user.start_time:
            print(f"    입장 시각 : {user.start_time.strftime(DT_FMT_SEC)}")

        if user.is_away():
            print(f"    자리비움 : 자리비움 중 ({user.away_start.strftime(DT_FMT)}부터)")

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
            print("[4] 돌아가기")

            sel = safe_input("선택 > ")
            if sel is None:
                self._handle_eof()
                return
            sel = sel

            if sel == "1":
                self._admin_user_list()
            elif sel == "2":
                self._admin_force_exit()
            elif sel == "3":
                self._admin_session_list()
            elif sel == "4":
                break
            else:
                print(".!! 오류: 유효하지 않은 선택입니다.")

    def _admin_user_list(self):
        print("=== 전체 유저 목록 ===")
        print(f"{'아이디':<20s} {'좌석':>4s} {'이용권 정보':<30s}")
        print("-" * 60)
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
                t_str = f"기간권 (잔여 {u.remain}일)"
            else:
                t_str = "없음"
            print(f"{u.id:<20s} {seat_str:>4s} {t_str:<30s}")

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
        if not user.is_entered():
            print(f".!! 오류: '{uid}'은(는) 현재 입장 중이 아닙니다.")
            return

        now = self.get_now()
        seat = self._find_seat_by_user(uid)
        seat_num = seat.id if seat else "?"
        self._do_exit(user, now)
        self.save_all()
        print(f"... '{uid}'을(를) {seat_num}번 좌석에서 강제 퇴장하였습니다.")

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

    def cmd_logout(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        now = self.get_now()
        ticket = self._find_ticket(user.ticket_id)

        # 시간권 차감 (입장 중일 때)
        if ticket and ticket.type == 2 and user.start_time:
            deduction = self._calc_deduction(user, ticket, now)
            user.remain = max(0, user.remain - deduction)
            if user.remain <= 0:
                user.ticket_id = 0
                user.remain = 0
                user.start_time = None
                seat = self._find_seat_by_user(user.id)
                if seat:
                    seat.user_id = ""

        elif ticket and ticket.type == 1 and user.start_time:
            deduction = self._calc_deduction(user, ticket, now)
            user.remain = max(0, user.remain - deduction)
            if user.remain <= 0:
                user.ticket_id = 0
                user.remain = 0
                user.start_time = None
                # 만료 시에만 좌석 반납
                seat = self._find_seat_by_user(user.id)
                if seat:
                    seat.user_id = ""

        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None and not s.is_shutdown_record():
                enter = s.enter_time
                s.usage_min = math.floor((now - enter).total_seconds() / 60)
                break


        self.save_all()
        print("... 로그아웃 되었습니다.")
        self.current_user = None

    def cmd_pause(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return
        user = self.current_user
        ticket = self._find_ticket(user.ticket_id)
        if ticket is None or ticket.type != 2:
            print(".!! 오류: 시간권만 자리비움이 가능합니다.")
            return

        
        if not user.is_entered():
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
        if not user.is_entered():
            print(".!! 오류: 현재 입장 중이 아닙니다.")
            return
        if not user.is_away():
            print(".!! 오류: 현재 자리비움 상태가 아닙니다.")
            return

        now = self.get_now()
        ticket = self._find_ticket(user.ticket_id)
       

        if ticket and ticket.type == 2:
            away_sec = (now - user.away_start).total_seconds()
            away_min = math.ceil(away_sec / 60)
            user.away_time += away_min
            half_deduct=math.ceil(away_min/2)
           
         
          
            active_sec = (user.away_start - user.start_time).total_seconds()
            active_deduct = math.ceil(active_sec / 60)
           
            total_deduct  = active_deduct + half_deduct
            user.remain   = max(0, user.remain - total_deduct)
            user.start_time = now
            user.away_start = None

            print(f"... 자리비움이 해제되었습니다.")
            print(f"    자리비움 시간: {fmt_minutes(away_min)} / 차감 시간: {fmt_minutes(half_deduct)} / "
                  f"잔여 시간: {fmt_minutes(user.remain)} ({ticket.type_name()})")

        self._save_users()

    # ─── EOF 처리 ───
    def _handle_eof(self):
        print("\n... EOF 감지. 프로그램을 종료합니다.")
        now = self.get_now()
        if self.current_user:
            user = self.current_user
            ticket = self._find_ticket(user.ticket_id)
            if ticket and user.is_entered():
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
        특정 날짜와 시각으로 프로그램 시간을 변경합니다 (미래로만 이동 가능).
        입력 형식: time YYYY-MM-DD HH:MM
        """
        if len(args) < 2:
            print(".!! 오류: 날짜와 시각을 모두 입력하세요. (예: time 2000-01-01 00:00)")
            return

        target_str = f"{args[0]} {args[1]}"
    
        try:
            # 1. 입력받은 문자열을 기획서 표준 형식(YYYY-MM-DD HH:MM)으로 변환 [cite: 212]
            target_time = datetime.strptime(target_str, "%Y-%m-%d %H:%M")
        
            # 2. 새로운 오프셋 계산
            new_offset = target_time - datetime.now()
        
            # 3. [핵심] 오프셋이 0보다 작거나 같은지 확인 (과거 또는 현재 시각 차단)
            if new_offset.total_seconds() <= 0:
                print(".!! 오류: 현재 시각보다 이후의 시각만 설정할 수 있습니다.")
                return

            # 4. 검증 통과 시 오프셋 업데이트
            self.time_offset = new_offset
            print(f"... 시각이 변경되었습니다: {self.get_now().strftime('%Y-%m-%d %H:%M')}")
            return
        
        except ValueError:
            print(".!! 오류: 날짜 형식이 올바르지 않습니다. (예: 2000-01-01 00:00)")

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
            "pause": self.cmd_pause,
            "resume": self.cmd_resume,
            "time":self.cmd_set_time,
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
