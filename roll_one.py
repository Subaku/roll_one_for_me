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

import logging
import os
import pickle
import praw
import random
import re
import string
import sys
import time
import configparser
import dice
from rofm_bot import RollOneForMe

from pprint import pprint  #for debugging / live testing

# Make sure you're in the correct local directory.
try:
    full_path = os.path.abspath(__file__)
    root_dir = os.path.dirname(full_path)
    os.chdir(root_dir)
except:
    pass

# As a function for live testing, as opposed to the one-line in main()
def prepare_logger(this_logging_level=logging.INFO,
                   other_logging_level=logging.ERROR,
                   log_filename=None,
                   log_file_mode='a',
                   format_string=None):
    '''Clears the logging root and creates a new one to use, setting basic
config.'''
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=other_logging_level,
                        format=format_string)
    for my_module in ('rofm_bot', 'dice', 'tables', ''):
        logging.getLogger(my_module).setLevel(this_logging_level)
    if log_filename:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(this_logging_level)
        file_handler.setFormatter(logging.Formatter(format_string))
        logging.getLogger().addHandler(file_handler)

    
def config_test():
    conf = configparser.RawConfigParser()
    conf.read("config.ini")
    try:
        configurate(conf)
    except:
        pass
    return conf

def configurate(config):
    # Dice
    d_conf = config['dice']
    dice.set_limits(
        int(d_conf['max_n']),
        int(d_conf['max_k']),
        int(d_conf['max_compound_roll_length']))
    # IO
    io_conf = config['io']
    prepare_logger(
        getattr(logging, io_conf['my_log_level']),
        getattr(logging, io_conf['external_log_level']),
        io_conf['log_filename'],
        io_conf['log_file_mode'],
        io_conf['log_format_string'])

def main(config_file,
         this_logging_level=logging.INFO,
         other_logging_level=logging.ERROR,
         ):
    '''Logs into Reddit, looks for unanswered user mentions, and
    generates and posts replies'''
    # Initialize
    prepare_logger(logging_level)
    config = configparser.RawConfigParser()
    config.read(config_file)
    configurate(config)
    logging.info("Initializing rofm.")
    rofm = RollOneForMe()
    trivial_passes_count = 0
    logging.info("Enter core loop.")
    trivial_per_heartbeat = config['io']['n_trivial_passes_per_heartbeat']
    try:
        while True:
            rofm.act()
            
            trivial = rofm.end_of_pass()
            trivial_passes_count = (
                0 if not trivial
                else trivial_passes_count + 1)
            if trivial_passes_count == trivial_per_heartbeat:
                logging.info(
                    "{} passes without incident.".format(
                        _trivial_passes_per_heartbeat))
                trivial_passes_count = 0
            time.sleep(int(config['sleep']['between_checks']))
    except Exception as e:
        logging.critical("Top level error.  Crashing out.")
        logging.shutdown("Shutdown error: {}".format(e))
        raise(e)

####################

def log_item(item_ref):
    filename = "{}/rofm-{}-{}.log".format(log_dir, self.origin.author,
                                          self.origin.fullname)
    with open(filename, 'w') as f:
        f.write("Time    :  {}\n".format(fdate() ))
        f.write("Author  :  {}\n".format(self.origin.author))
        try:
            f.write("Link    :  {}\n".format(self.origin.permalink))
        except:
            f.write("Link    :  Unavailable (PM?)\n")
        f.write("Type    :  {}\n".format(type(self.origin)))
        try:
            f.write("Body    : (below)\n[Begin body]\n{}\n[End body]\n".format(
                get_post_text(self.origin)))
        except:
            f.write("Body    : Could not resolve message body.")
        f.write("\n")
        try:
            f.write("Submission title : {}\n".format(
                self.origin.submission.title))
            f.write("Submission body  :"
                    " (below)\n[Begin selftext]\n{}\n[End selftext]\n".format(
                        self.origin.submission.selftext))
        except:
            f.write("Submission: Could not resolve submission.")
    filename = filename.rstrip("log") + "pickle"
    with open(filename, 'wb') as f:
        pickle.dump(self, f)

    # This function is unused, but may be useful in future logging
    def describe_source(self):
        return "From [this]({}) post by user {}...".format(
            self.source.permalink, self.source.author)


# if __name__=="__main__":
#     print("Current working directory:", os.getcwd() )
#     if len(sys.argv) > 1:
#         main()
#     elif 'y' in input("Run main? >> ").lower():
#         main()


def configtest():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config


def dbg():
    prepare_logger(logging.DEBUG)

