#!/usr/bin/env python3
from bot import CMD_SUFFIX

class _BotCommands:
    def __init__(self):
        self.StartCommand = 'start'
        self.MirrorCommand = [f'mirror{CMD_SUFFIX}', f'm{CMD_SUFFIX}']
        self.QbMirrorCommand = [f'qbmirror{CMD_SUFFIX}', f'qm{CMD_SUFFIX}']
        self.YtdlCommand = [f'ytdl{CMD_SUFFIX}', f'y{CMD_SUFFIX}']
        self.LeechCommand = [f'leech{CMD_SUFFIX}', f'l{CMD_SUFFIX}']
        self.QbLeechCommand = [f'qbleech{CMD_SUFFIX}', f'ql{CMD_SUFFIX}']
        self.YtdlLeechCommand = [f'ytdlleech{CMD_SUFFIX}', f'yl{CMD_SUFFIX}']
        self.CloneCommand = f'clone{CMD_SUFFIX}'
        self.CountCommand = f'count{CMD_SUFFIX}'
        self.DeleteCommand = f'del{CMD_SUFFIX}'
        self.CancelMirror = f'cancel{CMD_SUFFIX}'
        self.CancelAllCommand = [f'cancelall{CMD_SUFFIX}', 'cancellallbot']
        self.ListCommand = f'list{CMD_SUFFIX}'
        self.SearchCommand = f'search{CMD_SUFFIX}'
        self.StatusCommand = [f'status{CMD_SUFFIX}', 'statusall']
        self.UsersCommand = f'users{CMD_SUFFIX}'
        self.AuthorizeCommand = f'authorize{CMD_SUFFIX}'
        self.UnAuthorizeCommand = f'unauthorize{CMD_SUFFIX}'
        self.AddSudoCommand = f'addsudo{CMD_SUFFIX}'
        self.RmSudoCommand = f'rmsudo{CMD_SUFFIX}'
        self.PingCommand = [f'ping{CMD_SUFFIX}', 'pingall']
        self.RestartCommand = [f'restart{CMD_SUFFIX}', 'restartall']
        self.StatsCommand = f'stats{CMD_SUFFIX}'
        self.HelpCommand = f'help{CMD_SUFFIX}'
        self.LogCommand = f'log{CMD_SUFFIX}'
        self.ShellCommand = f'shell{CMD_SUFFIX}'
        self.EvalCommand = f'eval{CMD_SUFFIX}'
        self.ExecCommand = f'exec{CMD_SUFFIX}'
        self.ClearLocalsCommand = f'clearlocals{CMD_SUFFIX}'
        self.BotSetCommand = f'bsetting{CMD_SUFFIX}'
        self.UserSetCommand = [f'usetting{CMD_SUFFIX}', f'us{CMD_SUFFIX}']
        self.BtSelectCommand = f'btsel{CMD_SUFFIX}'
        self.SpeedCommand = f'speedtest{CMD_SUFFIX}'
        self.RssCommand = f'rss{CMD_SUFFIX}'
        self.AddImageCommand = f'addimg{CMD_SUFFIX}'
        self.ImagesCommand = f'images{CMD_SUFFIX}'
        self.MediaInfoCommand = f'mediainfo{CMD_SUFFIX}'
        self.BroadcastCommand = [f'broadcast{CMD_SUFFIX}', 'broadcastall']

BotCommands = _BotCommands()