'''Various component classes for /u/roll_one_for_me, as well as the
primary RollOneForMe class.'''

# Todo: set a maximum recursion depth.

# Todo: a table header beginning with ! between the dice and the
# header should not be included in the "defaults" but only accessible
# by request or link.
import logging
import time
import praw
import pickle
import os
import re
from enum import Enum
from collections import deque

import dice # ??
from dnd_tables import TableSource
from rofm_classes import Request, RollOneStats


####################
## This page: Basic Reddit access and mail fetching
class RedditBot:
    '''Base for Reddit bot components.  Handles login, provides reddit
handle at self.r.
    '''
    def __init__(self, sign_in=True, **kwargs):
        self.r = None
        super(RedditBot, self).__init__()
        if sign_in:
            self.sign_in(**kwargs)

    def sign_in(self, sign_in_attempts=5, sleep_on_failure=30):
        '''Signs into Reddit, attempting $sign_in_attempts attempts before
returning an error.
        '''
        for i in range(sign_in_attempts):
            try:
                logging.info("Attempting to sign in...")
                r = self._attempt_sign_in()
                logging.info("Signed in.")
                return r
            except Exception as e:
                #requests.exceptions.ConnectionError
                #praw.objects.ClientException
                print("Got type", type(e))
                print(e)
                logging.info("Sign in failed.  Sleeping...")
                time.sleep(sleep_on_failure)
        logging.critical("Could not sign in after {} attempts.  Crashing out.")
        raise RuntimeError("Could not sign in.")

    def _attempt_sign_in(self):
        '''Attempt to sign into Reddit.  This function assumes a properly
OAuth-configured praw.ini file.
        '''
        r = praw.Reddit(
            user_agent=(
                'Generate an outcome for random tables, under the name'
                ' /u/roll_one_for_me.'
                ' Written and maintained by /u/PurelyApplied'),
            site_name="roll_one")
        r.refresh_access_information()
        self.r = r


class MailHandling(RedditBot):
    '''Mail and mention handling wrapper.'''
    def __init__(self):
        super(MailHandler, self).__init__()

    def __repr__(self):
        return "<MailHandler>"

    def fetch_new_mail(self, unset=False, **kwargs) -> list:
        '''Fetches any mail currently set as unread.  Does not unset
notification by default.  kwargs passed to praw's get_unread'''
        return list(self.r.get_unread(unset_has_mail=unset, **kwargs))

    def fetch_inbox(self, **kwargs) -> list:
        '''Fetches all mail in inbox.  kwargs passed to praw's get-inbox.
        Does not unset notification, overwriting kwargs if necessary.
        (Use fetch_new_mail instead.)

        '''
        # Fetches all inbox messages and mentions
        kwargs['unset_has_mail'] = False
        return list(self.r.get_inbox(**kwargs))

    def fetch_mentions(self, **kwargs) -> list:
        '''Fetches user mentions. kwargs passed to praw's get_mentions.
        Does not unset notification, overwriting kwargs if necessary.
        (Use fetch_new_mail instead.)

        '''
        kwargs['unset_has_mail'] = False
        return list(self.r.get_mentions(**kwargs))



####################
## This page: Table and Request processing

class TableProcessing(RedditBot):
    def __init__(self):
        super(TableProcessing, self).__init__()

    def get_table_sources(self, request,
                          include_provided = True,
                          get_OP = True,
                          get_top_level = True,
                          get_links = True):
        body = root_ref.body
        table_sources = []
        logging.debug("Generating table sources...")
        if include_provided:
            logging.debug("Converting mail itself...")
            table_sources += [TableSource(body)]
        if get_OP and isinstance(root_ref, praw.objects.Comment):
            logging.debug("Fetching OP...")
            op_ref = self.r.get_submission(
                submission_id=root_ref.submission.id)
            logging.debug("Converting OP to TableSource...")
            table_sources += [TableSource(op_ref.selftext)]
        if get_top_level and isinstance(root_ref, praw.objects.Comment):
            logging.debug("Converting top-level comments to TableSource...")
            table_sources += [TableSource(c.body) for c in op_ref.comments]
        if get_links and isinstance(root_ref, praw.objects.Comment):
            logging.debug("Searching for links...")
            link_texts = re.findall(r"\[.*?\]\(.*?\)", body)
            link_urls = [re.search(r"\[.*.\]\((.*)\)", l).group(1)
                         for l in link_texts]
            logging.debug("Fetching submissions from urls...")
            link_refs = [self.r.get_submission(url) for url in link_urls]
            logging.debug("Converting found links to TableSource...")
            table_sources += [TableSource(l.selftext
                                          if hasattr(l, 'selftext')
                                          else (l.body
                                                if hasattr(l, 'body')
                                                else '')) for l in link_refs]
        logging.debug("Removing nil TableSources")
        return [t for t in table_sources if t]

    

COMMANDS = Enum('request',
                [
                    # These are general categoricals; requires no args
                    'roll_requesting',
                    'roll_op',
                    'roll_top_level',
                    'roll_link',
                    'provide_organizational',
                    # These will require specific arguments
                    'roll_dice', # Takes die notation as arg
                    'roll_table_with_tag', # Takes tag as arg
                ])



class RequestProcessing(TableProcessing):
    def __init__(self):
        super(RequestProcessing, self).__init__()
        # Queue elements will be of the above enum, possibly paired
        # with args:  (cmd, args)
        self.queue = deque()

    def _default_queue(self):
        '''Produces the default repsonse queue: request, OP, top level'''
        # TODO: add self?
        self.queue = deque([COMMANDS.roll_top_level,
                            COMMANDS.roll_op,
                            COMMANDS.roll_requesting])

    def _build_queue_from_tags(self, explicit_command_tags, link_tags):
        pass

    def build_process_queue(self, request):
        explicit_command_tags = re.findall(r"\[\[.*?\]\]", request.text)
        link_tags = re.findall(r"\[[^\[]*?\]\s*\(.*?\)", request.text)
        if not explicit_command_tags and not link_tags:
            self._default_queue()
        else:
            self._build_queue_from_tags(explicit_command_tags, link_tags)

    def process_request(self, request):
        self.build_process_queue(self, request)
        while self.process_queue:
            # process one command
            # Append an item to request.response_items
            pass

    def respond_to_request(self, mention_ref):
        # Todo: there's a lot of potential optimization to be done
        # here.  If someone just calls '[[roll DICE]]' for instance, I
        # wouldn't need all the references.
        logging.debug("Searching for commands...")
        commands = re.findall(r"\[\[(.+?)\]\]", mention_ref.body)
        logging.debug("Commands found: {}".format(commands))
        logging.info("Generating response to user-mention")
        sources = self.get_table_sources(mention_ref)
        logging.info("Table sources generated.  Generating response.")
        # respond, marks as read.
        # Possible sources: summoning comment, OP, top-level comments
        # to OP, any links in summoning text
        logging.info("Generating reply...")
        # mention_ref.mark_as_read()


        

class RollOneForMe(Sentinel, RequestProcessing, MailHandling):
    '''/u/roll_one_for_me bot.'''
    def __init__(self, load_stats_filename=None):
        super(RollOneForMe, self).__init__()
        self.stats = RollOneStats(load_stats_filename)

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
        
