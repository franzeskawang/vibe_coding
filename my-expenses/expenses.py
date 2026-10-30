#!/usr/bin/env python3
"""List expenses from a UTF-8 CSV file."""

import argparse
import csv
import io
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


# 定義終端顏色碼、CSV 欄位名稱與取消標記。
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
HEADERS = ("\u65e5\u671f", "\u9805\u76ee", "\u91d1\u984d")
CATEGORY_KEYWORDS = (
    ("\u9910\u98f2", ("\u65e9\u9910", "\u5348\u9910", "\u665a\u9910", "\u5496\u5561", "\u98f2\u6599")),
    ("\u4ea4\u901a", ("\u6377\u904b", "\u516c\u8eca", "\u8a08\u7a0b\u8eca", "\u9ad8\u9435")),
    ("\u5a1b\u6a02", ("\u96fb\u5f71", "\u5531\u6b4c", "\u904a\u6232")),
)
OTHER_CATEGORY = "\u5176\u4ed6"
CANCEL = object()


# 讀取使用者輸入，支援按 Esc 立即回到上一層。
def read_input(prompt):
    """Read one line, returning None immediately when Escape is pressed."""
    # 管線輸入以 ESC 字元作為取消記號。
    if not sys.stdin.isatty():
        answer = input(prompt)
        return None if answer == "\x1b" else answer

    print(prompt, end="", flush=True)
    # Windows 控制台用 msvcrt 逐鍵讀取，可直接偵測 Esc。
    if sys.platform == "win32":
        import msvcrt

        chars = []
        while True:
            char = msvcrt.getwch()
            if char == "\x1b":
                print()
                return None
            if char in ("\r", "\n"):
                print()
                return "".join(chars)
            if char in ("\x00", "\xe0"):
                msvcrt.getwch()  # Consume the second part of a special key.
                continue
            if char == "\x03":
                raise KeyboardInterrupt
            if char in ("\b", "\x7f"):
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
                continue
            chars.append(char)
            print(char, end="", flush=True)

    # Unix 終端切換至逐鍵輸入，結束後還原終端設定。
    import termios
    import tty

    fd = sys.stdin.fileno()
    previous_mode = termios.tcgetattr(fd)
    chars = []
    try:
        tty.setraw(fd)
        while True:
            char = sys.stdin.read(1)
            if char in ("\r", "\n"):
                print()
                return "".join(chars)
            if char == "\x1b":
                print()
                return None
            if char in ("\x03", "\x04"):
                raise KeyboardInterrupt
            if char in ("\b", "\x7f"):
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
                continue
            chars.append(char)
            print(char, end="", flush=True)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous_mode)


# 處理命令列參數，包含 CSV 路徑與顏色選項。
def parse_args():
    parser = argparse.ArgumentParser(
        description="\u4f9d\u5e8f\u5217\u51fa\u652f\u51fa\u4e26\u8a08\u7b97\u7e3d\u984d\u3002"
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("expenses.csv"),
        help="CSV \u6a94\u6848\u8def\u5f91\uff08\u9810\u8a2d\u70ba\u7a0b\u5f0f\u540c\u8cc7\u6599\u593e\u4e0b\u7684 expenses.csv\uff09",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="\u95dc\u9589\u5f69\u8272\u8f38\u51fa",
    )
    return parser.parse_args()


# 讀取 CSV 並檢查欄位和金額，回傳資料或錯誤訊息。
def load_expenses(csv_path):
    """Read and validate rows, returning (rows, error)."""
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                return [], None

            missing_headers = [header for header in HEADERS if header not in reader.fieldnames]
            if missing_headers:
                missing = ", ".join(missing_headers)
                return None, f"CSV \u7f3a\u5c11\u6b04\u4f4d\uff1a{missing}"

            rows = []
            for line_number, row in enumerate(reader, start=2):
                if row is None or all(not (value or "").strip() for value in row.values()):
                    continue
                if None in row:
                    return None, f"CSV \u7b2c {line_number} \u884c\u7684\u6b04\u4f4d\u6578\u591a\u65bc\u6a19\u984c"

                amount_text = (row.get("\u91d1\u984d") or "").strip()
                try:
                    amount = Decimal(amount_text)
                except InvalidOperation:
                    return None, f"CSV \u7b2c {line_number} \u884c\u7684\u91d1\u984d\u4e0d\u662f\u6709\u6548\u6578\u5b57\uff1a{amount_text!r}"
                if not amount.is_finite():
                    return None, f"CSV \u7b2c {line_number} \u884c\u7684\u91d1\u984d\u5fc5\u9808\u662f\u6709\u9650\u6578\u5b57"

                rows.append(
                    {
                        "date": (row.get("\u65e5\u671f") or "").strip(),
                        "item": (row.get("\u9805\u76ee") or "").strip(),
                        "amount_text": amount_text,
                        "amount": amount,
                    }
                )
            return rows, None
    except (OSError, csv.Error) as error:
        return None, f"\u7121\u6cd5\u8b80\u53d6 {csv_path}: {error}"


