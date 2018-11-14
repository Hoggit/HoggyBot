import discord
from discord.ext import commands
from .utils.dataIO import dataIO
import os

class Standup:
    """See what people are working on today"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/standup/standup.json"

    def get_standups(self):
        return dataIO.load_json(self.file_path)

    def write_standups(self, standup):
        dataIO.save_json(self.file_path, standup)

    @commands.command(pass_context=True)
    async def standup(self, ctx, *, text=None):
        output = ""
        standups = self.get_standups()
        if text is None:
            standups.setdefault(ctx.message.channel.name, {})
            if standups[ctx.message.channel.name] == {}:
                output = "Apparently no one is working on anything.  Type ```!standup <What you're working on>``` to let people know what you're up to"
            else:
                for user,task in standups[ctx.message.channel.name].items():
                    output += "{0} is working on: {1}\n".format(user, task)
        else:
            standups.setdefault(ctx.message.channel.name, {})
            standups[ctx.message.channel.name][ctx.message.author.name] = text
            self.write_standups(standups)
            output = "{0} is working on {1}".format(ctx.message.author.name, text)
        await self.bot.say(output)

def check_folders():
    if not os.path.exists("data/standup"):
        print("Creating data/standup folder...")
        os.makedirs("data/standup")

def check_file():
    f = "data/standup/standup.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty standup.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_file()
    bot.add_cog(Standup(bot))
