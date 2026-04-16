import sqlite3
from datetime import datetime

import disnake
from disnake.ext import commands

LOG_CHANNEL_ID = 1492883517573566624
VERIFY_ROLE_ID = 1492887325766848542
STAFF_ROLE_ID = 1445719593736863774


class ActionButtons(disnake.ui.View):
    def __init__(self, cog, user, staff_member, original_message):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user
        self.staff_member = staff_member
        self.original_message = original_message

    @disnake.ui.button(label="✅ Одобрить", style=disnake.ButtonStyle.success)
    async def approve_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        guild = interaction.guild
        verify_role = guild.get_role(VERIFY_ROLE_ID)

        saved_roles = self.cog.get_user_roles(str(self.user.id))
        roles_to_add = []
        for role_id in saved_roles:
            role = guild.get_role(int(role_id))
            if role:
                roles_to_add.append(role)

        if verify_role and verify_role in self.user.roles:
            await self.user.remove_roles(verify_role, reason="Пользователь верифицирован")

        if roles_to_add:
            await self.user.add_roles(*roles_to_add, reason="Возврат ролей после верификации")

        self.cog.delete_user_roles(str(self.user.id))

        dm_embed = disnake.Embed(
            title="✅ Вы верифицированы",
            description=f"**Сервер:** {guild.name}\n"
                        f"**Вам возвращено ролей:** {len(roles_to_add)}\n"
                        f"**Верифицировал:** {self.staff_member.mention}",
            color=disnake.Color.green()
        )
        await self.cog.send_dm(self.user, dm_embed)

        log_embed = disnake.Embed(
            title="✅ Пользователь верифицирован",
            description=f"**Пользователь:** {self.user.mention} (`{self.user.id}`)\n"
                        f"**Вернулось ролей:** {len(roles_to_add)}\n"
                        f"**Верифицировал:** {self.staff_member.mention}",
            color=disnake.Color.green(),
            timestamp=datetime.utcnow()
        )
        await self.cog.log_to_channel(log_embed)

        await interaction.response.edit_message(
            content=f"✅ Пользователь {self.user.mention} успешно верифицирован!",
            embed=None,
            view=None
        )

    @disnake.ui.button(label="❌ Отказать", style=disnake.ButtonStyle.danger)
    async def deny_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        modal = DenyModal(self.cog, self.user, self.staff_member, self.original_message)
        await interaction.response.send_modal(modal)

    @disnake.ui.button(label="🔨 Забанить", style=disnake.ButtonStyle.danger)
    async def ban_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        modal = BanModal(self.cog, self.user, self.staff_member, self.original_message)
        await interaction.response.send_modal(modal)


