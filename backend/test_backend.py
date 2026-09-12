import os
import io
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all_endpoints():
    print("--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200, res.text
    print("Root OK:", res.json())

    print("\n--- 2. Testing Auth Login ---")
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    token = token_data["access_token"]
    print(f"Login OK! Got token for user {token_data['username']}")

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 3. Testing Students List & CRUD ---")
    students_res = client.get("/students", headers=headers)
    assert students_res.status_code == 200
    students = students_res.json()
    print(f"Total students retrieved: {len(students)}")
    assert len(students) >= 50

    # Add a test student
    new_s = client.post("/students", headers=headers, json={
        "name": "Test Student",
        "roll_number": "999",
        "grade": "Grade 8",
        "section": "A",
        "guardian_name": "Test Guardian",
        "phone": "0300-1112233",
        "dob": "2011-01-01"
    })
    assert new_s.status_code == 200
    created_id = new_s.json()["id"]
    print("Created test student ID:", created_id)

    # Delete test student
    del_res = client.delete(f"/students/{created_id}", headers=headers)
    assert del_res.status_code == 200
    print("Deleted test student cleanly")

    print("\n--- 4. Testing Fees & Challan PDF Generation ---")
    fees_res = client.get("/fees", headers=headers)
    assert fees_res.status_code == 200
    invoices = fees_res.json()
    print(f"Total invoices retrieved: {len(invoices)}")
    assert len(invoices) > 0

    first_inv_id = invoices[0]["id"]
    pdf_res = client.get(f"/fees/{first_inv_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
    print(f"Fee Challan PDF generated successfully! Size: {len(pdf_res.content)} bytes")

    print("\n--- 5. Testing Results & Report Card PDF Generation ---")
    first_student_id = students[0]["id"]
    results_res = client.get(f"/results/{first_student_id}", headers=headers)
    assert results_res.status_code == 200
    res_data = results_res.json()
    print(f"Results for student {res_data['student']['name']}: {len(res_data['results'])} subjects. Summary: {res_data['summary']}")

    report_pdf_res = client.get(f"/results/{first_student_id}/report-card/pdf")
    assert report_pdf_res.status_code == 200
    assert report_pdf_res.headers["content-type"] == "application/pdf"
    assert len(report_pdf_res.content) > 1000
    print(f"Report Card PDF generated successfully! Size: {len(report_pdf_res.content)} bytes")

    print("\n--- 6. Testing Dashboard Stats ---")
    dash_res = client.get("/dashboard/stats", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    print("Dashboard KPIs:", dash_data["kpis"])
    print("Grade Distribution:", dash_data["grade_distribution"])

    print("\n--- 7. Testing AI At-Risk Prediction with SHAP ---")
    ai_res = client.get("/ai/at-risk", headers=headers)
    assert ai_res.status_code == 200
    at_risk_list = ai_res.json()
    print(f"AI evaluated {len(at_risk_list)} students.")
    high_risk = [s for s in at_risk_list if s["risk_category"] == "High"]
    print(f"High risk students identified: {len(high_risk)}")
    if high_risk:
        sample = high_risk[0]
        print(f"Sample High-Risk Student: {sample['name']} | Roll: {sample['roll_number']} | Risk: {sample['risk_score']}% | Reasons: {sample['top_reasons']}")

    print("\n--- 8. Testing RAG Policy Chatbot ---")
    # Topics
    topics_res = client.get("/chatbot/topics")
    assert topics_res.status_code == 200
    print(f"Chatbot topics available: {len(topics_res.json()['topics'])}")

    # Ask Question
    chat_q = client.post("/chatbot/ask", json={"question": "What is the fee refund policy?"})
    assert chat_q.status_code == 200
    chat_ans = chat_q.json()
    print(f"Chatbot Question: What is the fee refund policy?")
    print(f"Chatbot Answer: {chat_ans['answer']}")
    print(f"Sources: {chat_ans['sources']} | Grounded: {chat_ans['grounded']}")

    print("\n=======================================================")
    print(">>> ALL 8 BACKEND TEST SUITES PASSED SUCCESSFULLY! <<<")
    print("=======================================================")

if __name__ == "__main__":
    test_all_endpoints()
