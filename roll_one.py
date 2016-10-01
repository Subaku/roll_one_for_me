#!/usr/bin/python3
'''Implementation for Reddit bot /u/roll_one_for_me.

Bot usage: summon with user mention to /u/roll_one_for_me, or send a
private message.

Default behavior: Summoning text / private message is parsed for
tables and links to tables.  If called using a user-mention, the
original post and top-level comments are also scanned.

Each table is parsed and rolled, and a reply is given.

Tables must begin with a die notation starting a newline (ignoring
punctuation).

'''

#TODO: I have a lot of generic 'except:' catches that should be
#specified to error type.  I need to learn PRAW's error types.

# import dice
# raises dice.ParseException if dice.roll input string is bad.
import logging
import os
import pickle
import praw
import random
import re
import string
import sys
import time

from pprint import pprint  #for debugging / live testing

# Make sure you're in the correct local directory.
try:
    full_path = os.path.abspath(__file__)
    root_dir = os.path.dirname(full_path)
    os.chdir(root_dir)
except:
    pass

##################
# Some constants #
##################
# TODO: This should be a config file.
_version="2.0.0"
_last_updated="2016-09-21"

_seen_max_len = 50
_fetch_limit=25

_trash = string.punctuation + string.whitespace

_header_regex = "^(\d+)?[dD](\d+)(.*)"
_line_regex = "^(\d+)(\s*-+\s*\d+)?(.*)"
_summons_regex = "u/roll_one_for_me"

_mentions_attempts = 10
_answer_attempts = 10

_sleep_on_error = 30
_sleep_between_checks = 60

_log_dir = "./logs"

_trivial_passes_per_heartbeat = 30

_log_format_string = (
    '%(asctime)s - %(levelname)-8s - %(name)-12s;'
    ' Line %(lineno)-4d: %(message)s')


# As a function for live testing, as opposed to the one-line in main()
def prepare_logger(this_logging_level=logging.INFO,
                   other_logging_level=logging.ERROR,
                   log_filename=None,
                   file_mode='a'):
    '''Clears the logging root and creates a new one to use, setting basic
config.'''
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=other_logging_level,
                        format=_log_format_string)
    logging.getLogger('').setLevel(this_logging_level)
    pass
    # Add file logging


class Sentinel:
    def __init__(self, reddit_handle, *seen_posts):
        self.r = reddit_handle
        self.seen = list(seen_posts)
        self.organizing_posts_made = 0
        
    def __repr__(self):
        return "<Sentinel>"

    def sintinel_check(self):
        '''This function groups the following:
        * Get the newest submissions to /r/DnDBehindTheStreen
        * Attempt to parse the item as containing tables
        * If tables are detected, post a top-level comment requesting that
        table rolls be performed there for readability
        # * Update list of seen tables
        # * Prune seen tables list if large.
        
        '''

        logging.info("Scanning for new posts...")
        keep_it_tidy_reply = (
            "It looks like this post has some tables!"
            "  To keep things tidy and not detract from actual discussion"
            " of these tables, please make your /u/roll_one_for_me requests"
            " as children to this comment." +
            BeepBoop() )
        try:
            logging.debug("Fetching newest submissions to /r/DnDBehindTheScreen")
            BtS = r.get_subreddit('DnDBehindTheScreen')
            new_subs = BtS.get_new(limit=_fetch_limit)
        except:
            logging.critical("Fetching failed.")
            return
        saw_something_said_something = False
        for item in new_subs:
            if item not in self.seen:
                if has_tables(item):
                    try:
                        # Check if I have already replied
                        top_level_authors = [com.author for com in item.comments]
                        if not r.user in top_level_authors:
                            item.add_comment(keep_it_tidy_reply)
                            self.organizing_posts_made += 1
                            logging.info(
                                "Organizational comment made to thread:"
                                " {}".format(TS.source.title))
                            saw_something_said_something = True
                    except:
                        logging.error("Error in Sentinel checking.")
        # Prune list to max size
        self.seen[:] = self.seen[-_seen_max_len:]
        return saw_something_said_something



