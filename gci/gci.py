import asyncio
import os
import discord
import time
from .utils import checks
from .utils.dataIO import fileIO
from discord.ext import commands

class GCI:
    """
    Tracks active GCIs on hoggit
    """
    active_time = 60 * 30 #30 minutes.
    warn_time = 60 * 25#25 minutes

    def __init__(self, bot, dataFile):
        self.bot = bot
        self.dataFile = dataFile
        self.data = fileIO(dataFile, "load")
        self.active_gcis = []


    async def start_monitor(self):
        await self.bot.wait_until_ready()
        try:
            for gci in self.active_gcis:
                if gci['start_time'] + active_time > time.time():
                    await self.bot.send_message(gci['user'], "30 minute duration achieved. Sunsetting.")
                    self.sunset(gci)
                elif gci['start_time'] + warn_time > time.time():
                    await self.bot.send_message(gci['user'], "You have been active as GCI for 25 minutes, in 5 minutes you will be automatically sunset. To continue for another 30 minutes, use !gci refresh")
        except:
            log("Unexpected error with the gci monitor: " + sys.exc_info()[0])
        finally:
            await asyncio.sleep(60)
            asyncio.ensure_future(self.start_monitor())


    def clear_role(user,role):
        """Not yet.."""
        role_id = self.data['active_role_id']
        if not role_id:
            return
        self.bot.remove_roles(user, role)

    def sunset(self, user):
        #self.clear_role(user)
        self.active_gcis[:] = [gci for gci in self.active_gcis if gci['user'].id != user.id]

    def sunrise(self, user, freq, remarks):
        gci = {}
        gci['user'] = author
        gci['start_time'] = time.time()
        gci['freq'] = freq
        gci['remarks'] = remarks
        self.active_gcis.append(gci)

    def valid_user(self, user: discord.User):
        return self.data['role_id'] in [r.id for r in user.roles]

    def save_data(self, data):
        fileIO(self.dataFile, 'save', data)

    @commands.group(name="gci", pass_context=True, no_pm=True, invoke_without_command=True)
    def _gci(self, ctx):
        """List active GCIs"""
        if len(self.active_gcis) == 0:
            await self.bot.say("No GCIs currently online.")
            return
        response = "Current GCIs online:\n"
        for gci in self.active_gcis:
            response += "{} ({}) - {}\n".format(
                            gci['user'].name,
                            gci['freq'],
                            gci['remarks'] if gci['remarks'] else "No remarks"
                            )
        await self.bot.say(response)

    @_gci.command(name="role")
    @checks.mod_or_permissions(manage_server=True)
    def _role(self, role: discord.Role):
        self.data['role_id'] = role.id
        self.save_data(self.data)
        await self.bot.say("Set GCI role to: {}".format(role.name))

    @_gci.command(name="active_role")
    @checks.mod_or_permissions(manage_server=True)
    def _active_role(self, role: discord.Role):
        self.data['active_role_id'] = role.id
        self.save_data(self.data)
        await self.bot.say("Set Active GCI role to: {}".format(role.name))

    @_gci.command(name="refresh", pass_context=True)
    async def _refresh(self, ctx):
        found = False
        author = ctx.message.author
        for gci in self.active_gcis:
            if gci['user'].id == author.id:
                found = True
                gci['start_time'] = time.time()
                break
        if found:
            await self.bot.send_message(author, "Refreshed your GCI timer for another 30 minutes")
        else:
            await self.bot.send_message(author, "Doesn't look like you were signed up as GCI yet. Use !gci sunrise <freq>")
        return


    @_gci.command(name="sunset", pass_context=True):
    async def _sunset(self, ctx):
        author = ctx.message.author
        found = False
        for gci in self.active_gcis:
            if gci['user'].id == author.id:
                found = True
                self.sunset(author)
                break
        if found:
            await self.bot.say("Sunsetting.")
        else:
            await self.bot.say("You weren't signed up as a GCI.")


    @_gci.command(name="sunrise", no_pm=True, pass_context=True)
    async def _sunrise(self, ctx, freq: str, *, remarks: str):
        author = ctx.message.author
        if not self.valid_user(author):
            await self.bot.say("You're not allowed to be a GCI. Ask Staff about getting the role")
            return
        self.sunrise(author, freq, remarks)
        await self.bot.say("Added {} as GCI on {} with remarks [{}]".format(author.mention, freq, remarks))


def setup(bot):
    if not os.path.exists('data/gci'):
        log("data/gci dir doesn't exist yet. Creating...")
        os.makedirs("data/gci")

    f = "data/gci/data.json"
    if not fileIO(f, "check"):
        log("Creating empty data.json")
        fileIO(f, "save", {})

    bot.add_cog(GCI(bot, f))
