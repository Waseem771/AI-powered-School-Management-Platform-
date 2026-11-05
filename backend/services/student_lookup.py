"""Finds which student a question means, and refuses to guess.

A bare number is a roll number, never a database id. An id is used only when it is asked for by
name ("student id 12", or "id:12" from a tool). Several matches are all returned, so the caller
can ask which one was meant.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlmodel import Session, select

from config import SCHOOL_NAME, SUBJECTS
from models.student import Student
from services import chat_intent

ID_PREFIX = "id:"
_MIN_NAME_WORD_LENGTH = 3
_MAX_IDENTIFIER_LENGTH = 80

# Words in a question that are never read as part of a student's name.
_NOT_NAMES = frozenset(
    """
    a about academy address admission after all also am an and any are as at average
    balance be best birth by can card challan challans class collected collection contact could
    data date details did do does dob dues during each exam exams father fee fees final finals find
    first for from full get give got grade grades guardian had has have he her hers high him his how
    i id in info information invoice invoices is it its last late latest let list look low lookup
    marks me medium midterm midterms month monthly mother my name named need number of on one only
    or our out outstanding overall paid parent pay payment payments pending percentage performance
    phone please profile rank record records report result results risk roll rs school score scored
    scores search section see she should show so status student students subject subjects summary
    tell term than thanks that the their them then there these they this those to too top total
    unpaid us was we were what when where which who whose why will with would you your
    absent age again amount attendance cell daughter doing due fail failed fine kindly many mobile much now
    owe owes pass passed passing pls plz remaining son studying today
    aap batao bataen bataein dikhao hai hain hen ka ke ki kia kitna kitni kitne ko kya mein ne par se
    """.split()
) | frozenset(month for month in chat_intent.MONTH_NAMES) | frozenset(
    word.casefold() for subject in SUBJECTS for word in subject.split()
)


@dataclass(frozen=True)
class Mention:
    """Who a question seems to mean. `certain` is False when part of the name did not match."""
    students: Tuple[Student, ...] = ()
    searched: str = ""
    certain: bool = True
    explicit: bool = False

    @property
    def student(self) -> Optional[Student]:
        return self.students[0] if len(self.students) == 1 and self.certain else None

    @property
    def needs_clarifying(self) -> bool:
        if self.explicit and not self.students:
            return True
        return bool(self.students) and self.student is None


def _name_words(text: str) -> Tuple[str, ...]:
    return tuple(re.findall(r"\w+", (text or "").casefold()))


def _contains_in_order(words: Sequence[str], name: Sequence[str]) -> bool:
    size = len(name)
    return size > 0 and any(tuple(words[i:i + size]) == tuple(name) for i in range(len(words) - size + 1))


def _all_students(session: Session) -> List[Student]:
    return list(session.exec(select(Student).order_by(Student.id)).all())


def students_with_roll(students: Sequence[Student], roll: str) -> List[Student]:
    """Exact roll number first. "45" also finds "045", because staff rarely type the zeros."""
    wanted = roll.strip().casefold()
    exact = [student for student in students if student.roll_number.casefold() == wanted]
    if exact or not wanted.isdigit():
        return exact
    return [student for student in students if student.roll_number.isdigit() and int(student.roll_number) == int(wanted)]


def find_matching_students(session: Session, identifier: object) -> List[Student]:
    """Every student a tool's identifier could mean: a roll number, a name, or "id:12"."""
    text = str(identifier or "").strip()[:_MAX_IDENTIFIER_LENGTH]
    if not text:
        return []
    if text.casefold().startswith(ID_PREFIX):
        number = text[len(ID_PREFIX):].strip()
        student = session.get(Student, int(number)) if number.isdigit() else None
        return [student] if student else []

    students = _all_students(session)
    by_roll = students_with_roll(students, text)
    if by_roll or text.isdigit():
        return by_roll

    wanted = _name_words(text)
    if not wanted:
        return []
    same_name = [student for student in students if _name_words(student.name) == wanted]
    if same_name:
        return same_name
    return [student for student in students if set(wanted) <= set(_name_words(student.name))]


