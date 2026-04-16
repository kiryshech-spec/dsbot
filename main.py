import disnake
from disnake.ext import commands
import os

# Токен берется из переменных окружения (настройки хостинга)
# На Bothost нужно в панели управления добавить переменную BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")

# Проверка наличия токена
if not TOKEN:
    print("❌ ОШИБКА: Токен не найден!")
    print("📌 Добавьте переменную окружения BOT_TOKEN в настройках хостинга")
    print("📌 Или создайте файл .env с содержимым: BOT_TOKEN=ваш_токен")
    exit(1)

# ID вашего сервера (ПКМ по иконке сервера → Копировать ID)
GUILD_ID = 1226547432805109901  # ЗАМЕНИТЕ НА ID ВАШЕГО СЕРВЕРА

intents = disnake.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    test_guilds=[GUILD_ID]
)


@bot.event
async def on_ready():
    print(f"\n{'=' * 60}")
    print(f"✅ Бот {bot.user} успешно запущен!")
    print(f"📊 На серверах: {len(bot.guilds)}")
    print(f"🆔 ID бота: {bot.user.id}")
    print(f"{'=' * 60}\n")

    # Проверяем загруженные коги
    print("📂 Загруженные коги:")
    for cog in bot.cogs:
        print(f"   • {cog}")

    # Проверяем зарегистрированные команды
    print("\n📝 Зарегистрированные слеш-команды:")
    for cmd in bot.slash_commands:
        print(f"   • /{cmd.name} - {cmd.description}")

    print(f"\n{'=' * 60}")
    print("🎮 Бот готов к работе!")
    print(f"{'=' * 60}\n")


# Загружаем все коги из папки cogs
cogs_folder = "./cogs"
if os.path.exists(cogs_folder):
    for filename in os.listdir(cogs_folder):
        if filename.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Загружен ког: {filename}")
            except Exception as e:
                print(f"❌ Ошибка загрузки {filename}: {e}")
else:
    print("⚠️ Папка cogs не найдена, создаю...")
    os.makedirs(cogs_folder)
    print("📁 Папка cogs создана, поместите туда ваши коги")

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except disnake.LoginFailure:
        print("❌ ОШИБКА: Неверный токен! Проверьте переменную BOT_TOKEN")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")