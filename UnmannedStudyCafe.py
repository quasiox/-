#!/usr/bin/env python3
"""
무인 스터디카페 UnmannedStudyCafe
C03팀 기획서 기반 구현
"""
from __future__ import annotations

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

    def save_all(self):
        self._save_users()
        self._save_seats()
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

    def _calc_deduction(self, user: User, ticket: Ticket, now: self.get_now()) -> int:
        """start_time 기준 차감할 분 수 계산"""
        if user.start_time is None:
            return 0

        if ticket.type == 2 and user.away_start:
            # 시간권 + 자리비움: 절반 차감
            active_sec = (user.away_start - user.start_time).total_seconds()
            away_sec = (now - user.away_start).total_seconds()
            return math.ceil(active_sec / 60) + math.ceil(away_sec / 60 / 2)
        else:
            # 정기권이거나 자리비움 아님: 전체 차감
            elapsed_sec = (now - user.start_time).total_seconds()
            return math.ceil(elapsed_sec / 60)

    def _check_expiry(self, user: User, now: self.get_now() = None):
        """이용권 만료 확인 및 처리. 만료 시 True 반환"""
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

        if ticket.type in (1, 2):
            eff = self._calc_effective_remain(user, now)
            if eff <= 0:
                expired = True

        elif ticket.type == 3:  # 종일권: 날짜 변경 시 만료
            if user.start_time and user.start_time.date() != now.date():
                expired = True

        elif ticket.type == 4:  # 기간권
            if user.start_time:
                expire_date = user.start_time.date() + timedelta(days=ticket.duration)
                if now.date() >= expire_date:
                    expired = True

        if expired:
            old_name = ticket.type_name()
            old_dur = ticket.duration_str()
            user.ticket_id = 0
            user.remain = 0
            user.start_time = None
            user.away_start = None
            # 좌석 반납
            seat = self._find_seat_by_user(user.id)
            if seat:
                seat.user_id = ""
            return True
        return False

    # ─── 퇴장 처리 핵심 로직 ───
    def _do_exit(self, user: User, now: self.get_now() = None) -> tuple[int, int]:
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
            user.start_time = now  # 시간권: 계속 차감을 위해 기준 시점 갱신
        # 종일권/기간권: 별도 차감 없음

        user.away_start = None

        # 좌석 반납
        if seat:
            seat.user_id = ""

        # 세션 업데이트
        usage_min = math.floor((now - self._get_session_enter(user)).total_seconds() / 60) \
            if self._get_session_enter(user) else 0
        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None:
                s.exit_time = now
                s.usage_min = usage_min
                break

        return deduction, user.remain

    def _get_session_enter(self, user: User) -> datetime | None:
        for s in reversed(self.sessions):
            if s.user_id == user.id and s.exit_time is None:
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
        print("=== 좌석 현황 ===")
        for r in range(ROWS):
            row_str = ""
            for c in range(COLS):
                idx = r * COLS + c
                seat = self.seats[idx]
                if seat.is_empty():
                    label = ""
                elif self.current_user and seat.user_id == self.current_user.id:
                    label = "내좌석"
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
                    user.start_time = None
                    user.away_start = None
                elif ticket.type == 2:  # 시간권
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
                    user.start_time = now
                    user.away_start = None

        self.save_all()
        print("... 프로그램을 종료합니다.")
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

        user = self._find_user(uid_input.strip())                   #strip 사용 할건지?
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
            uid = uid_input.strip()             #strip?
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
            phone = normalize_phone(phone_input.strip())
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
        confirm = safe_input("선택: 이대로 가입하시겠습니까? (Yes/...) > ")
        if confirm is None:
            self._handle_eof()
            return
        if confirm.strip() != "Yes":        #strip?
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
            seat_input = seat_input.strip()
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
        user.away_start = None

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

        deduction, remain = self._do_exit(user, now)

        if ticket and ticket.type in (1, 2):
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
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
        if user.has_ticket():
            ticket = self._find_ticket(user.ticket_id)
            if ticket:
                eff = self._calc_effective_remain(user)
                print(f".!! 오류: 이미 유효한 이용권({ticket.type_name()} {ticket.duration_str()}, "
                      f"잔여 {fmt_minutes(eff)})을 보유 중입니다.")
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
        type_input = type_input.strip()
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
        if confirm.strip().lower() != "y":
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
            sel = sel.strip()

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
        uid = uid_input.strip()
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
        if not self.sessions:
            print("    기록이 없습니다.")
            return
        for s in self.sessions:
            et = s.enter_time.strftime(DT_FMT_SEC)
            xt = s.exit_time.strftime(DT_FMT_SEC) if s.exit_time else "(이용 중)"
            print(f"    {s.user_id} | 이용권:{s.ticket_id} | 좌석:{s.seat_id} | "
                  f"입장:{et} | 퇴장:{xt} | {s.usage_min}분")

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
            user.start_time = now  # 기준 시점 갱신
            user.away_start = None
            if user.remain <= 0:
                user.ticket_id = 0
                user.remain = 0
                user.start_time = None

        # 정기권 차감 (입장 중일 때)
        if ticket and ticket.type == 1 and user.start_time:
            deduction = self._calc_deduction(user, ticket, now)
            user.remain = max(0, user.remain - deduction)
            user.start_time = None
            user.away_start = None
            if user.remain <= 0:
                user.ticket_id = 0
                user.remain = 0

        self.save_all()
        print("... 로그아웃 되었습니다.")
        self.current_user = None

    def cmd_pause(self, args: list[str]):
        if args:
            print(".!! 오류: 인자가 없어야 합니다.")
            return

        user = self.current_user
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
        away_sec = (now - user.away_start).total_seconds()
        away_min = math.ceil(away_sec / 60)

        if ticket and ticket.type == 2:
            # 시간권: 절반만 차감
            half_deduct = math.ceil(away_min / 2)
            user.remain = max(0, user.remain - half_deduct)
            # start_time을 조정: 자리비움 기간의 절반만 경과한 것처럼
            # 실제로는 remain을 직접 차감했으므로, start_time을 now로 갱신하고
            # remain에서 (enter→away) 구간도 차감해야 함
            # 더 깔끔하게: active구간 차감 + away 절반 차감, start_time = now
            active_sec = (user.away_start - user.start_time).total_seconds()
            active_deduct = math.ceil(active_sec / 60)
            total_deduct = active_deduct + half_deduct
            # 위에서 half_deduct만 뺐으므로 active_deduct도 빼야 함
            # 아... remain에서 half_deduct만 뺐는데, 사실 active 구간은 이미 남아있는 remain에 반영 안 됨
            # 정리: remain은 구매 시점의 초기값에서 시작. start_time 이후 경과분만큼 차감해야 함.
            # resume 시: remain -= (active + half_away), start_time = now
            user.remain = max(0, user.remain - active_deduct)  # active 구간 추가 차감
            # 이미 half_deduct를 뺐으므로 총 = active_deduct + half_deduct
            user.start_time = now
            user.away_start = None

            print(f"... 자리비움이 해제되었습니다.")
            print(f"    자리비움 시간: {fmt_minutes(away_min)} / 차감 시간: {fmt_minutes(half_deduct)} / "
                  f"잔여 시간: {fmt_minutes(user.remain)} ({ticket.type_name()})")
        else:
            # 시간권 아닌 경우: 자리비움 해제만 (정기권은 원래 입장 중에만 차감이므로
            # 자리비움 동안에도 전체 차감됨 - 사용자 요청)
            user.away_start = None
            print(f"... 자리비움이 해제되었습니다.")

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
                    user.start_time = None
                    user.away_start = None
                elif ticket.type == 2:
                    deduction = self._calc_deduction(user, ticket, now)
                    user.remain = max(0, user.remain - deduction)
                    user.start_time = now
                    user.away_start = None
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
                return self.get_now()

            # 4. 검증 통과 시 오프셋 업데이트
            self.time_offset = new_offset
            print(f"... 시각이 변경되었습니다: {self.get_now().strftime('%Y-%m-%d %H:%M')}")
        
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
            print(f"현재시각 : {self.get_now()}입니다")
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

            raw_cmd = tokens[0]
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
