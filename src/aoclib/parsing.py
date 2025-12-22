"""
Implements parsing of strings with a simple set of production rules.

Largely inspired by the ideas described in
https://en.wikipedia.org/wiki/Parsing_expression_grammar, though this does not
stick to just formal grammars.

The "atomic" parsing can be done by arbitrary functions making this rather
flexible. Literal and regex-based atoms are provided and are already enough to
tackle most parsing tasks. The hope is that this approach is "nicer" than using
regex exclusively (which gets ugly fast when repeated groups get involved).

Arbitrary processing of the parsed items (e.g. converting to int) can also be
applied in order to produce rich return values.

Example usage:

from aoclib.parsing import regex, seplist
from functools import cache

@cache
def foo_parser():
    add_op = regex("(plus) ([0-9]+)").zipconv(None, int)
    sub_op = regex("(minus) ([0-9]+)").zipconv(None, int)
    return seplist(add_op | sub_op, ",")

def process(s):
    result = 0
    for op in foo_parser().parse(s):
        match op:
            case ("plus", val): result += val
            case ("minus", val): result -= val
    return result

print(process("plus 1, minus 2, plus 3, minus 4"))
"""

import re
from typing import NamedTuple, Any
from functools import partial, cache

class Parser:
    """
    Parser wraps basic parsing functions, providing a fuller interface.

    In addition to feeding strings into the parsing, it also provides
    facilities for whitespace trimming and transformation of result objects.

    Note: Parsers are immutable so methods that add conversions / modify
    settings return new instances.
    """

    def __init__(self, parse_fn, **kwargs):
        """
        Creates a Parser driven by the given parse_fn.

        parse_fn(s, i) shall try to parse characters from string s starting at
        index i. It should not retain any state.

        If the parse succeeds, it shall return (result, i') where result is
        some value representing the result of the parsing, and i' is the
        exclusive end of the consumed character range (i.e. where the next
        parse should start).

        If the parse fails it shall return None.

        kwargs may be optionally passed to set starting values of properties
        "conversions", "trim_ws", and "tag".
        """
        self._parse_fn = parse_fn
        self._conversions = kwargs.get("conversions", ())
        self._trim_ws = kwargs.get("trim_ws", False)
        self._tag = kwargs.get("tag", None)

    __slots__ = ("_parse_fn", "_conversions", "_trim_ws", "_tag")

    def _copy_with(self, **kwargs):
        """
        Returns a copy of this Parser with modified settings.

        Any new conversion is added. Other settings, if provided, override the
        originals.
        """
        if self._conversions:
            new_convs = kwargs.get("conversions", ())
            kwargs["conversions"] = self._conversions + new_convs
        kwargs.setdefault("trim_ws", self._trim_ws)
        kwargs.setdefault("tag", self._tag)
        # Note: crucial that this returns a Parser (as opposed to type(self)),
        # so that modifying attributes will "finalize" instances of _ParserList
        # and make them no longer eligible for merging with other instances
        # (otherwise, the modified atrributes would incorrectly apply to those
        # too).
        return Parser(self._parse_fn, **kwargs)

    def conv(self, *fns):
        """
        Attaches conversion functions to be applied to the result (in order).

        Converting to None results in parse failure (see also: skip()).
        """
        if not fns: return self
        return self._copy_with(conversions=fns)

    def zipconv(self, *fns):
        """
        Attaches conversions that will be applied to elements of the result
        (first fn to result[0], second to result[1], and so on). Only makes
        sense if the result is a tuple or list.

        "None" fns indicate no-ops; it is ok to specify fewer functions than
        elements.

        This is mainly for convenience as it can be awkward to express such
        operations directly via conv().
        """
        if all(fn is None for fn in fns): return self
        def elem_converter(result):
            if isinstance(result, tuple):
                return tuple(elem_converter(list(result)))
            if isinstance(result, list):
                for (i, fn) in enumerate(fns):
                    if i == len(result): break
                    if fn is not None:
                        result[i] = fn(result[i])
                return result
            else:
                raise TypeError("zipconv only works for lists and tuples")
        return self._copy_with(conversions=(elem_converter,))

    def const(self, val):
        """Adds a conversion that replaces the result with a fixed value."""
        return self._copy_with(conversions=(lambda _: val,))

    def skip(self):
        """
        Adds a conversion that replaces the result with None without failing
        the parse.

        Note: this also removes the tag, if one exists.
        """
        return self._copy_with(conversions=(lambda _: self.__SKIP,), tag=None)

    def trim_ws(self, enable=True):
        """Enable to consume leading/trailing whitespace."""
        if self._trim_ws == enable: return self
        return self._copy_with(trim_ws=enable)

    def tag(self, tag):
        """
        Specifies a tag to attach to the final result.

        Then the result will be returned as a (tag, value) tuple (this may be
        particularly useful in match statements or for combining parse results
        into a dict).
        """
        if self._tag == tag: return self
        return self._copy_with(tag=tag)

    def __add__(self, other):
        """Provide the "+" (chaining) operation."""
        return _ParserChain(self, other)

    def __or__(self, other):
        """Provide the "|" (first-match) operation."""
        return _ParserFirstMatch(self, other)

    __SKIP = object()
    __WS_PATT = re.compile(r"\s*")

    def run(self, s: str, i: int):
        """
        Runs this parser on string s, consuming characters starting at i.

        Returns (result, end_of_consumed_range) or None.
        """
        if self._trim_ws:
            # The pattern accepts 0 chars so it should always match
            i = self.__WS_PATT.match(s, i).end()

        parse_ret = self._parse_fn(s, i)
        if parse_ret is None: return None

        result, new_i = parse_ret
        for fn in self._conversions:
            result = fn(result)
            if result is self.__SKIP:
                result = None
            elif result is None:
                return None
        if self._tag is not None:
            result = _Tagged(tag=self._tag, result=result)
        if self._trim_ws:
            new_i = self.__WS_PATT.match(s, new_i).end()
        return (result, new_i)

    def parse(self, s: str):
        """
        Attempts to parse the whole string s (all characters must be consumed).

        Returns the result or None.
        """
        parse_ret = self.run(s, 0)
        if parse_ret is None: return None
        if parse_ret[1] != len(s): return None
        return parse_ret[0]

