from bot import config_dict

i = config_dict["CMD_SUFFIX"]


class _BotCommands:
    def __init__(self):
        self.StartCommand: str = "start"
        self.MirrorCommand: list[str] = [f"mirror{i}", f"m{i}"]
        self.YtdlCommand: list[str] = [f"ytdl{i}", f"y{i}"]
        self.LeechCommand: list[str] = [f"leech{i}", f"l{i}"]
        self.YtdlLeechCommand: list[str] = [f"ytdlleech{i}", f"yl{i}"]
        self.CloneCommand: list[str] = [f"clone{i}", f"c{i}"]
        self.CountCommand: str = f"count{i}"
        self.DeleteCommand: str = f"del{i}"
        self.CancelAllCommand: str = f"stopall{i}"
        self.ListCommand: str = f"list{i}"
        self.SearchCommand: str = f"search{i}"
        self.StatusCommand: list[str] = [f"status{i}", "statusall"]
        self.UsersCommand: str = f"users{i}"
        self.AuthorizeCommand: str = f"authorize{i}"
        self.UnAuthorizeCommand: str = f"unauthorize{i}"
        self.AddSudoCommand: str = f"addsudo{i}"
        self.RmSudoCommand: str = f"rmsudo{i}"
        self.PingCommand: str = f"ping{i}"
        self.RestartCommand: list[str] = [f"restart{i}", "restartall"]
        self.StatsCommand: list[str] = [f"stats{i}", "statsall"]
        self.HelpCommand: str = f"help{i}"
        self.LogCommand: str = f"log{i}"
        self.ShellCommand: str = f"shell{i}"
        self.AExecCommand: str = f"aexec{i}"
        self.ExecCommand: str = f"exec{i}"
        self.BotSetCommand: str = f"botsettings{i}"
        self.UserSetCommand: str = f"settings{i}"
        self.MediaInfoCommand: str = f"mediainfo{i}"
        self.BroadcastCommand: list[str] = [f"broadcast{i}", "broadcastall"]


BotCommands = _BotCommands()
