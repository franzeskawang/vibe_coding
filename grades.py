students = []

with open("grades.csv", "r", encoding="utf-8-sig") as grades_file:
    lines = grades_file.read().splitlines()

if lines:
    headings = lines[0].split(",")
    for line in lines[1:]:
        columns = line.split(",")
        row = dict(zip(headings, columns))
        chinese = float(row["chinese"])
        english = float(row["english"])
        math = float(row["math"])
        average = (chinese + english + math) / 3
        students.append(
            {
                "name": row["name"],
                "student_id": row["student_id"],
                "chinese": chinese,
                "english": english,
                "math": math,
                "average": average,
            }
        )

passing_students = [student for student in students if student["average"] >= 60]
failing_students = [student for student in students if student["average"] < 60]
total_math = sum(student["math"] for student in students)
math_average = total_math / len(students) if students else None

reset = "\033[0m"
cyan = "\033[36m"
green = "\033[32m"
red = "\033[31m"
yellow = "\033[33m"
bold = "\033[1m"

print(f"{bold}{cyan}學生三科平均{reset}")
print(f"{cyan}+------------+------------+--------+--------+--------+--------+{reset}")
print(f"{cyan}| 姓名       | 學號       | 國文   | 英文   | 數學   | 平均   |{reset}")
print(f"{cyan}+------------+------------+--------+--------+--------+--------+{reset}")

for student in students:
    average_color = green if student["average"] >= 60 else red
    print(
        f"| {student['name']:<10} | {student['student_id']:<10} "
        f"| {student['chinese']:>6.1f} | {student['english']:>6.1f} "
        f"| {student['math']:>6.1f} | {average_color}{student['average']:>6.1f}{reset} |"
    )

print(f"{cyan}+------------+------------+--------+--------+--------+--------+{reset}")

if math_average is None:
    math_average_text = "沒有資料"
else:
    math_average_text = f"{math_average:.1f}"

passing_names = "、".join(student["name"] for student in passing_students) or "-"
failing_names = "、".join(
    f"{student['name']}（平均 {student['average']:.1f}）" for student in failing_students
) or "-"

print(f"{yellow}全班數學平均：{math_average_text}{reset}")
print(f"{green}及格名單：{passing_names}{reset}")
print(f"{green}及格人數：{len(passing_students)}/{len(students)}{reset}")
print(f"{red}不及格名單：{failing_names}{reset}")
