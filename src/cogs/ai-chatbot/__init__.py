import discord
from discord.ext import commands
from models import Scrim
from .ai_support import ask_ai, log_unknown_query
from core import Quotient

class ScrimAssistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.support_channel_id = 1394525636097347595
        self.cancel_claim_channel = "<#1392385316219785226>"
        self.waiting_channel = "<#1393108743226396774>"
        self.idp_time_channel = "<#1392100262763696258>"
        self.support_ping = "<@520174525090889731> <@1263356161344671805>"

    async def ai_response(self, message: discord.Message, query: str, scrim: Scrim | None):
        # Pattern-based human-like replies
        query_lower = query.lower()

        if any(q in query_lower for q in ["slot he", "slot hai","slot chahiye", "free slot", "kya slot"]):
            if scrim and scrim.available_slots:
                return f"✅ Currently available slots: {', '.join(map(str, scrim.available_slots))}\n\n📝 idhr jake slot lelo {self.cancel_claim_channel}."
            return f"📌 Slot available nahi hai abhi. Aap {self.cancel_claim_channel} me reminder set kar sakte ho.\n\nAlso check: {self.waiting_channel}"

        if "waiting" in query_lower and any(w in query_lower for w in ["kaise milega", "slot", "waiting format"]):
            return (
                "**__PRO SCRIMS WAITING SLOTS__**  \n"
                "1・ **Join __PRO SCRIMS WAITING VC__ at IDP time. Don’t leave.**  \n"
                "2・ **2 min ke andar room join karna hoga.**  \n"
                "\n⏰ **Free Slot Times:**  \n"
                "12:57pm, 1:57pm, 2:57pm, 3:57pm, 4:57pm,  \n"
                "6:57pm, 7:57pm, 8:57pm, 9:57pm, 10:57pm  \n"
                f"\n🔗 VC Link: https://discord.gg/6qab8vND  \n"
                f"📝 Admin ko message kar lo, agar available hoga to de denge."
            )

        if any(q in query_lower for q in ["cancel", "slot cancel"]):
            return f"Slot cancel karne ke liye yahan jao: {self.cancel_claim_channel}"

        if "how to register" in query_lower or "register kaise" in query_lower:
            return f"Ye mujhe bhi nahi pata 😅 Admin se puchh lo please. {self.support_ping}"

        if "idp" in query_lower and any(q in query_lower for q in ["kab aayega", "kab hai", "kab start"]):
            return f"Mujhe nahi pata bhai, thoda wait karo ya admin se puchh lo. Check: {self.idp_time_channel}\n\n {self.support_ping}"
        
        if all(word.startswith("<@") and word.endswith(">") for word in message.content.split()):
            return
        
        if "how to verify result ss" and any(q in query_lower for q in ["result ss kaha dena hai", "result ss kaise dena hai"]):
            return (
                "Result screenshot dene ke liye, aapko apne match ke result ka screenshot lena hoga. "
                "Phir us screenshot ko yahan upload karo: <#1392100339783831612>.\n\n"
                "Agar koi dikkat ho to {self.support_ping} se puchh lo."
            )

        if "idp" in query_lower and any(q in query_lower for q in ["kab aayega", "kab hai", "kab start"]):
            return f"schedule idhr mil jayega check karlo {self.idp_time_channel}\n\n kuch samaj nai aaya to admin se puchh lo - {self.support_ping}"


        if query_lower.strip() in ["ok", "thanks", "acha", "thik", "hmm", "thank you"]:
            return "Okay! Let me know if you need anything else 😊"

        return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != self.support_channel_id:
            return

        query = message.content
        scrim = await Scrim.filter(guild_id=message.guild.id).first()

        human_reply = await self.ai_response(message, query, scrim)
        if human_reply:
            await message.reply(human_reply)
            return

        # Fallback to AI if no pattern matched
        db_context = f"Available slots: {', '.join(map(str, scrim.available_slots)) if scrim else 'Unknown'}"
        response = await ask_ai(query.lower(), db_context)

        if response.strip() == "[unknown] (Sorry, main sirf slot aur registration se related madad kar sakta hoon.)":
            fallback_msg = (
                "⚠️ Yeh query thoda alag hai aur mujhe pura samajh nahi aaya 😅\n"
                "Agar slot/cancel/waiting/IDP se related hai to clearly batayein,\n"
                f"warna please {self.support_ping} se puchh lo 🙏"
            )
            await message.reply(fallback_msg)
            await log_unknown_query(query, message.author.id)
            return


        await message.reply(response)

async def setup(bot: Quotient):
    await bot.add_cog(ScrimAssistant(bot))
