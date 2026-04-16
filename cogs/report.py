import sqlite3
from datetime import datetime

import disnake
from disnake.ext import commands

# ID канала для репортов
REPORT_CHANNEL_ID = 1492904531238064198


class ReportModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="ID или имя пользователя",
                placeholder="Введите Discord ID или имя пользователя...",
                custom_id="target",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="Суть нарушения",
                placeholder="Опишите что произошло...",
                custom_id="violation",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=1000
            ),
            disnake.ui.TextInput(
                label="Доказательства (ссылка)",
                placeholder="Вставьте ссылку на доказательства...",
                custom_id="evidence",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=500
            ),
        ]
        super().__init__(title="📝 Создание репорта", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        target = interaction.text_values["target"]
        violation = interaction.text_values["violation"]
        evidence = interaction.text_values["evidence"]

        cog = interaction.bot.get_cog("ReportCog")
        await cog.create_report(interaction, target, violation, evidence)


class ReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect('reports.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_number INTEGER,
                reporter_id TEXT,
                reporter_name TEXT,
                target TEXT,
                violation TEXT,
                evidence TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        self.cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('last_report_number', '0')"
        )
        self.conn.commit()

    def get_next_report_number(self) -> int:
        self.cursor.execute("SELECT value FROM settings WHERE key = 'last_report_number'")
        last_number = int(self.cursor.fetchone()[0])
        next_number = last_number + 1
        self.cursor.execute(
            "UPDATE settings SET value = ? WHERE key = 'last_report_number'",
            (str(next_number),)
        )
        self.conn.commit()
        return next_number

    async def send_dm(self, user_id: int, embed: disnake.Embed) -> bool:
        try:
            user = await self.bot.fetch_user(user_id)
            await user.send(embed=embed)
            return True
        except:
            return False

    async def create_report(self, interaction: disnake.ModalInteraction, target: str, violation: str, evidence: str):
        report_number = self.get_next_report_number()

        self.cursor.execute('''
            INSERT INTO reports (
                report_number, reporter_id, reporter_name, target, 
                violation, evidence, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_number,
            str(interaction.author.id),
            str(interaction.author),
            target,
            violation,
            evidence,
            datetime.utcnow().isoformat(),
            'pending'
        ))
        self.conn.commit()

        # Подтверждение пользователю
        user_embed = disnake.Embed(
            title="✅ Репорт создан",
            description=f"**Ваш репорт #{report_number} успешно отправлен!**\n"
                        f"Модераторы рассмотрят его в ближайшее время.",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=user_embed, ephemeral=True)

        # Отправляем в канал репортов
        report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        if report_channel:
            embed = disnake.Embed(
                title=f"📋 Новый репорт #{report_number}",
                description=f"**От кого:** {interaction.author.mention}\n"
                            f"**ID отправителя:** `{interaction.author.id}`\n"
                            f"**Нарушитель:** `{target}`\n"
                            f"**Нарушение:** {violation}\n"
                            f"**Доказательства:** [Ссылка]({evidence})\n"
                            f"**Статус:** ⏳ Ожидает рассмотрения",
                color=disnake.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Репорт #{report_number}")

            view = ReportActions(self, report_number, interaction.author.id)
            await report_channel.send(embed=embed, view=view)

        # Логируем
        log_channel = self.bot.get_channel(1492883517573566624)
        if log_channel:
            log_embed = disnake.Embed(
                title="📝 Создан новый репорт",
                description=f"**Репорт #{report_number}**\n"
                            f"**От:** {interaction.author.mention}\n"
                            f"**Нарушитель:** `{target}`",
                color=disnake.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=log_embed)

    async def update_report_status(self, report_number: int, status: str, moderator: disnake.Member,
                                   reason: str = None):
        self.cursor.execute(
            "UPDATE reports SET status = ? WHERE report_number = ?",
            (status, report_number)
        )
        self.conn.commit()

        self.cursor.execute(
            "SELECT reporter_id, target FROM reports WHERE report_number = ?",
            (report_number,)
        )
        result = self.cursor.fetchone()
        if result:
            reporter_id, target = result

            if status == "approved":
                dm_embed = disnake.Embed(
                    title=f"✅ Репорт #{report_number} принят",
                    description=f"**Нарушитель:** `{target}`\n"
                                f"**Решение принял:** {moderator.mention}\n"
                                f"Спасибо за помощь в поддержании порядка!",
                    color=disnake.Color.green()
                )
            else:
                dm_embed = disnake.Embed(
                    title=f"❌ Репорт #{report_number} отклонён",
                    description=f"**Нарушитель:** `{target}`\n"
                                f"**Решение принял:** {moderator.mention}\n"
                                f"**Причина:** {reason}",
                    color=disnake.Color.red()
                )

            await self.send_dm(int(reporter_id), dm_embed)

    # ========== КОМАНДА /report ==========
    @commands.slash_command(
        name="report",
        description="Создать репорт на нарушителя"
    )
    async def report_command(self, inter: disnake.ApplicationCommandInteraction):
        """Открывает модальное окно для создания репорта"""
        modal = ReportModal()
        await inter.response.send_modal(modal)


class ReportActions(disnake.ui.View):
    def __init__(self, cog, report_number: int, reporter_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.report_number = report_number
        self.reporter_id = reporter_id

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success)
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not interaction.author.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "❌ У вас нет прав для управления репортами",
                ephemeral=True
            )

        await self.cog.update_report_status(self.report_number, "approved", interaction.author)

        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.green()
        embed.description = embed.description.replace("⏳ Ожидает рассмотрения", "✅ Принят")
        embed.add_field(name="Решение", value=f"Принял: {interaction.author.mention}", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send("✅ Репорт принят, пользователь уведомлён", ephemeral=True)

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger)
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not interaction.author.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "❌ У вас нет прав для управления репортами",
                ephemeral=True
            )

        modal = RejectModal(self.cog, self.report_number, interaction.author, interaction.message)
        await interaction.response.send_modal(modal)


class RejectModal(disnake.ui.Modal):
    def __init__(self, cog, report_number: int, moderator: disnake.Member, message):
        self.cog = cog
        self.report_number = report_number
        self.moderator = moderator
        self.message = message
        components = [
            disnake.ui.TextInput(
                label="Причина отклонения",
                placeholder="Введите причину...",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=500
            )
        ]
        super().__init__(title="❌ Отклонение репорта", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values["reason"]

        await self.cog.update_report_status(self.report_number, "rejected", self.moderator, reason)

        embed = self.message.embeds[0]
        embed.color = disnake.Color.red()
        embed.description = embed.description.replace("⏳ Ожидает рассмотрения", "❌ Отклонён")
        embed.add_field(name="Решение", value=f"Отклонил: {self.moderator.mention}\nПричина: {reason}", inline=False)

        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Репорт отклонён, пользователь уведомлён", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(ReportCog(bot))