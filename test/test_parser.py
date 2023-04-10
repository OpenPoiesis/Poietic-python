import unittest

from holon.flows.expression.parser import Lexer, TokenType, ParserError
from holon.flows.expression.parser import ExpressionParser, SyntaxError
from holon.flows.expression import \
        ValueExpressionNode, \
        VariableExpressionNode, \
        BinaryExpressionNode, \
        UnaryExpressionNode, \
        FunctionExpressionNode

class TestLexer(unittest.TestCase):
    def test_Empty(self):
        lexer = Lexer("")
        
        self.assertTrue(lexer.at_end)
        self.assertEqual(lexer.next().token_type, TokenType.EMPTY)
        lexer.advance()
        self.assertTrue(lexer.at_end)
        self.assertEqual(lexer.next().token_type, TokenType.EMPTY)
    

    def test_Space(self):
        lexer = Lexer(" ")
        
        self.assertFalse(lexer.at_end)
        self.assertEqual(lexer.next().token_type, TokenType.EMPTY)
        self.assertTrue(lexer.at_end)
    
    def test_Unexpected(self):
        lexer = Lexer("$")
        token = lexer.next()

        self.assertEqual(token.token_type, TokenType.ERROR)
        self.assertEqual(token.error, ParserError.UNEXPECTED_CHARACTER)

        self.assertEqual(token.text, "$")
    
    def testInteger(self):
        lexer = Lexer("1234")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "1234")
    

    def test_ThousandsSeparator(self):
        lexer = Lexer("123_456_789")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "123_456_789")
    

    def test_MultipleIntegers(self):
        lexer = Lexer("1 22 333 ")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "1")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "22")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "333")
    

    def test_InvalidInteger(self):
        lexer = Lexer("1234x")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.ERROR)
        self.assertEqual(token.error, ParserError.INVALID_CHAR_IN_NUMBER)
        self.assertEqual(token.text, "1234x")
    

    def test_Float(self):
        lexer = Lexer("10.20 10e20 10.20e30 10.20e-30")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.FLOAT)
        self.assertEqual(token.text, "10.20")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.FLOAT)
        self.assertEqual(token.text, "10e20")
        
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.FLOAT)
        self.assertEqual(token.text, "10.20e30")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.FLOAT)
        self.assertEqual(token.text, "10.20e-30")
    


    def test_Identifier(self):
        lexer = Lexer("an_identifier_1")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.IDENTIFIER)
        self.assertEqual(token.text, "an_identifier_1")
    

    def test_Punctuation(self):
        lexer = Lexer("( , )")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.LEFT_PAREN)
        self.assertEqual(token.text, "(")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.COMMA)
        self.assertEqual(token.text, ",")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.RIGHT_PAREN)
        self.assertEqual(token.text, ")")
    
    
    def testOperator(self):
        lexer = Lexer("+ - * / %")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "+")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "-")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "*")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "/")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "%")
    

    def test_MinusOperator(self):
        lexer = Lexer("1-2")
        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "1")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.OPERATOR)
        self.assertEqual(token.text, "-")

        token = lexer.next()
        self.assertEqual(token.token_type, TokenType.INT)
        self.assertEqual(token.text, "2")

        # TODO: Test trivia.

