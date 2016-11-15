'''Various component classes for /u/roll_one_for_me, as well as the
primary RollOneForMe class.'''

# Todo: set a maximum recursion depth.

# Todo: a table header beginning with ! between the dice and the
# header should not be included in the "defaults" but only accessible
# by request or link.
import logging
import dice
import time
import praw
import pickle
from enum import Enum
from collections import deque
import re
from dnd_tables import TableSource
import os
import shutil

####################
## Request isn't a bot... maybe this belongs somewhere else.  It's own
## file?

class Request:
    '''A single summons or PM.  Associate praw_ref should already be
verified to be a summons or PM request.
    '''
    def __init__(self, praw_ref):
        super(Request, self).__init__()
        self.ref = praw_ref
        self.text = praw_ref.body
        # Elements are tuple of Header, dice, text.  Will ultimately
        # generate the response text
        self.response_items = []

    def __str__(self):
        return self.get_response_text()

    def __repr__(self):
        return "<Request>"

    def add_item(self, head='', roll_str='', outcome=''):
        self.response_items.append((head, roll_str, outcome))

    def get_response_text(self):
        return "\n\n".join(
            "    \n".join(
                item)
            for item in self.response_items)


    def get_log_str(self):
        ret_str = ''
        ret_str += "Time    :  {}\n".format(fdate() )
        ret_str += "Author  :  {}\n".format(self.origin.author)
        try:
            ret_str += "Link    :  {}\n".format(self.origin.permalink)
        except:
            ret_str += "Link    :  Unavailable (PM?)\n"
            ret_str += "Type    :  {}\n".format(type(self.origin))
        try:
            ret_str += (
                "Body    : (below)\n[Begin body]\n{}\n[End body]\n".format(
                    get_post_text(self.origin)))
        except:
            ret_str += "Body    : Could not resolve message body."
        ret_str += "\n"
        try:
            f.write("Submission title : {}\n".format(
                self.origin.submission.title))
            f.write("Submission body  :"
                    " (below)\n[Begin selftext]\n{}\n[End selftext]\n".format(
                        self.origin.submission.selftext))
        except:
            f.write("Submission: Could not resolve submission.")




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


class MailHandler(RedditBot):
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



####################
## This page: Sentinel functionality
class Sentinel(RedditBot):
    '''Sentinel action for /u/roll_one_for_me.  Monitors
/r/DnDBehindTheScreen for posts with tables, and adds orgizational
thread to keep requests from cluttering top-level comments.
    '''
    ####################
    ## Class members and methods
    # These are class-members to allow more natural config-file setup
    fetch_limit = 50
    cache_limit = 100
    fetch_failures_allowed = 5

    @classmethod
    def set_fetch_limit(cls, new_fetch_limit):
        cls.fetch_limit = new_fetch_limit

    @classmethod
    def set_cache_limit(cls, new_cache_limit):
        cls.cache_limit = new_cache_limit

    @classmethod
    def set_cache_limit(cls, new_fail_limit):
        cls.fetch_failures_allowed = new_fail_limit

    ####################
    ## Instance methods
    def __init__(self, *seen_posts):
        super(Sentinel, self).__init__()
        self.seen = list(seen_posts)
        self.fetch_failure_count = 0

    def __repr__(self):
        return "<Sentinel>"

    def fetch_new_subs(self):
        try:
            logging.debug("Fetching newest /r/DnDBehindTheScreen submissions")
            BtS = self.r.get_subreddit('DnDBehindTheScreen')
            new_submissions = BtS.get_new(limit=Sentinel.fetch_limit)
            self.fetch_failure_count = 0
            return new_submissions
        except:
            logging.error("Fetching new posts failed...")
            self.fetch_failure_count += 1
            if self.fetch_failure_count >= Sentinel.fetch_failures_allowed:
                logging.critical("Allowed failures exceeded.  Raising error.")
                raise RuntimeError(
                    "Sentinel fetch failure limit ({}) reached.".format(
                        Sentinel.fetch_failures_allowed))
            else:
                logging.error("Will try again next cycle.")
                return None

    def sentinel_comment(self, beep_boop=True):
        '''Produce organizational comment text'''
        reply_text = (
            "It looks like this post has some tables!"
            "  To keep things tidy and not detract from actual discussion"
            " of these tables, please make your /u/roll_one_for_me requests"
            " as children to this comment.")
        if beep_boop:
            reply_text += "\n\n" + self.beep_boop()
        return reply_text

    def beep_boop(self):
        raise NotImplementedError(
            "BeepBoop needs to be obfusated by RollOneforMe")

    def act_as_sentinel(self):
        '''This function groups the following:
        * Get the newest submissions to /r/DnDBehindTheStreen
        * Attempt to parse the item as containing tables
        * If tables are detected, post a top-level comment requesting that
        table rolls be performed there for readability
        # * Update list of seen tables
        # * Prune seen tables list if large.
        '''

        num_orgos_made = 0
        new_submissions = self.fetch_new_subs()
        for item in new_submissions:
            if item not in self.seen:
                logging.debug("Considering submission: {}".format(item.title))
                if TableSource(item.selftext):
                    try:
                        # Verify I have not already replied, but
                        # thread isn't in cache (like after reload)
                        top_level_authors = [com.author
                                             for com in item.comments]
                        if self.r.user not in top_level_authors:
                            #item.add_comment(self.sentinel_comment())
                            print("Not commenting on it.")
                            num_orgos_made += 1
                            logging.info(
                                "Organizational comment made to thread:"
                                " {}".format(TS.source.title))
                    except:
                        logging.error("Error in Sentinel checking.")
        # Prune list to max size
        self.seen = self.seen[-cache_limit:]
        return num_orgos_made



