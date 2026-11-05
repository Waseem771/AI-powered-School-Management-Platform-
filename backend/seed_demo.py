"""Builds a demo database for a fictional school in Khairpur, in its own file.

    python seed_demo.py                 builds demo.db, here in backend/
    python seed_demo.py --replace       rebuilds it, with dates fresh for today

It never opens the app's own database. It writes only to a file with "demo" in its name, and will
not overwrite one unless told to. Every name and record is made up, and the phone numbers use a
prefix that no Pakistani mobile or Khairpur line has. Nothing here is real or validated: it is for
showing the product. Set the admin password with DEMO_ADMIN_PASSWORD, or one is printed once.
"""
import argparse
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlmodel import Session, SQLModel, create_engine

from config import GRADES, SECTIONS, SUBJECTS
from models.fee import AcademicYear, FeeStructure, Invoice, Payment
from models.result import FINAL_TERM, MIDTERM, Result
from models.student import Student
from services.admin_setup import ADMIN_USERNAME, ensure_admin_account
from services.fee_ledger import DUE_DATE_DISPLAY_FORMAT, payment_status, school_today

DEMO_ADMIN_USERNAME = ADMIN_USERNAME
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "demo.db"
STUDENTS_PER_CLASS = 12
MONTHS_OF_FEES = 3
MONTHLY_TUITION = 3500.0
EXAM_FEE = 500.0
EXAM_FEE_MONTHS = (10, 3)  # knowledge_base/fee_policy.txt
DUE_DAY = 10
PHONE_PREFIX = "0999"
SEED = 20261105
TOTAL_MARKS = 100.0

FIRST_NAMES = [
    "Aamir", "Adeel", "Ahsan", "Arsalan", "Asif", "Ayaz", "Bashir", "Dilawar", "Fahad", "Faraz", "Ghulam", "Habib",
    "Imtiaz", "Irfan", "Jawad", "Kamran", "Mansoor", "Nabeel", "Noman", "Qasim", "Rizwan", "Sajid", "Salman", "Shahzad",
    "Sohail", "Tahir", "Waqas", "Yasir", "Zeeshan", "Zubair", "Afsheen", "Amna", "Anila", "Asma", "Bushra", "Farah",
    "Fozia", "Hira", "Humaira", "Javeria", "Komal", "Lubna", "Madiha", "Marvi", "Nadia", "Naila", "Parveen", "Rabia",
    "Rukhsana", "Saima", "Samina", "Shazia", "Sindhu", "Sumaira", "Tahira", "Uzma", "Yasmeen", "Zahida",
]
FAMILY_NAMES = ["Soomro", "Memon", "Abro", "Shaikh", "Junejo", "Mangi", "Mirani", "Khuhro", "Chandio", "Siyal", "Kalhoro", "Arain", "Rajper", "Dahri", "Solangi", "Bozdar"]
GUARDIAN_FIRST_NAMES = ["Abdul Karim", "Ghulam Nabi", "Muhammad Hassan", "Allah Dino", "Abdul Rasheed", "Nazir Ahmed", "Mumtaz Ali", "Gul Hassan", "Sikandar Ali", "Rahim Bux"]

# (kind, share of the school): marks around the range given, with failed subjects where stated.
ACADEMIC_PROFILES = [
    ("strong", 0.56, (72, 93), 0),
    ("steady", 0.24, (60, 74), 0),
    ("borderline", 0.12, (58, 68), 1),
    ("weak", 0.08, (30, 46), 3),
]
FALLING_SHARE = 0.15
RISING_SHARE = 0.20
# How a family's fees went. Deliberately drawn apart from marks: paying late says nothing about ability.
FEE_PROFILES = [("paid", 0.62), ("part_paid", 0.14), ("behind", 0.12), ("this_month_open", 0.12)]

# The people SAMPLE_DEMO_SCENARIO.md relies on. test_demo_seed.py holds them to it.
SHOWCASE: List[Dict[str, Any]] = [
    {"name": "Hina Soomro", "roll": "801", "grade": "Grade 8", "section": "A", "midterm": [74, 70, 80, 78, 84, 76], "final": [78, 72, 85, 81, 88, 80], "fees": "part_paid"},
    {"name": "Ali Junejo", "roll": "802", "grade": "Grade 8", "section": "A", "midterm": [66, 62, 70, 64, 72, 68], "final": [68, 64, 72, 66, 74, 70], "fees": "paid"},
    {"name": "Ali Junejo", "roll": "1051", "grade": "Grade 10", "section": "B", "midterm": [58, 62, 55, 60, 66, 64], "final": [60, 64, 58, 62, 68, 66], "fees": "paid"},
    {"name": "Danish Memon", "roll": "901", "grade": "Grade 9", "section": "A", "midterm": [62, 70, 58, 64, 72, 66], "final": [38, 52, 33, 36, 55, 49], "fees": "paid"},
    {"name": "Sara Abro", "roll": "751", "grade": "Grade 7", "section": "B", "midterm": [54, 40, 62, 66, 70, 60], "final": [55, 37, 65, 67, 72, 60], "fees": "paid"},
    {"name": "Maham Shaikh", "roll": "1001", "grade": "Grade 10", "section": "A", "midterm": [86, 82, 90, 88, 84, 85], "final": [88, 84, 92, 90, 86, 87], "fees": "behind"},
    {"name": "محمد علی", "roll": "701", "grade": "Grade 7", "section": "A", "midterm": [70, 78, 66, 68, 80, 72], "final": [72, 80, 68, 70, 82, 74], "fees": "paid"},
    {"name": "Kiran Mangi", "roll": "651", "grade": "Grade 6", "section": "B", "midterm": None, "final": None, "fees": "this_month_open", "enrolled_days_ago": 2},
    {"name": "Asad Solangi", "roll": "852", "grade": "Grade 8", "section": "B", "midterm": [60, 58, 62, 64, 66, 60], "final": [62, 60, 64, 66, 68, 62], "fees": "part_paid", "archived": True},
]


