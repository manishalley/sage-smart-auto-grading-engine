"""
evaluator.py
Phase 2: Question Splitting + AI Grading + Teacher Override Support

Exam Structure:
- Part A: Q1-Q10, 1 mark each = 10 marks
- Part B: 5 units x 2 questions each (Q11-Q20), attempt 1 per unit
          Each question = 10 marks → 5 x 10 = 50 marks
- Total = 60 marks
"""

import json
import re
import os
import google.generativeai as genai


class Evaluator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")

    def load_answer_key(self, answer_key_path: str) -> dict:
        with open(answer_key_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def split_questions(self, full_text: str) -> dict:
        text = full_text.replace("Ql", "Q1").replace("O1", "Q1")
        pattern = r'(?:^|\n)\s*(?:Q(\d+)|(\d+)[.):])\s+'
        matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))

        answers = {}
        for i, match in enumerate(matches):
            q_num = match.group(1) or match.group(2)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            answer_text = text[start:end].strip()
            answers[f"Q{q_num}"] = answer_text

        return answers

    def grade_part_a(self, student_answers: dict, answer_key: dict) -> list:
        results = []
        part_a_key = answer_key.get("part_a", {})

        for q_num in [f"Q{i}" for i in range(1, 11)]:
            student_ans = student_answers.get(q_num, "").strip()
            correct_ans = part_a_key.get(q_num, "")

            if not student_ans:
                results.append({
                    "question": q_num,
                    "student_answer": "[Not attempted]",
                    "correct_answer": correct_ans,
                    "marks_awarded": 0,
                    "max_marks": 1,
                    "ai_feedback": "Not attempted.",
                    "teacher_override": None
                })
                continue

            prompt = f"""You are an exam evaluator. Grade this Part A answer (1 mark max).

Question: {q_num}
Correct Answer: {correct_ans}
Student Answer: {student_ans}

Rules:
- Award 1 mark if the core concept is correct (exact wording not required)
- Award 0 if incorrect or irrelevant
- Be lenient with minor spelling errors

Respond ONLY in this exact JSON format:
{{
  "marks": 0 or 1,
  "feedback": "one sentence explanation"
}}"""

            try:
                response = self.model.generate_content(prompt)
                raw = response.text.strip().strip("```json").strip("```").strip()
                data = json.loads(raw)
                results.append({
                    "question": q_num,
                    "student_answer": student_ans,
                    "correct_answer": correct_ans,
                    "marks_awarded": int(data.get("marks", 0)),
                    "max_marks": 1,
                    "ai_feedback": data.get("feedback", ""),
                    "teacher_override": None
                })
            except Exception as e:
                results.append({
                    "question": q_num,
                    "student_answer": student_ans,
                    "correct_answer": correct_ans,
                    "marks_awarded": 0,
                    "max_marks": 1,
                    "ai_feedback": f"[Grading error: {e}]",
                    "teacher_override": None
                })

        return results

    def grade_part_b(self, student_answers: dict, answer_key: dict) -> list:
        results = []
        part_b_key = answer_key.get("part_b", {})

        units = {
            "Unit 1": ["Q11", "Q12"],
            "Unit 2": ["Q13", "Q14"],
            "Unit 3": ["Q15", "Q16"],
            "Unit 4": ["Q17", "Q18"],
            "Unit 5": ["Q19", "Q20"],
        }

        for unit_name, q_options in units.items():
            attempted_q = None
            for q in q_options:
                if student_answers.get(q, "").strip():
                    attempted_q = q
                    break

            if not attempted_q:
                results.append({
                    "unit": unit_name,
                    "question": "Not attempted",
                    "student_answer": "",
                    "correct_answer": "",
                    "marks_awarded": 0,
                    "max_marks": 10,
                    "ai_feedback": "No question attempted for this unit.",
                    "teacher_override": None
                })
                continue

            student_ans = student_answers[attempted_q]
            q_key = part_b_key.get(attempted_q, {})
            correct_ans = q_key.get("answer", "")
            keywords = q_key.get("keywords", [])

            prompt = f"""You are a strict but fair university exam evaluator. Grade this Part B answer out of 10 marks.

Unit: {unit_name}
Question: {attempted_q}

Model Answer:
{correct_ans}

Key Concepts Expected: {', '.join(keywords)}

Student Answer:
{student_ans}

Grading Rubric:
- 9-10: Complete, accurate, well-explained with all key concepts
- 7-8: Mostly correct, minor gaps in explanation
- 5-6: Partially correct, covers some key points
- 3-4: Shows basic understanding but significant gaps
- 1-2: Very limited understanding, mostly incorrect
- 0: Not attempted or completely wrong

Respond ONLY in this exact JSON format:
{{
  "marks": <integer 0-10>,
  "feedback": "<2-3 sentences: what was good, what was missing>",
  "concepts_covered": ["list", "of", "concepts", "student", "got", "right"],
  "concepts_missing": ["list", "of", "missing", "or", "wrong", "concepts"]
}}"""

            try:
                response = self.model.generate_content(prompt)
                raw = response.text.strip().strip("```json").strip("```").strip()
                data = json.loads(raw)
                results.append({
                    "unit": unit_name,
                    "question": attempted_q,
                    "student_answer": student_ans,
                    "correct_answer": correct_ans,
                    "marks_awarded": min(10, max(0, int(data.get("marks", 0)))),
                    "max_marks": 10,
                    "ai_feedback": data.get("feedback", ""),
                    "concepts_covered": data.get("concepts_covered", []),
                    "concepts_missing": data.get("concepts_missing", []),
                    "teacher_override": None
                })
            except Exception as e:
                results.append({
                    "unit": unit_name,
                    "question": attempted_q,
                    "student_answer": student_ans,
                    "correct_answer": correct_ans,
                    "marks_awarded": 0,
                    "max_marks": 10,
                    "ai_feedback": f"[Grading error: {e}]",
                    "teacher_override": None
                })

        return results

    def apply_overrides(self, results: dict, overrides: dict) -> dict:
        for section in ["part_a", "part_b"]:
            for item in results[section]:
                q = item.get("question", "")
                if q in overrides:
                    item["teacher_override"] = overrides[q]
                    item["marks_awarded"] = overrides[q]
        return results

    def calculate_totals(self, part_a_results: list, part_b_results: list) -> dict:
        part_a_total = sum(r["marks_awarded"] for r in part_a_results)
        part_b_total = sum(r["marks_awarded"] for r in part_b_results)
        grand_total = part_a_total + part_b_total

        return {
            "part_a_total": part_a_total,
            "part_a_max": 10,
            "part_b_total": part_b_total,
            "part_b_max": 50,
            "grand_total": grand_total,
            "grand_max": 60,
            "percentage": round((grand_total / 60) * 100, 1),
            "grade": self._get_grade(grand_total)
        }

    def _get_grade(self, marks: int) -> str:
        p = (marks / 60) * 100
        if p >= 90: return "O (Outstanding)"
        if p >= 75: return "A+ (Excellent)"
        if p >= 60: return "A (Good)"
        if p >= 50: return "B (Above Average)"
        if p >= 40: return "C (Pass)"
        return "F (Fail)"

    def evaluate(self, ocr_result: dict, answer_key_path: str, session_id: str, output_dir: str) -> dict:
        print("🔄 Loading answer key...")
        answer_key = self.load_answer_key(answer_key_path)

        print("🔄 Splitting questions from OCR text...")
        student_answers = self.split_questions(ocr_result["full_text"])
        print(f"   Found {len(student_answers)} answers: {list(student_answers.keys())}")

        print("🔄 Grading Part A (Q1-Q10)...")
        part_a = self.grade_part_a(student_answers, answer_key)

        print("🔄 Grading Part B (Q11-Q20)...")
        part_b = self.grade_part_b(student_answers, answer_key)

        totals = self.calculate_totals(part_a, part_b)

        evaluation = {
            "session_id": session_id,
            "subject": answer_key.get("subject", "Unknown"),
            "student_name": answer_key.get("student_name", ""),
            "part_a": part_a,
            "part_b": part_b,
            "totals": totals
        }

        out_path = os.path.join(output_dir, session_id, "evaluation.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(evaluation, f, indent=4, ensure_ascii=False)

        print(f"✅ Evaluation complete! Total: {totals['grand_total']}/60")
        return evaluation