class TestParser(unittest.TestCase):
    def testEmpty(self):
        parser = ExpressionParser("")
        with self.assertRaises(SyntaxError):
            parser.parse()


    def tesBinary(self):
        expr =BinaryExpressionNode("+",
                                   VariableExpressionNode("a"),
                                    ValueExpressionNode(1))

        e1 = ExpressionParser("a + 1").parse()
        e2 = ExpressionParser("a+1").parse()

        self.assertEqual(e1, expr)
        self.assertEqual(e2, expr)
    
    
    def testFactorAndTermRepetition(self):
        expr =BinaryExpressionNode(
            "*",
            BinaryExpressionNode(
                "*",
                VariableExpressionNode("a"),
                VariableExpressionNode("b")
            ), 
            VariableExpressionNode("c")
        )
        self.assertEqual(ExpressionParser("a * b * c").parse(), expr)

        expr2 =BinaryExpressionNode( \
            "+",
            BinaryExpressionNode( \
                "+",
                VariableExpressionNode("a"),
                VariableExpressionNode("b")
            ), \
            VariableExpressionNode("c")
        )
        self.assertEqual(ExpressionParser("a + b + c").parse(), expr2)
    
    
    def testPrecedence(self):
        expr =BinaryExpressionNode(
            "+",
            VariableExpressionNode("a"),
            BinaryExpressionNode(
                "*",
                VariableExpressionNode("b"),
                VariableExpressionNode("c")
            )
        )
        self.assertEqual(ExpressionParser("a + b * c").parse(), expr)
        self.assertEqual(ExpressionParser("a + (b * c)").parse(), expr)

        expr2 =BinaryExpressionNode(
            "+",
            BinaryExpressionNode(
                "*",
                VariableExpressionNode("a"),
                VariableExpressionNode("b")
            ),
            VariableExpressionNode("c")
        )
        self.assertEqual(ExpressionParser("a * b + c").parse(), expr2)
        self.assertEqual(ExpressionParser("(a * b) + c").parse(), expr2)
    
    
    def testUnary(self):
        expr = UnaryExpressionNode("-", VariableExpressionNode("x"))
        self.assertEqual(ExpressionParser("-x").parse(), expr)

        expr2 = BinaryExpressionNode(
            "-",
            VariableExpressionNode("x"),
            UnaryExpressionNode(
                "-",
                VariableExpressionNode("y")
            )
        )
        self.assertEqual(ExpressionParser("x - -y").parse(), expr2)
    
    def testFunction(self):
        expr = FunctionExpressionNode("fun", [VariableExpressionNode("x")])
        self.assertEqual(ExpressionParser("fun(x)").parse(), expr)

        expr2 = FunctionExpressionNode("fun", [VariableExpressionNode("x"),
                                               VariableExpressionNode("y")])
        self.assertEqual(ExpressionParser("fun(x,y)").parse(), expr2)

    
    
    def testErrorMissingParenthesis(self):
        parser = ExpressionParser("(")
        with self.assertRaisesRegex(SyntaxError, "Expression expected"):
            parser.parse()
        
    
    def testErrorMissingParenthesisFunctionCall(self):
        parser = ExpressionParser("func(1,2,3")
        with self.assertRaisesRegex(SyntaxError, "Missing right parenthesis"):
            parser.parse()
    
    def testUnaryExpressionExpected(self):
        parser = ExpressionParser("1 + -")
        with self.assertRaisesRegex(SyntaxError, "Expression expected"):
            parser.parse()
    

        parser2 = ExpressionParser("-")
        with self.assertRaisesRegex(SyntaxError, "Expression expected"):
            parser2.parse()
    
    
    def testFactorUnaryExpressionExpected(self):
        parser = ExpressionParser("1 *")
        with self.assertRaisesRegex(SyntaxError, "Expression expected"):
            parser.parse()
    
    def testTermExpressionExpected(self):
        parser = ExpressionParser("1 +")
        with self.assertRaisesRegex(SyntaxError, "Expression expected"):
            parser.parse()
    
    def testUnexpectedToken(self):
        parser = ExpressionParser("1 1")
        with self.assertRaisesRegex(SyntaxError, "Unexpected token"):
            parser.parse()
    
    
    # TODO: This works when we have trivia parsing

    # def testFullText(self):
    #     text = "-( a  + b ) * f( c, d, 100_000\n)"
    #     parser = ExpressionParser(text)
    #     if not(result := parser.expression()):
    #         self.fail("Expected valid expression to be parsed")
    #     
    #     self.assertEqual(text, result.fullText)

