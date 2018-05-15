import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from .utils.chat_formatting import pagify, box
import os
import re

class Commendations:
    """Commendations

    Allows users to commend eachother, and keeps a running tally of each user's commendations
    """

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/commendations/commendations.json"
        self.c_commendations = dataIO.load_json(self.file_path)


    @commands.group(pass_context=True)
    async def commend(self, ctx, user: discord.Member, text):
        self.bot.say("Got ctx [{}], user [{}], text [{}]".format(ctx, user, text))




def check_folders():
    if not os.path.exists("data/commendations"):
        print("Creating data/commendations folder...")
        os.makedirs("data/commendations")


def check_files():
    f = "data/customcom/commendations.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commendations.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Commendations(bot))
