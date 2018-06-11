import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from .utils.chat_formatting import pagify, box
import os
import re

class SameUserError(Exception):
    pass

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
        user = commendation['user.id']
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
        comm['user'] = user.name
        comm['user.id'] = user.id
        comm['text'] = text
        comm['author.id'] = author.id
        comm['author'] = author.name
        return comm

    @commands.group(name="commend", pass_context=True)
    async def commend(self, ctx, user: discord.Member = None, *, text = ""):
        """
        Adds a commendation to the given member, with the provided text as the reason behind it
        """
        author = ctx.message.author
        try:
            commendation = self.commendation(author, user, text)
            print("commendation: {}".format(commendation))
            self.store(ctx, commendation)
            await self.bot.say("Commended {}.".format(user.name))
        except SameUserError:
            await self.bot.say("You can't give yourself a commendation you nitwit")

    @commands.group(name = "commendations", pass_context=True)
    async def commendations(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commendations.command(name = "list", pass_context=True)
    async def list(self, ctx, user: discord.Member):
        """
        Provides the number of commendations the given user has received
        """
        server_id = ctx.message.server.id
        if server_id not in self.c_commendations:
            await self.bot.say("No commendations found for {}".format(user.name))
            return
        server_comms = self.c_commendations[server_id]
        if user.id not in server_comms:
            await self.bot.say("No commendations found for {}".format(user.name))
            return
        user_comms = server_comms[user.id]
        await self.bot.say("{} has {} commendations".format(user.name, len(user_comms)))

    @commendations.command(name = "leaderboard", pass_context = True)
    async def leaderboard(self, ctx):
        """
        Returns a leaderboard of the top 10 commendees on your server.
        """
        server_id = ctx.message.server.id
        if server_id not in self.c_commendations:
            await self.bot.say("No commendations on this server yet")
            return
        commended_users = self.topCommendees(self.c_commendations[server_id], 10)
        print("Commended users: {}".format(commended_users))
        commended_user_ranks = []
        leaders=[]
        rank=1
        for user_id, count in commended_users:
            user = ctx.message.server.get_member(user_id).name
            leaders.append("#{} {}: {}".format(rank, user, count))
            rank += 1
        message = """
        Top 10 Commendees
        ```{}```
        """.format("\n".join(leaders))
        await self.bot.say(message)

    def topCommendees(self, commendation_dict, amount):
        dic_to_list = lambda dic: [(k, len(v)) for (k, v) in dic.items()]
        commendation_counts = dic_to_list(commendation_dict)
        print("commendation counts: {}".format(commendation_counts))
        commendation_counts = sorted(commendation_counts, key=lambda x: x[1], reverse=True)
        print("sorted counts: {}".format(commendation_counts))
        return commendation_counts[:amount]

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
