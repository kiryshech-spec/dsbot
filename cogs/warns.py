import sqlite3
from datetime import datetime

import disnake
from disnake.ext import commands

# ID канала для логов
LOG_CHANNEL_ID = 1492883517573566624


class WarnsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        """Инициализация SQLite базы данных"""
        self.conn = sqlite3.connect('warns.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                reason TEXT,
                moderator_id TEXT,
                timestamp TEXT
            )
        ''')
        self.conn.commit()

    def get_warns_count(self, user_id: str) -> int:
        """Возвращает количество варнов пользователя"""
        self.cursor.execute("SELECT COUNT(*) FROM warns WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def get_warns(self, user_id: str) -> list:
        """Возвращает список варнов пользователя"""
        self.cursor.execute("SELECT reason, moderator_id, timestamp FROM warns WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def add_warn(self, user_id: str, reason: str, moderator_id: str):
        """Добавляет варн"""
        self.cursor.execute(
            "INSERT INTO warns (user_id, reason, moderator_id, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, reason, moderator_id, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    def remove_last_warn(self, user_id: str):
        """Удаляет последний варн"""
        self.cursor.execute(
            "DELETE FROM warns WHERE id = (SELECT MAX(id) FROM warns WHERE user_id = ?)",
            (user_id,)
        )
        self.conn.commit()

    def clear_warns(self, user_id: str):
        """Очищает все варны пользователя"""
        self.cursor.execute("DELETE FROM warns WHERE user_id = ?", (user_id,))
        self.conn.commit()

    async def log_to_channel(self, embed: disnake.Embed):
        """Отправляет сообщение в лог-канал"""
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    async def send_dm(self, user: disnake.User, embed: disnake.Embed) -> bool:
        """Отправляет ЛС пользователю"""
        try:
            await user.send(embed=embed)
            return True
        except:
            return False

    @commands.slash_command(
        name="warn",
        description="Выдать предупреждение пользователю"
    )
    async def warn(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.User,
            reason: str = "Не указана"
    ):
        """Выдаёт варн. На 3-м варне — автоматический бан."""

        if not inter.author.guild_permissions.ban_members:
            return await inter.response.send_message(
                "❌ У вас нет прав на выдачу предупреждений (нужно право `Ban Members`)",
                ephemeral=True
            )

        if user == inter.author:
            return await inter.response.send_message(
                "❌ Нельзя выдать предупреждение самому себе",
                ephemeral=True
            )

        if user.bot:
            return await inter.response.send_message(
                "❌ Нельзя выдавать предупреждение боту",
                ephemeral=True
            )

        self.add_warn(str(user.id), reason, str(inter.author.id))
        warn_count = self.get_warns_count(str(user.id))

        dm_embed = disnake.Embed(
            title="⚠️ Вы получили предупреждение",
            description=f"**Сервер:** {inter.guild.name}\n"
                        f"**Модератор:** {inter.author.mention}\n"
                        f"**Причина:** {reason}\n"
                        f"**Всего варнов:** {warn_count}/3",
            color=disnake.Color.orange()
        )
        dm_sent = await self.send_dm(user, dm_embed)
        dm_status = "✅" if dm_sent else "❌ (ЛС закрыты)"

        log_embed = disnake.Embed(
            title="📝 Выдано предупреждение",
            description=f"**Пользователь:** {user.mention} (`{user.id}`)\n"
                        f"**Модератор:** {inter.author.mention}\n"
                        f"**Причина:** {reason}\n"
                        f"**Всего варнов:** {warn_count}/3\n"
                        f"**ЛС уведомление:** {dm_status}",
            color=disnake.Color.gold(),
            timestamp=datetime.utcnow()
        )
        await self.log_to_channel(log_embed)

        response_text = f"✅ Пользователю {user.mention} выдано предупреждение.\n" \
                        f"**Причина:** {reason}\n" \
                        f"**Теперь варнов:** {warn_count}/3\n" \
                        f"**ЛС уведомление:** {dm_status}"

        if warn_count >= 3:
            try:
                await inter.guild.ban(
                    user,
                    reason=f"Автоматический бан: 3 предупреждения. Последнее: {reason}"
                )
                response_text += f"\n🔨 **Пользователь {user.mention} забанен автоматически (3/3 варна)**"

                ban_embed = disnake.Embed(
                    title="🔨 Вы забанены",
                    description=f"**Сервер:** {inter.guild.name}\n"
                                f"**Причина:** Достигнуто 3 предупреждения\n"
                                f"**Последний варн:** {reason}",
                    color=disnake.Color.red()
                )
                await self.send_dm(user, ban_embed)

                log_embed.add_field(
                    name="🔨 Автоматический бан",
                    value=f"Пользователь забанен за 3 предупреждения",
                    inline=False
                )
                await self.log_to_channel(log_embed)
                self.clear_warns(str(user.id))

            except Exception as e:
                response_text += f"\n⚠️ Не удалось забанить пользователя: {e}"

        await inter.response.send_message(response_text, ephemeral=True)

    @commands.slash_command(
        name="варн",
        description="Выдать предупреждение пользователю (русская команда)"
    )
    async def warn_ru(
            self,
            inter: disnake.ApplicationCommandInteraction,
            пользователь: disnake.User,
            причина: str = "Не указана"
    ):
        await self.warn(inter, пользователь, причина)

    @commands.slash_command(
        name="unwarn",
        description="Снять последнее предупреждение с пользователя"
    )
    async def unwarn(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.User
    ):
        """Снимает последний варн"""

        if not inter.author.guild_permissions.ban_members:
            return await inter.response.send_message(
                "❌ У вас нет прав на снятие предупреждений",
                ephemeral=True
            )

        warn_count = self.get_warns_count(str(user.id))

        if warn_count == 0:
            return await inter.response.send_message(
                f"❌ У пользователя {user.mention} нет предупреждений",
                ephemeral=True
            )

        warns = self.get_warns(str(user.id))
        last_warn = warns[-1] if warns else None

        self.remove_last_warn(str(user.id))
        new_count = self.get_warns_count(str(user.id))

        dm_embed = disnake.Embed(
            title="✅ С вас снято предупреждение",
            description=f"**Сервер:** {inter.guild.name}\n"
                        f"**Модератор:** {inter.author.mention}\n"
                        f"**Снят варн по причине:** {last_warn[0] if last_warn else 'Неизвестно'}\n"
                        f"**Осталось варнов:** {new_count}/3",
            color=disnake.Color.green()
        )
        dm_sent = await self.send_dm(user, dm_embed)
        dm_status = "✅" if dm_sent else "❌ (ЛС закрыты)"

        log_embed = disnake.Embed(
            title="✅ Снято предупреждение",
            description=f"**Пользователь:** {user.mention} (`{user.id}`)\n"
                        f"**Модератор:** {inter.author.mention}\n"
                        f"**Снят варн по причине:** {last_warn[0] if last_warn else 'Неизвестно'}\n"
                        f"**Осталось варнов:** {new_count}/3\n"
                        f"**ЛС уведомление:** {dm_status}",
            color=disnake.Color.green(),
            timestamp=datetime.utcnow()
        )
        await self.log_to_channel(log_embed)

        await inter.response.send_message(
            f"✅ Снято последнее предупреждение с {user.mention}\n"
            f"**Осталось варнов:** {new_count}/3\n"
            f"**ЛС уведомление:** {dm_status}",
            ephemeral=True
        )

    @commands.slash_command(
        name="анварн",
        description="Снять последнее предупреждение с пользователя (русская команда)"
    )
    async def unwarn_ru(
            self,
            inter: disnake.ApplicationCommandInteraction,
            пользователь: disnake.User
    ):
        await self.unwarn(inter, пользователь)


def setup(bot: commands.Bot):
    bot.add_cog(WarnsCog(bot))