class DenyModal(disnake.ui.Modal):
    def __init__(self, cog, user, staff_member, original_message):
        self.cog = cog
        self.user = user
        self.staff_member = staff_member
        self.original_message = original_message
        components = [
            disnake.ui.TextInput(
                label="Причина отказа",
                placeholder="Введите причину...",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=500
            )
        ]
        super().__init__(title="❌ Отказ в верификации", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values["reason"]
        guild = interaction.guild
        verify_role = guild.get_role(VERIFY_ROLE_ID)

        if verify_role and verify_role in self.user.roles:
            await self.user.remove_roles(verify_role, reason=f"Отказ в верификации: {reason}")

        self.cog.delete_user_roles(str(self.user.id))

        dm_embed = disnake.Embed(
            title="❌ Верификация отклонена",
            description=f"**Сервер:** {guild.name}\n"
                        f"**Причина:** {reason}\n"
                        f"**Модератор:** {self.staff_member.mention}",
            color=disnake.Color.red()
        )
        await self.cog.send_dm(self.user, dm_embed)

        log_embed = disnake.Embed(
            title="❌ Отказ в верификации",
            description=f"**Пользователь:** {self.user.mention} (`{self.user.id}`)\n"
                        f"**Причина:** {reason}\n"
                        f"**Модератор:** {self.staff_member.mention}",
            color=disnake.Color.red(),
            timestamp=datetime.utcnow()
        )
        await self.cog.log_to_channel(log_embed)

        await self.original_message.edit(
            content=f"❌ Пользователю {self.user.mention} отказано в верификации.\n**Причина:** {reason}",
            embed=None,
            view=None
        )

        await interaction.response.send_message("✅ Готово", ephemeral=True)


class BanModal(disnake.ui.Modal):
    def __init__(self, cog, user, staff_member, original_message):
        self.cog = cog
        self.user = user
        self.staff_member = staff_member
        self.original_message = original_message
        components = [
            disnake.ui.TextInput(
                label="Причина бана",
                placeholder="Введите причину...",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=500
            )
        ]
        super().__init__(title="🔨 Бан пользователя", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values["reason"]
        guild = interaction.guild

        try:
            await guild.ban(self.user, reason=f"Бан при верификации: {reason}")

            dm_embed = disnake.Embed(
                title="🔨 Вы забанены",
                description=f"**Сервер:** {guild.name}\n"
                            f"**Причина:** {reason}\n"
                            f"**Модератор:** {self.staff_member.mention}",
                color=disnake.Color.red()
            )
            await self.cog.send_dm(self.user, dm_embed)

            log_embed = disnake.Embed(
                title="🔨 Пользователь забанен",
                description=f"**Пользователь:** {self.user.mention} (`{self.user.id}`)\n"
                            f"**Причина:** {reason}\n"
                            f"**Модератор:** {self.staff_member.mention}",
                color=disnake.Color.dark_red(),
                timestamp=datetime.utcnow()
            )
            await self.cog.log_to_channel(log_embed)

            self.cog.delete_user_roles(str(self.user.id))

            await self.original_message.edit(
                content=f"🔨 Пользователь {self.user.mention} забанен.\n**Причина:** {reason}",
                embed=None,
                view=None
            )

            await interaction.response.send_message("✅ Готово", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при бане: {e}",
                ephemeral=True
            )


class ActionModal(disnake.ui.Modal):
    def __init__(self, cog, staff_member: disnake.Member):
        self.cog = cog
        self.staff_member = staff_member
        components = [
            disnake.ui.TextInput(
                label="ID пользователя",
                placeholder="Введите Discord ID пользователя...",
                custom_id="user_id",
                style=disnake.TextInputStyle.short,
                required=True,
                min_length=17,
                max_length=20
            )
        ]
        super().__init__(title="🔍 Верификация пользователя", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        user_id = int(interaction.text_values["user_id"])
        guild = interaction.guild
        user = guild.get_member(user_id)

        if not user:
            return await interaction.response.send_message(
                f"❌ Пользователь с ID `{user_id}` не найден на сервере",
                ephemeral=True
            )

        verify_role = guild.get_role(VERIFY_ROLE_ID)
        if verify_role not in user.roles:
            return await interaction.response.send_message(
                f"❌ Пользователь {user.mention} не имеет роли ожидания верификации",
                ephemeral=True
            )

        embed = disnake.Embed(
            title="🔐 Запрос на верификацию",
            description=f"**Пользователь:** {user.mention}\n"
                        f"**ID:** {user.id}\n"
                        f"**Имя:** {user.name}\n"
                        f"**Ник:** {user.display_name}\n"
                        f"**Аккаунт создан:** {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                        f"**Зашёл на сервер:** {user.joined_at.strftime('%d.%m.%Y %H:%M')}\n"
                        f"**Запросил:** {self.staff_member.mention}",
            color=disnake.Color.blue(),
            timestamp=datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)
        original_msg = await interaction.original_response()

        view = ActionButtons(self.cog, user, self.staff_member, original_msg)
        await original_msg.edit(view=view)


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect('verification.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT,
                role_id TEXT,
                joined_at TEXT,
                PRIMARY KEY (user_id, role_id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS verified_users (
                user_id TEXT PRIMARY KEY,
                verified_at TEXT,
                verified_by TEXT
            )
        ''')
        self.conn.commit()

    def save_user_roles(self, user_id: str, roles: list, joined_at: str):
        self.cursor.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        for role_id in roles:
            self.cursor.execute(
                "INSERT INTO user_roles (user_id, role_id, joined_at) VALUES (?, ?, ?)",
                (user_id, str(role_id), joined_at)
            )
        self.conn.commit()

    def get_user_roles(self, user_id: str) -> list:
        self.cursor.execute("SELECT role_id FROM user_roles WHERE user_id = ?", (user_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def delete_user_roles(self, user_id: str):
        self.cursor.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        self.conn.commit()

    async def log_to_channel(self, embed: disnake.Embed):
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    async def send_dm(self, user: disnake.User, embed: disnake.Embed) -> bool:
        try:
            await user.send(embed=embed)
            return True
        except:
            return False

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        guild = member.guild
        current_roles = [role.id for role in member.roles if role.name != "@everyone"]
        joined_at = datetime.utcnow().isoformat()

        if current_roles:
            self.save_user_roles(str(member.id), current_roles, joined_at)
            await member.remove_roles(*member.roles[1:], reason="Снятие ролей при входе (верификация)")

        verify_role = guild.get_role(VERIFY_ROLE_ID)
        if verify_role:
            await member.add_roles(verify_role, reason="Выдана роль ожидания верификации")

            log_embed = disnake.Embed(
                title="👤 Новый пользователь",
                description=f"**Пользователь:** {member.mention} (`{member.id}`)\n"
                            f"**Имя:** {member.name}\n"
                            f"**Сохранено ролей:** {len(current_roles)}\n"
                            f"**Статус:** Ожидает верификации",
                color=disnake.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await self.log_to_channel(log_embed)

    @commands.slash_command(name="action", description="Верифицировать пользователя (только для персонала)")
    async def action(self, inter: disnake.ApplicationCommandInteraction):
        staff_role = inter.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in inter.author.roles:
            return await inter.response.send_message(
                "❌ У вас нет прав на использование этой команды",
                ephemeral=True
            )

        modal = ActionModal(self, inter.author)
        await inter.response.send_modal(modal)

    @commands.slash_command(name="действие", description="Верифицировать пользователя (русская команда)")
    async def action_ru(self, inter: disnake.ApplicationCommandInteraction):
        await self.action(inter)


def setup(bot: commands.Bot):
    bot.add_cog(VerificationCog(bot))