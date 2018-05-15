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

    def store(self, ctx, commendation):
        server = ctx.message.server
        user = commendation['user']
        if server.id not in self.c_commendations:
            self.c_commendations[server.id] = {}
        server_commendations = self.c_commendations[server.id]
        if user not in server_commendations:
            server_commendations[user] = []
        user_commendations = server_commendations[user]
        user_commendations.append(commendation)
        server_commendations[user] = user_commendations
        self.c_commendations[server.id] = server_commendations
        dataIO.save_json(self.file_path, self.c_commendations)

    def commendation(self, author, user, text):
        if author.id == user.id:
            raise SameUserError()
        comm = {}
        comm['user'] = user.id
        comm['text'] = text
        comm['author'] = author.id
        return comm

    @commands.group(name="commend", pass_context=True)
    async def commend(self, ctx, user: discord.Member, text):
        author = ctx.message.author
        try:
            commendation = self.commendation(author, user, text)
            print("commendation: {}".format(commendation))
            self.store(ctx, commendation)
            await self.bot.say("Commended {}.".format(user.name))
        except SameUserError:
            await self.bot.say("You can't give yourself a commendation you nitwit")


class SameUserError(Exception):
    pass

class Commendation:

    def __init__(self, author, user, text):
        if author.id == user.id:
            raise SameUserError()

        self.author = author.id
        self.user = user.id
        self.text = text

def check_folders():
    if not os.path.exists("data/commendations"):
        print("Creating data/commendations folder...")
        os.makedirs("data/commendations")


def check_files():
    f = "data/commendations/commendations.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commendations.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Commendations(bot))