class _Tagged(NamedTuple):
    """Represents tagged parse results."""
    tag: Any
    result: Any

def recursive(recipe_fn, arity=1):
    """
    Helper for producing Parsers with recursive definitions.

    The recipe_fn shall be given ParserRefs A, B, et al as parameters, and
    shall use them to define & return Parsers A, B, et al.

    recursive() will "close the loop" on those references to produce concrete
    instances of A, B, et al.

    The arity argument shall specify the number of arguments / return values
    for the recipe_fn (for arity > 1, recipe_fn should take separate
    arguments, and return a tuple).
    """
    class ParserRef(Parser):
        def __init__(self):
            super().__init__(self.run_ref)

        __slots__ = "_ref"

        def set_ref(self, p: Parser):
            self._ref = p
        def run_ref(self, s: str, i: int):
            return self._ref.run(s, i)

    if arity == 1:
        tbd = ParserRef()
        tbd.set_ref(actual := recipe_fn(tbd))
        return actual
    else:
        tbds = tuple(ParserRef() for _ in range(arity))
        actuals = recipe_fn(*tbds)
        for (tbd, actual) in zip(tbds, actuals):
            tbd.set_ref(actual)
        return actuals

def contextual(context_parser: Parser, recipe_fn):
    """
    Helper for defining a contextual Parser (whose behavior depends on what has
    been parsed before).

    context_parser is a Parser that will be run first and produces the context
    as result. If it fails then the overall contextual parse will fail.

    recipe_fn shall take that result as argument and return a Parser.

    The Parser returned by contextual() will parse the context, use the recipe
    to create a contextual parser, and then run that; the overall result will
    be the same as produced by the contextual parser (meaning the result of
    the context_parser is implicitly dropped, but note that the recipe may
    choose to include it in the result).
    """

    def parse_fn(s, i):
        context_ret = context_parser.run(s, i)
        if context_ret is None: return None

        context, ni = context_ret
        return recipe_fn(context).run(s, ni)
    return Parser(parse_fn)

@cache
def ex(z: str):
    """
    Creates a Parser consuming an exact string (also trims whitespace).

    The result is always None (like with "skip()").
    """
    def parse_fn(s, i):
        if not s.startswith(z, i): return None
        return (None, i + len(z))
    return Parser(parse_fn, trim_ws=True)