# 依照 docs/categories.md 的關鍵字，將項目歸入分類。
def categorize_item(item):
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in item for keyword in keywords):
            return category
    return OTHER_CATEGORY


# 主選單程式主流程，轉交列出、新增與刪除功能。
def main():
    args = parse_args()
    csv_path = args.csv_file
    use_color = sys.stdout.isatty() and not args.no_color

    # 終端支援時才套用 ANSI 色碼。
    def color(text, code):
        return f"{code}{text}{RESET}" if use_color else text

    while True:
        print("\n1. \u5217\u51fa  2. \u65b0\u589e  4. \u522a\u9664  0. \u96e2\u958b")
        try:
            choice = read_input("\u8acb\u9078\u64c7\uff1a")
        except EOFError:
            print()
            return 0

        if choice is None:
            continue
        choice = choice.strip()
        if choice == "0":
            return 0
        if choice == "1":
            result = list_expenses(csv_path, color)
            if result:
                return result
        elif choice == "2":
            result = add_expense(csv_path)
            if result is CANCEL:
                print("\u5df2\u53d6\u6d88\uff0c\u56de\u5230\u4e3b\u9078\u55ae\u3002")
            elif result:
                print(result, file=sys.stderr)
            else:
                print("\u5df2\u65b0\u589e\u652f\u51fa\u3002")
        elif choice == "4":
            delete_expense(csv_path, color)
        else:
            print("\u9078\u9805\u7121\u6548\uff0c\u8acb\u8f38\u5165 1\u30012\u30014 \u6216 0\u3002")


# 列出所有記帳並計算總金額。
def list_expenses(csv_path, color):
    rows, error = load_expenses(csv_path)
    if error:
        print(error, file=sys.stderr)
        return 1
    if not rows:
        print(color("\u6c92\u6709\u652f\u51fa\u8cc7\u6599\u3002", CYAN))
        return 0

    total = sum((row["amount"] for row in rows), Decimal("0"))
    subtotals = {}
    for number, row in enumerate(rows, start=1):
        category = categorize_item(row["item"])
        subtotals[category] = subtotals.get(category, Decimal("0")) + row["amount"]
        print(
            f"{color(f'{number}.', YELLOW)} "
            f"{color(row['date'], CYAN)}  {color(row['item'], CYAN)}  "
            f"{color(row['amount_text'], GREEN)}"
        )
    print(f"\u7e3d\u91d1\u984d\uff1a{color(format(total, 'f'), GREEN)}")
    print("\u5206\u985e\u5c0f\u8a08\uff1a")
    for category, _ in CATEGORY_KEYWORDS:
        if category in subtotals:
            print(f"  {category}\uff1a{color(format(subtotals[category], 'f'), GREEN)}")
    if OTHER_CATEGORY in subtotals:
        print(f"  {OTHER_CATEGORY}\uff1a{color(format(subtotals[OTHER_CATEGORY], 'f'), GREEN)}")
    return 0