#class Bot(Sentinel, TableHandler, MailHandler):
#    def __init__(self, reddit_handle):
        # Sentinel.__init__(self, reddit_handle)
        # TableHandler.__init__(self, reddit_handle)
        # MailHandler.__init__(self, reddit_handle)
        





class MailHandler:
    def process(self):
        '''Processes notifications.  Returns True if any item was processed.'''
        my_mail = list(self.r.get_unread(unset_has_mail=False))
        requests_list = []
        for notification in my_mail:
            try:
                requests_list.append(Request(notification, self.r))
            except:
                logging.warning("Mail could not be transformed to Request")
                notification.mark_as_read()
        return requests_list


class TableHandler:
    def __init__(self):
        pass

    def determine_commands(self, command_string):
        pass


    
def main(debug=False, logging_level=logging.INFO):
    '''Logs into Reddit, looks for unanswered user mentions, and
    generates and posts replies

    '''
    # Initialize
    prepare_logger(logging_level)
    r = attempt_sign_in()
    sentinel = Sentinel(r)
    mail_handler = MailHandler(r)
    table_handler = TableHandler(r)
    trivial_passes_count = 0
    logging.info("Enter core loop.")
    while True:
        try:
            while True:
                was_mail = mail_handler.process()
                made_org_comm = sentinel.check()
                if not was_mail and not was_sub:
                    trivial_passes_count += 1
                else:
                    trivial_passes_count += 0
                if trivial_passes_count == _trivial_passes_per_heartbeat:
                    logging.info("{} passes without incident (or first pass).".format(_trivial_passes_per_heartbeat))
                    trivial_passes_count = 0
                time.sleep(_sleep_between_checks)
        except Exception as e:
            logging.critical("Top level error.  Crashing out.")
            logging.shutdown("Error: {}".format(e))
            raise(e)


def BeepBoop():
    '''Builds and returns reply footer "Beep Boop I'm a bot..."'''
    s = "\n\n-----\n\n"
    s += ("*Beep boop I'm a bot."
          "  You can find usage and known issue details about me,"
          " as well as my source code, on"
          " [GitHub](https://github.com/PurelyApplied/roll_one_for_me)."
          "  I am maintained by /u/PurelyApplied.*" )
    s += "\n\n^(v{}; code base last updated {})".format(_version, _last_updated)
    return s


def attempt_sign_in(attempts=5, sleep_on_failure=30):
    for i in range(attempts):
        try:
            logging.info("Attempting to sign in...")
            r = sign_in()
            logging.info("Signed in.")
            return r
        except:
            logging.info("Sign in failed.  Sleeping...")
            time.sleep(sleep_on_failure)
    logging.critical("Could not sign in after {} attempts.  Crashing out.")
    logging.shutdown()
    raise RuntimeError("Could not sign in.")


def sign_in():
    '''Sign in to reddit using PRAW; returns Reddit handle'''
    r = praw.Reddit(
        user_agent=(
            'Generate an outcome for random tables, under the name'
            '/u/roll_one_for_me. Written and maintained by /u/PurelyApplied'),
        site_name="roll_one")
    # login info in praw.ini.  TODO: OAuth2
    r.login(disable_warning=True)
    return r


# Fetches anything set as unread
def fetch_mail(r, unset=False):
    return list(r.get_unread(unset_has_mail=unset))

# Not just the new ones
def fetch_mentions(r):
    return list(r.get_mentions())


####################
# classes
'''Class definitions for the roll_one_for_me bot

A Request fetches the submission and top-level comments of the
appropraite thread.

Each of these items become a TableSource.

A TableSource is parsed for Tables.

A Table contains many TableItems.

When a Table is rolled, the appropraite TableItems are identified.

These are then built into TableRoll objects for reporting.

'''

