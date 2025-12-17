# CoDoc in MD

CoDoc in MD 是一個使用 [Reflex](https://reflex.dev/) 構建的即時協作 Markdown 編輯器。它允許使用者創建文檔，並透過即時預覽功能進行編輯。

## 功能特色

-   **即時協作**：支援多用戶同時編輯同一個文檔（目前使用記憶體內存儲進行演示）。
-   **Markdown 編輯**：整合 Monaco Editor，提供優質的程式碼編輯體驗。
-   **即時預覽**：左側編輯，右側即時渲染 Markdown 結果。
-   **多種視圖模式**：
    -   **Split**：同時顯示編輯器與預覽。
    -   **Editor**：專注於寫作，僅顯示編輯器。
    -   **Preview**：專注於閱讀，僅顯示預覽結果。
-   **用戶追蹤**：顯示當前在線的協作與其隨機生成的身份（名稱與顏色）。

## 安裝與執行

本專案使用 [Poetry](https://python-poetry.org/) 進行依賴管理。請確保您的系統已安裝 Python 3.10+ 和 Poetry。

### 1. 克隆專案

```bash
git clone <repository-url>
cd codoc_in_md
```

### 2. 安裝依賴

使用 Poetry 安裝專案所需的套件：

```bash
poetry install
```

### 3. 執行應用程式

啟動 Reflex 開發伺服器：

```bash
poetry run reflex run
```

啟動後，您可以在瀏覽器中訪問：

-   **前端頁面**：[http://localhost:3000](http://localhost:3000)
-   **後端 API**：[http://localhost:8000](http://localhost:8000)

## 使用說明

1.  **創建新文檔**：
    -   打開首頁後，系統會自動為您生成一個唯一的文檔 ID 並重定向。
    -   您也可以點擊介面上的 "New Doc" 按鈕來創建新的空白文檔。

2.  **分享與協作**：
    -   複製瀏覽器網址列中的 URL（包含 `doc_id`）。
    -   將連結分享給其他人。
    -   當其他人打開連結時，你們將進入同一個編輯空間，可以看到彼此的修改與在線狀態。

3.  **切換視圖**：
    -   使用介面上的視圖切換按鈕（Split / Editor / Preview）來調整最適合您的工作模式。

## 技術棧

-   **Reflex**: 全端 Python Web 框架。
-   **Reflex Monaco**: 整合 Monaco Editor 到 Reflex。
-   **Python 3.10+**: 核心語言。