# 收集新記帳資料，驗證後附加到 CSV。
def add_expense(csv_path):
    rows, error = load_expenses(csv_path)
    if error:
        return error

    while True:
        try:
            date_answer = read_input("\u65e5\u671f\uff08YYYY-MM-DD\uff0c\u76f4\u63a5\u6309 Enter \u4ee5\u4eca\u5929\uff09\uff1a")
        except EOFError:
            return "\u8f38\u5165\u5df2\u4e2d\u65b7\uff0c\u6c92\u6709\u65b0\u589e\u8cc7\u6599\u3002"
        if date_answer is None:
            return CANCEL
        date_text = date_answer.strip()
        # 日期可留白使用今天，輸入時必須是 YYYY-MM-DD。
        if not date_text:
            date_text = date.today().isoformat()
            break
        try:
            parsed_date = date.fromisoformat(date_text)
            if parsed_date.isoformat() == date_text:
                break
        except ValueError:
            pass
        print("\u65e5\u671f\u683c\u5f0f\u932f\u8aa4\uff0c\u8acb\u4f7f\u7528 YYYY-MM-DD\u3002")

    while True:
        try:
            item_answer = read_input("\u9805\u76ee\uff1a")
        except EOFError:
            return "\u8f38\u5165\u5df2\u4e2d\u65b7\uff0c\u6c92\u6709\u65b0\u589e\u8cc7\u6599\u3002"
        if item_answer is None:
            return CANCEL
        item = item_answer.strip()
        # 項目去除前後空白後不可為空。
        if item:
            break
        print("\u9805\u76ee\u4e0d\u80fd\u7a7a\u767d\u3002")

    while True:
        try:
            amount_answer = read_input("\u91d1\u984d\uff08\u5927\u65bc 0 \u7684\u6574\u6578\uff09\uff1a")
        except EOFError:
            return "\u8f38\u5165\u5df2\u4e2d\u65b7\uff0c\u6c92\u6709\u65b0\u589e\u8cc7\u6599\u3002"
        if amount_answer is None:
            return CANCEL
        amount_text = amount_answer.strip()
        try:
            # 只接受大於零的整數金額。
            amount = int(amount_text)
            if amount > 0:
                break
        except ValueError:
            pass
        print("\u91d1\u984d\u5fc5\u9808\u662f\u5927\u65bc 0 \u7684\u6574\u6578\uff0c\u8acb\u91cd\u65b0\u8f38\u5165\u3002")

    try:
        # 新檔或空檔先寫入欄位列名，以追加方式保留既有資料。
        write_header = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(HEADERS)
            writer.writerow((date_text, item, amount))
    except OSError as error:
        return f"\u7121\u6cd5\u5beb\u5165 {csv_path}: {error}"
    return None


# 列出記帳、驗證使用者輸入的編號，只刪除指定列。
def delete_expense(csv_path, color):
    rows, error = load_expenses(csv_path)
    if error:
        print(error, file=sys.stderr)
        return
    if not rows:
        print(color("\u6c92\u6709\u652f\u51fa\u8cc7\u6599\uff0c\u6c92\u6709\u53ef\u522a\u9664\u7684\u8a18\u5e33\u3002", CYAN))
        return

    for number, row in enumerate(rows, start=1):
        print(
            f"{color(f'{number}.', YELLOW)} "
            f"{color(row['date'], CYAN)}  {color(row['item'], CYAN)}  "
            f"{color(row['amount_text'], GREEN)}"
        )

    while True:
        try:
            answer = read_input("\u8acb\u8f38\u5165\u8981\u522a\u9664\u7684\u7de8\u865f\uff1a")
        except EOFError:
            print("\n\u8f38\u5165\u5df2\u4e2d\u65b7\uff0c\u6c92\u6709\u522a\u9664\u8a18\u5e33\u3002")
            return
        if answer is None:
            print("\u5df2\u53d6\u6d88\uff0c\u56de\u5230\u4e3b\u9078\u55ae\u3002")
            return
        answer = answer.strip()

        try:
            selected = int(answer)
        except ValueError:
            print("\u8f38\u5165\u7121\u6548\uff1a\u8acb\u8f38\u5165\u6574\u6578\u7de8\u865f\u3002")
            continue
        if selected < 1:
            print("\u7de8\u865f\u7121\u6548\uff1a\u7de8\u865f\u4e0d\u80fd\u5c0f\u65bc 1\u3002")
            continue
        if selected > len(rows):
            print(f"\u7de8\u865f\u8d85\u51fa\u7bc4\u570d\uff1a\u8acb\u8f38\u5165 1 \u5230 {len(rows)}\u3002")
            continue
        break

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            # 讀取 CSV 所有列資料，保留其他記帳不變。
            records = list(csv.reader(csv_file))

        kept_records = records[:1]
        data_number = 0
        for record in records[1:]:
            if not any(value.strip() for value in record):
                kept_records.append(record)
                continue
            data_number += 1
            if data_number != selected:
                kept_records.append(record)

        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerows(kept_records)
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            csv_file.write(output.getvalue())
    except (OSError, csv.Error) as error:
        print(f"\u7121\u6cd5\u522a\u9664\u8a18\u5e33\uff1a{error}", file=sys.stderr)
        return

    print(f"\u5df2\u522a\u9664\u7b2c {selected} \u7b46\u8a18\u5e33\u3002")


# 直接執行此檔案時啟動主程式。
if __name__ == "__main__":
    raise SystemExit(main())
