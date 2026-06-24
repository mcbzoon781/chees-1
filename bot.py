import discord
from discord.ext import commands
import chess
import random
import json
import os

# تحديد الصلاحيات التي يحتاجها البوت للعمل وقراءة الرسائل
intents = discord.Intents.default()
intents.message_content = True  

# تحديد البوت مع البادئة "." بدلاً من "!" و "/"
bot = commands.Bot(command_prefix=".", intents=intents)

# ⚙️ ملف حفظ إعدادات القنوات المسموحة لكل سيرفر على حدة
CONFIG_FILE = "config.json"
# الهيكل الجديد سيكون: { "guild_id_string": [channel_id_1, channel_id_2] }
GUILD_CONFIGS = {}

# ملف حفظ الأدمن
ADMINS_FILE = "admins.json"
ADMINS = {}

def load_admins():
    """تحميل قائمة الأدمن من الملف"""
    global ADMINS
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r") as f:
                ADMINS = json.load(f)
                print(f"📂 تم تحميل قائمة الأدمن بنجاح: {ADMINS}")
        except Exception as e:
            print(f"❌ خطأ أثناء تحميل ملف الأدمن: {e}")
            ADMINS = {}
    else:
        ADMINS = {}

def save_admins():
    """حفظ قائمة الأدمن في ملف JSON"""
    try:
        with open(ADMINS_FILE, "w") as f:
            json.dump(ADMINS, f, indent=4)
            print(f"💾 تم حفظ قائمة الأدمن بنجاح!")
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الأدمن: {e}")

def is_admin(user_id, guild_id):
    """التحقق من أن المستخدم أدمن في السيرفر"""
    guild_id_str = str(guild_id)
    if guild_id_str not in ADMINS:
        return False
    return str(user_id) in ADMINS[guild_id_str]

def load_config():
    """تحميل القنوات المسموحة من الملف عند بدء التشغيل وتوزيعها حسب السيرفر"""
    global GUILD_CONFIGS
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                GUILD_CONFIGS = json.load(f)
                print(f"📂 تم تحميل إعدادات السيرفرات بنجاح: {GUILD_CONFIGS}")
        except Exception as e:
            print(f"❌ خطأ أثناء تحميل ملف الإعدادات: {e}")
            GUILD_CONFIGS = {}
    else:
        GUILD_CONFIGS = {}

