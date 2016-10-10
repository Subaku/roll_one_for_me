#roll_one_for_me: README.md

This repository contains source code for Reddit bot /u/roll_one_for_me
(henceforth "ROFM").  ROFM is a summonable bot who will generate an
outcome provided by a random table, typically in one of the D&D
related subreddits, /r/DnDBehindTheScreen and the affiliated
/r/BehindTheTables being the most common.

#Usage: Rolling

ROFM v2.0 brought with it a massive overhaul to its command lexicon.

A user-mention of "/u/roll_one_for_me" will summon ROFM.  By default,
ROFM will attempt to find and parse tables in the submission text, any
top-level comments, and any links targetting Reddit itself.  Results
are provided in a reply to the summoning comment.

Users may also send ROFM a private message.  Default behavior is the
same, but of course there is submission text or comments.

**Links must be in the [Text](url) format to be noticed by ROFM.**

Default behavior may be overridden using a command in the form of
"[[COMMAND]]".  If an explicit command is given, *only* those commands
provided will be executed.  The following commands are available.

* [[Roll DICE]]: Rolls whatever is provided by DICE is some standard
  die notation, discussed in more detail below.  So, for instance,
  [[Roll 2d8]] or [[Roll 4d6^3]]

* [[OP]]: Rolls any tables present in the submission text

* [[Top]]: Rolls any tables present in top-level comments

* [[ANY OTHER STRING]]: Rolls any table whose header matches the
  provided string.


#Usage: Tables and formatting

A table must begin with a header line, which itself begins with some
die notation.  Punctuation is ignored to allow for Reddit formatting.

In the lines following the header, an enumerated list is expected.  At
least one newline is expected between table outcomes.  Lines begin
with a digit, although the value of the digit is not important.  (This
is to allow Reddit's automatic formatting, where a user may use "1."
for every row.)  Ranges are allowed, separating values with a hyphen.
Again, leading punctuation is ignored to allow for formatting.

Table outcomes may produce additional rolls.  If a dice-string is
detected, it will be rolled.  Additionally, an outcome may include a
reference to another table by including a header string reference to
that table.

If the table header has a bang ("!") between the die roll and the
header text, it will not be included in the "default" rolling and will
only be included when called directly with a [[reference]] command, or
when linked by another table's outcome.

An example is given below:

-----

d4 This is an example.

1.  This is a one.

2-3.  This outcome has even-odds.

4.  You rolled a lucky four!  Roll the [special table]!


d6 ! This is a special table

1.  One
1.  Two
1.  Three
1.  2d6
1.  Nine
1.  Eighteen

-----

A maximum chain depth of 10 has been set to avoid malicious misuse.

#Dice Format:

With v2.0, ROFM can now parse more sophisticated dice commands.
Expected format is [N=1]dK.

Examples: 1d4, d6, 2d10.

Basic mathematical operations are permitted, using + - / *.  Division
uses integer division (no decimal or remainder).

Examples: 2d10 + 5, 1d20-2, 1d8 * 1d2.

Additionall, the operators v and ^ may be used to indicate the bottom
or top (respectively) L dice to be used.

Examples: (Roll with disadvantage:) 2d20v1, (Roll a stat:) 4d6^3


#Known Issues:

* Since the bot constantly strips punctuation so as to avoid parsing
  Reddit's markup, it will leave parentheses and the like open, drop a
  plural's possessive, and so on if an entry were to end or begin with
  them.

* v1.0 would roll inline tables.  This is temporarily disabled, though
  the value itself will be rolled.  Additionally, any table references
  present in any outcome will be rolled, since no sub-table outcomes
  are distinguished.

* If a section header immediately following a table begins with a
  number, it may be parsed as part of the table.  This in turn will
  raise an error when the expected number of outcomes does not match
  the number of "outcomes" detected.