def _narrow_by_class(students: Sequence[Student], text: str) -> List[Student]:
    """Only ever used to choose between several matches, never to reject the only one."""
    narrowed = list(students)
    grade = chat_intent.extract_grade(text)
    section = chat_intent.extract_section(text)
    for wanted in (grade and (lambda s: s.grade == grade), section and (lambda s: s.section == section)):
        if wanted:
            kept = [student for student in narrowed if wanted(student)]
            narrowed = kept or narrowed
    return narrowed


def _without_school_name(text: str) -> str:
    return re.sub(re.escape(SCHOOL_NAME), " ", text, flags=re.IGNORECASE)


def _has_unknown_neighbour(words: Sequence[str], used: Set[str]) -> bool:
    """"Sara Malik" must not become Zoya Malik because only "Malik" is on file."""
    for index, word in enumerate(words):
        if word not in used:
            continue
        for neighbour in words[max(index - 1, 0):index + 2]:
            is_other_word = neighbour not in used and neighbour not in _NOT_NAMES
            if is_other_word and len(neighbour) >= 2 and not neighbour.isdigit():
                return True
    return False


def _mention_by_name(students: Sequence[Student], text: str) -> Mention:
    words = _name_words(_without_school_name(text))
    known = {word for student in students for word in _name_words(student.name)}
    candidates = {
        word for word in words
        if word in known and word not in _NOT_NAMES and len(word) >= _MIN_NAME_WORD_LENGTH
    }
    if not candidates:
        return Mention()

    scores = [(len(candidates & set(_name_words(student.name))), student) for student in students]
    best = max(score for score, _ in scores)
    matches = [student for score, student in scores if score == best]
    in_order = [student for student in matches if _contains_in_order(words, _name_words(student.name))]
    matches = in_order or matches

    used = {word for student in matches for word in _name_words(student.name)} & set(words)
    certain = candidates <= used and not _has_unknown_neighbour(words, used)
    searched = " ".join(word for word in words if word in used or (word not in _NOT_NAMES and not word.isdigit()))
    return Mention(tuple(_narrow_by_class(matches, text)), searched.title(), certain)


def mentioned_students(session: Session, text: str) -> Mention:
    """Who this text names, by id, roll number, or name, in that order."""
    student_id = chat_intent.explicit_student_id(text)
    if student_id is not None:
        student = session.get(Student, student_id)
        return Mention((student,) if student else (), f"student id {student_id}", explicit=True)

    students = _all_students(session)
    roll = chat_intent.explicit_roll(text)
    if roll is None:
        return _mention_by_name(students, text)

    matches = students_with_roll(students, roll)
    by_name = _mention_by_name(students, text)
    # "Ahmed, roll 012" when 012 is Bilal: show both rather than trust either.
    disagrees = bool(by_name.students) and not set(s.id for s in matches) & set(s.id for s in by_name.students)
    return Mention(tuple(matches), f"roll number {roll}", not disagrees, explicit=True)


def student_in_earlier_messages(session: Session, history: Sequence[Dict[str, Any]]) -> Mention:
    """The student the conversation was last about.

    Assistant text counts only through its roll numbers: a policy answer that says "Iqbal Day"
    is not about a student called Iqbal.
    """
    students = _all_students(session)
    for message in reversed(list(history)[-8:]):
        text = str(message.get("content", ""))
        rolls = chat_intent.all_explicit_rolls(text)
        if rolls:
            found = {student.id: student for roll in rolls for student in students_with_roll(students, roll)}
            if found:
                return Mention(tuple(found.values()), "the student above")
        elif message.get("role") == "user":
            mention = _mention_by_name(students, text)
            if mention.students:
                return mention
    return Mention()


def narrow_to_class(mention: Mention, text: str) -> Mention:
    if not (chat_intent.extract_grade(text) or chat_intent.extract_section(text)):
        return mention
    narrowed = _narrow_by_class(mention.students, text)
    return Mention(tuple(narrowed), mention.searched, mention.certain or len(narrowed) == 1)


def student_brief(student: Student) -> Dict[str, Any]:
    return {
        "id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "grade": student.grade,
        "section": student.section,
        "archived": student.archived_at is not None,
    }