class Request:
    def __init__(self, praw_ref, r):
        self.origin = praw_ref
        self.reddit = r
        self.tables_sources = []
        self.outcome = None

        self._parse()

    def __repr__(self):
        return "<Request from >".format(str(self))

    def __str__(self):
        via = None
        if isinstance(self.origin, praw.objects.Comment):
            via = "mention in {}".format(self.origin.submission.title)
        elif isinstance(self.origin, praw.objects.Message):
            via = "private message"
        else:
            via = "a mystery!"
        return "/u/{} via {}".format(self.origin.author, via)

    def _parse(self):
        '''Fetches text of submission and top-level comments from thread
        containing this Request.  Builds a TableSource for each, and
        attempts to parse each for tables.

        '''
        # Default behavior: OP and top-level comments, as applicable
        
        #print("Parsing Request...", file=sys.stderr)
        if re.search("\[.*?\]\s*\(.*?\)", self.origin.body):
            #print("Adding links...", file=sys.stderr)
            self.get_link_sources()
        else:
            #print("Adding default set...", file=sys.stderr)
            self.get_default_sources()

    def _maybe_add_source(self, source, desc):
        '''Looks at PRAW submission and adds it if tables can be found.'''
        T = TableSource(source, desc)
        if T.has_tables():
            self.tables_sources.append(T)

    def reply_to(self):
        if self.is_summons() or self.is_PM():
            logging.info("Generating reply...")
            reply_text = self.roll()
            without_issue = True
            if not reply_text:
                reply_text = ("I'm sorry, but I can't find anything"
                              " that I know how to parse.\n\n")
                logging.warning("No tables found.")
                without_issue = False
            reply_text += BeepBoop()
            if len(reply_text) > 10000:
                logging.debug("Had to clip message")
                addition = ("\n\n**This reply would exceed 10000 characters"
                            " and has been shortened.  Chaining replies is an"
                            " intended future feature.")
                clip_point = 10000 - len(addition) - len(BeepBoop()) - 200
                reply_text = reply_text[:clip_point] + addition + BeepBoop()
                without_issue = False
            self.reply(reply_text)
            logging.info("{} resolving request: {}.".format(
                "Successfully" if okay else "Questionably", self))
        self.origin.mark_as_read()

    def get_link_sources(self):
        links = re.findall("\[.*?\]\s*\(.*?\)", self.origin.body)
        #print("Link set:", file=sys.stderr)
        #print("\n".join([str(l) for l in links]), file=sys.stderr)
        for item in links:
            desc, href = re.search("\[(.*?)\]\s*\((.*?)\)", item).groups()
            href = href.strip()
            if "reddit.com" in href.lower():
                lprint("Fetching href: {}".format(href.lower()))
                if "m.reddit" in href.lower():
                    lprint("Removing mobile 'm.'")
                    href = href.lower().replace("m.reddit", "reddit", 1)
                if ".json" in href.lower():
                    lprint("Pruning .json and anything beyond.")
                    href = href[:href.find('.json')]
                if not 'www' in href.lower():
                    lprint("Injecting 'www.' to href")
                    href = href[:href.find("reddit.com")] + 'www.' + href[href.find("reddit.com"):]
                href = href.rstrip("/")
                lprint("Processing href: {}".format(href))
                self._maybe_add_source(
                    self.reddit.get_submission(href),
                    desc)
                
    def get_default_sources(self):
        '''Default sources are OP and top-level comments'''
        try:
            # Add OP
            self._maybe_add_source(self.origin.submission, "this thread's original post")
            # Add Top-level comments
            top_level_comments = self.reddit.get_submission(None, self.origin.submission.id).comments
            for item in top_level_comments:
                self._maybe_add_source(item, "[this]({}) comment by {}".format(item.permalink, item.author) )
        except:
            lprint("Could not add default sources.  (PM without links?)")

    def roll(self):
        instance = [TS.roll() for TS in self.tables_sources]
        # prune trivial outcomes
        instance = [x for x in instance if x]
        return "\n\n-----\n\n".join(instance)

    def reply(self, reply_text):
        self.origin.reply(reply_text)

    def is_summons(self):
        return re.search(_summons_regex, get_post_text(self.origin).lower())

    def is_PM(self):
        return type(self.origin) == praw.objects.Message

    def log(self, log_dir):
        filename = "{}/rofm-{}-{}.log".format(log_dir, self.origin.author, self.origin.fullname)
        with open(filename, 'w') as f:
            f.write("Time    :  {}\n".format(fdate() ))
            f.write("Author  :  {}\n".format(self.origin.author))
            try:
                f.write("Link    :  {}\n".format(self.origin.permalink))
            except:
                f.write("Link    :  Unavailable (PM?)\n")
            f.write("Type    :  {}\n".format(type(self.origin)))
            try:
                f.write("Body    : (below)\n[Begin body]\n{}\n[End body]\n".format( get_post_text(self.origin)))
            except:
                f.write("Body    : Could not resolve message body.")
            f.write("\n")
            try:
                f.write("Submission title : {}\n".format(self.origin.submission.title))
                f.write("Submission body  : (below)\n[Begin selftext]\n{}\n[End selftext]\n".format(self.origin.submission.selftext))
            except:
                f.write("Submission: Could not resolve submission.")
        filename = filename.rstrip("log") + "pickle"
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    # This function is unused, but may be useful in future logging
    def describe_source(self):
        return "From [this]({}) post by user {}...".format(self.source.permalink, self.source.author)


