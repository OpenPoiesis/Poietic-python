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
    line: int
    column: int

    def __init__(self):
        self.line = 1
        self.column = 1

    def advance(self, character: str):
        if character == '\n' or character == '\r':
            self.column = 1
            self.line += 1
        else:
            self.column += 1

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"

class Token:
    token_type: TokenType
    text: str
    location: TextLocation
    error: Optional[ParserError]

    def __init__(self,
                 type_: TokenType,
                 text: str, location: TextLocation,
                 error: Optional[ParserError] = None):
        self.token_type = type_
        self.text = text
        self.location = location
        self.error = error

    def __str__(self) -> str:
        return f"<{self.token_type}({self.location}):{self.text}>"

class ParserResult:
    _value: Union[TokenType, ParserError]

    def __init__(self, value: Union[TokenType, ParserError]):
        self._value = value

    @property
    def value(self) -> Optional[TokenType]:
        if isinstance(value := self._value, TokenType):
            return cast(TokenType, value)
        else:
            return None

    @property
    def error(self) -> Optional[ParserError]:
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
    source: str
    current_index: int
    current_char: Optional[str]
    location: TextLocation


    def __init__(self, source: str):
        self.source = source
        self.current_index = 0
        try:
            self.current_char = self.source[self.current_index]
        except IndexError:
            self.current_char = None
        self.location = TextLocation()

    @property
    def at_end(self) -> bool:
        return self.current_index >= len(self.source)

    def advance(self):
        if self.at_end:
            return

        self.current_index += 1

        try:
            self.current_char = self.source[self.current_index]
            self.location.advance(self.current_char)
        except IndexError:
            self.current_char = None

    def accept(self):
        assert self.current_char is not None
        self.advance()

    def accept_char(self, character: str) -> bool:
        if self.current_char == character:
            self.accept()
            return True
        else:
            return False

    def accept_whitespace(self) -> bool:
        if not (char := self.current_char):
            return False

        if char.isspace():
            self.accept()
            return True
        else:
            return False

    def accept_digit(self) -> bool:
        if not (char := self.current_char):
            return False

        if char.isnumeric():
            self.accept()
            return True
        else:
            return False

    def accept_letter(self) -> bool:
        if not (char := self.current_char):
            return False

        if char.isalpha():
            self.accept()
            return True
        else:
            return False

    def accept_pred(self, predicate: Callable[[str], bool]) -> bool:
        if not (char := self.current_char):
            return False

        if predicate(char):
            self.accept()
            return True
        else:
            return False

    # Lexer methods
    def accept_number(self) -> Optional[ParserResult]:
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
        if not self.accept_letter() or self.accept_char("_"):
            return None

        while self.accept_letter() \
                or self.accept_number() \
                or self.accept_char("_"):
            # Just accept it.
            pass

        return ParserResult(TokenType.IDENTIFIER)

    def accept_operator(self) -> Optional[ParserResult]:
        if self.accept_char("-") \
                or self.accept_char("+") \
                or self.accept_char("*") \
                or self.accept_char("/") \
                or self.accept_char("%"):
            return ParserResult(TokenType.OPERATOR)
        else:
            return None
   
    def accept_punctuation(self) -> Optional[ParserResult]:
        if self.accept_char("("):
            return ParserResult(TokenType.LEFT_PAREN)
        elif self.accept_char(")"):
            return ParserResult(TokenType.RIGHT_PAREN)
        elif self.accept_char(","):
            return ParserResult(TokenType.COMMA)
        else:
            return None

    def accept_token(self) -> Optional[ParserResult]:
        return self.accept_number() \
                or self.accept_identifier() \
                or self.accept_operator() \
                or self.accept_punctuation()

    def accept_leading_trivia(self):
        while self.accept_whitespace():
            pass
    def accept_trailing_trivia(self):
        while self.accept_whitespace() \
                or self.accept_char('\n') \
                or self.accept_char('\r'):
            pass

    def next(self) -> Token:
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


