# lexer.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-31
#
from typing import Optional, Union, cast, Callable
from enum import Enum, auto

__all__ = [
    "Lexer",
    "TokenType",
    "Token",
    "ParserError",
]

class TokenType(Enum):
    EMPTY = auto()
    ERROR = auto()

    INT = auto()
    FLOAT = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    COMMA = auto()

class ParserError(Enum):
    INVALID_CHAR_IN_NUMBER = auto()
    UNEXPECTED_CHARACTER = auto()

    MISSING_RIGHT_PARENTHESIS = auto()
    EXPRESSION_EXPECTED = auto()
    UNEXPECTED_TOKEN = auto()
    
    def __str__(self):
        match self:
            case self.INVALID_CHAR_IN_NUMBER:
                return "Invalid character in number"
            case self.UNEXPECTED_CHARACTER:
                return "Unexpected character"
            case self.MISSING_RIGHT_PARENTHESIS:
                return "Missing right parenthesis"
            case self.EXPRESSION_EXPECTED:
                return "Expression expected"
            case self.UNEXPECTED_TOKEN:
                return "Unexpected token"


class TextLocation:
    """User-oriented location in the text indexed by line and column."""

    line: int
    """Line location in the text or expression source."""
    column: int
    """Column location in the text or expression source."""

    def __init__(self):
        """Create an initial text location, which is at row 1 and column 1."""
        self.line = 1
        self.column = 1

    def advance(self, character: str):
        """Advance the location by one character. If the character is a newline
        then advance the row and reset the column to 1."""

        if character == '\n' or character == '\r':
            self.column = 1
            self.line += 1
        else:
            self.column += 1

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"

class Token:
    """Arithmetic expression token."""

    token_type: TokenType
    """Type of the token."""

    text: str
    """Textual content of the token."""

    location: TextLocation
    """Location of the token in the text."""

    error: Optional[ParserError]
    """Error associated with the token, if any was detected."""

    def __init__(self,
                 type_: TokenType,
                 text: str, location: TextLocation,
                 error: Optional[ParserError] = None):
        """Create a new token of given type, with given text at specified
        location."""

        self.token_type = type_
        self.text = text
        self.location = location
        self.error = error

    def __str__(self) -> str:
        return f"<{self.token_type}({self.location}):{self.text}>"

class ParserResult:
    """Result from parsing. An internal class that represents either a token
    type or a parser error."""

    _value: Union[TokenType, ParserError]

    def __init__(self, value: Union[TokenType, ParserError]):
        """Create a new parser result."""
        self._value = value

    @property
    def value(self) -> Optional[TokenType]:
        """Get a success value of the result or `None` if the result was an
        error."""
        if isinstance(value := self._value, TokenType):
            return cast(TokenType, value)
        else:
            return None

    @property
    def error(self) -> Optional[ParserError]:
        """Get an error value of the result or `None` if the result was a
        success."""
        if isinstance(value := self._value, ParserError):
            return cast(ParserError, value)
        else:
            return None

    def __str__(self) -> str:
        if (value := self.value):
            return f"ParserResult(value={value})"
        elif (error := self.error):
            return f"ParserResult(error={error})"
        else:
            return f"ParserResult(invalid={self._value})"

