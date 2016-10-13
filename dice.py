'''A dice parser that is more combersome but more responsive than the
module available in pypi.dice

'''

import random
import operator
import logging

_OPERATOR_MAP = {"+" : operator.add,
                 "-" : operator.sub,
                 "*" : operator.mul,
                 "/" : operator.floordiv}
# TODO(2016-10-09) This is unused.  Was that intentional..?
_OP_TO_STR = {operator.add : "+",
              operator.sub : "-",
              operator.mul : "*",
              operator.floordiv : "/",}
# Regex for a single die roll
REGEX=r"\d*\s*d\s*\d+(?:\s*[v^]\s*\d+)?"


class RollParsingError(RuntimeError):
    pass


class RollLimitError(RuntimeError):
    pass


def do_basic_math(values: "[int, operator, int, operator, ...]"):
    # mult/div pass
    i = 0
    while i < len(values)-2:
        if values[i+1] in (operator.mul, operator.floordiv):
            values[i] = values[i+1](values[i], values[i+2])
            values = values[:i+1] + values[i+3:]
        else:
            i += 1
    # add/diff pass
    while len(values) > 1:
        values[0] = values[1](values[0], values[2])
        values = values[:1] + values[3:]
    return values[0]


class SimpleRoll:
    '''At most {n=1}dK{[v^][L=K]}
    For instance:
    d5, 2d5, 4d5v2.

    Class members 'max_n', 'max_k' limit permissible roll sizes.'''
    
    max_n = 100
    max_k = 1000

    @classmethod
    def set_roll_limits(cls, max_n=100, max_k=1000):
        cls.max_n, cls.max_k = max_n, max_k

    def __init__(self, input_string):
        logging.debug("Initialize SimpleRoll")
        self.n, self.k, self.l = None, None, None
        self._last_roll, self.value = None, None
        logging.debug(
            "Generating SimpleRoll from input string: {}".format(input_string))
        if "d" not in input_string:
            logging.error("RollParsingError")
            raise RollParsingError("SimpleRoll received non-roll string.")
        self.string = input_string.replace(" ", "").lower()
        count, tail = self.string.split("d")
        self.n = int(count) if count else 1
        self.k = (
            int(tail)
            if not self._limiting()
            else int(tail.split(self._limiting())[0]))
        self.l = (
            self.n
            if not self._limiting()
            else int(tail.split(self._limiting())[1]))
        # sanity:
        self._sanity()
        # These will be set in roll()
        self._last_roll = None
        self._value = None
        self.roll()
        logging.debug("Generated: {}".format(self))

    def __repr__(self):
        return "<SimpleRoll: {}>".format(self.string)

    def __str__(self):
        if self.n == 1:
            return "[d{}] -> {}".format(self.k, self._last_roll[0])
        if not self._limiting():
            return "[{}: {}] -> {}".format(
                self.string,
                " ".join(str(v) for v in self._last_roll),
                self._value)
        elif self._limiting() == "v":
            return "[{}: {} ({})] -> {}".format(
                self.string,
                " ".join(str(v) for v in self._last_roll[:self.l]),
                " ".join(str(v) for v in self._last_roll[self.l:]),
                self._value)
        else:
            return "[{}: ({}) {}] -> {}".format(
                self.string,
                " ".join(str(v) for v in self._last_roll[:-self.l]),
                " ".join(str(v) for v in self._last_roll[-self.l:]),
                self._value)

    def __int__(self):
        return self._value

    def __add__(self, other):
        return int(self) + other
    
    def _sanity(self):
        if self.l <= 0:
            logging.error("RollLimitError - kept <= 0")
            raise RollLimitError("SimpleRoll to keep non-positive dice count.")
        if self.n <= 0:
            logging.error("RollLimitError - dice count <= 0")
            raise RollLimitError("SimpleRoll to roll non-positive dice count.")
        if self.k <= 1:
            logging.error("RollLimitError - die face <= 1")
            raise RollLimitError("SimpleRoll die face must be at least two.")
        if self.l > self.n:
            logging.error("RollLimitError - kept > count")
            raise RollLimitError("SimpleRoll to keep more dice than present.")
        if self.n > SimpleRoll.max_n:
            logging.error(
                "RollLimitError - dice limit ({})".format(SimpleRoll.max_n))
            raise RollLimitError("SimpleRoll exceeds maximum allowed dice.")
        if self.k > SimpleRoll.max_k:
            logging.error(
                "RollLimitError - die face limit ({})".format(SimpleRoll.max_k))
            raise RollLimitError("SimpleRoll exceeds maximum allowed die face.")

    def _limiting(self):
        '''Returnes "^", "v", or "" when "^", "v", or neither are present in
the generating string, respectively.'''
        if "^" in self.string:
            return "^"
        if "v" in self.string:
            return "v"
        return ""

    def get_range(self):
        '''Returns tuple (low, high) of the lowest and highest possible
rolls'''
        return (self.l, self.l * self.k)

    def roll(self):
        self._last_roll = sorted([random.randint(1, self.k)
                                 for i in range(self.n)])
        if self.n == self.l:
            self._value = sum(self._last_roll)
        elif "^" in self.string:
            self._value = sum(self._last_roll[-self.l:])
        elif "v" in self.string:
            self._value = sum(self._last_roll[:self.l])
        else:
            raise RuntimeError("SimpleRoll l != n, but without v or ^")
        return self._value

    