def academic_session(today: date) -> str:
    """The school year runs from August to May, under the academic calendar."""
    start = today.year if today.month >= 8 else today.year - 1
    return f"{start}-{start + 1}"


def _billing_months(today: date) -> List[date]:
    """The first of each billing month, oldest first, ending with this one."""
    months = []
    year, month = today.year, today.month
    for _ in range(MONTHS_OF_FEES):
        months.append(date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return list(reversed(months))


def _moment(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 6, 0, tzinfo=timezone.utc)


def _pick_weighted(rng: random.Random, options: Sequence[Tuple]) -> Tuple:
    roll = rng.random()
    running = 0.0
    for option in options:
        running += option[1]
        if roll < running:
            return option
    return options[-1]


def _fresh_names(rng: random.Random, taken: set) -> List[str]:
    combos = [f"{first} {family}" for first in FIRST_NAMES for family in FAMILY_NAMES if f"{first} {family}" not in taken]
    rng.shuffle(combos)
    return combos


def _phone(number: int) -> str:
    return f"{PHONE_PREFIX}-{number:07d}"


def _guardian(rng: random.Random, name: str) -> str:
    family = name.split()[-1]
    if family not in FAMILY_NAMES:
        family = rng.choice(FAMILY_NAMES)
    return f"{rng.choice(GUARDIAN_FIRST_NAMES)} {family}"


def _class_roll(grade: str, section: str, position: int) -> str:
    """Grade 8-A runs 801, 802...; Grade 8-B runs 851, 852..."""
    return str(int(grade.split()[-1]) * 100 + (50 if section == "B" else 0) + position)


def _dob(rng: random.Random, grade: str, today: date) -> str:
    age = int(grade.split()[-1]) + 5
    return date(today.year - age, rng.randint(1, 12), rng.randint(1, 28)).isoformat()


def _academic_marks(rng: random.Random) -> Tuple[List[float], List[float]]:
    """A random student's midterm and final, following a profile."""
    kind, _, (low, high), failed_subjects = _pick_weighted(rng, ACADEMIC_PROFILES)
    final = [float(rng.randint(low, high)) for _ in SUBJECTS]
    for index in rng.sample(range(len(SUBJECTS)), failed_subjects):
        final[index] = float(rng.randint(24, 38))

    # A borderline student stays level, so the school also holds Medium estimates with no fall behind them.
    roll = 1.0 if kind == "borderline" else rng.random()
    if roll < FALLING_SHARE:
        change = rng.randint(14, 24)
    elif roll < FALLING_SHARE + RISING_SHARE:
        change = -rng.randint(4, 12)
    else:
        change = rng.randint(-3, 3)
    midterm = [float(max(10, min(100, mark + change + rng.randint(-3, 3)))) for mark in final]
    return midterm, final


def _student_plans(rng: random.Random, today: date) -> List[Dict[str, Any]]:
    """Everyone in the school: the showcase people, then made-up students filling each class."""
    plans = list(SHOWCASE)
    taken = {plan["name"] for plan in SHOWCASE}
    names = iter(_fresh_names(rng, taken))
    used_rolls = {plan["roll"] for plan in SHOWCASE}

    for grade in GRADES:
        for section in SECTIONS:
            present = sum(1 for plan in SHOWCASE if plan["grade"] == grade and plan["section"] == section)
            position = 1
            for _ in range(STUDENTS_PER_CLASS - present):
                while _class_roll(grade, section, position) in used_rolls:
                    position += 1
                midterm, final = _academic_marks(rng)
                plans.append({
                    "name": next(names),
                    "roll": _class_roll(grade, section, position),
                    "grade": grade,
                    "section": section,
                    "midterm": midterm,
                    "final": final,
                    "fees": _pick_weighted(rng, FEE_PROFILES)[0],
                })
                position += 1
    return plans


def _add_exam(session: Session, student_id: int, marks: Sequence[float], exam_type: str, year_id: int) -> None:
    session.add_all([
        Result(student_id=student_id, subject=subject, marks_obtained=float(mark), total_marks=TOTAL_MARKS, exam_type=exam_type, academic_year_id=year_id)
        for subject, mark in zip(SUBJECTS, marks)
    ])


def _payments_for(rng: random.Random, profile: str, position: int, count: int, amount: float, due: date, today: date) -> List[Tuple[float, date]]:
    """What was paid on one invoice. `position` counts months from the oldest."""
    is_latest = position == count - 1
    is_second_latest = position == count - 2
    if profile == "behind" and (is_latest or is_second_latest):
        return []
    if profile == "this_month_open" and is_latest:
        return []
    if profile == "part_paid" and is_second_latest:
        first_part = round(amount / 2, -2)
        return [(first_part / 2, due - timedelta(days=3)), (first_part / 2, due + timedelta(days=6))]
    if is_latest and due > today and rng.random() < 0.5:
        return []
    return [(amount, due - timedelta(days=rng.randint(0, 6)))]


def _add_fees(session: Session, rng: random.Random, student_id: int, profile: str, enrolled: date, today: date, used_challans: set) -> None:
    months = [month for month in _billing_months(today) if month.replace(day=28) >= enrolled]
    for position, month in enumerate(months):
        amount = MONTHLY_TUITION + (EXAM_FEE if month.month in EXAM_FEE_MONTHS else 0.0)
        due = month.replace(day=DUE_DAY)
        payments = [
            (paid, min(when, today))
            for paid, when in _payments_for(rng, profile, position, len(months), amount, due, today)
        ]
        while True:
            challan = f"CHN-{rng.randint(1000, 9999)}"
            if challan not in used_challans:
                used_challans.add(challan)
                break
        invoice = Invoice(
            student_id=student_id,
            amount=amount,
            month=month.strftime("%B %Y"),
            due_date=due.strftime(DUE_DATE_DISPLAY_FORMAT),
            challan_number=challan,
            status=payment_status(amount, sum(paid for paid, _ in payments)),
            created_at=_moment(min(month, today)),
        )
        session.add(invoice)
        session.flush()
        session.add_all([
            Payment(invoice_id=invoice.id, amount_paid=paid, paid_at=_moment(when), payment_mode=rng.choice(["cash", "bank", "online"]))
            for paid, when in payments
        ])


def _safe_output(path: Path, replace: bool) -> Path:
    path = Path(path).resolve()
    if "demo" not in path.name.lower():
        raise ValueError(f"Refusing to write to '{path.name}': the demo database's file name must contain 'demo'.")
    if path.exists():
        if not replace:
            raise FileExistsError(f"{path} already exists. Run with --replace to rebuild it.")
        path.unlink()
    return path


def build_demo_database(path: Path, today: Optional[date] = None, admin_password: str = "", replace: bool = False) -> Dict[str, int]:
    """Builds the file, and returns what it holds. The same day always gives the same data."""
    today = today or school_today()
    output = _safe_output(path, replace)
    rng = random.Random(SEED)
    engine = create_engine(f"sqlite:///{output.as_posix()}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        ensure_admin_account(session, is_production=False, admin_password=admin_password)
        year = AcademicYear(label=academic_session(today), is_current=True)
        session.add(year)
        session.flush()
        session.add_all([FeeStructure(grade=grade, amount=MONTHLY_TUITION, academic_year_id=year.id) for grade in GRADES])

        plans = _student_plans(rng, today)
        used_challans: set = set()
        session_start = _billing_months(today)[0]
        for index, plan in enumerate(plans):
            days_ago = plan.get("enrolled_days_ago")
            enrolled = today - timedelta(days=days_ago) if days_ago is not None else session_start
            student = Student(
                name=plan["name"],
                roll_number=plan["roll"],
                grade=plan["grade"],
                section=plan["section"],
                guardian_name=_guardian(rng, plan["name"]),
                phone=_phone(100000 + index),
                dob=_dob(rng, plan["grade"], today),
                created_at=_moment(enrolled),
                archived_at=_moment(today - timedelta(days=20)) if plan.get("archived") else None,
            )
            session.add(student)
            session.flush()
            if plan["midterm"]:
                _add_exam(session, student.id, plan["midterm"], MIDTERM, year.id)
                _add_exam(session, student.id, plan["final"], FINAL_TERM, year.id)
            _add_fees(session, rng, student.id, plan["fees"], enrolled, today, used_challans)
        session.commit()
        summary = {"students": len(plans), "invoices": len(used_challans)}
    engine.dispose()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the fictional Khairpur demo database.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="File to write. Its name must contain 'demo'.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing demo database.")
    args = parser.parse_args()

    summary = build_demo_database(args.output, admin_password=os.getenv("DEMO_ADMIN_PASSWORD", ""), replace=args.replace)
    print(f"Built {args.output}: {summary['students']} students, {summary['invoices']} challans. Username: {DEMO_ADMIN_USERNAME}")


if __name__ == "__main__":
    main()