@cache
def regex(z: str):
    """
    Creates a Parser consuming text matching a regex (also trims whitespace).

    If the match had capturing groups, the result contains the captured values.
    In the case of named groups, the values are in a dict keyed by name.
    In the case of multiple groups, the values are in a tuple.
    In the case of a single group, the result is the single captured value.

    If there were no groups, the result is the entire matched text.
    """
    patt = re.compile(z)
    def parse_fn(s, i):
        match = patt.match(s, i)
        if not match: return None

        if match.groupdict():
            return (match.groupdict(), match.end())
        elif len(match.groups()) > 1:
            return (match.groups(), match.end())
        elif len(match.groups()) == 1:
            return (match.group(1), match.end())
        else:
            return (match.group(0), match.end())
    return Parser(parse_fn, trim_ws=True)

@cache
def chomp(n: int):
    """
    A Parser that consumes and returns the given number of characters.
    """
    def parse_fn(s, i):
        if not i + n <= len(s): return None
        return (s[i:i+n], i + n)
    return Parser(parse_fn)

def star(p: Parser, at_least=0, at_most=None):
    """
    Creates a Parser that repeats the given Parser as many times as it can
    within the specified bounds.

    Defaults to accepting any number of repeats (including 0).

    The result is a list of the constituent results, discarding None's and
    flattening sub-lists. Note: other types of iterables like tuples are not
    flattened.
    """
    def parse_fn(s, i):
        rep_count = 0
        results = []
        while (at_most is None) or (rep_count < at_most):
            parse_ret = p.run(s, i)
            if parse_ret is None: break

            rep_count += 1
            nxt_result, nxt_i = parse_ret
            _add_result(results, nxt_result)
            i = nxt_i

        if rep_count < at_least:
            return None
        else:
            return (results, i)
    return Parser(parse_fn)

def seplist(p: Parser, sep: str):
    """
    Creates a Parser for a list of separated items.

    Each item is parsed by the given parser. The list has to be non-empty. sep
    can be either a string or a parser to be used to recognize the separators.

    The result is a list of the item parse results (separator parse results
    are skipped).
    """
    if not (isinstance(sep, Parser) or isinstance(sep, str)):
        raise TypeError(f"{type(sep)} not supported here")
    if isinstance(sep, str): sep = ex(sep)

    return p + star(sep.skip() + p)

class _ParserList(Parser):
    """
    Wraps the generic logic used to implement combining parsers into lists,
    used for the "+" (chaining) and "|" (first-of) operations. The main reason
    this exists is to produce flattened lists when combining many parsers with
    the natural "a + b + c + d .. " syntax; such flattening is suitable for
    associative operations.

    Subclasses must implement do_parse that contains the logic to perform
    parsing based on the given parsers.
    """
    def __init__(self, *parsers):
        # accumulate the list, flattening inputs that match the current type
        flattened = []
        to_flatten = type(self)
        for p in parsers:
            if isinstance(p, to_flatten):
                flattened.extend(p._parsers)
            else:
                flattened.append(p)
        self._parsers = tuple(flattened)
        super().__init__(partial(self.do_parse, self._parsers))

    __slots__ = "_parsers"

    def do_parse(self, parsers, s, i): raise NotImplemented

class _ParserChain(_ParserList):
    """
    Creates a Parser that combines the given ones in series (all have to
    succeed).

    The result is a list of the constituent results, discarding None's and
    flattening sub-lists. Note: other types of iterables like tuples are not
    flattened.
    """
    def do_parse(self, parsers, s, i):
        results = []
        for p in parsers:
            parse_ret = p.run(s, i)
            if parse_ret is None: return None

            nxt_result, nxt_i = parse_ret
            _add_result(results, nxt_result)
            i = nxt_i
        return (results, i)

class _ParserFirstMatch(_ParserList):
    """
    Creates a Parser combining the given ones in parallel (just one has to
    succeed).

    The result is the result of the first succeeding Parser.
    """
    def do_parse(self, parsers, s, i):
        for p in parsers:
            parse_ret = p.run(s, i)
            if parse_ret is not None: return parse_ret
        return None

def _add_result(acc, sub_result):
    """Utility function used in chain / star to "flatten" and skip None's."""
    if isinstance(sub_result, list):
        acc.extend(filter(lambda z: z is not None, sub_result))
    elif sub_result is not None:
        acc.append(sub_result)
