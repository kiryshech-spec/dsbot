import disnake
from disnake.ext import commands
from disnake.ui import Modal, TextInput, View, Button

# ID канала для отправки заявок
APPLICATION_CHANNEL_ID = 1445415190710718577

# ID роли, которая может использовать команду setup_apps
ALLOWED_ROLE_ID = 1413460782179553280

# Доступные должности
ROLES_LIST = {
    "Модератор": {
        "description": "Следит за порядком и соблюдением правил",
        "role_id": 1413461127307726940
    },
    "Ивентер": {
        "description": "Проводит интересные ивенты и мероприятия",
        "role_id": 1445724141268242504
    }
}


def has_permission(inter: disnake.ApplicationCommandInteraction) -> bool:
    """Проверяет, есть ли у пользователя право использовать команду"""
    # Администратор всегда может
    if inter.author.guild_permissions.administrator:
        return True
    # Проверяем наличие роли
    role = inter.guild.get_role(ALLOWED_ROLE_ID)
    if role and role in inter.author.roles:
        return True
    return False


class ApplicationModal(Modal):
    """Модальное окно для заявки на должность"""

    def __init__(self, role_name: str):
        self.role_name = role_name

        components = [
            TextInput(
                label="Как вас зовут?",
                placeholder="Введите ваше имя/никнейм",
                custom_id="name",
                required=True,
                max_length=100
            ),
            TextInput(
                label="Сколько вам лет?",
                placeholder="Введите ваш возраст",
                custom_id="age",
                required=True,
                max_length=3
            ),
            TextInput(
                label="Сколько времени готовы уделять серверу?",
                placeholder="Пример: 2-3 часа в день",
                custom_id="time",
                required=True,
                max_length=200
            ),
            TextInput(
                label="Расскажите немного о себе",
                placeholder="Ваши сильные и слабые стороны, чем занимаетесь...",
                custom_id="about",
                required=True,
                style=disnake.TextInputStyle.paragraph,
                max_length=1000
            ),
            TextInput(
                label="Ваше знание правил (от 1 до 10)",
                placeholder="Пример: 8",
                custom_id="rules_knowledge",
                required=True,
                max_length=2
            ),
        ]
        super().__init__(
            title=f"Заявка на должность {role_name}",
            components=components,
            custom_id=f"app_{role_name}"
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        # Получаем данные из формы
        name = interaction.text_values["name"]
        age = interaction.text_values["age"]
        time = interaction.text_values["time"]
        about = interaction.text_values["about"]
        rules_knowledge = interaction.text_values["rules_knowledge"]

        # Создаем embed для отправки в канал
        embed = disnake.Embed(
            title=f"📋 Новая заявка на {self.role_name}",
            description=f"От пользователя: {interaction.author.mention}",
            color=disnake.Color.blue(),
            timestamp=interaction.created_at
        )
        embed.add_field(name="👤 Имя", value=name, inline=True)
        embed.add_field(name="🎂 Возраст", value=age, inline=True)
        embed.add_field(name="⏰ Время", value=time, inline=True)
        embed.add_field(name="📝 О себе", value=about[:1024], inline=False)
        embed.add_field(name="📖 Знание правил", value=f"{rules_knowledge}/10", inline=True)
        embed.set_footer(text=f"ID: {interaction.author.id}")

        # Кнопки для принятия/отказа
        view = ApplicationReviewView(
            user_id=interaction.author.id,
            user_name=name,
            role_name=self.role_name
        )

        # Отправляем в канал с заявками
        channel = interaction.guild.get_channel(APPLICATION_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Ваша заявка на **{self.role_name}** отправлена! Ожидайте решения в личных сообщениях.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Ошибка: канал для заявок не найден. Сообщите администратору.",
                ephemeral=True
            )


class ApplicationReviewView(View):
    """Кнопки для принятия/отказа заявки"""

    def __init__(self, user_id: int, user_name: str, role_name: str):
        super().__init__(timeout=86400)  # 24 часа
        self.user_id = user_id
        self.user_name = user_name
        self.role_name = role_name

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.green)
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        # Проверка прав (только админы или роль ALLOWED_ROLE_ID)
        if not interaction.author.guild_permissions.administrator:
            allowed_role = interaction.guild.get_role(ALLOWED_ROLE_ID)
            if not allowed_role or allowed_role not in interaction.author.roles:
                await interaction.response.send_message("❌ У вас нет прав для принятия заявок!", ephemeral=True)
                return

        # Отключаем кнопки
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Отправляем результат пользователю в ЛС
        try:
            user = await interaction.client.fetch_user(self.user_id)
            embed = disnake.Embed(
                title="✅ Ваша заявка одобрена!",
                description=f"Поздравляем! Ваша заявка на должность **{self.role_name}** была **принята**!\n"
                            f"Теперь вы часть команды {interaction.guild.name}.",
                color=disnake.Color.green()
            )
            await user.send(embed=embed)
        except:
            pass

        # Обновляем embed в канале
        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.green()
        embed.add_field(name="📌 Решение", value=f"✅ Принято {interaction.author.mention}", inline=False)
        await interaction.message.edit(embed=embed)

        # Выдаём роль (если указана)
        role_id = ROLES_LIST.get(self.role_name, {}).get("role_id")
        if role_id:
            guild = interaction.guild
            role = guild.get_role(role_id)
            if role:
                member = guild.get_member(self.user_id)
                if member:
                    await member.add_roles(role)

        await interaction.response.send_message(f"✅ Заявка {self.user_name} принята!", ephemeral=True)

    @disnake.ui.button(label="❌ Отказать", style=disnake.ButtonStyle.red)
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        # Проверка прав (только админы или роль ALLOWED_ROLE_ID)
        if not interaction.author.guild_permissions.administrator:
            allowed_role = interaction.guild.get_role(ALLOWED_ROLE_ID)
            if not allowed_role or allowed_role not in interaction.author.roles:
                await interaction.response.send_message("❌ У вас нет прав для отказа заявок!", ephemeral=True)
                return

        # Отключаем кнопки
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Отправляем результат пользователю в ЛС
        try:
            user = await interaction.client.fetch_user(self.user_id)
            embed = disnake.Embed(
                title="❌ Ваша заявка отклонена",
                description=f"К сожалению, ваша заявка на должность **{self.role_name}** была **отклонена**.\n"
                            f"Вы можете попробовать подать заявку снова позже.",
                color=disnake.Color.red()
            )
            await user.send(embed=embed)
        except:
            pass

        # Обновляем embed в канале
        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.red()
        embed.add_field(name="📌 Решение", value=f"❌ Отказано {interaction.author.mention}", inline=False)
        await interaction.message.edit(embed=embed)

        await interaction.response.send_message(f"❌ Заявка {self.user_name} отклонена!", ephemeral=True)