class Roll:
    '''A roll consists of one or more SimpleRoll instances, separated by
operators +-*/.  Mathematical priority of */ are respected, but
parentheses are not permitted.  All operations are performed with
left-to-right implicit associativity.  Division is performed as
integer division.  

Class member 'max_compound_roll_length' limits the numer of die
predicates allowed.

    '''

    max_compound_roll_length = 20

    @classmethod
    def set_max_roll_length(cls, max_len=20):
        cls.max_compound_roll_length = max_len

    def __init__(self, input_string):
        logging.debug(
            "Generating Roll from input string: {}".format(input_string))
        self.string = input_string.replace(" ", "").lower()
        self.items = []
        self.value = None
        # Begin parsing
        self._parse()
        self.evaluate()
        logging.debug("Generated: {}".format(self))

    def __repr__(self):
        return "<Roll: {}>".format(self.string)

    def __str__(self):
        if len(self.items) == 1:
            return str(self.items[0])
        return "[({}){}] -> {}".format(
            str(self.items[0]),
            "".join(
                " {} ({})".format(
                    str(self.items[i]),
                    str(self.items[i+1]))
                for i in range(1, len(self.items), 2)),
            self.value)
        return str(self.items)

    def __int__(self):
        return self.value
    
    def _parse(self):
        logging.debug("Parsing Roll...")
        # Identify operator positions:
        ops = [(i, s) for i, s in enumerate(self.string) if s in '*/+-']
        logging.debug("Operators: {}".format(ops))
        if len(ops) // 2 >= Roll.max_compound_roll_length:
            logging.error("RollLimitError - predicate length")
            raise RollLimitError(
                "Roll exceeds maximum predicate length ({}).".format(
                    Roll.max_compound_roll_length))
        logging.debug("Building items...")
        # Kind of awkward, but too many boundary cases otherwise
        ## Allocate space
        self.items = [None] * (2 * len(ops) + 1)
        ## Inject operators
        self.items[1::2] = [o for _, o in ops]
        logging.debug("Items: {}".format(self.items))
        ## Update index ranging
        starts = [0] + [i + 1 for i, _ in ops]
        stops = [i for i, _ in ops] + [len(self.string)]
        self.items[::2] = [self.string[start:stop]
                            for start, stop in zip(starts, stops)]
        logging.debug("Items: {}".format(self.items))
        # Convert to SimpleRolls
        logging.debug("Converting to odd indexed items to SimpleRoll...")
        for i, v in enumerate(self.items):
            # operators stay as operator strings
            if not i % 2:
                self.items[i] = (int(v)
                                 if v.isnumeric()
                                 else SimpleRoll(v))

    def evaluate(self):
        self.value = do_basic_math([int(v)
                                    if not i % 2
                                    else _OPERATOR_MAP[v]
                                    for i, v in enumerate(self.items)])
    
    def roll(self):
        for item in self.items:
            if isinstance(item, SimpleRoll):
                item.roll()
        return self.evaluate()

    def get_range(self):
        ranges = [self.v.get_range()
                  if not i % 2
                  else _OPERATOR_MAP[v]
                  for i, v in enumerate(self.items)]
        low_range = [(v[0]
                      if not (i > 0 and ranges[i-1] == operator.floordiv)
                      else v[1])
                     if not i % 2
                     else v
                     for i, v in enumerate(ranges)]
        high_range = [(v[1]
                       if not (i > 0 and ranges[i-1] == operator.floordiv)
                       else v[0])
                      if not i % 2
                      else v
                      for i, v in ranges]
        return (do_basic_math(low_range), do_basic_math(high_range))

    
def roll(input_string):
    return int(Roll(input_string))
