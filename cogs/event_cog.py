import disnake
from disnake.ext import commands

# ID для категории и каналов
CATEGORY_ID = 1493960953450991656
LOG_CHANNEL_ID = 1493521581585076334
ANNOUNCE_CHANNEL_ID = 1418448567013740576
ALLOWED_ROLES = [1445719593736863774, 1445724141268242504]


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ EventCog инициализирован")

    @commands.slash_command(name="event", description="🎮 Управление ивентами")
    async def event(self, inter: disnake.ApplicationCommandInteraction):
        if not any(role.id in ALLOWED_ROLES for role in inter.author.roles):
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return

        embed = disnake.Embed(
            title="🎮 Панель управления ивентами",
            description="Используйте кнопки ниже",
            color=disnake.Color.blurple()
        )
        await inter.response.send_message(embed=embed, view=EventView())

    @commands.slash_command(name="unlock", description="Разблокировать доступ в голосовой канал")
    async def unlock_channel(
            self,
            inter: disnake.ApplicationCommandInteraction,
            member: disnake.Member,
            channel: disnake.VoiceChannel
    ):
        if not any(role.id in ALLOWED_ROLES for role in inter.author.roles):
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return

        try:
            await channel.set_permissions(member, connect=None, reason=f"Разблокировка от {inter.author}")
            await inter.response.send_message(f"✅ {member.mention} разблокирован в {channel.mention}!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class EventView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="📌 Создать ивент", style=disnake.ButtonStyle.green)
    async def create_event(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not any(role.id in ALLOWED_ROLES for role in inter.author.roles):
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        await inter.response.send_modal(CreateEventModal())

    @disnake.ui.button(label="🔚 Завершить ивент", style=disnake.ButtonStyle.red)
    async def end_event(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not any(role.id in ALLOWED_ROLES for role in inter.author.roles):
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        category = inter.guild.get_channel(CATEGORY_ID)

        if not category:
            await inter.edit_original_response(content="❌ Категория не найдена!")
            return

        deleted = 0
        for channel in category.channels:
            try:
                await channel.delete()
                deleted += 1
            except:
                pass

        await inter.edit_original_response(content=f"✅ Удалено каналов: {deleted}")

    @disnake.ui.button(label="🚫 Выгнать участника", style=disnake.ButtonStyle.danger)
    async def kick_member(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not any(role.id in ALLOWED_ROLES for role in inter.author.roles):
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return

        category = inter.guild.get_channel(CATEGORY_ID)
        if not category:
            await inter.response.send_message("❌ Категория не найдена!", ephemeral=True)
            return

        members_in_voice = []
        for channel in category.voice_channels:
            for member in channel.members:
                if member.id != inter.author.id:
                    members_in_voice.append(member)

        members_in_voice = list(set(members_in_voice))

        if not members_in_voice:
            await inter.response.send_message("❌ Нет других участников!", ephemeral=True)
            return

        select = MemberSelect(members_in_voice)
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите участника:", ephemeral=True, view=view)


class CreateEventModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Название", placeholder="Название ивента...", custom_id="name", max_length=100),
            disnake.ui.TextInput(label="Описание", placeholder="Описание...", custom_id="desc", max_length=500,
                                 style=disnake.TextInputStyle.paragraph),
            disnake.ui.TextInput(label="Лимит", placeholder="1-99", custom_id="limit", max_length=2),
        ]
        super().__init__(title="Создание ивента", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        name = inter.text_values["name"]
        desc = inter.text_values["desc"]
        limit = inter.text_values["limit"]

        if not limit.isdigit() or not (1 <= int(limit) <= 99):
            await inter.response.send_message("❌ Лимит 1-99!", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)

        category = inter.guild.get_channel(CATEGORY_ID)
        if not category:
            await inter.edit_original_response(content="❌ Категория не найдена!")
            return

        voice = await inter.guild.create_voice_channel(name=f"🎙 {name}", category=category, user_limit=int(limit),
                                                       position=0)
        text = await inter.guild.create_text_channel(name=f"📝 {name}", category=category, position=1)

        announce = inter.guild.get_channel(ANNOUNCE_CHANNEL_ID)
        if announce:
            await announce.send(f"🎉 **{name}**\n{desc}\n{voice.mention}\n{text.mention}\nЛимит: {limit}")

        await inter.edit_original_response(content=f"✅ Ивент создан!\n{voice.mention}\n{text.mention}")


class MemberSelect(disnake.ui.StringSelect):
    def __init__(self, members):
        options = [disnake.SelectOption(label=m.display_name, value=str(m.id)) for m in members[:25]]
        super().__init__(placeholder="Выберите участника...", options=options)

    async def callback(self, inter: disnake.MessageInteraction):
        member = inter.guild.get_member(int(self.values[0]))
        if not member:
            await inter.response.send_message("❌ Не найден!", ephemeral=True)
            return
        await inter.response.send_modal(KickReasonModal(member))


class KickReasonModal(disnake.ui.Modal):
    def __init__(self, member):
        self.member = member
        components = [disnake.ui.TextInput(label="Причина", placeholder="Причина исключения...", custom_id="reason",
                                           max_length=500, style=disnake.TextInputStyle.paragraph)]
        super().__init__(title=f"Исключение {member.display_name}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        reason = inter.text_values["reason"]

        await inter.response.defer(ephemeral=True)

        if self.member.id == inter.author.id:
            await inter.edit_original_response(content="❌ Нельзя исключить себя!")
            return

        voice = self.member.voice
        if not voice or not voice.channel:
            await inter.edit_original_response(content="❌ Участник не в голосовом канале!")
            return

        category = inter.guild.get_channel(CATEGORY_ID)
        if voice.channel.category_id != CATEGORY_ID:
            await inter.edit_original_response(content="❌ Участник не в ивенте!")
            return

        # СОХРАНЯЕМ КАНАЛ ДО ОТКЛЮЧЕНИЯ
        voice_channel = voice.channel

        # БЛОКИРУЕМ ДОСТУП К КАНАЛУ (СТАВИМ ЗАМОЧЕК)
        try:
            # Запрещаем подключаться к этому голосовому каналу
            await voice_channel.set_permissions(
                self.member,
                connect=False,
                reason=f"Исключён из ивента: {reason}"
            )

            # Отключаем участника из канала
            await self.member.move_to(None, reason=f"Исключён из ивента: {reason}")

        except Exception as e:
            await inter.edit_original_response(content=f"❌ Ошибка: {e}")
            return

        # Отправляем причину в ЛС
        try:
            embed = disnake.Embed(
                title="🔒 Вы исключены из ивента!",
                description=f"**Сервер:** {inter.guild.name}\n"
                            f"**Канал:** {voice_channel.mention}\n"
                            f"**Причина:** {reason}\n"
                            f"**Кто исключил:** {inter.author.mention}\n\n"
                            f"🔒 Вам **заблокирован доступ** в этот голосовой канал",
                color=disnake.Color.red()
            )
            await self.member.send(embed=embed)
        except:
            pass

        # Логируем в канал
        log_channel = inter.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = disnake.Embed(
                title="🔨 Исключение участника из ивента",
                description=f"**Участник:** {self.member.mention} ({self.member})\n"
                            f"**Канал:** {voice_channel.mention}\n"
                            f"**Причина:** {reason}\n"
                            f"**Кто исключил:** {inter.author.mention}\n"
                            f"**Статус:** 🔒 Доступ в канал заблокирован\n"
                            f"**Время:** <t:{int(inter.created_at.timestamp())}:F>",
                color=disnake.Color.orange()
            )
            await log_channel.send(embed=embed)

        # Отправляем подтверждение
        await inter.edit_original_response(
            content=f"✅ {self.member.mention} исключён из ивента!\n"
                    f"🔒 Доступ в канал {voice_channel.mention} заблокирован!\n"
                    f"📝 Причина отправлена в ЛС и лог-канал."
        )


def setup(bot):
    bot.add_cog(EventCog(bot))
    print("🎮 EventCog загружен!")