import disnake
from disnake.ext import commands
import random
from datetime import datetime
import json
import os

# ========== Файл для хранения данных (если нет своих функций) ==========
DATA_FILE = "economy_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"balances": {}, "voice_track": {}, "last_message": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class GamblingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Кулдауны для команд
        # 12 часов = 43200 секунд
        self.luck_cooldown = commands.CooldownMapping.from_cooldown(1, 43200, commands.BucketType.user)
        self.dice_cooldown = commands.CooldownMapping.from_cooldown(1, 43200, commands.BucketType.user)
        # У казино НЕТ кулдауна

    def check_cooldown(self, inter, mapping):
        """Проверка кулдауна"""
        bucket = mapping.get_bucket(inter)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return retry_after
        return None

    def add_money(self, user_id: str, amount: int):
        """Добавляет монеты пользователю"""
        data = load_data()
        data["balances"][user_id] = data["balances"].get(user_id, 0) + amount
        save_data(data)
        return data["balances"][user_id]

    def get_balance(self, user_id: str) -> int:
        """Получает баланс пользователя"""
        data = load_data()
        return data["balances"].get(user_id, 0)

    def format_cooldown(self, seconds: float) -> str:
        """Форматирует время кулдауна в читаемый вид"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours} ч. {minutes} мин."
        elif minutes > 0:
            return f"{minutes} мин. {secs} сек."
        else:
            return f"{secs} сек."

    # ========== /luck - Монетка ==========
    @commands.slash_command(name="luck", description="Подбросить монетку 50/50 и выиграть 100 монет (кд 12 часов)")
    async def luck(self, inter: disnake.ApplicationCommandInteraction):
        """Игра в монетку: орёл/решка, при победе +100 монет. Кулдаун 12 часов."""

        # Проверка кулдауна
        retry_after = self.check_cooldown(inter, self.luck_cooldown)
        if retry_after:
            await inter.response.send_message(
                f"⏰ Вы уже использовали **/luck**!\n"
                f"Следующий раз можно будет через **{self.format_cooldown(retry_after)}**.",
                ephemeral=True
            )
            return

        # Результат броска
        result = random.choice(["орёл", "решка"])
        win = random.choice([True, False])  # 50/50 шанс победы

        # Эмодзи для результата
        emojis = {
            "орёл": "🦅",
            "решка": "🪙"
        }

        if win:
            reward = 100
            new_balance = self.add_money(str(inter.author.id), reward)

            embed = disnake.Embed(
                title="🎲 Подброшена монетка!",
                description=f"{emojis[result]} Выпал **{result}**!\n\n"
                            f"✅ **ПОБЕДА!** Вы выиграли **+{reward}** монет!",
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="💰 Новый баланс", value=f"{new_balance} монет", inline=True)
            embed.set_footer(text="Следующая игра будет доступна через 12 часов")
        else:
            embed = disnake.Embed(
                title="🎲 Подброшена монетка!",
                description=f"{emojis[result]} Выпал **{result}**!\n\n"
                            f"❌ **ПРОИГРЫШ!** В следующий раз повезёт!",
                color=disnake.Color.red(),
                timestamp=datetime.now()
            )
            embed.set_footer(text="Следующая игра будет доступна через 12 часов")

        embed.set_footer(text=f"Запросил: {inter.author.display_name} | Следующая игра через 12 часов",
                         icon_url=inter.author.avatar.url if inter.author.avatar else None)

        await inter.response.send_message(embed=embed)

    # ========== /dice - Кости ==========
    @commands.slash_command(name="dice",
                            description="Бросить кости (1-6). Угадайте число и выиграйте 100 монет (кд 12 часов)")
    async def dice(
            self,
            inter: disnake.ApplicationCommandInteraction,
            guess: int = commands.Param(description="Ваше число от 1 до 6", ge=1, le=6)
    ):
        """Игра в кости: угадайте число от 1 до 6, при победе +100 монет. Кулдаун 12 часов."""

        # Проверка кулдауна
        retry_after = self.check_cooldown(inter, self.dice_cooldown)
        if retry_after:
            await inter.response.send_message(
                f"⏰ Вы уже использовали **/dice**!\n"
                f"Следующий раз можно будет через **{self.format_cooldown(retry_after)}**.",
                ephemeral=True
            )
            return

        # Бросок кубика
        roll = random.randint(1, 6)

        # Эмодзи для чисел
        dice_emojis = {
            1: "⚀",
            2: "⚁",
            3: "⚂",
            4: "⚃",
            5: "⚄",
            6: "⚅"
        }

        if guess == roll:
            reward = 100
            new_balance = self.add_money(str(inter.author.id), reward)

            embed = disnake.Embed(
                title="🎲 Бросок костей!",
                description=f"{dice_emojis[roll]} Выпало число **{roll}**!\n"
                            f"Ваше число: **{guess}**\n\n"
                            f"✅ **ПОБЕДА!** Вы угадали и получили **+{reward}** монет!",
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="💰 Новый баланс", value=f"{new_balance} монет", inline=True)
        else:
            embed = disnake.Embed(
                title="🎲 Бросок костей!",
                description=f"{dice_emojis[roll]} Выпало число **{roll}**!\n"
                            f"Ваше число: **{guess}**\n\n"
                            f"❌ **ПРОИГРЫШ!** Попробуйте ещё раз!",
                color=disnake.Color.red(),
                timestamp=datetime.now()
            )

        embed.set_footer(text=f"Запросил: {inter.author.display_name} | Следующая игра через 12 часов",
                         icon_url=inter.author.avatar.url if inter.author.avatar else None)

        await inter.response.send_message(embed=embed)

    # ========== /casino - Казино с риском (БЕЗ КД) ==========
    @commands.slash_command(name="casino",
                            description="Поставьте монеты и угадайте число (2-12). Выигрыш x5! (БЕЗ КУЛДАУНА)")
    async def casino(
            self,
            inter: disnake.ApplicationCommandInteraction,
            bet: int = commands.Param(description="Сумма ставки (мин 10 монет)", ge=10),
            guess: int = commands.Param(description="Ваше число от 2 до 12", ge=2, le=12)
    ):
        """Игра в казино: ставка на число от 2 до 12 (сумма двух кубиков), выигрыш x5. БЕЗ КУЛДАУНА."""

        # Проверка баланса
        user_id = str(inter.author.id)
        current_balance = self.get_balance(user_id)

        if current_balance < bet:
            await inter.response.send_message(
                f"❌ Недостаточно монет! У вас **{current_balance}**, а ставка **{bet}**.",
                ephemeral=True
            )
            return

        # Бросок двух кубиков
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        dice_emojis = {
            1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"
        }

        if guess == total:
            win_amount = bet * 5
            new_balance = self.add_money(user_id, win_amount)

            embed = disnake.Embed(
                title="🎰 КАЗИНО - БРОСОК КОСТЕЙ",
                description=f"🎲 Кубик 1: {dice_emojis[dice1]} **{dice1}**\n"
                            f"🎲 Кубик 2: {dice_emojis[dice2]} **{dice2}**\n"
                            f"📊 Сумма: **{total}**\n"
                            f"🎯 Ваше число: **{guess}**\n\n"
                            f"✨ **ДЖЕКПОТ!** Вы выиграли **{win_amount}** монет! (x5)",
                color=disnake.Color.gold(),
                timestamp=datetime.now()
            )
            embed.add_field(name="💰 Новый баланс", value=f"{new_balance} монет", inline=True)
        else:
            new_balance = self.add_money(user_id, -bet)

            embed = disnake.Embed(
                title="🎰 КАЗИНО - БРОСОК КОСТЕЙ",
                description=f"🎲 Кубик 1: {dice_emojis[dice1]} **{dice1}**\n"
                            f"🎲 Кубик 2: {dice_emojis[dice2]} **{dice2}**\n"
                            f"📊 Сумма: **{total}**\n"
                            f"🎯 Ваше число: **{guess}**\n\n"
                            f"💸 **ПРОИГРЫШ!** Вы потеряли **{bet}** монет.",
                color=disnake.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="💰 Новый баланс", value=f"{new_balance} монет", inline=True)

        embed.set_footer(text=f"Запросил: {inter.author.display_name} | Можно играть сколько угодно",
                         icon_url=inter.author.avatar.url if inter.author.avatar else None)

        await inter.response.send_message(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(GamblingCog(bot))