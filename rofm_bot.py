'''Various component classes for /u/roll_one_for_me, as well as the
primary RollOneForMe class.'''

# Todo: set a maximum recursion depth.

# Todo: a table header beginning with ! between the dice and the
# header should not be included in the "defaults" but only accessible
# by request or link.
import dice # ??
from dnd_tables import TableSource
from rofm_classes import Request, RollOneStats
from rofm_sentinel import Sentinel
from reddit_bot import RedditBot, MailHandling
from rofm_request_handling import RequestProcessing


class RollOneForMe(Sentinel, RequestProcessing, MailHandling):
    '''/u/roll_one_for_me bot.'''
    def __init__(self, load_stats_filename=None):
        super(RollOneForMe, self).__init__()
        print("rofm make stats...")
        self.stats = RollOneStats(load_stats_filename)
        print("made")
        
    def __repr__(self):
        return "<RollOneForMe>"

    def act(self):
        self.act_as_sentinel()
        self.answer_mail()

    def answer_mail(self):
        new_mail = self.fetch_new_mail()
        for notification in new_mail:
            # Mark as read within this loop, upon reply.
            pass
        
