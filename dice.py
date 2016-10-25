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
_OP_TO_STR = {op : ch for ch, op in _OPERATOR_MAP.items()}

# Regex for a single die roll
REGEX=r"\d*\s*d\s*\d+(?:\s*[v^]\s*\d+)?"


class RollParsingError(RuntimeError):
    pass


class RollLimitError(RuntimeError):
    pass


class BasicMathError(ValueError):
    pass


class SimpleRoll:
    '''At most {n=1}dK{[v^][L=K]}
    For instance:
    d5, 2d5, 4d5v2.
    Class members 'max_n', 'max_k' limit permissible roll sizes.'''

    max_n = 100
    max_k = 1000

    @classmethod
    def set_roll_limits(cls, max_n=None, max_k=None):
        if max_n:
            cls.max_n = max_n
        if max_k:
            cls.max_k = max_k

    def __init__(self, input_string):
        logging.debug("Initialize SimpleRoll")
        # Allocate
        self.n, self.k, self.l = None, None, None
        # These will be set below in roll()
        self._last_roll, self._value = None, None
        logging.debug(
            "Generating SimpleRoll from input string: {}".format(input_string))
        # Make sure it's a roll to begin with
        if "d" not in input_string:
            logging.error("RollParsingError")
            raise RollParsingError("SimpleRoll received non-roll string.")
        # Purge whitespace, get numbers
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
        # TODO: this roll will probably end up being redundant, but I
        # won't want to leave _last_roll and _value as None
        self.roll()
        logging.debug("Roll generated: {}".format(self))

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
        logging.debug("Simple roll generated: {}".format(self))

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
        self.value = self._do_basic_math([int(v)
                                          if not i % 2
                                          else _OPERATOR_MAP[v]
                                          for i, v in enumerate(self.items)])

    def roll(self):
        for item in self.items:
            if isinstance(item, SimpleRoll):
                item.roll()
        self.evaluate()
        return int(self)

    def get_range(self):
        ranges = [v.get_range()
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
        return (self._do_basic_math(low_range), self._do_basic_math(high_range))

    

    def _do_basic_math(self, values: "[int, operator, int, operator, ...]"):
        '''Performs basic math operators in a list of alternating ints and
operators.  Respects priority of multiplication and division.'''
        # We'll use a sanitized eval call for simplicity.  To address the
        # possible security issue, we'll be explicit about incomming
        # types.
        if len(values) % 2 != 1:
            raise BasicMathError("Malformed list in _do_basic_math")
        if not all(isinstance(v, int) for v in values[::2]):
            raise BasicMathError("Expected int in even indexed positions.")
        if not all(op in _OP_TO_STR.keys() for op in values[1::2]):
            raise BasicMathError("Expected operator in odd indexed positions.")
        as_str = [str(v)
                  if not i%2
                  else _OP_TO_STR[v]
                  for i, v in enumerate(values)]
        total = eval("".join(as_str))
        return total

    
def roll(input_string):
    return Roll(input_string).roll()

def set_limits(max_n=None, max_k=None, max_predicate=None):
    SimpleRoll.set_roll_limits(max_n, max_k)
    Roll.set_max_roll_length(max_predicate)