def save_config():
    """حفظ إعدادات السيرفرات المنفصلة في ملف JSON لكي لا تضيع"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(GUILD_CONFIGS, f, indent=4)
            print(f"💾 تم حفظ إعدادات السيرفرات بنجاح!")
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الإعدادات: {e}")

# قاموس لتخزين الألعاب الجارية وغرف الانتظار في السيرفر
games = {}

def is_player_busy(user):
    """تحقق مما إذا كان اللاعب مشاركاً بالفعل في أي مباراة قائمة حالياً في السيرفر"""
    for channel_id, game in games.items():
        if user in game.get("players", []):
            return True
    return False

class JoinView(discord.ui.View):
    def __init__(self, host, ctx):
        super().__init__(timeout=180)  # تنتهي صلاحية الزر بعد 3 دقائق
        self.host = host
        self.ctx = ctx

    @discord.ui.button(label="دخول ♟️", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_id = interaction.channel_id
        
        # التأكد من أن غرفة الانتظار لا تزال قائمة ولم تبدأ اللعبة بعد
        if channel_id not in games or games[channel_id]["state"] != "lobby":
            await interaction.response.send_message("❌ انتهت صلاحية هذه الغرفة أو بدأت المباراة بالفعل!", ephemeral=True)
            return

        user = interaction.user
        
        # منع منشئ التحدي من اللعب ضد نفسه
        if user == self.host:
            await interaction.response.send_message("❌ أنت مسجل بالفعل كلاعب أول في هذه المباراة! بانتظار خصمك...", ephemeral=True)
            return

        if is_player_busy(user):
            await interaction.response.send_message("❌ أنت تشارك بالفعل في مباراة شطرنج قائمة في السيرفر حالياً! لا يمكنك الانضمام لتحدٍ جديد حتى تنهي مباراتك السابقة.", ephemeral=True)
            return

        # تسجيل اللاعب الثاني وإيقاف استقبال التفاعل على الزر
        game = games[channel_id]
        game["players"].append(user)
        self.stop()

        # تعديل الزر في ديسكورد ليكون ملغياً ولا يمكن ضغطه مرة أخرى
        button.disabled = True
        button.label = "تم بدء اللعب 🎮"
        button.style = discord.ButtonStyle.grey
        await interaction.response.edit_message(view=self)

        # خلط اللاعبين عشوائياً وتوزيع الألوان
        players = game["players"]
        random.shuffle(players)

        game["white"] = players[0]
        game["black"] = players[1]
        game["board"] = chess.Board()
        game["state"] = "playing"

        embed = discord.Embed(
            title="🎮 بدأت ملحمة الشطرنج!",
            description=f"⚪ **اللون الأبيض:** {game['white'].mention}\n⚫ **اللون الأسود:** {game['black'].mention}\n\nالدور الآن للقطع البيضاء ⚪!\n💡 اكتب `.تحرك` للعب (مثال: `.تحرك e2e4`).",
            color=discord.Color.green()
        )
        await self.ctx.send(embed=embed)
        
        # عرض رقعة الشطرنج لأول مرة بالصور
        await display_board(self.ctx, game["board"])

@bot.event
async def on_ready():
    # تحميل القنوات المخزنة والأدمن
    load_config()
    load_admins()
    
    # وضع حالة نشاط مميزة للبوت في ديسكورد
    await bot.change_presence(activity=discord.Game(name=".شطرنج ♟️"))
        
    print("--------------------------------------")
    print(f"🤖 البوت جاهز لِلعب الشطرنج بالأوامر العربية!")
    print(f"اسم البوت الحالي: {bot.user}")
    print("--------------------------------------")

# ================== أوامر الإدارة ==================

@bot.command(name="اضافة_ادمن")
async def add_admin(ctx, user_id: str):
    """إضافة أدمن من خلال كوبي يوزر ايدي"""
    if not ctx.guild:
        await ctx.send("❌ هذا الأمر يمكن استخدامه داخل السيرفرات فقط!")
        return
    
    # التحقق من صلاحيات المستخدم (يحتاج صلاحية إدارة السيرفر)
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ عذراً! هذا الأمر مخصص فقط للأدمن الذين يملكون صلاحية **إدارة السيرفر**.")
        return
    
    try:
        user_id_int = int(user_id.strip())
    except ValueError:
        await ctx.send("❌ يرجى إدخال أرقام فقط للـ ID!")
        return
    
    guild_id_str = str(ctx.guild.id)
    if guild_id_str not in ADMINS:
        ADMINS[guild_id_str] = []
    
    if str(user_id_int) in ADMINS[guild_id_str]:
        await ctx.send(f"⚠️ هذا المستخدم مضاف بالفعل كأدمن في هذا السيرفر!")
        return
    
    ADMINS[guild_id_str].append(str(user_id_int))
    save_admins()
    
    # محاولة الحصول على اسم المستخدم
    try:
        user = await bot.fetch_user(user_id_int)
        await ctx.send(f"✅ تم إضافة {user.mention} كأدمن للبوت في هذا السيرفر بنجاح!")
    except:
        await ctx.send(f"✅ تم إضافة المستخدم ذو الـ ID `{user_id_int}` كأدمن للبوت في هذا السيرفر بنجاح!")

@bot.command(name="ازالة_ادمن")
async def remove_admin(ctx, user_id: str):
    """إزالة أدمن من خلال كوبي يوزر ايدي"""
    if not ctx.guild:
        await ctx.send("❌ هذا الأمر يمكن استخدامه داخل السيرفرات فقط!")
        return
    
    # التحقق من صلاحيات المستخدم (يحتاج صلاحية إدارة السيرفر)
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ عذراً! هذا الأمر مخصص فقط للأدمن الذين يملكون صلاحية **إدارة السيرفر**.")
        return
    
    try:
        user_id_int = int(user_id.strip())
    except ValueError:
        await ctx.send("❌ يرجى إدخال أرقام فقط للـ ID!")
        return
    
    guild_id_str = str(ctx.guild.id)
    if guild_id_str not in ADMINS or str(user_id_int) not in ADMINS[guild_id_str]:
        await ctx.send("❌ هذا المستخدم ليس أدمن للبوت في هذا السيرفر!")
        return
    
    ADMINS[guild_id_str].remove(str(user_id_int))
    save_admins()
    
    try:
        user = await bot.fetch_user(user_id_int)
        await ctx.send(f"✅ تم إزالة {user.mention} من قائمة الأدمن في هذا السيرفر!")
    except:
        await ctx.send(f"✅ تم إزالة المستخدم ذو الـ ID `{user_id_int}` من قائمة الأدمن في هذا السيرفر!")

@bot.command(name="اوامر")
async def show_commands(ctx):
    """عرض قائمة الأوامر كرسالة تفاعلية"""
    embed = discord.Embed(
        title="📋 قائمة أوامر البوت",
        description="اختر القسم الذي تريد عرض أوامره:",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="🎮 أوامر اللعبة", 
        value="`.شطرنج` - بدء مباراة جديدة\n`.تحرك` - تحريك قطعة\n`.انسحاب` - الانسحاب من المباراة\n`.انهاء` - إيقاف المباراة",
        inline=False
    )
    embed.add_field(
        name="🔧 أوامر الإدارة", 
        value="`.اضافة_روم` - إضافة روم مسموح باللعب فيها\n`.حذف_روم` - حذف روم من القائمة\n`.الرومات` - عرض الرومات المسموحة\n`.اضافة_ادمن` - إضافة أدمن للبوت\n`.ازالة_ادمن` - إزالة أدمن من البوت",
        inline=False
    )
    embed.add_field(
        name="📖 أوامر عامة", 
        value="`.اوامر` - عرض هذه القائمة",
        inline=False
    )
    embed.set_footer(text="جميع الأوامر تبدأ بعلامة . (نقطة)")
    
    # إنشاء أزرار تفاعلية
    view = CommandsView(ctx)
    await ctx.send(embed=embed, view=view)

class CommandsView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
    
    @discord.ui.button(label="🎮 أوامر اللعبة", style=discord.ButtonStyle.primary)
    async def game_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎮 أوامر اللعبة",
            description="جميع أوامر اللعبة تبدأ بعلامة `.`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="`.شطرنج`", 
            value="إنشاء غرفة انتظار والبدء في تحدي شطرنج جديد",
            inline=False
        )
        embed.add_field(
            name="`.تحرك [الحركة]`", 
            value="تحريك قطعة شطرنج على الرقعة (مثال: `.تحرك e2e4`)",
            inline=False
        )
        embed.add_field(
            name="`.انسحاب`", 
            value="الانسحاب من مباراة الشطرنج القائمة وإعلان فوز الخصم",
            inline=False
        )
        embed.add_field(
            name="`.انهاء`", 
            value="إيقاف مباراة الشطرنج الحالية أو إلغاء غرفة الانتظار",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔧 أوامر الإدارة", style=discord.ButtonStyle.success)
    async def admin_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔧 أوامر الإدارة",
            description="جميع أوامر الإدارة تبدأ بعلامة `.`",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="`.اضافة_روم [رقم_الروم]`", 
            value="إضافة روم مسموح باللعب فيها بالسيرفر الحالي (للمشرفين فقط)",
            inline=False
        )
        embed.add_field(
            name="`.حذف_روم [رقم_الروم]`", 
            value="إزالة روم من قائمة الرومات المسموحة بالسيرفر الحالي (للمشرفين فقط)",
            inline=False
        )
        embed.add_field(
            name="`.الرومات`", 
            value="عرض جميع الرومات المسموح باللعب فيها في هذا السيرفر",
            inline=False
        )
        embed.add_field(
            name="`.اضافة_ادمن [ايدي_المستخدم]`", 
            value="إضافة أدمن للبوت في هذا السيرفر (يحتاج صلاحية إدارة السيرفر)",
            inline=False
        )
        embed.add_field(
            name="`.ازالة_ادمن [ايدي_المستخدم]`", 
            value="إزالة أدمن من البوت في هذا السيرفر (يحتاج صلاحية إدارة السيرفر)",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📖 أوامر عامة", style=discord.ButtonStyle.secondary)
    async def general_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📖 أوامر عامة",
            description="جميع الأوامر العامة تبدأ بعلامة `.`",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="`.اوامر`", 
            value="عرض هذه القائمة التفاعلية للأوامر",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================== أوامر إدارة القنوات ==================

@bot.command(name="اضافة_روم")
async def add_channel(ctx, *, رقم_الروم: str):
    """إضافة روم مخصصة وتخزينها تحت معرف السيرفر الحالي"""
    if not ctx.guild:
        await ctx.send("❌ هذا الأمر يمكن استخدامه داخل السيرفرات فقط!")
        return

    # التحقق من صلاحيات المستخدم (مشرف أو أدمن البوت)
    if not ctx.author.guild_permissions.manage_channels and not is_admin(ctx.author.id, ctx.guild.id):
        await ctx.send("❌ عذراً! هذا الأمر مخصص فقط للمشرفين أو أدمن البوت.")
        return

    try:
        channel_id = int(رقم_الروم.strip())
        # التحقق من أن القناة موجودة فعلاً في السيرفر الحالي
        channel = ctx.guild.get_channel(channel_id) or await ctx.guild.fetch_channel(channel_id)
        if not channel:
            await ctx.send("❌ لم أتمكن من العثور على هذه القناة في هذا السيرفر. تأكد من صحة الـ ID!")
            return
    except Exception:
        await ctx.send("❌ صيغة الـ ID غير صحيحة. يرجى كتابة أرقام فقط!")
        return

    guild_id_str = str(ctx.guild.id)
    if guild_id_str not in GUILD_CONFIGS:
        GUILD_CONFIGS[guild_id_str] = []

    if channel_id in GUILD_CONFIGS[guild_id_str]:
        await ctx.send(f"⚠️ هذه الروم {channel.mention} مضافة بالفعل في القائمة المسموحة لهذا السيرفر!")
        return

    GUILD_CONFIGS[guild_id_str].append(channel_id)
    save_config()
    await ctx.send(f"✅ تم إضافة الروم {channel.mention} بنجاح! يمكن للاعبين في هذا السيرفر اللعب داخلها الآن.")

@bot.command(name="حذف_روم")
async def remove_channel(ctx, *, رقم_الروم: str):
    """حذف روم مخصصة من إعدادات السيرفر الحالي"""
    if not ctx.guild:
        await ctx.send("❌ هذا الأمر يمكن استخدامه داخل السيرفرات فقط!")
        return

    # التحقق من صلاحيات المستخدم (مشرف أو أدمن البوت)
    if not ctx.author.guild_permissions.manage_channels and not is_admin(ctx.author.id, ctx.guild.id):
        await ctx.send("❌ عذراً! هذا الأمر مخصص فقط للمشرفين أو أدمن البوت.")
        return

    try:
        channel_id = int(رقم_الروم.strip())
    except ValueError:
        await ctx.send("❌ يرجى إدخال أرقام فقط للـ ID!")
        return

    guild_id_str = str(ctx.guild.id)
    if guild_id_str not in GUILD_CONFIGS or channel_id not in GUILD_CONFIGS[guild_id_str]:
        await ctx.send("❌ هذه الروم ليست مضافة في قائمة الرومات المسموحة لهذا السيرفر!")
        return

    GUILD_CONFIGS[guild_id_str].remove(channel_id)
    save_config()
    await ctx.send(f"✅ تم إزالة الروم بنجاح من قائمة هذا السيرفر.")

@bot.command(name="الرومات")
async def list_channels(ctx):
    """عرض رومات اللعب المسموحة للسيرفر الحالي"""
    if not ctx.guild:
        await ctx.send("❌ هذا الأمر يمكن استخدامه داخل السيرفرات فقط!")
        return

    guild_id_str = str(ctx.guild.id)
    allowed_channels = GUILD_CONFIGS.get(guild_id_str, [])

    if not allowed_channels:
        await ctx.send("🌐 البوت يعمل حالياً في جميع قنوات هذا السيرفر دون قيود (لم يتم تحديد قنوات مخصصة بعد).")
        return

    channels_mentions = []
    for cid in allowed_channels:
        channel = ctx.guild.get_channel(cid)
        if channel:
            channels_mentions.append(channel.mention)
        else:
            channels_mentions.append(f"`{cid}` (قناة غير موجودة أو مخفية عن البوت)")

    embed = discord.Embed(
        title="📌 القنوات المسموحة للعب الشطرنج في هذا السيرفر",
        description="\n".join([f"- {m}" for m in channels_mentions]),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# ================== أوامر اللعبة ==================

@bot.command(name="شطرنج")
async def chess_start(ctx):
    """بدء مباراة جديدة والتحقق من قيود القنوات المسموحة"""
    if not ctx.guild:
        await ctx.send("❌ يمكنك لعب الشطرنج داخل السيرفرات فقط!")
        return

    channel_id = ctx.channel.id
    guild_id_str = str(ctx.guild.id)
    allowed_channels = GUILD_CONFIGS.get(guild_id_str, [])
    
    # 🚫 التحقق مما إذا كانت القناة الحالية مسموحاً باللعب فيها ضمن هذا السيرفر بالتحديد
    if allowed_channels and channel_id not in allowed_channels:
        allowed_mentions = " أو ".join([f"<#{cid}>" for cid in allowed_channels])
        await ctx.send(f"❌ عذراً يا {ctx.author.mention}! لا يمكنك بدء مباراة في هذه القناة. يرجى الذهاب للرومات المخصصة للعب في هذا السيرفر: {allowed_mentions}")
        return

    if channel_id in games:
        await ctx.send("❌ هناك مباراة قائمة أو غرفة انتظار بالفعل في هذه القناة! استخدم `.انهاء` لإنهائها أولاً.")
        return
    
    if is_player_busy(ctx.author):
        await ctx.send(f"❌ يا {ctx.author.mention}، لا يمكنك بدء تحدٍ جديد لأنك تشارك حالياً في مباراة شطرنج أخرى قائمة في السيرفر! أنهِ مباراتك الحالية أولاً.")
        return
    
    # إنشاء غرفة انتظار وإضافة اللاعب الأول (منشئ الأمر)
    games[channel_id] = {
        "state": "lobby",
        "players": [ctx.author],
        "white": None,
        "black": None,
        "board": None
    }
    
    embed = discord.Embed(
        title="♟️ غرفة انتظار مباراة الشطرنج",
        description=f"اللاعب الأول: {ctx.author.mention}\n\n**بانتظار انضمام اللاعب الثاني...**\nاضغط على زر **دخول ♟️** أدناه للتحدي! وسيتم توزيع الألوان عشوائياً.",
        color=discord.Color.blue()
    )
    
    # ربط الزر التفاعلي بالرسالة المرسلة
    view = JoinView(ctx.author, ctx)
    await ctx.send(embed=embed, view=view)

@bot.command(name="تحرك")
async def move(ctx, *, الحركة: str):
    """تحريك القطع وتحديث رقعة اللعب جولة بعد جولة"""
    channel_id = ctx.channel.id
    if channel_id not in games or games[channel_id]["state"] != "playing":
        await ctx.send("❌ لا توجد مباراة قائمة حالياً في هذه القناة. اكتب `.شطرنج` للبدء.")
        return
    
    game = games[channel_id]
    board = game["board"]
    
    # تحديد من هو اللاعب الذي عليه الدور الحالي
    expected_player = game["white"] if board.turn == chess.WHITE else game["black"]
    
    # التحقق من أن الشخص الذي كتب الأمر هو اللاعب الذي عليه الدور فعلاً
    if ctx.author != expected_player:
        await ctx.send(f"❌ ليس دورك يا {ctx.author.mention}! الدور الحالي لـ: {expected_player.mention}")
        return
    
    try:
        user_move = chess.Move.from_uci(الحركة.strip().lower())
        
        if user_move in board.legal_moves:
            board.push(user_move)
            await ctx.send(f"✅ تم تحريك القطعة بواسطة {ctx.author.mention}: **{الحركة}**")
            
            # عرض الرقعة المحدثة بالصور
            await display_board(ctx, board)
            
            # التحقق من حالات انتهاء المباراة
            if board.is_checkmate():
                winner = game["white"] if board.turn == chess.BLACK else game["black"]
                await ctx.send(f"🎉 **كش ملك! انتهت المباراة بفوز البطل {winner.mention}!**")
                del games[channel_id]
            elif board.is_game_over():
                await ctx.send("🤝 **انتهت المباراة بالتعادل! مباراة رائعة من الطرفين.**")
                del games[channel_id]
                
        else:
            await ctx.send("❌ حركة غير قانونية! يرجى التحقق من القواعد والمحاولة مجدداً.")
            
    except ValueError:
        await ctx.send("❌ صيغة الحركة غير صحيحة. استخدم الصيغة القياسية مثل: `e2e4`.")

@bot.command(name="انسحاب")
async def chess_forfeit(ctx):
    """الانسحاب من المباريات الجارية"""
    channel_id = ctx.channel.id
    if channel_id not in games or games[channel_id]["state"] != "playing":
        await ctx.send("❌ لا توجد مباراة قائمة حالياً في هذه القناة لكي تنسحب منها!")
        return
    
    game = games[channel_id]
    player = ctx.author
    
    # التحقق من أن الشخص الذي يطلب الانسحاب هو لاعب فعلي في التحدي
    if player not in game["players"]:
        await ctx.send("❌ أنت لست لاعباً في هذه المباراة لكي تنسحب منها!")
        return
    
    # تحديد الفائز (الطرف الآخر في التحدي)
    winner = game["black"] if player == game["white"] else game["white"]
    
    # إعلان الانسحاب وفوز اللاعب الآخر
    embed = discord.Embed(
        title="🏳️ استسلام وانسحاب من المباراة",
        description=f"أعلن اللاعب {player.mention} استسلامه وانسحابه من المعركة!\n\n🎉 **الفائز في المباراة:** {winner.mention}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    
    # مسح اللعبة من قائمة الألعاب النشطة
    del games[channel_id]

@bot.command(name="انهاء")
async def chess_stop(ctx):
    """إنهاء اللعبة أو إلغاء غرف الانتظار"""
    channel_id = ctx.channel.id
    if channel_id in games:
        game = games[channel_id]
        # التحقق من أن من ينهي اللعبة هو أحد اللاعبين المشاركين أو مشرف السيرفر أو أدمن البوت
        if ctx.author in game["players"] or ctx.author.guild_permissions.manage_messages or is_admin(ctx.author.id, ctx.guild.id):
            del games[channel_id]
            await ctx.send("🛑 تم إيقاف مباراة الشطرنج وغرفة الانتظار بنجاح.")
        else:
            await ctx.send("❌ لا يمكنك إيقاف المباراة إلا إذا كنت أحد اللاعبين المتنافسين أو مشرفاً!")
    else:
        await ctx.send("❌ لا توجد مباراة قائمة حالياً لكي يتم إيقافها.")

# ================== دوال مساعدة ==================

async def display_board(ctx, board):
    """توليد وعرض رقعة الشطرنج الحالية كصورة"""
    channel_id = ctx.channel.id
    game = games.get(channel_id)
    if not game:
        return

    # استخراج حالة القطع الحالية (FEN) لإنتاج رابط الصورة المباشر
    board_fen = board.board_fen()
    image_url = f"https://chessboardimage.com/{board_fen}.png"
    
    # تحديد اللاعب صاحب الدور الحالي والإشارة له
    current_player = game["white"] if board.turn == chess.WHITE else game["black"]
    turn_color = "اللون الأبيض ⚪" if board.turn == chess.WHITE else "اللون الأسود ⚫"
    
    embed = discord.Embed(
        title="♟️ رقعة الشطرنج الحالية",
        description=f"الدور الحالي لـ: {current_player.mention} ({turn_color})\n\n💡 اكتب `.تحرك` للعب (مثال: `.تحرك e2e4`).",
        color=discord.Color.gold()
    )
    embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)

# تشغيل البوت بالتوكن الخاص بك
bot.run("MTUxOTMzMjk0NDAzNDkyNjc0Mw.GIKPw0.6R-_2HW6GS0fm_HZl-ljb0WPpc-Mh3DhUHQ-8w")