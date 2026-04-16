import asyncio
import json
import os
from datetime import datetime
from typing import List, Tuple

import disnake
from disnake.ext import commands, tasks

# ========== Файл для хранения данных ==========
DATA_FILE = "economy_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"balances": {}, "voice_track": {}, "last_message": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ========== ВСЕ РОЛИ ==========
ROLES = {
    # ID_роли: ("Название", цена)
    1494311529066008616: ("・𝙎𝙥𝙚𝙚𝙙𝙬𝙖𝙜𝙤𝙣・", 5000),
    1494311409574609080: ("SIGMA", 5000),
    1492600982327267519: ("Абсолют", 5000),
    1494312203623333939: ("Санта", 5000),
    1494312236292898856: ("фембойчик", 5000),
    1494312345571168346: ("я тут мать", 5000),
    # НОВЫЕ РОЛИ:
    1421864122810892328: ("долбоеб", 10000),
    1445724141268242504: ("эвентер", 10000),
    1445719593736863774: ("staff", 50000),
    1414992622992494713: ("HELPER", 100000),
    1413461127307726940: ("Moderator", 250000),
}

# Для меню
ROLES_FOR_MENU = [(role_id, name, price) for role_id, (name, price) in ROLES.items()]

# ========== Константы ==========
UNBAN_PRICE = 10000
RUB_PRICE = 1000000  # 1 млн монет = 1 рубль на карту
MESSAGE_REWARD = 100   # 100 монет за сообщение (при соблюдении кулдауна)
VOICE_REWARD = 100     # 100 монет в минуту в голосовом
COOLDOWN_SECONDS = 60  # 1 минута

# ID канала для логов
LOG_CHANNEL_ID = 1494314197608304692  # <- СЮДА ВСТАВЬТЕ ID КАНАЛА ДЛЯ ЛОГОВ


