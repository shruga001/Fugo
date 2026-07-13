import discord
from discord.ext import commands
from discord import app_commands
import json, os
from fns import *

"""
This file contains the setup process for a Discord guild, including channel and role configuration.
- in previous versions, the setup did offer a dropdown menu for channel selection , but due to uncertainty about the server sizing and certain discord limits , we decided to use a manual input method for channel IDs.
- The setup is initiated by the `/setup` command, which checks permissions and initializes the configuration.
- The setup includes steps for configuring channels, roles, and guild owner/co-owner settings.
- It uses Discord's UI components like buttons and modals to interact with the user.
- The setup process is designed to be flexible and user-friendly, guiding the user through each step.
- The setup includes a warning about overwriting previous configurations in case any exists.
- The user is guided through selecting channels for various purposes (TND, UNO, critical updates, etc.).
- Staff and bot manager roles can be added during the setup.
- The final configuration is previewed before saving.
- The setup process ensures that all necessary channels and roles are configured for the guild to function properly.

The purpose of this file is to provide a structured and interactive way for server administrators to set up their guild's configuration, ensuring that all necessary components are in place for the bot to operate effectively.

This also helps us at the backend server for managing guilds, as it creates a standardized configuration file for each guild, with seperate directories for polls, embeds, and market data.
allowing us to easily manage and access guild-specific data in case of any issues or updates.
"""
class ChannelInput(discord.ui.View):
    """
    instead of having seperate views for each channel input, we use a single view with buttons to handle channel selection.
    This allows us to reuse the same logic for different channel types, reducing code duplication and making it easier to maintain.
    The `check_key` dictionary maps each channel type to the next one in the setup process.
    The `descs` dictionary provides descriptions for each channel type, which can be used to guide the user during setup.
    """
    def __init__(self,config,keys):
        super().__init__(timeout=None)
        self.config = config
        self.keys = keys
        self.check_key = {"TND_channel":"UNO_channel","UNO_channel":"critical_update_channel","critical_update_channel":"monster_channel","monster_channel":"message_channels","message_channels":"allowed_channels"}
        self.descs = {"TND_channel":"Setup a channel for TND(truth and dare)","UNO_channel":"Setup a channel for game of UNO","critical_update_channel":"Setup a private channel for critical bot updates","message_channels":"Setup up your server general chat channel","allowed_channels":"Setup channels where users can run commands","monster_channel":"Setup a channel for monster drops"}
    @discord.ui.button(label="Enter channel id",style=discord.ButtonStyle.blurple)
    async def take_input(self,i:discord.Interaction,_):
        modal = discord.ui.Modal(title="Enter Channel ID")
        modal.add_item(discord.ui.TextInput(label="Channel ID", placeholder="123456789012345678"))
        async def modal_cb(modal_i:discord.Interaction): # callback for handling the channel ID input from the modal
            cid = int(modal.children[0].value)
            channel = i.guild.get_channel(cid)
            if channel and isinstance(channel, discord.TextChannel):
                if self.keys in ["monster_channel","critical_update_channel"]:
                    self.config[str(self.keys)] = cid
                else:
                    self.config[str(self.keys)] = [cid]
                await modal_i.response.send_message(f"Channel selected: {channel.mention}")
                if self.keys!="allowed_channels":
                    self.next_key = self.check_key[self.keys]
                    await modal_i.followup.send(f"{self.descs[self.next_key]}",view=ChannelInput(self.config,self.next_key))
                else:
                    await modal_i.followup.send("Time to setup your staff",view=StaffSetup(self.config))
            else:
                await modal_i.response.send_message("Invalid channel ID.", ephemeral=True)
        modal.on_submit = modal_cb
        await i.response.send_modal(modal)
    @discord.ui.button(label="How to get channel id", style=discord.ButtonStyle.blurple)
    async def how_to_get_id(self, i:discord.Interaction, _):
        await i.response.send_message(
            "To get a channel ID, enable Developer Mode in Discord settings:\n"
            "1. Go to User Settings > Advanced.\n"
            "2. Enable Developer Mode.\n"
            "3. Right-click the channel and select 'Copy ID'.\n"
            "Paste the ID here.",
            ephemeral=False
        )
def get_category_options(guild):
    return [
        discord.SelectOption(label=category.name, value=str(category.id))
        for category in guild.categories if category.text_channels
    ]

def get_text_channel_options_for_category(category):
    channels = category.text_channels
    if len(channels) > 25:
        return None
    return [
        discord.SelectOption(label=ch.name, value=str(ch.id))for ch in channels
    ]

def get_role_options(channel:discord.TextChannel):
    # Get all roles in the channel that are not bots and has access to the channel
    return [discord.SelectOption(label=role.name, value=str(role.id))
            for role in channel.guild.roles if not role.is_bot_managed() and role.permissions.read_messages and role.permissions.send_messages]