class Lexer:
    """Lexer of arithmetic expression."""

    source: str
    """Source string of the arithmetic expression to be parsed."""

    current_index: int
    """Current location of the lexer - index within the source string."""

    current_char: Optional[str]
    """Currently parsed character or `None` if the lexer is at the end."""

    location: TextLocation
    """Text location of the parser."""


    def __init__(self, source: str):
        """Create a new lexer parsing a source string."""

        self.source = source
        self.current_index = 0
        try:
            self.current_char = self.source[self.current_index]
        except IndexError:
            self.current_char = None
        self.location = TextLocation()

    @property
    def at_end(self) -> bool:
        """Flag whether the lexer is at end. `True` means that the lexer
        reached end of the string."""
        return self.current_index >= len(self.source)

    def advance(self):
        """Advance the lexer by one character, if it is not at the end."""
        if self.at_end:
            return

        self.current_index += 1

        try:
            self.current_char = self.source[self.current_index]
            self.location.advance(self.current_char)
        except IndexError:
            self.current_char = None

    def accept(self):
        """Accept current character unconditionally."""

        assert self.current_char is not None
        self.advance()

    def accept_char(self, character: str) -> bool:
        """Accept current character if it is equal to `character`."""
        if self.current_char == character:
            self.accept()
            return True
        else:
            return False

    def accept_whitespace(self) -> bool:
        """Accept current character if it is a whitespace."""
        if not (char := self.current_char):
            return False

        if char.isspace():
            self.accept()
            return True
        else:
            return False

    def accept_digit(self) -> bool:
        """Accept current character if it is a digit."""
        if not (char := self.current_char):
            return False

        if char.isnumeric():
            self.accept()
            return True
        else:
            return False

    def accept_letter(self) -> bool:
        """Accept current character if it is a letter."""
        if not (char := self.current_char):
            return False

        if char.isalpha():
            self.accept()
            return True
        else:
            return False

    def accept_pred(self, predicate: Callable[[str], bool]) -> bool:
        """Accept current character if it matches a predicate."""

        if not (char := self.current_char):
            return False

        if predicate(char):
            self.accept()
            return True
        else:
            return False

    # Lexer methods
    def accept_number(self) -> Optional[ParserResult]:
        """Parse and accept the next token if it is a number.

        Returns parse error if the number contains invalid character, such as a
        letter.
        """
        token_type: TokenType = TokenType.INT

        if not self.accept_digit():
            return None

        while self.accept_digit() or self.accept_char("_"):
            # Just accept it.
            pass

        if self.accept_char("."):
            if not self.accept_digit():
                return ParserResult(ParserError.INVALID_CHAR_IN_NUMBER)
            while self.accept_digit() or self.accept_char("_"):
                # Just accept it.
                pass
            token_type = TokenType.FLOAT

        if self.accept_char("e") or self.accept_char("E"):
            self.accept_char("-")

            if not self.accept_digit():
                return ParserResult(ParserError.INVALID_CHAR_IN_NUMBER)
            while self.accept_digit() or self.accept_char("_"):
                # Just accept it.
                pass
            token_type = TokenType.FLOAT

        if self.accept_letter():
            return ParserResult(ParserError.INVALID_CHAR_IN_NUMBER)
        else:
            return ParserResult(token_type)

    def accept_identifier(self) -> Optional[ParserResult]:
        """Parse and accept the next token if it is an identifier."""
        if not self.accept_letter() or self.accept_char("_"):
            return None

        while self.accept_letter() \
                or self.accept_number() \
                or self.accept_char("_"):
            # Just accept it.
            pass

        return ParserResult(TokenType.IDENTIFIER)

    def accept_operator(self) -> Optional[ParserResult]:
        """Accepts arithmetic operator."""

        if self.accept_char("-") \
                or self.accept_char("+") \
                or self.accept_char("*") \
                or self.accept_char("/") \
                or self.accept_char("%"):
            return ParserResult(TokenType.OPERATOR)
        else:
            return None
   
    def accept_punctuation(self) -> Optional[ParserResult]:
        """Accepts punctuation such as parenthesis or a comma."""
        if self.accept_char("("):
            return ParserResult(TokenType.LEFT_PAREN)
        elif self.accept_char(")"):
            return ParserResult(TokenType.RIGHT_PAREN)
        elif self.accept_char(","):
            return ParserResult(TokenType.COMMA)
        else:
            return None

    def accept_token(self) -> Optional[ParserResult]:
        """Accepts one of the valid arithmetic expression tokens: a number, an
        identifier, an operator or a punctuation character (parenthesis or a
        comma)."""
        return self.accept_number() \
                or self.accept_identifier() \
                or self.accept_operator() \
                or self.accept_punctuation()

    def accept_leading_trivia(self):
        # TODO: Implement trivia parsing
        # NOTE: This method should parse any characters that are not
        # significant for the token such as whitespace or comments, up to the
        # next token.
        while self.accept_whitespace():
            pass
    def accept_trailing_trivia(self):
        # TODO: Implement trivia parsing
        # NOTE: This method should parse any characters that are not
        # significant for the token such as whitespace or comments and new-line
        # from the currently parsed token.

        while self.accept_whitespace() \
                or self.accept_char('\n') \
                or self.accept_char('\r'):
            pass

    def next(self) -> Token:
        """Parse the next token at the lexer's position and return the parsed
        token."""

        start_index: int = self.current_index

        # TODO: Include trivia in the token
        self.accept_leading_trivia()

        if self.at_end:
            return Token(TokenType.EMPTY,
                         text=self.source[start_index:],
                         location=self.location)
        elif (result := self.accept_token()):
            end_index = self.current_index
            self.accept_trailing_trivia()

            if (token_type := result.value):
                return Token(token_type,
                             text=self.source[start_index:end_index],
                             location=self.location)
            elif (error := result.error):
                return Token(TokenType.ERROR,
                             text=self.source[start_index:end_index],
                             location=self.location,
                             error=error)
            else:
                raise RuntimeError(f"Unexpected result::result")
        else:
            self.accept()
            return Token(TokenType.ERROR,
                         text=self.source[start_index:self.current_index],
                         location=self.location,
                         error=ParserError.UNEXPECTED_CHARACTER)