class TableSource:
    def __init__(self, praw_ref, descriptor):
        self.source = praw_ref
        self.desc = descriptor
        self.tables = []

        self._parse()

    def __repr__(self):
        return "<TableSource from {}>".format(self.desc)


    def roll(self):
        instance = [T.roll() for T in self.tables]
        # Prune failed rolls
        instance = [x for x in instance if x]
        if instance:
            ret = "From {}...\n\n".format(self.desc)
            for item in instance:
                ret += item.unpack()
            return ret
        return None

    def has_tables(self):
        return ( 0 < len(self.tables) )

    def _parse(self):
        indices = []
        text = get_post_text(self.source)
        lines = text.split("\n")
        for line_num in range(len(lines)):
            l = lines[line_num]
            if re.search(_header_regex, l.strip(_trash)):
                indices.append(line_num)
        # TODO: if no headers found?
        if len(indices) == 0:
            return None

        table_text = []
        for i in range(len(indices) -1):
            table_text.append("\n".join(lines[ indices[i]:indices[i+1] ]))
        table_text.append("\n".join(lines[ indices[-1]: ]))

        self.tables = [ Table(t) for t in table_text ]


class TableSourceFromText(TableSource):
    def __init__(self, text, descriptor):
        self.text = text
        self.desc = descriptor
        self.tables = []

        self._parse()

    # This is nearly identical to TableSource._parse ; if this is ever
    # used outside of testing, it behooves me to make a single
    # unifying method
    def _parse(self):
        indices = []
        text = self.text
        lines = text.split("\n")
        for line_num in range(len(lines)):
            l = lines[line_num]
            if re.search(_header_regex, l.strip(_trash)):
                indices.append(line_num)
        if len(indices) == 0:
            return None
        table_text = []
        for i in range(len(indices) -1):
            table_text.append("\n".join(lines[ indices[i]:indices[i+1] ]))
        table_text.append("\n".join(lines[ indices[-1]: ]))
        self.tables = [ Table(t) for t in table_text ]