def get_member_options(channel):
    return [discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in channel.members if not member.bot]

# ====== Setup classes ======

class WarningView(discord.ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config

    @discord.ui.button(label="I Understand", style=discord.ButtonStyle.danger)
    async def understand(self, interaction, button):
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "Before continuing, ensure staff & bot managers can see this channel.",
            view=OwnerDisplay(self.config))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.send_message("❌ Setup cancelled.", ephemeral=False)

class OwnerDisplay(discord.ui.View):
    def __init__(self, config): 
        super().__init__(timeout=None); 
        self.config = config

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_btn(self, interaction, button):
        button.disabled = True
        self.config["owner"] = interaction.guild.owner_id
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"👤 Guild Owner: {interaction.guild.owner.mention}\nNow add co-owners:",
            view=CoOwnerSetup(self.config))

class CoOwnerSetup(discord.ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config

    @discord.ui.button(label="Add Co-Owner", style=discord.ButtonStyle.primary)
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(view=self)
        options = get_member_options(interaction.channel)
        select = discord.ui.Select(placeholder="Select co-owner", options=options)
        async def callback(i: discord.Interaction):
            uid = int(select.values[0])
            if uid not in self.config["co_owner"]:
                self.config["co_owner"].append(uid)
            await i.response.edit_message(content=f"✅ <@{uid}> added. Press Continue on previous message.", view=self)

        select.callback = callback
        view = discord.ui.View(); view.add_item(select)
        await interaction.followup.send("Pick a co-owner:", view=view)
    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_btn(self, interaction, button):
        try:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("🎯 Setup TND Channel:", view=ChannelInput(self.config,"TND_channel"))
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {type(e).__name__}: {e}", ephemeral=True)   


# =========== The rest of your code unchanged =============

class StaffSetup(discord.ui.View):
    def __init__(self, config): 
        super().__init__(timeout=None); self.config=config

    @discord.ui.button(label="Add Staff Role", style=discord.ButtonStyle.primary)
    async def add_role(self, i,b):
            b.disabled=True
            try:
                await i.response.edit_message(view=self)
                select=discord.ui.Select(placeholder="Staff role", options=get_role_options(i.channel))
                async def callback(ii):
                    rid=int(select.values[0]); self.config["staff_roles"].append(rid)
                    await ii.response.send_message(f"✅ <@&{rid}> added. Press Continue.", ephemeral=False)
                select.callback=callback; 
                v=discord.ui.View(); 
                v.add_item(select)
                await i.followup.send("Choose staff role:", view=v)
            except Exception as e:
                b.disabled=False
                await i.response.edit_message(view=self)
                await i.followup.send(f"❌ An error occurred: {type(e).__name__}: {e}", ephemeral=True)
    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_btn(self, i,b): 
        b.disabled=True 
        try:
            await i.response.edit_message(view=self)
            await i.followup.send("🧰 Setup Bot Managers:", view=BotManagerSetup(self.config))
        except Exception as e:
            await i.followup.send(f"❌ An error occurred: {type(e).__name__}: {e}", ephemeral=True)
class BotManagerSetup(discord.ui.View):
    def __init__(self, config):
         super().__init__(timeout = None); 
         self.config = config
    @discord.ui.button(label="Add Manager Role", style=discord.ButtonStyle.primary)
    async def add_role(self, i,b):
        b.disabled=True
        await i.response.edit_message(view=self)
        select=discord.ui.Select(placeholder="Manager role", options=get_role_options(i.channel))
        async def callback(ii):
            rid=int(select.values[0]); self.config["bot_manager_role"].append(rid)
            await ii.response.send_message(f"✅ <@&{rid}> added. Press Continue.", ephemeral=False)
        select.callback=callback; v=discord.ui.View(); v.add_item(select)
        await i.followup.send("Choose manager role:", view=v)

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_btn(self, i,b):
        try:
            b.disabled=True
            await i.response.edit_message(view=self)
            await i.followup.send("Time to preview your server config", view=preview_config(self.config))   
        except Exception as e:
            await i.followup.send(f"❌ An error occurred: {type(e).__name__}: {e}", ephemeral=True)
# The FinalPreview view is identical to your original
# ... followed by your same FinalPreview and Setup COG classes (unchanged)
class preview_config(discord.ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config

    @discord.ui.button(label="Preview Config", style=discord.ButtonStyle.primary)
    async def preview(self, i, b):
        b.disabled = True
        await i.response.edit_message(view=self)
        await prev_config(i, self.config)

    @discord.ui.button(label="Restart Setup", style=discord.ButtonStyle.danger)
    async def restart(self, i, b):
        await i.response.send_message("🔁 Restarting...", view=OwnerDisplay(self.config))
async def prev_config(i, config):
    e=discord.Embed(title="Guild Config Preview", color=discord.Color.green())
    e.add_field(name="Notes", value="Preview of guild configuration. Check carefully before saving.", inline=False)
    for key,val in config.items():
        e.add_field(name=key, value=str(val), inline=False)
    await i.followup.send(embed=e, view=FinalPreview(config))

class FinalPreview(discord.ui.View):
    def __init__(self, config): 
        super().__init__(timeout=None); self.config=config

    @discord.ui.button(label="Save & Finish", style=discord.ButtonStyle.success)
    async def save(self,i,b):
        self.config['setup']=True
        gid=i.guild.id; 
        os.makedirs(f"guilds_data/{gid}", exist_ok=True)
        os.makedirs(f"guilds_data/{gid}/embeds", exist_ok=True)
        os.makedirs(f"guilds_data/{gid}/polls", exist_ok=True)
        polls = glob_fns().load_json("guilds_data/guild_polls.json")
        glob_fns().save_json(polls, f"guilds_data/{gid}/polls/0.json")
        embeds = glob_fns().load_json("guilds_data/guild_embeds.json")
        glob_fns().save_json(embeds, f"guilds_data/{gid}/embeds/0.json")
        sub_log = glob_fns().load_json("guilds_data/guild_sub_log.json")
        glob_fns().save_json(sub_log, f"guilds_data/{gid}/sub_log.json")
        market = glob_fns().load_json("guilds_data/guild_market.json")
        glob_fns().save_json(market, f"guilds_data/{gid}/market.json")
        with open(f"guilds_data/{gid}/lb.json", "w") as f:
            json.dump({}, f, indent=4)  
        with open(f"guilds_data/{gid}/msg.json", "w") as f:
            json.dump({}, f, indent=4)  
        with open(f"guilds_data/{gid}/config.json","w") as f:
            json.dump(self.config,f,indent=4)
        await i.response.send_message("✅ Setup complete & saved.", ephemeral=False)

    @discord.ui.button(label="Restart Setup", style=discord.ButtonStyle.danger)
    async def restart(self,i,b):
        await i.response.send_message("🔁 Restarting...", view=OwnerDisplay(self.config))

class Setup(commands.Cog):
    def __init__(self, bot): 
        self.bot=bot
    @app_commands.command(name="setup", description="Start guild setup")
    async def setup(self,i:discord.Interaction):
        await i.response.defer(ephemeral=False)
        try:
            if not os.path.exists("guilds_data/guild_format.json"):
                await i.followup.send("❌ Guild format file not found. Please contact the bot owner.", ephemeral=True)
                return
            if not i.guild.owner_id == i.user.id and not i.user.guild_permissions.administrator:
                if not i.user.id == 1208682967225081916:
                    await i.followup.send("❌ You do not have permission to run this command.", ephemeral=False)
                    return
                else:
                    await i.followup.send("SuperUser detected on owner/admin only, proceeding.", ephemeral=False)
            with open("guilds_data/guild_format.json") as f:
                config=json.load(f); config['owner']=i.guild.owner_id
            await i.followup.send("⚠️ This will overwrite previous setup and delete all existing data.", view=WarningView(config))
        except Exception as e:
            await i.followup.send(f"❌ An error occurred: {type(e).__name__}: {e}", ephemeral=True)
            return
    @app_commands.command(name="add_item", description="Add an item to the guild's market")
    async def add_item(self, i: discord.Interaction,item_name: str, item_price: int, item_desc: str,role: discord.Role):
        market_path = f"guilds_data/{i.guild.id}/market.json"
        if not os.path.exists(market_path):
            await i.response.send_message("❌ Market data not found. Please run setup first.", ephemeral=True)
            return
        with open(market_path, "r") as f:
            market_data = json.load(f)
        market_data.update({
            item_name: {
                "price": item_price,
                "description": item_desc,
                "role_id": role.id
            }
        })
        glob_fns().save_json(market_data, market_path)
        await i.response.send_message(f"✅ Item '{item_name}' added to the market for {item_price} coins.", ephemeral=False)
    # @app_commands.command(name="Add rank",description="Add a new rank in levelling system")
    # async def add_rank(self,i:discord.Interaction,Level:int,rank_role:discord.Role):
    #     if Level>100:
    #         i.response.send_message("Ranks can only be added upto level 100 as of now")
    #         return
    #     rank_file = f"guilds_data/{i.guild_id}/guild_ranks.json"
    #     if not os.path.exists(rank_file):
    #         await i.response.send_message("❌ Ranks data file not found. Please run setup first.", ephemeral=True)
    #         return
    #     with open(rank_file, "r") as f:
    #         market_data = json.load(f)
    #     market_data.update({str(Level):rank_role.id})
    #     glob_fns().save_json(market_data, rank_file)
    #     await i.response.send_message(f"✅ Rank '{rank_role.mention}' added to the Ranks, run p!ranks for all ranks added in server", ephemeral=False)
async def setup(bot): await bot.add_cog(Setup(bot)) 