# ========== Экономический ког ==========
class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_check.start()

    def cog_unload(self):
        self.voice_check.cancel()

    # ========== Получение монет за сообщения ==========
    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        data = load_data()
        user_id = str(message.author.id)
        now = datetime.now()

        last_msg = data["last_message"].get(user_id)
        if last_msg:
            last_time = datetime.fromisoformat(last_msg)
            if (now - last_time).total_seconds() < COOLDOWN_SECONDS:
                save_data(data)
                return

        # Начисляем монеты (100 монет)
        data["balances"][user_id] = data["balances"].get(user_id, 0) + MESSAGE_REWARD
        data["last_message"][user_id] = now.isoformat()
        save_data(data)

    # ========== Голосовые награды (каждую минуту по 100 монет) ==========
    @tasks.loop(seconds=60.0)
    async def voice_check(self):
        data = load_data()
        now = datetime.now()

        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    if member.bot:
                        continue

                    user_id = str(member.id)
                    track = data["voice_track"].get(user_id, {})

                    last_join = track.get("last_join")
                    if last_join:
                        last_time = datetime.fromisoformat(last_join)
                        minutes = int((now - last_time).total_seconds() // 60)
                        if minutes >= 1:
                            # Начисляем 100 монет за каждую полную минуту
                            reward = minutes * VOICE_REWARD
                            data["balances"][user_id] = data["balances"].get(user_id, 0) + reward
                            # Обновляем время последнего начисления
                            data["voice_track"][user_id]["last_join"] = now.isoformat()

        save_data(data)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        data = load_data()
        user_id = str(member.id)

        if after.channel and (not before.channel or before.channel != after.channel):
            # Зашёл в голосовой
            if user_id not in data["voice_track"]:
                data["voice_track"][user_id] = {}
            data["voice_track"][user_id]["last_join"] = datetime.now().isoformat()
            save_data(data)

        elif before.channel and not after.channel:
            # Вышел из голосового
            if user_id in data["voice_track"]:
                del data["voice_track"][user_id]
                save_data(data)

    @voice_check.before_loop
    async def before_voice_check(self):
        await self.bot.wait_until_ready()

    # ========== КОМАНДЫ ==========

    @commands.slash_command(name="balance", description="Показать ваш баланс монет")
    async def balance(self, inter: disnake.ApplicationCommandInteraction):
        data = load_data()
        user_id = str(inter.author.id)
        balance = data["balances"].get(user_id, 0)

        embed = disnake.Embed(
            title="💰 Ваш баланс",
            description=f"У вас **{balance}** монет",
            color=disnake.Color.gold()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="bal_top", description="Топ 10 пользователей по балансу")
    async def bal_top(self, inter: disnake.ApplicationCommandInteraction):
        data = load_data()
        balances = data["balances"]

        sorted_users = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]

        if not sorted_users:
            await inter.response.send_message("📭 Нет данных о балансах.", ephemeral=True)
            return

        embed = disnake.Embed(title="🏆 Топ по монетам", color=disnake.Color.blue())
        description = ""
        for i, (user_id, bal) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                name = user.display_name if user else user_id
            except:
                name = user_id
            description += f"{i}. **{name}** — {bal} монет\n"

        embed.description = description
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="buy_role", description="Купить роль за монеты")
    async def buy_role(self, inter: disnake.ApplicationCommandInteraction):
        if not ROLES_FOR_MENU:
            await inter.response.send_message("❌ Список ролей пуст.", ephemeral=True)
            return

        view = RolePaginationView(inter.author.id, ROLES_FOR_MENU)
        embed = disnake.Embed(
            title="🛒 Магазин ролей",
            description="Используйте меню ниже для покупки ролей",
            color=disnake.Color.purple()
        )
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.slash_command(name="unban_shop", description="Купить разбан за 10 000 монет")
    async def unban_shop(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User):
        """Купить разбан для указанного пользователя"""
        if not inter.author.guild_permissions.ban_members:
            await inter.response.send_message("❌ У вас нет прав на использование разбана через магазин.",
                                              ephemeral=True)
            return

        data = load_data()
        buyer_id = str(inter.author.id)
        balance = data["balances"].get(buyer_id, 0)

        if balance < UNBAN_PRICE:
            await inter.response.send_message(f"❌ Недостаточно монет! Нужно: {UNBAN_PRICE}, у вас: {balance}",
                                              ephemeral=True)
            return

        # Проверяем, забанен ли пользователь
        try:
            ban_entry = await inter.guild.fetch_ban(user)
        except disnake.NotFound:
            await inter.response.send_message(f"❌ Пользователь {user.mention} не забанен.", ephemeral=True)
            return

        # Списываем монеты
        data["balances"][buyer_id] = balance - UNBAN_PRICE
        save_data(data)

        # Разбан
        await inter.guild.unban(user)

        embed = disnake.Embed(
            title="✅ Разбан куплен!",
            description=f"Вы разбанили {user.mention} за **{UNBAN_PRICE}** монет.",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="exchange",
                            description="Обменять монеты на реальные рубли (1 рубль = 1 000 000 монет)")
    async def exchange(self, inter: disnake.ApplicationCommandInteraction, amount: int):
        """Обмен монет на рубли (вывод на карту)"""
        if amount < 1:
            await inter.response.send_message("❌ Сумма должна быть больше 0", ephemeral=True)
            return

        data = load_data()
        user_id = str(inter.author.id)
        balance = data["balances"].get(user_id, 0)

        needed = amount * RUB_PRICE
        if balance < needed:
            await inter.response.send_message(f"❌ Недостаточно монет! Нужно: {needed}, у вас: {balance}",
                                              ephemeral=True)
            return

        # Списываем монеты
        data["balances"][user_id] = balance - needed
        save_data(data)

        # Здесь должен быть код для реального перевода на карту
        # Сейчас просто уведомление
        embed = disnake.Embed(
            title="💸 Запрос на вывод",
            description=f"Вы обменяли **{needed}** монет на **{amount} руб.**\n"
                        f"Свяжитесь с администрацией для получения выплаты на карту.",
            color=disnake.Color.orange()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

        # Отправляем в лог-канал для админов
        log_channel = inter.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🔔 {inter.author.mention} запросил вывод {amount} руб. ({needed} монет)")


# ========== ПАГИНАТОР ДЛЯ РОЛЕЙ ==========
class RoleBuyDropdown(disnake.ui.StringSelect):
    def __init__(self, roles_page: List[Tuple[int, str, int]], author_id: int):
        options = []
        for role_id, name, price in roles_page:
            display_name = name[:90] if len(name) > 90 else name
            options.append(
                disnake.SelectOption(
                    label=display_name,
                    description=f"Цена: {price} монет",
                    value=str(role_id),
                    emoji="🛒"
                )
            )
        super().__init__(
            placeholder="Выберите роль для покупки",
            options=options,
            custom_id="role_buy_dropdown"
        )
        self.author_id = author_id

    async def callback(self, interaction: disnake.MessageInteraction):
        if interaction.author.id != self.author_id:
            await interaction.response.send_message("❌ Это меню не для вас!", ephemeral=True)
            return

        role_id = int(self.values[0])
        role_name, price = ROLES[role_id]
        guild = interaction.guild
        role = guild.get_role(role_id)

        if not role:
            await interaction.response.send_message("❌ Роль не найдена на сервере.", ephemeral=True)
            return

        data = load_data()
        user_id = str(interaction.author.id)
        balance = data["balances"].get(user_id, 0)

        if balance < price:
            await interaction.response.send_message(f"❌ Недостаточно монет! Нужно: {price}, у вас: {balance}",
                                                    ephemeral=True)
            return

        if role in interaction.author.roles:
            await interaction.response.send_message(f"❌ У вас уже есть роль {role.mention}.", ephemeral=True)
            return

        # Покупка
        data["balances"][user_id] = balance - price
        save_data(data)
        await interaction.author.add_roles(role)

        embed = disnake.Embed(
            title="✅ Покупка успешна!",
            description=f"Вы купили роль {role.mention} за **{price}** монет.",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RolePaginationView(disnake.ui.View):
    def __init__(self, author_id: int, roles_list: List[Tuple[int, str, int]], items_per_page: int = 5):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.roles_list = roles_list
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = (len(roles_list) + items_per_page - 1) // items_per_page
        self.update_components()

    def get_page_items(self) -> List[Tuple[int, str, int]]:
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.roles_list[start:end]

    def update_components(self):
        self.clear_items()
        page_items = self.get_page_items()
        if page_items:
            self.add_item(RoleBuyDropdown(page_items, self.author_id))

        if self.total_pages > 1:
            # Кнопки навигации
            prev_btn = disnake.ui.Button(label="◀ Назад", style=disnake.ButtonStyle.secondary, custom_id="prev",
                                         disabled=(self.current_page == 0))
            page_btn = disnake.ui.Button(label=f"{self.current_page + 1}/{self.total_pages}",
                                         style=disnake.ButtonStyle.secondary, disabled=True, custom_id="page")
            next_btn = disnake.ui.Button(label="Вперед ▶", style=disnake.ButtonStyle.secondary, custom_id="next",
                                         disabled=(self.current_page == self.total_pages - 1))

            prev_btn.callback = self.prev_callback
            next_btn.callback = self.next_callback

            self.add_item(prev_btn)
            self.add_item(page_btn)
            self.add_item(next_btn)

    async def prev_callback(self, interaction: disnake.MessageInteraction):
        if interaction.author.id != self.author_id:
            await interaction.response.send_message("❌ Не для вас!", ephemeral=True)
            return
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def next_callback(self, interaction: disnake.MessageInteraction):
        if interaction.author.id != self.author_id:
            await interaction.response.send_message("❌ Не для вас!", ephemeral=True)
            return
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(view=self)


# ========== Функция setup для загрузки кога ==========
def setup(bot: commands.Bot):
    bot.add_cog(EconomyCog(bot))