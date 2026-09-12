import random
from datetime import datetime, date
from sqlmodel import Session, select
from database import engine, create_db_and_tables
from models.user import User, hash_password
from models.student import Student
from models.fee import AcademicYear, FeeStructure, Invoice, Payment
from models.result import Result
from config import GRADES, SUBJECTS

PAKISTANI_NAMES = [
    # Boys
    "Ahmed Khan", "Bilal Tariq", "Muhammad Usman", "Hamza Ali", "Zain Ul Abideen",
    "Daniyal Shah", "Saad Rafique", "Umar Farooq", "Hassan Raza", "Abdullah Malik",
    "Faizan Butt", "Taha Siddiqui", "Haris Mehmood", "Shahzaib Abbasi", "Waleed Aslam",
    "Mustafa Qureshi", "Subhan Cheema", "Arham Javed", "Ali Haider", "Ibrahim Afridi",
    "Sufyan Dar", "Rehan Baig", "Farhan Saeed", "Zubair Hashmi", "Talha Nadeem",
    # Girls
    "Ayesha Fatima", "Zoya Malik", "Fatima Noor", "Eman Zahra", "Hania Amir",
    "Maryam Nawaz", "Laiba Tariq", "Minahil Khan", "Zainab Bibi", "Mahnoor Iqbal",
    "Anaya Rehman", "Hoorain Fatima", "Khadija Tul Kubra", "Bareera Ali", "Kinza Hashmi",
    "Sana Mir", "Alishba Khan", "Mishal Tahir", "Rameen Farooq", "Sadia Pervez",
    "Iqra Aziz", "Syeda Dua", "Mehak Gul", "Natalia Shah", "Yumna Zaidi"
]

GUARDIAN_NAMES = [
    "Tariq Mehmood", "Farooq Ahmed", "Malik Arshad", "Siddique Akbar", "Rashid Javed",
    "Dr. Nadeem Abbasi", "Shahid Raza", "Kashif Ali", "Zafar Iqbal", "Mian Mansha",
    "Irfan Cheema", "Sohail Butt", "Naveed Aslam", "Babar Azam", "Kamran Akmal",
    "Asif Afridi", "Waqar Younis", "Wasim Akram", "Shoaib Akhtar", "Saqlain Mushtaq"
]

