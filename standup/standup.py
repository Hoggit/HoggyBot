import discord
from discord.ext import commands

class Standup:
    """See what people are working on today"""
    whos_doin_wat = {}

    def __init__(self, bot):
        self.bot = bot


    @commands.command(pass_context=True)
    async def standup(self, ctx, *, text=None):
        output = ""
        if text is None:
            Standup.whos_doin_wat.setdefault(ctx.message.channel, {})
            if Standup.whos_doin_wat[ctx.message.channel] == {}:
                output = "Apparently no one is working on anything.  Type ```!standup <What you're working on>``` to let people know what you're up to"
            else:
                for user,task in Standup.whos_doin_wat[ctx.message.channel].items():
                    output += "{0} is working on: {1}\n".format(user, task)
        else:
            Standup.whos_doin_wat.setdefault(ctx.message.channel, {})
            Standup.whos_doin_wat[ctx.message.channel][ctx.message.author.name] = text
            output = "{0} is working on {1}".format(ctx.message.author.name, text)
        await self.bot.say(output)



def setup(bot):
    bot.add_cog(Standup(bot))
