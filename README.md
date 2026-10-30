# 角色扮演 Discord Bot

可套用任何角色的 Discord 聊天機器人，透過長庚大學 CGU LLM API 呼叫 GPT 回答訊息。內建角色：《偵探已經，死了。》的「西耶絲塔」。

## 功能

- **角色扮演**：角色設定寫在 `personas/` 資料夾的文字檔，改 `.env` 的 `PERSONA` 就能換角色。
- **記憶功能**：每個頻道各自記住對話。最近的對話保留原文，較早的對話自動整理成重點摘要，重開程式也不會忘記。每個角色的記憶分開存。
- **兩種使用模式**：
  - 設定專屬頻道：在該頻道每則訊息都回應，不用 `@`。
  - 不設定：任何頻道都能用，但要 `@` Bot。
- **長訊息自動分段**：超過 Discord 2000 字上限時會自動切開。

## 使用方式

| 動作 | 怎麼做 |
|---|---|
| 跟 Bot 聊天 | 專屬頻道直接打字；其他頻道輸入 `@Bot名稱 你的訊息` |
| 清除記憶 | 輸入 `!reset`（其他頻道要 `@Bot名稱 !reset`） |

## 啟動

在資料夾裡點兩下 **`start.bat`**，看到「已登入：Bot名稱」就代表上線了。

- 關掉黑色視窗，Bot 就會下線。
- 修改 `.env` 或 `bot.py` 之後，要關掉視窗重新啟動才會生效。

> 不要直接用 `python bot.py` 執行，套件裝在 `.venv` 裡，會出現 `No module named 'discord'`。

## 設定（`.env`）

| 設定 | 說明 |
|---|---|
| `DISCORD_TOKEN` | Discord Bot Token（開發者頁面 → Bot → Reset Token） |
| `OPENAI_API_KEY` | CGU API Key（[API Key 頁面](https://air.cgu.edu.tw/workspace4/LLMAPI/index.php)） |
| `OPENAI_BASE_URL` | `https://air.cgu.edu.tw/cgullmapi/v1` |
| `OPENAI_MODEL` | 使用的模型，目前是 `gpt-6-luna` |
| `CHANNEL_ID` | 專屬頻道 ID，留空 = 任何頻道都能用但要 `@` |
| `PERSONA` | 要套用的角色，填 `personas/` 裡的檔名（不含 `.txt`），例如 `siesta` |

> `.env` 裡有金鑰，不要分享、截圖或上傳到 GitHub。

### 可用模型

| 模型 | 特色 | 額度 |
|---|---|---|
| `gpt-6-luna` | 快（約 4 秒）、回答簡潔自然 | OpenAI 美元額度 |
| `gpt-oss-120b` | 較慢（約 8 秒）、回答詳細 | 學校算力池（不花美元） |

美元額度用完時，把 `OPENAI_MODEL` 改成 `gpt-oss-120b` 即可。其他模型見 [CGU API 說明](https://air.cgu.edu.tw/workspace4/LLMAPI/api_call.html)。

### 取得頻道 ID

1. Discord → 使用者設定 → 進階 → 開啟 **開發者模式**。
2. 對頻道按右鍵 → **複製頻道 ID**。

## 新增或切換角色

1. 複製 `personas/_範本.txt`，改名成英文檔名，例如 `personas/rem.txt`。
2. 打開檔案，把作品、角色名稱、語氣、口頭禪等內容換成你要的角色，存檔時選 **UTF-8** 編碼。
3. 打開 `.env`，改成 `PERSONA=rem`。
4. 關掉黑色視窗，重新點兩下 `start.bat`。啟動訊息會顯示目前的角色，例如 `已登入：...（角色：rem，模型：gpt-6-luna）`。

補充：

- **Bot 名稱和頭像：** 要到 Discord 開發者頁面的 **Bot** 頁另外修改。
- **回覆格式規則：** 「使用繁體中文、回覆簡潔」這些規則所有角色共用，寫在 `bot.py` 的 `FORMAT_RULES`，角色檔裡不用重寫。
- **範本檔：** 以 `_` 開頭的檔案不會被當成角色。
- **填錯檔名：** 啟動時會列出所有可用的角色。

## 調整（`bot.py`）

| 項目 | 位置 |
|---|---|
| 所有角色共用的回覆格式 | `FORMAT_RULES` |
| 摘要規則 | `SUMMARY_PROMPT` |
| 累積幾則訊息就壓縮成摘要 | `MAX_HISTORY = 20` |
| 壓縮後保留幾則原文 | `KEEP_RECENT = 10` |

## 檔案說明

```
discord-gpt-bot/
├── bot.py             主程式
├── start.bat          啟動檔（點兩下執行）
├── .env               金鑰與設定（不要外流）
├── requirements.txt   需要的套件
├── personas/          角色設定
│   ├── siesta.txt     西耶絲塔
│   └── _範本.txt      新角色範本
├── memory/            對話記憶（角色名稱/頻道ID.json）
├── .venv/             Python 環境
└── .gitignore
```

## 常見問題

| 狀況 | 原因與解法 |
|---|---|
| `No module named 'discord'` | 用 `start.bat` 啟動，不要直接執行 `python bot.py` |
| `PrivilegedIntentsRequired` | 開發者頁面 → Bot → Privileged Gateway Intents → 打開 **Message Content Intent** 並存檔 |
| Bot 在線但不回應 | 沒設 `CHANNEL_ID` 時要 `@` 它；或 Bot 沒有該頻道的檢視、傳送訊息權限 |
| 回「呼叫 GPT 時發生錯誤」 | 看黑色視窗的錯誤訊息：`401` 金鑰錯誤、`403` 額度用完或模型不允許、`404` 模型名稱錯誤 |
| Bot 答非所問、一直扯舊話題 | 輸入 `!reset` 清除記憶 |
| 啟動時顯示「找不到角色設定檔」 | `.env` 的 `PERSONA` 要和 `personas/` 裡的檔名一樣（不含 `.txt`） |
| 角色說話出現亂碼 | 角色檔要用 UTF-8 編碼存檔 |

## 重新安裝（換電腦或從 GitHub 下載）

`.env`、`.venv/`、`memory/` 不會上傳到 GitHub。在新電腦上，先在資料夾裡執行：

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

再打開 `.env` 填入 `DISCORD_TOKEN` 和 `OPENAI_API_KEY`。

## 注意

- 對話內容會存在 `memory/` 資料夾（在這台電腦上），建議讓頻道成員知道。
- 所有人的提問都使用你的 CGU API 額度，可在 API Key 頁面查看剩餘額度。