####################
## This page: Stats for bot and bot built from components above.
class RollOneStats:
    '''Stats for /u/roll_one_for_me, to be included in message footer.'''
    def __init__(self, *load_args, **load_kwargs):
        self.summons_answered = 0
        self.private_messages_replied = 0
        self.tables_rolled = 0
        self.dice_rolled = 0
        self.sentinel_posts_made = 0
        self.since = datetime.datetime.utcnow()
        if load_args:
            self.load_data(*load_args, **load_kwargs)
        
    def __str__(self):
        return ("Since {since}:    \n"
                "{summons_answered:>3} summons answered and    \n"
                "{private_messages_replied:>3} PMs replied.    \n"
                "{tables_rolled:>3} tables rolled,    \n"
                "{dice_rolled:>3} total dice rolled.    \n"
                "{sentinel_posts_made:>3} organizing comments made.    \n"
                .format(**self.__dict__))
    
    def __repr__(self):
        return "<RollOneStats>"

    def __eq__(self, other):
        if not isinstance(other, RollOneStats):
            raise TypeError("RollOneStats only compares to other RollOneStats")
        # No entries are different
        return not any(getattr(self, key) != getattr(other, key)
                       for key in self.__dict__)

    def save_data(self, cache_file, tmp_file='./.tmp'):
        # Write first to a temp file to preserve the old file until
        # we're sure we have successfully written our data.  "Just in
        # case"
        with open(tmp_file, 'wb') as handle:
            pickle.dump(self, handle)
        # TODO(2016-11-02) : will this overwrite or raise an error?
        shutil.move(tmp_file, cache_file)
        
    def load_data(self, cache_file,
                  raise_on_failure=True, create_file_if_missing=False):
        if not os.path.isfile(cache_file):
            logging.error(
                "Cannot open stats file {!r}: file does not exist.".format(
                    cache_file))
            if raise_on_failure:
                raise RuntimeError("Could not open stats file")
            elif create_file_if_missing:
                logging.info("Creating cache file at {!r}".format(cache_file))
                self.save_data(cache_file)
                return
            else:
                return
        with open(cache_file, 'rb') as handle:
            old = pickle.load(handle)
        self.__dict__.update(old.__dict__)

    def copy(self):
        copied = RollOneStats()
        copied.__dict__.update(self.__dict__)
        return copied
        

class RollOneForMe(Sentinel, RequestProcessing):
    '''/u/roll_one_for_me bot.'''
    def __init__(self, load_stats_filename=None):
        super(RollOneForMe, self).__init__()
        self.stats = RollOneStats()
        if load_stats_filename:
            self.stats.attempt_to_load(load_stats_filename)

    def __repr__(self):
        return "<RollOneForMe>"

    def act(self):
        self.act_as_sentinel()
        self.answer_mail()