def seed_database():
    print("=== [EduCore AI] Seeding Database with 50 Students & Historical Records ===")
    create_db_and_tables()

    with Session(engine) as session:
        # Check if already seeded
        existing_students = session.exec(select(Student)).all()
        if len(existing_students) >= 50:
            print(f"[Seed] Database already contains {len(existing_students)} students. Skipping seed.")
            return

        # 1. Seed Admin User
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin"
            )
            session.add(admin)
            print("[Seed] Created admin account: admin / admin123")

        # 2. Seed Academic Year
        ay = session.exec(select(AcademicYear).where(AcademicYear.label == "2025-2026")).first()
        if not ay:
            ay = AcademicYear(label="2025-2026", is_current=True)
            session.add(ay)
            session.commit()
            session.refresh(ay)

        # 3. Seed Fee Structures
        for g in GRADES:
            fs = session.exec(select(FeeStructure).where(FeeStructure.grade == g)).first()
            if not fs:
                session.add(FeeStructure(
                    grade=g,
                    label="Monthly Tuition Fee",
                    amount=3500.0,
                    academic_year_id=ay.id
                ))

        # 4. Seed 50 Students
        # Distribution: 10 per grade (5 in Section A, 5 in Section B)
        student_objs = []
        name_idx = 0

        # Dedicated profiles to ensure exact showcase examples
        # Student 1: Ahmed Khan (Roll 045, Grade 8-B) - Featured for Challan & Report Card
        ahmed = Student(
            name="Ahmed Khan",
            roll_number="045",
            grade="Grade 8",
            section="B",
            guardian_name="Tariq Khan",
            phone="0300-5551234",
            dob="2011-04-14"
        )
        session.add(ahmed)
        student_objs.append(ahmed)

        # Student 2: Bilal Tariq (Roll 012, Grade 9-A) - High Risk Student with 85% risk
        bilal = Student(
            name="Bilal Tariq",
            roll_number="012",
            grade="Grade 9",
            section="A",
            guardian_name="Tariq Mehmood",
            phone="0321-4448899",
            dob="2010-09-22"
        )
        session.add(bilal)
        student_objs.append(bilal)

        # Student 3: Daniyal Shah (Roll 018, Grade 10-B) - High Risk Student
        daniyal = Student(
            name="Daniyal Shah",
            roll_number="018",
            grade="Grade 10",
            section="B",
            guardian_name="Shahid Shah",
            phone="0333-7776655",
            dob="2009-02-18"
        )
        session.add(daniyal)
        student_objs.append(daniyal)

        # Student 4: Zoya Malik (Roll 023, Grade 7-A) - Medium Risk Student
        zoya = Student(
            name="Zoya Malik",
            roll_number="023",
            grade="Grade 7",
            section="A",
            guardian_name="Malik Arshad",
            phone="0312-9993322",
            dob="2012-06-11"
        )
        session.add(zoya)
        student_objs.append(zoya)

        # Generate remaining 46 students
        roll_counter = 101
        for grade_idx, grade in enumerate(GRADES):
            for sec in ["A", "B"]:
                target_count = 5
                # Account for pre-inserted students
                if grade == "Grade 8" and sec == "B":
                    target_count -= 1
                if grade == "Grade 9" and sec == "A":
                    target_count -= 1
                if grade == "Grade 10" and sec == "B":
                    target_count -= 1
                if grade == "Grade 7" and sec == "A":
                    target_count -= 1

                for _ in range(target_count):
                    s_name = PAKISTANI_NAMES[name_idx % len(PAKISTANI_NAMES)]
                    name_idx += 1
                    g_name = GUARDIAN_NAMES[random.randint(0, len(GUARDIAN_NAMES) - 1)]
                    phone = f"03{random.randint(10,49)}-{random.randint(1000000, 9999999)}"
                    birth_year = 2013 - grade_idx
                    dob = f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

                    st = Student(
                        name=s_name,
                        roll_number=f"{roll_counter:03d}",
                        grade=grade,
                        section=sec,
                        guardian_name=g_name,
                        phone=phone,
                        dob=dob
                    )
                    roll_counter += 1
                    session.add(st)
                    student_objs.append(st)

        session.commit()
        for s in student_objs:
            session.refresh(s)

        print(f"[Seed] Successfully created {len(student_objs)} students.")

        # 5. Seed Invoices
        # Ahmed Khan: Has CHN-1045 for October 2025 (Rs. 4,000)
        inv_ahmed = Invoice(
            student_id=ahmed.id,
            amount=4000.0,
            month="October 2025",
            due_date="10-Oct-2025",
            challan_number="CHN-1045",
            status="pending"
        )
        session.add(inv_ahmed)

        # Also give Ahmed a pending November challan to match 2 unpaid invoices in risk demo
        inv_ahmed_nov = Invoice(
            student_id=ahmed.id,
            amount=3500.0,
            month="November 2025",
            due_date="10-Nov-2025",
            challan_number="CHN-1046",
            status="pending"
        )
        session.add(inv_ahmed_nov)

        # High risk students get 2-3 pending invoices
        for risky in [bilal, daniyal]:
            for m, due in [("September 2025", "10-Sep-2025"), ("October 2025", "10-Oct-2025")]:
                session.add(Invoice(
                    student_id=risky.id,
                    amount=4000.0,
                    month=m,
                    due_date=due,
                    challan_number=f"CHN-{random.randint(2000, 9999)}",
                    status="pending"
                ))

        # Other students
        for idx, s in enumerate(student_objs):
            if s.id in [ahmed.id, bilal.id, daniyal.id]:
                continue
            
            # 75% students paid, 25% pending
            is_pending = (idx % 4 == 0)
            status = "pending" if is_pending else "paid"
            inv = Invoice(
                student_id=s.id,
                amount=4000.0,
                month="October 2025",
                due_date="10-Oct-2025",
                challan_number=f"CHN-{random.randint(2000, 9999)}",
                status=status
            )
            session.add(inv)
            session.commit()
            session.refresh(inv)

            if status == "paid":
                session.add(Payment(
                    invoice_id=inv.id,
                    amount_paid=4000.0,
                    payment_mode=random.choice(["cash", "bank", "online"])
                ))

        session.commit()
        print("[Seed] Invoices & Payment records created.")

        # 6. Seed Academic Results
        # For Ahmed Khan: matching the exact Report Card on page 9:
        # English: 78, Math: 91, Science: 85, Urdu: 72, Islamiat: 88, Pak Studies: 80 (Total 494, 82.3%, A)
        ahmed_marks = {
            "English": 78.0,
            "Mathematics": 91.0,
            "Science": 85.0,
            "Urdu": 72.0,
            "Islamiat": 88.0,
            "Pakistan Studies": 80.0
        }
        for subj, marks in ahmed_marks.items():
            session.add(Result(
                student_id=ahmed.id,
                subject=subj,
                marks_obtained=marks,
                total_marks=100.0,
                exam_type="Final Term",
                academic_year_id=ay.id
            ))

        # Bilal Tariq (High Risk showcase): Failing 3 subjects, avg marks 44%
        bilal_marks = {
            "English": 34.0,
            "Mathematics": 28.0,
            "Science": 36.0,
            "Urdu": 58.0,
            "Islamiat": 54.0,
            "Pakistan Studies": 52.0
        }
        for subj, marks in bilal_marks.items():
            session.add(Result(
                student_id=bilal.id,
                subject=subj,
                marks_obtained=marks,
                total_marks=100.0,
                exam_type="Final Term",
                academic_year_id=ay.id
            ))

        # Daniyal Shah (High Risk showcase): Failing 3 subjects
        daniyal_marks = {
            "English": 31.0,
            "Mathematics": 35.0,
            "Science": 38.0,
            "Urdu": 45.0,
            "Islamiat": 50.0,
            "Pakistan Studies": 44.0
        }
        for subj, marks in daniyal_marks.items():
            session.add(Result(
                student_id=daniyal.id,
                subject=subj,
                marks_obtained=marks,
                total_marks=100.0,
                exam_type="Final Term",
                academic_year_id=ay.id
            ))

        # Zoya Malik (Medium Risk showcase): Failing 1 subject, 58% avg
        zoya_marks = {
            "English": 52.0,
            "Mathematics": 38.0,
            "Science": 64.0,
            "Urdu": 66.0,
            "Islamiat": 72.0,
            "Pakistan Studies": 58.0
        }
        for subj, marks in zoya_marks.items():
            session.add(Result(
                student_id=zoya.id,
                subject=subj,
                marks_obtained=marks,
                total_marks=100.0,
                exam_type="Final Term",
                academic_year_id=ay.id
            ))

        # Seed marks for all remaining students with diverse profiles
        for s in student_objs:
            if s.id in [ahmed.id, bilal.id, daniyal.id, zoya.id]:
                continue

            # Assign a student profile: 20% high achievers (85-98), 65% average (60-84), 15% struggling (35-58)
            profile_roll = random.random()
            if profile_roll < 0.20:
                base_min, base_max = 82, 98
            elif profile_roll < 0.85:
                base_min, base_max = 60, 84
            else:
                base_min, base_max = 35, 58

            for subj in SUBJECTS:
                m = round(random.uniform(base_min, base_max), 1)
                # clamp
                m = min(100.0, max(20.0, m))
                session.add(Result(
                    student_id=s.id,
                    subject=subj,
                    marks_obtained=m,
                    total_marks=100.0,
                    exam_type="Final Term",
                    academic_year_id=ay.id
                ))

        session.commit()
        print("[Seed] Student exam marks seeded across all 6 subjects.")

    print("=== [EduCore AI] Database Seed Completed Successfully ===")

if __name__ == "__main__":
    seed_database()
