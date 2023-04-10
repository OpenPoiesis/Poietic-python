# parser.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-31
#

from typing import Optional, Union, cast
from enum import Enum, auto

from .lexer import Lexer, TokenType, Token, ParserError
from .expression import *

__all__ = [
    "ExpressionParser",
]

# https:#craftinginterpreters.com/parsing-expressions.html
# https:#stackoverflow.com/questions/2245962/writing-a-parser-like-flex-bison-that-is-usable-on-8-bit-embedded-systems/2336769#2336769

class SyntaxError(Exception):
    error: "ParserError"

    def __init__(self, error: "ParserError"):
        self.error = error


class ExpressionASTKind(Enum):
    # [INT]
    INT = auto()
    # [DOUBLE]
    DOUBLE = auto()
    # [IDENT]
    VARIABLE = auto()
    # [LPAREN, EXPR, RPAREN]
    PARENTHESIS = auto()

    # [OP, EXPR]
    UNARY = auto()

    # [HLS, OP, RHS]
    BINARY = auto()

    # [FN, LPAREN, ARG, ..., RPAREN]
    FUNCTION = auto()


ExpressionASTItem = Union[Token, "ExpressionAST"]

class ExpressionAST:
    # Note: We are being a bit lazy here with Python, since it does not have a
    # nice way to support algebraic sum data type
    #
    kind: ExpressionASTKind
    items: list[ExpressionASTItem]
    def __init__(self, kind: ExpressionASTKind, items: list[ExpressionASTItem]):
        self.kind = kind
        self.items = items

    def __str__(self) -> str:
        items = ", ".join(str(item) for item in self.items)
        return f"{self.kind}[{items}]"