class Table:
    '''Container for a single set of TableItem objects
    A single post will likely contain many Table objects'''
    def __init__(self, text):
        self.text = text
        self.die = None
        self.header = ""
        self.outcomes = []
        self.is_inline = False

        self._parse()

    def __repr__(self):
        return "<Table with header: {}>".format(self.text.split('\n')[0])

    def _parse(self):
        lines = self.text.split('\n')
        head = lines.pop(0)
        head_match = re.search(_header_regex, head.strip(_trash))
        if head_match:
            self.die = int(head_match.group(2))
            self.header = head_match.group(3)
        self.outcomes = [ TableItem(l) for l in lines if re.search(_line_regex, l.strip(_trash)) ]

    def roll(self):
        try:
            weights = [ i.weight for i in self.outcomes]
            total_weight = sum(weights)
            if debug:
                lprint("Weights ; Outcome")
                pprint(list(zip(self.weights, self.outcomes)))
            if self.die != total_weight:
                self.header = "[Table roll error: parsed die did not match sum of item wieghts.]  \n" + self.header
            #stops = [ sum(weights[:i+1]) for i in range(len(weights))]
            c = random.randint(1, self.die)
            scan = c
            ind = -1
            while scan > 0:
                ind += 1
                scan -= weights[ind]

            R = TableRoll(d=self.die,
                          rolled=c,
                          head=self.header,
                          out=self.outcomes[ind])
            if len(self.outcomes) != self.die:
                R.error("Expected {} items found {}".format(self.die, len(self.outcomes)))
            return R
        # TODO: Handle errors more gracefully.
        except Exception as e:
            lprint("Exception in Table roll ({}): {}".format(self, e))
            return None


class TableItem:
    '''This class allows simple handling of in-line subtables'''
    def __init__(self, text, w=0):
        self.text = text
        self.inline_table = None
        self.outcome = ""
        self.weight = 0

        self._parse()

        # If parsing fails, particularly in inline-tables, we may want
        # to explicitly set weights
        if w:
            self.weight = w

    def __repr__(self):
        return "<TableItem: {}{}>".format(self.outcome, "; has inline table" if self.inline_table else "")

    def _parse(self):
        main_regex = re.search(_line_regex, self.text.strip(_trash))
        if not main_regex:
            return
        # Grab outcome
        self.outcome = main_regex.group(3).strip(_trash)
        # Get weight / ranges
        if not main_regex.group(2):
            self.weight = 1
        else:
            try:
                start = int(main_regex.group(1).strip(_trash))
                stop = int(main_regex.group(2).strip(_trash))
                self.weight = stop - start + 1
            except:
                self.weight = 1
        # Identify if there is a subtable
        if re.search("[dD]\d+", self.outcome):
            die_regex = re.search("[dD]\d+", self.outcome)
            try:
                self.inline_table = InlineTable(self.outcome[die_regex.start():])
            except RuntimeError as e:
                lprint("Error in inline_table parsing ; table item full text:")
                lprint(self.text)
                lprint(e)
                self.outcome = self.outcome[:die_regex.start()].strip(_trash)
        # this might be redundant
        self.outcome = self.outcome.strip(_trash)


    def get(self):
        if self.inline_table:
            return self.outcome + self.inline_table.roll()
        else:
            return self.outcome


class InlineTable(Table):
    '''A Table object whose text is parsed in one line, instead of expecting line breaks'''
    def __init__(self, text):
        super().__init__(text)
        self.is_inline = True

    def __repr__(self):
        return "<d{} Inline table>".format(self.die)

    def _parse(self):
        top = re.search("[dD](\d+)(.*)", self.text)
        if not top:
            return

        self.die = int(top.group(1))
        tail = top.group(2)
        #sub_outs = []
        while tail:
            in_match = re.search(_line_regex, tail.strip(_trash))
            if not in_match:
                lprint("Could not complete parsing InlineTable; in_match did not catch.")
                lprint("Returning blank roll area.")
                self.outcomes = [TableItem("1-{}. N/A".format(self.die))]
                return
            this_out = in_match.group(3)
            next_match = re.search(_line_regex[1:], this_out)
            if next_match:
                tail = this_out[next_match.start():]
                this_out = this_out[:next_match.start()]
            else:
                tail = ""

            TI_text = in_match.group(1) + (in_match.group(2) if in_match.group(2) else "") + this_out
            try:
                self.outcomes.append(TableItem(TI_text))
            except Exception as e:
                lprint("Error building TableItem in inline table; item skipped.")
                lprint("Exception:", e)


