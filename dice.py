'''A dice parser that is more combersome but more responsive than the
module available in pypi.dice

'''

import random
import operator
import logging
_operator_map = {"+" : operator.add,
                 "-" : operator.sub,
                 "*" : operator.mul,
                 "/" : operator.floordiv}
_op_to_str_map = {operator.add : "+",
                  operator.sub : "-",
                  operator.mul : "*",
                  operator.floordiv : "/",}
_max_n = 100
_max_k = 100
_max_compound_roll_length = 20

class RollParsingError(RuntimeError):
    pass

class RollLimitError(RuntimeError):
    pass


class SimpleRoll:
    '''At most {n=1}dK{[v^][L=K]}
    For instance:
    d5, 2d5, 4d5v2'''
    def __init__(self, input_string):
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
        if self.n > _max_n:
            logging.error("RollLimitError - dice limit")
            raise RollLimitError("SimpleRoll exceeds maximum allowed dice.")
        if self.k > _max_k:
            logging.error("RollLimitError - die face limit")
            raise RollLimitError("SimpleRoll exceeds maximum allowed die face.")

    def _limiting(self):
        '''Returnes "^", "v", or "" when "^", "v", or neither are present in
the generating string, respectively.'''
        if "^" in self.string:
            return "^"
        if "v" in self.string:
            return "v"
        return ""

    def __repr__(self):
        return "<SimpleRoll: {}>".format(self.string)

    def __str__(self):
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

    '''
    def __init__(self, input_string):
        self.string = input_string.replace(" ", "").lower()
        start = 0
        stop = 0
        self.items = []
        while stop < len(self.string):
            if self.string[stop] in "+-*/":
                self.items.extend([self.string[start:stop],
                                   self.string[stop]])
                start = stop+1
            stop += 1
        self.items.append(self.string[start:])
        for i in range(0, len(self.items), 2):
            self.items[i] = (
                int(self.items[i])
                if self.items[i].isnumeric()
                else SimpleRoll(self.items[i]))
        if len(self.items) // 2 > _max_compound_roll_length:
            logging.error("RollLimitError - predicate length")
            raise RollLimitError("Roll exceeds maximum predicate length.")
        self.value = self.evaluate()

    def __repr__(self):
        return "<Roll: {}>".format(self.string)

    def __str__(self):
        return "[({}){}] -> {}".format(
            str(self.items[0]),
            "".join(
                " {} ({})".format(
                    str(self.items[i]),
                    str(self.items[i+1]))
                for i in range(1, len(self.items), 2)),
            self.value)
        return str(self.items)

    def evaluate(self):
        values = [int(self.items[i])
                  if not i%2
                  else _operator_map[self.items[i]]
                  for i in range(len(self.items))]
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
        
def roll(input_string):
    return Roll(input_string).evaluate()