class ExpressionParser:
    lexer: Lexer
    current_token: Optional[Token]
    
    
    def __init__(self, string: str):
        """
        Creates a new parser for an expression source string.
        """
        self.lexer = Lexer(string)
        self.advance()
    
    
    @property
    def at_end(self) -> bool:
        """
        True if the parser is at the end of the source.
        """
        if (token := self.current_token):
            return token.token_type == TokenType.EMPTY
        
        else:
            return True
        
    
    def advance(self):
        """
        Advance to the next token.
        """
        self.current_token = self.lexer.next()
    
    
    def accept(self, token_type: TokenType) -> Optional[Token]:
        """
        Accept a token a type ``type``.
        
        - Returns: A token if the token matches the expected type, ``nil`` if
            the token does not match the expected type.
        """
        if not (token := self.current_token):
            return None
        
        if token.token_type == token_type:
            self.advance()
            return token
        
        else:
            return None
        
    
    # ----------------------------------------------------------------
    
    def operator(self, op: str) -> Optional[Token]:
        if not (token := self.current_token):
            return None
        
        if token.token_type == TokenType.OPERATOR and token.text == op:
            self.advance()
            return token
        
        else:
            return None
    
    
    def identifier(self) -> Optional[Token]:
        if (token := self.accept(TokenType.IDENTIFIER)):
            return token
        
        else:
            return None
        
    

    def number(self) -> Optional[ExpressionAST]:
        if (token := self.accept(TokenType.INT)):
            return ExpressionAST(ExpressionASTKind.INT, [token])
        
        elif (token := self.accept(TokenType.FLOAT)):
            return ExpressionAST(ExpressionASTKind.DOUBLE, [token])
        
        else:
            return None
        
    # variable_call -> IDENTIFIER ["(" ARGUMENTS ")"]
    
    def variable_or_call(self) -> Optional[ExpressionAST]:
        if not(ident := self.identifier()):
            return None
        
        items: list[ExpressionASTItem] = []
        items.append(ident)
        
        # TODO: Preserve the paren tokens
        if (lpar := self.accept(TokenType.LEFT_PAREN)):
            items.append(lpar)

            while True:
                if (arg := self.expression()):
                    items.append(arg)
                
                if not (comma := self.accept(TokenType.COMMA)):
                    break
                
                items.append(comma)
            

            if not (rpar := self.accept(TokenType.RIGHT_PAREN)):
                raise SyntaxError(ParserError.MISSING_RIGHT_PARENTHESIS)
            
            items.append(rpar)
            
            return ExpressionAST(ExpressionASTKind.FUNCTION, items)
        
        else:
            # We got a variable
            return ExpressionAST(ExpressionASTKind.VARIABLE, items)
        
    
    
    # primary -> NUMBER | STRING | VARIABLE_OR_CALL | "(" expression ")" ;

    def primary(self) -> Optional[ExpressionAST]:
        # TODO: true, false, nil
        if (node := self.number()):
            return node
        
        elif (node := self.variable_or_call()):
            return node
        
        elif (lparen := self.accept(TokenType.LEFT_PAREN)):
            items: list[ExpressionASTItem] = []
            items.append(lparen)
            if (expr := self.expression()):
                items.append(expr)
                
                if not (rparen := self.accept(TokenType.RIGHT_PAREN)):
                    raise SyntaxError(ParserError.MISSING_RIGHT_PARENTHESIS)
                
                items.append(rparen)
                
                return ExpressionAST(ExpressionASTKind.PARENTHESIS, items)
        
        return None
    
    
    # unary -> "-" unary | primary ;
    #
    def unary(self) -> Optional[ExpressionAST]:
        # TODO: Add '!'
        if (op := self.operator("-")):
            if not(right := self.unary()):
                raise SyntaxError(ParserError.EXPRESSION_EXPECTED)
            
            return ExpressionAST(ExpressionASTKind.UNARY, [op, right])
        else:
            return self.primary()
        

    # factor -> unary ( ( "/" | "*" ) unary )* ;
    #

    def factor(self) -> Optional[ExpressionAST]:
        if not(left := self.unary()):
            return None

        while True:
            if not (op := (self.operator("*") \
                    or self.operator("/") \
                    or self.operator("%"))):
                break

            if not (right := self.unary()):
                raise SyntaxError(ParserError.EXPRESSION_EXPECTED)
            
            left = ExpressionAST(ExpressionASTKind.BINARY, [left, op, right])

        return left
    

    # term -> factor ( ( "-" | "+" ) factor )* ;
    #
    def term(self) -> Optional[ExpressionAST]:
        if not(left := self.factor()):
            return None
        
        while True:
            if not (op := (self.operator("+") \
                    or self.operator("-"))):
                break

            if not (right := self.factor()):
                raise SyntaxError(ParserError.EXPRESSION_EXPECTED)
            
            left = ExpressionAST(ExpressionASTKind.BINARY, [left, op, right])
        
        return left
    
    
    def expression(self) -> Optional[ExpressionAST]:
        return self.term()
    
    
    def make_unbound(self, ast: ExpressionAST) -> UnboundExpression:
        match ast.kind:
            case ExpressionASTKind.INT:
                ivalue: int = int(cast(Token, ast.items[0]).text) 
                return ValueExpressionNode(ivalue)

            case ExpressionASTKind.DOUBLE:
                fvalue: float = float(cast(Token, ast.items[0]).text) 
                return ValueExpressionNode(fvalue)

            case ExpressionASTKind.VARIABLE:
                var: str = cast(Token, ast.items[0]).text
                return VariableExpressionNode(var)

            case ExpressionASTKind.PARENTHESIS:
                expr: ExpressionAST = cast(ExpressionAST, ast.items[1])
                return self.make_unbound(expr)

            case ExpressionASTKind.UNARY:
                operator: str = cast(Token, ast.items[0]).text
                operand = self.make_unbound(cast(ExpressionAST, ast.items[1]))
                return UnaryExpressionNode(operator, operand)

            case ExpressionASTKind.BINARY:
                operator: str = cast(Token, ast.items[1]).text
                left = self.make_unbound(cast(ExpressionAST, ast.items[0]))
                right = self.make_unbound(cast(ExpressionAST, ast.items[2]))
                return BinaryExpressionNode(operator, left, right)

            case ExpressionASTKind.FUNCTION:
                func: str = cast(Token, ast.items[0]).text
                args: list[ExpressionAST] = []
                # Skip commas (lazy way)
                for item in cast(list[ExpressionAST], ast.items[2:-1]):
                    if isinstance(item, Token):
                        continue
                    args.append(item)

                unbound_args = list(self.make_unbound(arg) for arg in args)

                return FunctionExpressionNode(func, unbound_args)
            
    def parse(self) -> UnboundExpression:
        if not (expr := self.expression()):
            raise SyntaxError(ParserError.EXPRESSION_EXPECTED)
        
        
        if (token := self.current_token):
            if token.token_type != TokenType.EMPTY:
                # from pdb import set_trace; set_trace()
                raise SyntaxError(ParserError.UNEXPECTED_TOKEN)
        
        return self.make_unbound(expr)