class TableRoll:
    def __init__(self, d, rolled, head, out, err=None):
        self.d = d
        self.rolled = rolled
        self.head = head
        self.out = out
        self.sub = out.inline_table
        self.err = err

        if self.sub:
            self.sob_out = self.sub.roll()

    def __repr__(self):
        return "<d{} TableRoll: {}>".format(self.d, self.head)

    def error(self, e):
        self.err = e

    def unpack(self):
        ret  = "{}...    \n".format(self.head.strip(_trash))
        ret += "(d{} -> {}) {}.    \n".format(self.d, self.rolled, self.out.outcome)
        if self.sub:
            ret += "Subtable: {}".format(self.sub.roll().unpack())
        ret += "\n\n"
        return ret


####################
## util
'''Contains roll_one_for_me utility functions'''

# Used by both Request and TableSource ; should perhaps depricate this
# and give each class its own method
def get_post_text(post):
    '''Returns text to parse from either Comment or Submission'''
    if type(post) == praw.objects.Comment:
        return post.body
    elif type(post) == praw.objects.Submission:
        return post.selftext
    else:
        lprint("Attempt to get post text from"
               " non-Comment / non-Submission post; returning empty string")
        return ""

def fdate():
    return "-".join(str(x) for x in time.gmtime()[:6])

####################
# Some testing items
_test_table = "https://www.reddit.com/r/DnDBehindTheScreen/comments/4aqi2l/fashion_and_style/"
_test_request = "https://www.reddit.com/r/DnDBehindTheScreen/comments/4aqi2l/fashion_and_style/d12wero"
T = "This has a d12 1 one 2 two 3 thr 4 fou 5-6 fiv/six 7 sev 8 eig 9 nin 10 ten 11 ele 12 twe"

if __name__=="__main__":
    print("Current working directory:", os.getcwd() )
    if len(sys.argv) > 1:
        main()
    elif 'y' in input("Run main? >> ").lower():
        main()


import dice
import matplotlib.pyplot as plt
def dice_test(n=10000):
    manual_cast = [max(random.randint(1, 6), random.randint(1, 6))
                   for i in range(n)]
    fancy_cast = [dice.roll("2d6^1")[0] for i in range(n)]
    plt.ion()
    plt.hist(manual_cast)
    plt.title("manual")
    plt.figure()
    plt.hist(fancy_cast)
    plt.title("fancy")
    



class TestA:
    def __init__(self):
        self._a = 6

class TestB(TestA):
    def __init__(self):
        TestA.__init__(self)
        self.__b = 9 # This one becomes mangled




def identify_table_heading_positions(text):
    linelist = text.split("\n")
    line_inds = []
    for i in range(len(linelist)):
        line = linelist[i].strip()
        print(" >>", line)
        if not line:
            print("Boring line.")
            continue
        left = line.strip(string.punctuation)
        possible_dice = re.search(r"^([0-9d\-\*/\+v\^ ]+)", left)
        if not possible_dice:
            print("Nothing significant.")
            continue
        roll_string = possible_dice.group(1).strip(string.punctuation + " ")
        if roll_string.isnumeric():
            print("Just a number.")
            continue
        print("Possible dice roll: ", roll_string)
        
        print(dice.roll(roll_string))


def test_text():
    return '''This is a test text.
**BOLD HEADING** followed by text.

This is a description of my table.

*2d4 - 1*  A table!

1 one
1 two
1 three
1 four 
1 five
1 six
1 seven'''

def make_hist_of(c, n=100):
    rolls = [dice.roll(c) for i in range(n)]
    counts = {v: rolls.count(v) for v in rolls}
    plt.xlim((min(counts.keys()) - 1, max(counts.keys()) + 1))
    plt.plot(sorted(counts), [counts[v] for v in sorted(counts)], ":o")
    plt.show()
    return

    


import operator