class RoleSelectDropdown(disnake.ui.StringSelect):
    """Выпадающий список для выбора должности"""

    def __init__(self):
        options = []
        for role_name in ROLES_LIST.keys():
            options.append(
                disnake.SelectOption(
                    label=role_name,
                    description=ROLES_LIST[role_name]["description"],
                    value=role_name,
                    emoji="📝"
                )
            )
        super().__init__(
            placeholder="Выберите должность",
            options=options,
            custom_id="role_select"
        )

    async def callback(self, interaction: disnake.MessageInteraction):
        selected_role = self.values[0]
        modal = ApplicationModal(selected_role)
        await interaction.response.send_modal(modal)


class ApplicationView(View):
    """Главное меню с дропдауном"""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelectDropdown())


class ApplicationsCog(commands.Cog):
    """Ког для системы заявок"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="setup_apps", description="Создать панель заявок")
    async def setup_applications(self, inter: disnake.ApplicationCommandInteraction):
        """Создаёт панель для подачи заявок"""

        # Проверка прав
        if not has_permission(inter):
            await inter.response.send_message(
                "❌ У вас нет прав для использования этой команды! Требуется роль Администратор или специальная роль.",
                ephemeral=True
            )
            return

        embed = disnake.Embed(
            title="📋 Подача заявок в персонал",
            description="Нажмите на меню ниже и выберите должность, на которую хотите подать заявку.\n\n"
                        f"**Доступные должности:**\n"
                        f"• **Модератор** — {ROLES_LIST['Модератор']['description']}\n"
                        f"• **Ивентер** — {ROLES_LIST['Ивентер']['description']}\n\n"
                        f"После заполнения формы, ваша заявка будет рассмотрена администрацией.\n"
                        f"Результат придёт вам в **личные сообщения**.",
            color=disnake.Color.purple()
        )

        view = ApplicationView()

        await inter.response.send_message(embed=embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(ApplicationsCog(bot))