import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path

import discord
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).parent / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 專屬頻道：設定後 Bot 只在這個頻道回應，而且每則訊息都回，不用 @
# 留空 = 任何頻道都能用，但要 @ Bot
# 頻道 ID：Discord 開啟開發者模式後，對頻道按右鍵 → 複製 ID
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or 0)

# 角色設定放在 personas/角色名稱.txt，用 .env 的 PERSONA 選擇要套用哪一個
PERSONA_DIR = Path(__file__).parent / "personas"
PERSONA = os.getenv("PERSONA", "siesta")

# 所有角色共用的回覆格式，會接在角色設定後面
FORMAT_RULES = """
【回覆格式】
- 一律使用繁體中文。
- 這是 Discord 聊天，回覆盡量簡潔，閒聊時一到三段即可；技術問題可以完整說明。
"""


def available_personas() -> list[str]:
    return sorted(p.stem for p in PERSONA_DIR.glob("*.txt") if not p.stem.startswith("_"))


def load_persona(name: str) -> str:
    path = PERSONA_DIR / f"{name}.txt"
    if not path.exists():
        raise SystemExit(
            f"找不到角色設定檔：{path}\n可用的角色：{', '.join(available_personas()) or '（無）'}"
        )
    return path.read_text(encoding="utf-8").strip() + "\n" + FORMAT_RULES


SYSTEM_PROMPT = load_persona(PERSONA)

SUMMARY_PROMPT = """\
你負責整理聊天記錄的重點。請把「舊的重點摘要」和「新的對話」合併成一份新的重點摘要：
- 保留重要的事實、每個人的喜好與約定、尚未結束的話題，並註明是誰說的。
- 省略寒暄和不重要的閒聊。
- 用繁體中文條列，總長度不超過 300 字。
- 只輸出摘要本身，不要加任何說明。
"""

# 記憶存在 memory/角色名稱/頻道ID.json，重開程式也不會忘
# 每個角色的記憶分開，換角色時不會把別人的口吻帶進來
MEMORY_DIR = Path(__file__).parent / "memory" / PERSONA
# 訊息累積到 MAX_HISTORY 則（使用者 + Bot 各算一則）時，
# 把較舊的訊息壓縮成重點摘要，只保留最新的 KEEP_RECENT 則原文
MAX_HISTORY = 20
KEEP_RECENT = 10

memories: dict[int, dict] = {}
# 同一個頻道一次只處理一則訊息，避免記憶檔被同時寫壞
locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

client_ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


def memory_path(channel_id: int) -> Path:
    return MEMORY_DIR / f"{channel_id}.json"


def load_memory(channel_id: int) -> dict:
    if channel_id not in memories:
        path = memory_path(channel_id)
        try:
            memories[channel_id] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            memories[channel_id] = {"summary": "", "messages": []}
        except (json.JSONDecodeError, OSError) as e:
            print(f"記憶檔讀取失敗，改用空白記憶：{path}（{e}）")
            memories[channel_id] = {"summary": "", "messages": []}
    return memories[channel_id]


def save_memory(channel_id: int) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = memory_path(channel_id)
    tmp = path.with_suffix(".tmp")
    # 先寫暫存檔再取代，避免寫到一半當機把記憶檔弄壞
    tmp.write_text(
        json.dumps(memories[channel_id], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def reset_memory(channel_id: int) -> None:
    memories[channel_id] = {"summary": "", "messages": []}
    memory_path(channel_id).unlink(missing_ok=True)


async def summarize(memory: dict) -> None:
    old = memory["messages"][:-KEEP_RECENT]
    bot_name = bot.user.display_name if bot.user else "Bot"
    lines = "\n".join(
        m["content"] if m["role"] == "user" else f"{bot_name}：{m['content']}"
        for m in old
    )
    resp = await client_ai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {
                "role": "user",
                "content": f"【舊的重點摘要】\n{memory['summary'] or '（無）'}\n\n【新的對話】\n{lines}",
            },
        ],
    )
    memory["summary"] = (resp.choices[0].message.content or "").strip()
    memory["messages"] = memory["messages"][-KEEP_RECENT:]


async def chat(channel_id: int, author: str, prompt: str) -> str:
    memory = load_memory(channel_id)
    # 群組裡有很多人，附上名字讓 Bot 分得出是誰在說話
    user_msg = {"role": "user", "content": f"{author}：{prompt}"}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if memory["summary"]:
        messages.append({"role": "system", "content": f"之前對話的重點摘要：\n{memory['summary']}"})
    messages += memory["messages"]
    messages.append(user_msg)

    resp = await client_ai.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    reply = resp.choices[0].message.content or "（沒有回應內容）"

    memory["messages"] += [user_msg, {"role": "assistant", "content": reply}]
    if len(memory["messages"]) >= MAX_HISTORY:
        try:
            await summarize(memory)
        except Exception as e:
            # 摘要失敗就先保留原文，下一則訊息會再試；但不讓它無限變長
            print(f"摘要失敗：{e}")
            memory["messages"] = memory["messages"][-MAX_HISTORY * 2:]
    save_memory(channel_id)
    return reply


@bot.event
async def on_ready():
    print(f"已登入：{bot.user}（角色：{PERSONA}，模型：{OPENAI_MODEL}）")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if CHANNEL_ID:
        if message.channel.id != CHANNEL_ID:
            return
    # 沒有專屬頻道時，只在被 @ 的時候回應，避免每句話都燒 API 費用
    # 打 @ 時 Discord 可能選到跟 Bot 同名的「身分組」，所以兩種都算
    elif bot.user not in message.mentions and not (
        message.guild and set(message.role_mentions) & set(message.guild.me.roles)
    ):
        return

    prompt = message.content
    for mention in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
        prompt = prompt.replace(mention, "")
    if message.guild:
        for role in message.guild.me.roles:
            prompt = prompt.replace(role.mention, "")
    prompt = prompt.strip()
    if not prompt:
        return

    channel_id = message.channel.id
    async with locks[channel_id]:
        # 輸入 !reset 清除這個頻道的記憶（摘要和檔案一起刪）
        if prompt == "!reset":
            reset_memory(channel_id)
            await message.channel.send("記憶已清除。")
            return

        async with message.channel.typing():
            try:
                reply = await chat(channel_id, message.author.display_name, prompt)
            except Exception as e:
                print(f"OpenAI 錯誤：{e}")
                reply = "抱歉，呼叫 GPT 時發生錯誤，請稍後再試。"

    # Discord 單則訊息上限 2000 字，太長就切開
    for i in range(0, len(reply), 2000):
        await message.channel.send(reply[i:i + 2000])


if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENAI_API_KEY:
        raise SystemExit("請先在 .env 填入 DISCORD_TOKEN 和 OPENAI_API_KEY")
    bot.run(DISCORD_TOKEN)
