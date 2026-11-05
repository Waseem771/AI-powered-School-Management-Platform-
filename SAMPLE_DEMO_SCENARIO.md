# Sample Demo Scenario

A 10-minute walk-through for school owners and principals, using the fictional Roshan Demo Academy. Set it up with [DEMO_GUIDE.md](DEMO_GUIDE.md).

Everything named here was run on a demo built on 5 November 2026, and `backend/test_demo_seed.py` checks that these students stay as described. **Money and dates depend on the day you build it**, so rehearse with your own build and note your figures. The steps change records, so rebuild before each demo.

**The story:** "You run a school with Excel and paper. Here is one morning with one system."

## 1. Sign in (30 seconds)

Sign in as `admin`. Point out the name, the tagline, and the DEMO MODE label.

> "Everything here is made up, so we can use it freely. A real school sees its own name and no label."

## 2. Dashboard (1 minute)

| You should see | On 5 Nov 2026 |
|---|---|
| Current students | 119 |
| Fees collected | Rs. 942,500, 71.8% of the amount billed |
| Fees still owed | Rs. 370,000, with Rs. 90,000 overdue |
| High academic estimate | 14 students |

Choose **October 2026** under "Fees shown for", then return to **All months**. Scroll to **Recent activity**.

> "When you open this each morning, you see where the school stands. Every figure comes from a record you can open."

## 3. Find a student (1 minute)

Go to **Students**. Choose **Grade 8**, then **Section A**. Search for `Hina`, and click **Hina Soomro** (#801).

> "One page for one child: details, fees, and results. No more three registers."

## 4. Record a payment and print a receipt (2 minutes)

In **Fees** on her profile, October shows **Paid Rs. 2,000, owes Rs. 2,000, Overdue**.

1. Click **Payments** on that row to show the two earlier part payments, then close it.
2. Click **Record Payment**. Rs. 2,000 is filled in. Choose **Cash** and click **Confirm Payment**.
3. Click **Print Receipt**. Close it, and click **Done**.

Still owed now reads **Rs. 0**.

> "Part payments are normal for families here. The balance is worked out from the payments themselves, and every payment gets a numbered receipt."

To show a mistake being caught, enter more than the amount owed before confirming, and read out the message.

## 5. Issue and print a challan (1 minute)

On the same row, click **Challan** to open the 2-part A4 challan, with a bank copy and a student copy.

If you are asked about Urdu, open **Fees**, search for roll `701`, and open that student's challan. The name is printed in Urdu.

## 6. Enter marks for a class (1.5 minutes)

Go to **Exam Results** and click **Enter for a Class**. Choose **Grade 8**, section **A**, **Science**, **Final Term**. Saved marks fill in. Change one or two, and type `150` in one box to show it refused. Correct it and click **Save**.

> "A teacher does a whole class on one screen. If anything is wrong, nothing is saved."

## 7. Report card (1 minute)

In the student search on that page, type `Hina`, and choose her. Click **Report Card**.

> "A4 and ready to sign, with the promotion decision and the reasons, following your exam policy."

## 8. Early warning (1 minute)

Go to **Academic Early Warning**. Read the amber notice aloud.

| Student | Show | Point to make |
|---|---|---|
| **Danish Memon** (#901) | **Why and what next**: High, with 3 failed subjects and a fall of 21.5 points since the midterm | The reasons are the model's own, and his fees are clear |
| **Maham Shaikh** (#1001) | Low estimate, with a separate fee follow-up | Unpaid fees never make a strong student look weak |
| **Kiran Mangi** (#651) | Not enough data | New student, so no invented score |

> "This points a teacher to who may need help. It was trained on made-up students and is not proof of anything. A teacher decides."

## 9. Ask the School Assistant (1 minute)

Go to **School Assistant** and ask these in order:

| Ask | You should see |
|---|---|
| `Fees of Ali Junejo` | It asks which one: #802 or #1051 |
| `1051` | That student's fees, **From school records** |
| `How many students are there?` | 119, with 1 archived not counted |
| `What is the fee refund policy?` | The refund rules, **From policy documents** |
| `What is the capital of France?` | It says it cannot answer |

> "It uses your records and your policies, it shows which, and it says so when it does not know."

## Close (30 seconds)

> "Simple School Management, Smarter Decisions. Enrollment, fees, results, and a clear picture of your school, in one place."

## Likely questions

| Question | Honest answer |
|---|---|
| Is our data safe? | Sign-in, separate sessions, and safer storage are built. Hosting for real records and backups must be settled before a pilot, and roles for different staff are not built yet |
| Can a teacher see only their class? | Not yet. There is one admin role for now |
| Can it charge late fees? | Not yet. Challans say the amount excludes late charges |
| Does it work without internet? | No, except when run on a local computer as in this demo |
| Can it run several campuses? | Not yet, and it should not be used that way |
| How accurate is the early warning? | Unknown. It has not been tested on real students |
| What does it cost? | Decide this before the meeting |
