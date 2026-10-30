# 專案貢獻指南

## 專案結構

本專案是 Python 命令列記帳工具。`expenses.py` 包含選單、CSV 讀取與驗證、列出、新增、刪除及終端輸入處理。`expenses.csv` 是預設 UTF-8 資料檔，與程式放在同一資料夾。目前沒有套件、資源或測試目錄；新增測試時請放在 `tests/`。不要將個人記帳資料提交到版本控制。

## 執行與開發指令

本程式只需要 Python 3 標準函式庫，無須建置或安裝相依套件。

- `python expenses.py`：啟動選單並使用程式旁的 `expenses.csv`。
- `python expenses.py path/to/other.csv`：改用指定的 CSV 檔案。
- `python -m py_compile expenses.py`：檢查語法，不會啟動互動選單。

修改功能後，請用暫存 CSV 副本操作，避免改動本機記帳資料。

## 程式風格

使用四個空格縮排；函式與變數採 `snake_case`，常數採 `UPPER_SNAKE_CASE`。維持 Python 3 相容，並優先使用標準函式庫。CSV 使用 UTF-8，欄位為 `日期,項目,金額`。保留繁體中文提示與註解；終端輸入等較不直觀的流程應加上簡短說明。目前沒有設定格式化或程式檢查工具。

## 測試指南

目前沒有測試框架或既有測試套件。小幅修改至少執行 `python -m py_compile expenses.py`，並以暫存 CSV 手動操作相關選單。若新增測試，使用標準函式庫 `unittest`，檔名採 `test_*.py`，放在 `tests/` 目錄。

## 提交與合併請求

目前沒有可參考的 Git 提交歷史。提交標題請簡短並使用祈使語氣，例如 `Add expense deletion menu option`。合併請求應說明使用者可見的變更、執行過的驗證，以及 CSV 格式或資料處理方式是否變動；請勿附上真實個人記帳資料或截圖。

## 資料與設定

預設資料檔為 `expenses.csv`，也可透過命令列參數指定其他 CSV。程式碼修改不可取代或重寫使用者的 CSV 資料；若功能本身需要新增或刪除記帳，僅按該功能指定的資料列操作。依賴與設定請保持精簡。

每次回覆時都添加emoji。

分類規則見 `docs/categories.md`。
