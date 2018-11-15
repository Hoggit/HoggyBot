import asyncio
import os
import discord
import time
import sys
from .utils import checks
from .utils.dataIO import fileIO
from discord.ext import commands

class GCI:
    """
    Tracks active GCIs on hoggit
    """

    def __init__(self, bot, dataFile):
        self.bot = bot
        self.dataFile = dataFile
        self.data = fileIO(dataFile, "load")
        self.active_gcis = []
        self.allow_role = None
        self.active_role = None
        self.update_roles()
        self.killSwitch = False
        self.active_time = 60 * 30 #30 minutes.
        self.warn_time = 60 * 25#25 minutes
        self.reminded = []
        asyncio.ensure_future(self.start_monitor())


    def __unload(self):
        log("Setting killswitch to True!")
        self.killSwitch = True


    def update_roles(self):
        for server in self.bot.servers:
            if 'active_role_id' in self.data:
                active_role_id = self.data['active_role_id']
                role = next(r for r in server.roles if r.id == active_role_id)
                if role:
                    self.active_role = role
                else:
                    self.active_role = None
            else:
                self.active_role = None

            if 'role_id' in self.data:
                allow_role_id = self.data['role_id']
                role = next(r for r in server.roles if r.id == allow_role_id)
                if role:
                    self.allow_role = role
                else:
                    self.allow_role = None
            else:
                self.allow_role = None

            if self.allow_role is not None or self.active_role is not None:
                return


    async def start_monitor(self):
        if self.killSwitch:
            log("Killswitch hit. Not re-polling")
            return
        await self.bot.wait_until_ready()
        try:
            for gci in self.active_gcis:
                if gci['start_time'] + self.active_time < time.time():
                    await self.bot.send_message(gci['user'], "30 minute duration achieved. Signing off.")
                    await self.midnight(gci['user'])
                elif gci['start_time'] + self.warn_time < time.time():
                    if gci['user'].id not in self.reminded:
                        await self.bot.send_message(gci['user'], "You have been active as GCI for 25 minutes, in 5 minutes you will be automatically signed-off. To continue for another 30 minutes, use !gci refresh")
                        self.reminded.append(gci['user'].id)
        except:
            log("Unexpected error with the gci monitor: " + sys.exc_info()[0])
        finally:
            await asyncio.sleep(60)
            asyncio.ensure_future(self.start_monitor())


    async def clear_active_role(self,user):
        if self.active_role:
            log("Active role is available. Unset {} role on {}".format(user.name, self.active_role))
            await self.bot.remove_roles(user, self.active_role)
        else:
            log("Active role is not set. Skipping")

    async def add_active_role(self,user):
        if self.active_role:
            log("Active role is available. Setting {} role on {}".format(user.name, self.active_role))
            await self.bot.add_roles(user, self.active_role)
        else:
            log("Active role is not set. Skipping")

    def remove_reminded_status(self, user):
        self.reminded[:] = [user_id for user_id in self.reminded if user_id != user.id]

    async def midnight(self, user):
        await self.clear_active_role(user)
        self.remove_reminded_status(user)
        self.active_gcis[:] = [gci for gci in self.active_gcis if gci['user'].id != user.id]

    async def sunrise(self, user, freq, remarks):
        log("Adding {} as GCI".format(user.name))
        gci = {}
        gci['user'] = user
        gci['start_time'] = time.time()
        gci['freq'] = freq
        gci['remarks'] = remarks
        self.active_gcis.append(gci)
        await self.add_active_role(user)
        log("Added Active Role to {}".format(user.name))

    def valid_user(self, user: discord.User):
        return self.data['role_id'] in [r.id for r in user.roles]

    def save_data(self, data):
        fileIO(self.dataFile, 'save', data)

    @commands.group(name="gci", pass_context=True, no_pm=True, invoke_without_command=True)
    async def _gci(self, ctx):
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
    async def _role(self, role: discord.Role):
        """Defines the role a user has to be in before being allowed to sunrise"""
        self.data['role_id'] = role.id
        self.save_data(self.data)
        self.update_roles()
        await self.bot.say("Set GCI role to: {}".format(role.name))

    @_gci.command(name="active_role")
    @checks.mod_or_permissions(manage_server=True)
    async def _active_role(self, role: discord.Role):
        """Defines the role that active GCIs get granted. Staff Only"""
        self.data['active_role_id'] = role.id
        self.save_data(self.data)
        self.update_roles()
        await self.bot.say("Set Active GCI role to: {}".format(role.name))

    @_gci.command(name="refresh", pass_context=True)
    async def _refresh(self, ctx):
        """Refreshes your timer back to 30 minutes"""
        author = ctx.message.author
        for gci in self.active_gcis:
            if gci['user'].id == author.id:
                self.remove_reminded_status(author)
                gci['start_time'] = time.time()
                await self.bot.send_message(author, "Refreshed your GCI timer for another 30 minutes")
                return
        await self.bot.send_message(author, "Doesn't look like you were signed up as GCI yet. Use !gci sunrise <freq>")


    @_gci.command(name="midnight", pass_context=True)
    async def _midnight(self, ctx):
        """Removes you from the list of active GCIs."""
        author = ctx.message.author
        for gci in self.active_gcis:
            if gci['user'].id == author.id:
                await self.midnight(author)
                await self.bot.say("{}, Signing off.".format(author.name))
                return
        await self.bot.say("You weren't signed up as a GCI.")


    @_gci.command(name="sunrise", no_pm=True, pass_context=True)
    async def _sunrise(self, ctx, freq: str, *, remarks: str):
        """Adds you to the list of Active GCIs
        The following must be provided:
        freq - The frequency you can be contacted at on SRS.
        remarks - Your callsign + anything related to your GCI slot (CAP flights only, for example)
        """
        author = ctx.message.author
        if not self.valid_user(author):
            await self.bot.say("You're not allowed to be a GCI. Ask Staff about getting the role")
            return
        await self.sunrise(author, freq, remarks)
        await self.bot.say("Added {} as GCI on {} with remarks [{}]".format(author.mention, freq, remarks))


def setup(bot):
    if not os.path.exists('data/gci'):
        print("data/gci dir doesn't exist yet. Creating...")
        os.makedirs("data/gci")

    f = "data/gci/data.json"
    if not fileIO(f, "check"):
        print("Creating empty data.json")
        fileIO(f, "save", {})

    bot.add_cog(GCI(bot, f))

def log(s):
    print("[GCI]: {}".format(s))
