/** A student's saved mark as text for an input box, and blank when there is none. */
export function markText(mark) {
  return mark === null || mark === undefined ? '' : String(mark);
}

/** The total to start with: what is already saved for this class, or 100. */
export function startingTotal(students) {
  return students.find((student) => student.total_marks)?.total_marks ?? 100;
}

/**
 * What stops a class sheet being saved, by student id. A blank box means "not entered" and is
 * left alone, so saving part of a class never wipes anything.
 */
export function markProblems(rows, totalText) {
  const total = Number(totalText);
  const problems = {};
  for (const row of rows) {
    const text = row.mark.trim();
    if (text === '') continue;
    const mark = Number(text);
    if (Number.isNaN(mark) || mark < 0) problems[row.id] = 'Enter a number, 0 or more.';
    else if (total > 0 && mark > total) problems[row.id] = `More than the total of ${total}.`;
  }
  return problems;
}

export function totalProblem(totalText) {
  const total = Number(totalText);
  if (!totalText || Number.isNaN(total) || total <= 0) return 'Enter total marks greater than zero.';
  return total > 1000 ? 'Total marks cannot be more than 1000.' : '';
}

/** Only the boxes with something in them are sent. */
export function entriesToSave(rows) {
  return rows
    .filter((row) => row.mark.trim() !== '')
    .map((row) => ({ student_id: row.id, marks_obtained: Number(row.mark) }));
}
